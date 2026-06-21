"""Chunking stage for RAG offline pipeline.

Extracts chunking logic from ``rag/offline/pipeline.py`` into a self-contained
stage with 4 strategies:

- **sentence** — sentence-boundary-aware splitting (handles Chinese + English)
- **semantic** — SemanticChunker from langchain_experimental (requires embedding_fn)
- **recursive** — RecursiveCharacterTextSplitter (traditional fixed-size, fastest)
- **small_to_big** — parent-child document pairs for Small-to-Big retrieval
- **auto** — auto-detect best strategy from document features

Each output chunk is a Document-like object with ``page_content`` and
``metadata`` attributes.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.offline.pipeline_config import ChunkingConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ChunkResult:
    """Result of a chunking operation returned by ``ChunkingStage.__call__``."""

    chunks: list = field(default_factory=list)  # list of Document-like objects
    total: int = 0
    strategy_used: str = ""
    parent_chunks: list = field(default_factory=list)
    child_chunks: list = field(default_factory=list)
    mapping: dict = field(default_factory=dict)  # child_id -> parent_id


# ---------------------------------------------------------------------------
# ChunkingStage
# ---------------------------------------------------------------------------


class ChunkingStage:
    """Apply a configurable chunking strategy to a list of documents.

    Parameters
    ----------
    config : ChunkingConfig
        Configuration dataclass controlling chunk sizes, strategy, thresholds.
    embedding_fn : object or None
        Embedding object that implements ``embed_documents`` / ``embed_query``
        (e.g. ``CustomEmbeddingFunction``). Required for ``semantic`` strategy;
        otherwise unused.
    """

    def __init__(
        self,
        config: ChunkingConfig,
        embedding_fn: Optional[Any] = None,
    ) -> None:
        self.config = config
        self._embedding_fn = embedding_fn  # for semantic chunking

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def __call__(
        self,
        documents: list,
        strategy: Optional[str] = None,
    ) -> ChunkResult:
        """Apply chunking and return a ``ChunkResult``.

        Parameters
        ----------
        documents : list
            List of Document-like objects with ``page_content`` and ``metadata``.
        strategy : str or None
            One of ``"auto"``, ``"sentence"``, ``"semantic"``, ``"recursive"``,
            ``"small_to_big"``.  If ``None``, falls back to
            ``self.config.strategy`` (default ``"auto"``).
        """
        strategy = strategy or self.config.strategy
        if strategy == "auto":
            strategy = self._detect_strategy(documents)

        if strategy == "small_to_big":
            result_dict = self._do_small_to_big(documents)
            return ChunkResult(
                chunks=result_dict["chunks"],
                total=len(result_dict["chunks"]),
                strategy_used=strategy,
                parent_chunks=result_dict["parent_chunks"],
                child_chunks=result_dict["child_chunks"],
                mapping=result_dict["mapping"],
            )
        elif strategy == "semantic":
            chunks = self._do_semantic(documents)
        elif strategy == "sentence":
            chunks = self._do_sentence(documents)
        else:
            # "recursive" (default fallback)
            chunks = self._do_recursive(documents)

        return ChunkResult(
            chunks=chunks,
            total=len(chunks),
            strategy_used=strategy,
        )

    def create_parent_child_chunks(
        self,
        documents: list,
        parent_size: Optional[int] = None,
        child_size: Optional[int] = None,
    ) -> dict:
        """Public access to Small-to-Big chunking (backward compat).

        Returns the same dict shape as the original
        ``RAGUtils._create_parent_child_chunks`` for ``faq_vector_sync``
        compatibility.
        """
        return self._do_small_to_big(documents, parent_size, child_size)

    # ------------------------------------------------------------------
    # Auto-detection
    # ------------------------------------------------------------------

    def _detect_strategy(self, documents: list) -> str:
        """Auto-select best chunking strategy based on document features.

        Decision tree
        ------------
        1. Average document length < 500 chars → ``small_to_big``.
        2. Has clear heading structure          → ``semantic``.
        3. Chinese character ratio > 80%        → ``sentence``.
        4. Otherwise                            → ``recursive``.
        """
        if not documents:
            return "recursive"

        total_len = sum(len(d.page_content) for d in documents)
        avg_len = total_len / len(documents)

        if avg_len < 500:
            return "small_to_big"

        if self._detect_headings(documents):
            return "semantic"

        if self._chinese_ratio(documents) > 0.8:
            return "sentence"

        return "recursive"

    def _chinese_ratio(self, documents: list) -> float:
        """Calculate ratio of CJK Unified Ideographs in the document collection."""
        total_chars = 0
        chinese_chars = 0
        for doc in documents:
            text = doc.page_content
            total_chars += len(text)
            chinese_chars += len(re.findall(r"[一-鿿]", text))
        if total_chars == 0:
            return 0.0
        return chinese_chars / total_chars

    def _detect_headings(self, documents: list) -> bool:
        """Check if documents have heading structure.

        Matched patterns
        ----------------
        - Markdown headings (``#`` … ``######``)
        - Chinese chapter markers (第X章, 第X节, 第X篇)
        - Numbered sections (``1.``, ``1、``, ``(1)``)
        - Chinese-numbered sections (``一.``, ``一、``)
        - Letter-numbered sections (``A.``)
        """
        heading_pattern = re.compile(
            r"^(#{1,6}\s"
            r"|第[一二三四五六七八九十百千万\d]+[章节部篇]"
            r"|\d+[\.\、\)]\s*"
            r"|\(\d+\)\s*"
            r"|[一二三四五六七八九十]+[\.\、\)]\s*"
            r"|[A-Z]\.\s+)"
        )
        heading_count = 0
        for doc in documents:
            for line in doc.page_content.split("\n"):
                line = line.strip()
                if heading_pattern.match(line):
                    heading_count += 1
                    if heading_count >= 3:
                        return True
        return False

    # ------------------------------------------------------------------
    # Strategy: sentence
    # ------------------------------------------------------------------

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences (supports Chinese and English).

        Chinese delimiters: ``。！？；``
        English delimiters: ``. ! ?``

        Newlines are also treated as boundaries for structured text.
        """
        pattern = r"(?<=[。！？；.!?\n])\s*"
        sentences = re.split(pattern, text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _create_chunk(content: str, metadata: dict) -> Any:
        """Create a Document-like object with ``page_content`` and ``metadata``.

        Uses the same ad-hoc object shape as the original ``RAGUtils`` so that
        downstream code (quality filter, ChromaDB indexing) sees the same
        interface without requiring langchain's ``Document``.
        """
        return type("obj", (object,), {
            "page_content": content,
            "metadata": metadata,
        })()

    def _do_sentence(
        self,
        documents: list,
        max_chunk_size: Optional[int] = None,
    ) -> list:
        """Sentence-level chunking (fallback strategy).

        Splits documents into sentences and merges them into chunks while
        respecting sentence boundaries.  Never splits mid-sentence.
        """
        max_chunk_size = max_chunk_size or self.config.chunk_size
        chunks = []
        for doc in documents:
            sentences = self._split_sentences(doc.page_content)
            current_chunk = ""
            current_sentences: List[str] = []

            for sent in sentences:
                # Single oversized sentence => its own chunk
                if len(sent) > max_chunk_size:
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, doc.metadata))
                        current_chunk = ""
                        current_sentences = []
                    chunks.append(self._create_chunk(sent, doc.metadata))
                    continue

                test_chunk = (
                    sent
                    if not current_chunk
                    else current_chunk + " " + sent
                )
                if len(test_chunk) <= max_chunk_size:
                    current_chunk = test_chunk
                    current_sentences.append(sent)
                else:
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, doc.metadata))
                    current_chunk = sent
                    current_sentences = [sent]

            if current_chunk:
                chunks.append(self._create_chunk(current_chunk, doc.metadata))

        logger.info("Sentence chunking produced %d chunks", len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # Strategy: semantic
    # ------------------------------------------------------------------

    def _create_semantic_splitter(
        self,
        embeddings: Optional[Any] = None,
        threshold: Optional[float] = None,
    ) -> SemanticChunker:
        """Create a ``SemanticChunker`` based on embedding similarity.

        Parameters
        ----------
        embeddings : object or None
            Embedding object with ``embed_documents`` / ``embed_query``.
            Defaults to ``self._embedding_fn``.
        threshold : float or None
            Breakpoint threshold (0.1–0.9).  Lower = more splits.
            Defaults to ``self.config.semantic_threshold``.

        Raises
        ------
        ValueError
            If neither ``embeddings`` nor ``self._embedding_fn`` is available.
        """
        threshold = (
            threshold if threshold is not None else self.config.semantic_threshold
        )
        if embeddings is None:
            if self._embedding_fn is None:
                raise ValueError("Embeddings not available for semantic chunking")
            embeddings = self._embedding_fn

        logger.info("Creating SemanticChunker with threshold=%s", threshold)

        return SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=threshold,
            min_chunk_size=50,
        )

    def _do_semantic(
        self,
        documents: list,
        threshold: Optional[float] = None,
    ) -> list:
        """Semantic chunking based on sentence-embedding similarity.

        Uses ``SemanticChunker`` to split documents at semantic boundaries
        where sentence similarity drops below *threshold*.

        Falls back to sentence chunking on failure (e.g. missing embeddings
        or langchain_experimental import error).
        """
        threshold = (
            threshold if threshold is not None else self.config.semantic_threshold
        )
        try:
            splitter = self._create_semantic_splitter(threshold=threshold)
            chunks = splitter.split_documents(documents)
            logger.info(
                "Semantic chunking produced %d chunks with threshold=%s",
                len(chunks),
                threshold,
            )
            return chunks
        except Exception as exc:
            logger.warning(
                "Semantic chunking failed, falling back to sentence splitter: %s",
                exc,
            )
            return self._do_sentence(documents)

    # ------------------------------------------------------------------
    # Strategy: recursive (fixed-size)
    # ------------------------------------------------------------------

    def _do_recursive(self, documents: list) -> list:
        """Traditional fixed-size recursive chunking (fastest)."""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        logger.info("Recursive chunking produced %d chunks", len(chunks))
        return chunks

    # ------------------------------------------------------------------
    # Strategy: Small-to-Big (parent-child)
    # ------------------------------------------------------------------

    def _do_small_to_big(
        self,
        documents: list,
        parent_size: Optional[int] = None,
        child_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Parent-child document pairs for Small-to-Big retrieval strategy.

        Creates two levels of chunks:

        * **parent** (large) — stored in ``ParentDocumentStore``, returned to
          the user as full context.
        * **child** (small) — indexed in ChromaDB for precise retrieval.
          Each child carries a ``parent_id`` linking back to its parent.

        Returns a dict with the same shape as the original
        ``RAGUtils._create_parent_child_chunks``::

            {
                "chunks": [Document-like, ...],        # child chunks for indexing
                "parent_chunks": [dict, ...],
                "child_chunks": [dict, ...],
                "mapping": {child_id: parent_id, ...},
            }
        """
        parent_size = parent_size or self.config.parent_size
        child_size = child_size or self.config.child_size
        min_chars = self.config.min_chunk_chars

        parent_chunks: list = []
        child_chunks: list = []
        mapping: dict = {}

        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_size,
            chunk_overlap=min(200, parent_size // 10),  # 10% overlap
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_size,
            chunk_overlap=min(50, child_size // 8),  # ~12.5% overlap
            length_function=len,
            separators=["\n", ". ", " ", ""],
        )

        for doc_idx, document in enumerate(documents):
            source = document.metadata.get("source", "unknown")
            page = document.metadata.get("page", 0)

            parent_docs = parent_splitter.split_documents([document])

            for parent_idx, parent_doc in enumerate(parent_docs):
                parent_id = (
                    f"parent_{doc_idx}_{parent_idx}_{uuid.uuid4().hex[:8]}"
                )

                parent_chunks.append({
                    "id": parent_id,
                    "content": parent_doc.page_content,
                    "metadata": {
                        **document.metadata,
                        "source": source,
                        "page": page,
                        "parent_idx": parent_idx,
                    },
                })

                child_docs = child_splitter.split_documents([parent_doc])

                for child_idx, child_doc in enumerate(child_docs):
                    child_id = (
                        f"child_{doc_idx}_{parent_idx}_{child_idx}_{uuid.uuid4().hex[:8]}"
                    )
                    child_content = child_doc.page_content

                    # Skip very short chunks (edge-case fragments)
                    if len(child_content) < min_chars:
                        continue

                    child_chunks.append({
                        "id": child_id,
                        "content": child_content,
                        "metadata": {
                            **document.metadata,
                            "source": source,
                            "page": page,
                            "parent_id": parent_id,  # link back to parent
                            "child_idx": child_idx,
                        },
                    })

                    mapping[child_id] = parent_id

        logger.info(
            "Parent-child chunking: %d parents, %d children",
            len(parent_chunks),
            len(child_chunks),
        )

        # Build Document-like list for the indexing step
        chunks = [
            self._create_chunk(c["content"], c["metadata"])
            for c in child_chunks
        ]

        return {
            "chunks": chunks,
            "parent_chunks": parent_chunks,
            "child_chunks": child_chunks,
            "mapping": mapping,
        }
