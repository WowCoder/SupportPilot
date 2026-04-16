"""
Vector Search Tool for Agentic RAG system.

Supports Small-to-Big retrieval strategy:
- Search in small chunks (ChromaDB) for precision
- Return corresponding large chunks (ParentDocumentStore) for context
"""
import logging
from typing import Any, Dict, List, Optional

from rag.core.tool import BaseTool, ToolResult
from rag.core.config import get_config
from rag.core.observability import timed_tool
from rag.parent_store import parent_store

logger = logging.getLogger(__name__)


class VectorSearchTool(BaseTool):
    """
    Vector similarity search tool.

    Features:
    - Standard retrieval: return chunks directly from ChromaDB
    - Small-to-Big retrieval: search small chunks, return large parent chunks
    """

    name = "vector_search"
    description = "Search documents using vector similarity. Supports Small-to-Big retrieval for complete context."

    def __init__(self, collection=None):
        """
        Initialize the vector search tool.

        Args:
            collection: ChromaDB collection (lazy-loaded if not provided)
        """
        self.config = get_config()
        self._collection = collection
        self._lazy_load_collection = collection is None

    def _get_collection(self):
        """Lazy-load ChromaDB collection."""
        if self._collection is None and self._lazy_load_collection:
            try:
                import chromadb
                client = chromadb.PersistentClient(path="./chroma_db")
                self._collection = client.get_collection("knowledge")
            except Exception as e:
                logger.error(f'Failed to load ChromaDB collection: {e}')
                raise
        return self._collection

    @timed_tool
    def execute(self,
                query: str,
                k: int = None,
                similarity_threshold: float = None,
                use_small_to_big: bool = None,
                **kwargs) -> ToolResult:
        """
        Execute vector search.

        Args:
            query: Search query string
            k: Number of results to return (default from config)
            similarity_threshold: Minimum similarity score (default from config)
            use_small_to_big: Use Small-to-Big retrieval (default from config)

        Returns:
            ToolResult with list of search results
        """
        try:
            # Load config defaults
            k = k or self.config.get('tools.vector.k', 5)
            similarity_threshold = similarity_threshold or self.config.get('tools.vector.similarity_threshold', 0.25)
            use_small_to_big = use_small_to_big if use_small_to_big is not None else self.config.get('tools.vector.use_small_to_big', True)

            collection = self._get_collection()
            if collection is None:
                return ToolResult(success=False, error="ChromaDB collection not available")

            # Query ChromaDB
            results = collection.query(
                query_texts=[query],
                n_results=k * 3 if use_small_to_big else k,  # Get more candidates for Small-to-Big
                include=["documents", "distances", "metadatas"]
            )

            if not results.get('documents') or not results['documents'][0]:
                return ToolResult(success=True, data=[])

            # Process results
            retrieved = []
            seen_parent_ids = set()

            for doc, distance, meta in zip(
                results['documents'][0],
                results['distances'][0],
                results['metadatas'][0] or [{}] * len(results['documents'][0])
            ):
                similarity = 1 - distance
                if similarity < similarity_threshold:
                    continue

                if use_small_to_big:
                    # Small-to-Big mode: get parent chunk
                    parent_id = meta.get('parent_id') if meta else None
                    if parent_id and parent_id not in seen_parent_ids:
                        seen_parent_ids.add(parent_id)
                        parent_doc = parent_store.get(parent_id)
                        if parent_doc:
                            retrieved.append({
                                'content': parent_doc['content'],  # Large chunk
                                'similarity': float(similarity),
                                'source': parent_doc['metadata'].get('source', 'unknown'),
                                'parent_id': parent_id,
                                'child_content': doc  # Small chunk for reference
                            })
                else:
                    # Standard mode: return the chunk directly
                    retrieved.append({
                        'content': doc,
                        'similarity': float(similarity),
                        'source': meta.get('source', 'unknown') if meta else 'unknown'
                    })

            # Sort by similarity and limit to k
            retrieved.sort(key=lambda x: x['similarity'], reverse=True)
            retrieved = retrieved[:k]

            logger.debug(f'Vector search returned {len(retrieved)} results')
            return ToolResult(success=True, data=retrieved)

        except Exception as e:
            logger.error(f'Vector search failed: {e}', exc_info=True)
            return ToolResult(success=False, error=str(e))


# Global instance
vector_search = VectorSearchTool()
