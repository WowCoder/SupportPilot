"""Indexing stage for the RAG offline pipeline.

Handles ChromaDB indexing, deduplication via content hashing,
and parent-document storage for small-to-big retrieval.
"""

import hashlib
import logging
import os

from rag.offline.pipeline_config import IndexingConfig

logger = logging.getLogger(__name__)


class IndexingStage:
    """Index chunks into ChromaDB with deduplication and small-to-big support.

    Flow:
    1. Load existing content hashes from ChromaDB metadata (dedup baseline)
    2. Filter incoming chunks against known hashes (skip duplicates)
    3. For small-to-big: store parent chunks in ParentDocumentStore first
    4. Add child / regular chunks to the ChromaDB collection
    5. Track newly added hashes in-memory for subsequent calls
    """

    def __init__(self, config: IndexingConfig, collection, parent_store):
        self.config = config
        self.collection = collection        # ChromaDB Collection
        self.parent_store = parent_store    # ParentDocumentStore instance
        self._hashes: set = set()

    # ------------------------------------------------------------------
    # Hash management
    # ------------------------------------------------------------------

    def load_hashes(self):
        """Load existing content hashes from ChromaDB metadata for dedup."""
        try:
            existing = self.collection.get(include=["metadatas"])
            for meta in existing.get("metadatas", []):
                if meta and "content_hash" in meta:
                    self._hashes.add(meta["content_hash"])
            logger.info(f"Loaded {len(self._hashes)} document hashes from Chroma")
        except Exception as e:
            logger.error(f"Error loading document hashes: {e}", exc_info=True)

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute MD5 hash for deduplication."""
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Main indexing entry-point
    # ------------------------------------------------------------------

    def __call__(
        self,
        chunks: list,
        file_path: str,
        use_small_to_big: bool = False,
        small_to_big_data: dict = None,
    ) -> dict:
        """Index chunks into ChromaDB.

        Parameters
        ----------
        chunks : list
            List of Document-like objects, each with ``.page_content`` and
            ``.metadata`` (dict, may contain ``parent_id``).
        file_path : str
            Absolute path of the source file (used for metadata).
        use_small_to_big : bool
            Whether this batch uses the small-to-big strategy.
        small_to_big_data : dict or None
            Only used when ``use_small_to_big`` is True.  Expected keys:
            - ``parent_chunks``: list of ``{id, content, metadata}`` dicts
            - ``child_chunks``:  list of ``{id, content, metadata}`` dicts
              whose ``id`` values are used as ChromaDB document IDs.

        Returns
        -------
        dict with keys:
            success         : bool
            chunks_added    : int
            chunks_total    : int
            is_duplicate    : bool
        """
        filename = os.path.basename(file_path)
        chunks_total = len(chunks)
        new_chunks = 0

        documents_to_add = []
        ids_to_add = []
        metadatas_to_add = []

        # --- small-to-big: persist parent chunks first -----------------
        parent_chunks_count = 0
        child_chunks_count = 0

        if use_small_to_big and small_to_big_data:
            parent_chunks = small_to_big_data.get("parent_chunks", [])
            child_chunks = small_to_big_data.get("child_chunks", [])
            parent_chunks_count = len(parent_chunks)
            child_chunks_count = len(child_chunks)

            for parent in parent_chunks:
                self.parent_store.put(
                    doc_id=parent["id"],
                    content=parent["content"],
                    metadata=parent["metadata"],
                )
            logger.info(
                f"Stored {len(parent_chunks)} parent chunks to ParentDocumentStore"
            )

        # --- dedup loop -------------------------------------------------
        for i, chunk in enumerate(chunks):
            content = chunk.page_content
            content_hash = self.compute_hash(content)

            if content_hash not in self._hashes:
                self._hashes.add(content_hash)
                documents_to_add.append(content)

                # Use pre-generated ID for small-to-big children,
                # otherwise generate a deterministic one.
                if use_small_to_big:
                    doc_id = child_chunks[i]["id"]
                else:
                    doc_id = f"{filename}_{len(self._hashes)}"

                ids_to_add.append(doc_id)

                metadata = {
                    "source": filename,
                    "filepath": file_path,
                    "content_hash": content_hash,
                    "page": chunk.metadata.get("page", 0)
                    if hasattr(chunk, "metadata")
                    else 0,
                }

                # Small-to-Big: attach parent_id to child metadata
                if use_small_to_big and hasattr(chunk, "metadata"):
                    parent_id = chunk.metadata.get("parent_id")
                    if parent_id:
                        metadata["parent_id"] = parent_id

                metadatas_to_add.append(metadata)
                new_chunks += 1

        # --- bulk-add to ChromaDB --------------------------------------
        if new_chunks > 0 and documents_to_add:
            logger.info(f"Adding {new_chunks} chunks to Chroma collection")
            logger.info(f"IDs to add: {ids_to_add[:3]}...")
            try:
                self.collection.add(
                    documents=documents_to_add,
                    ids=ids_to_add,
                    metadatas=metadatas_to_add,
                )
                logger.info(f"Added {new_chunks} new chunks from {file_path} to Chroma")

                verify_count = self.collection.count()
                logger.info(f"ChromaDB count after add: {verify_count}")
            except Exception as e:
                logger.error(f"Failed to add to Chroma: {e}", exc_info=True)
                return {
                    "success": False,
                    "chunks_added": 0,
                    "error": f"Chroma add failed: {str(e)}",
                }
        else:
            logger.info(
                f"No new chunks added from {file_path} "
                f"(possibly duplicate or no chunks)"
            )
            logger.info(f"new_chunks={new_chunks}, documents_to_add={len(documents_to_add)}")

        return {
            "success": True,
            "chunks_added": new_chunks,
            "chunks_total": chunks_total,
            "is_duplicate": new_chunks == 0 and chunks_total > 0,
            "parent_chunks": parent_chunks_count,
            "child_chunks": child_chunks_count,
        }

    # ------------------------------------------------------------------
    # Deletion helpers
    # ------------------------------------------------------------------

    def delete_by_source(self, filename: str) -> bool:
        """Delete all chunks from a given source file.

        Removes entries from both ChromaDB and the ParentDocumentStore,
        and purges their content hashes from the in-memory dedup set.

        Returns
        -------
        bool
            True if any documents were deleted, False otherwise.
        """
        try:
            existing = self.collection.get(
                where={"source": filename},
                include=["metadatas"],
            )

            if existing and existing.get("ids"):
                self.collection.delete(ids=existing["ids"])
                for meta in existing.get("metadatas", []):
                    if meta and "content_hash" in meta:
                        self._hashes.discard(meta["content_hash"])

                self.parent_store.delete_by_source(filename)
                logger.info(f"Deleted documents from source: {filename}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error deleting documents: {e}", exc_info=True)
            return False
