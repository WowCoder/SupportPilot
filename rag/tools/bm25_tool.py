"""
BM25 Keyword Search Tool for Agentic RAG system.

Supports full-text search using BM25 algorithm:
- Tokenize query and documents
- Calculate BM25 scores based on term frequency and inverse document frequency
- Return top-k results sorted by relevance
"""
import logging
import re
from typing import Any, Dict, List, Optional
from pathlib import Path

from rag.core.tool import BaseTool, ToolResult
from rag.core.config import get_config

logger = logging.getLogger(__name__)


class BM25Tool(BaseTool):
    """
    BM25 keyword search tool.

    Features:
    - Token-based matching with customizable tokenization
    - BM25 scoring with configurable k1 and b parameters
    - Supports filtering by metadata
    """

    name = "bm25_search"
    description = "Search documents using BM25 keyword matching. Good for exact term matches and multi-keyword queries."

    # BM25 parameters
    K1 = 1.5  # Term frequency scaling parameter (typical range: 1.2-2.0)
    B = 0.75  # Length normalization parameter (typical range: 0.5-1.0)

    def __init__(self, documents: List[Dict[str, Any]] = None):
        """
        Initialize the BM25 search tool.

        Args:
            documents: List of documents with 'content' and 'metadata' keys.
                      If not provided, documents will be loaded lazily.
        """
        self.config = get_config()
        self._documents = documents
        self._idf_cache = {}
        self._doc_lengths = []
        self._avg_doc_length = 0
        self._vocab = set()
        self._lazy_load = documents is None

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into lowercase tokens.

        Args:
            text: Input text to tokenize

        Returns:
            List of lowercase tokens
        """
        # Simple tokenization: split on whitespace and punctuation
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens

    def _ensure_index(self) -> bool:
        """
        Build BM25 index if documents are available.

        Returns:
            True if index was built successfully, False if no documents
        """
        if self._documents is None and self._lazy_load:
            try:
                # Try to load documents from ChromaDB or file
                # For now, return False as BM25 needs pre-indexed documents
                logger.warning('BM25: No documents available for indexing')
                return False
            except Exception as e:
                logger.error(f'Failed to load documents for BM25: {e}')
                return False

        if not self._documents:
            return False

        # Build index if not already built
        if not self._idf_cache:
            self._build_index()

        return True

    def _build_index(self) -> None:
        """
        Build BM25 index from documents.

        Calculates:
        - Document frequencies for IDF calculation
        - Document lengths for normalization
        - Vocabulary for fast lookup
        """
        import math

        self._idf_cache = {}
        self._doc_lengths = []
        self._vocab = set()

        # Count document frequencies
        doc_freq = {}
        for doc in self._documents:
            content = doc.get('content', '')
            tokens = self._tokenize(content)
            self._doc_lengths.append(len(tokens))
            unique_tokens = set(tokens)
            self._vocab.update(unique_tokens)

            for token in unique_tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        # Calculate IDF for each term
        num_docs = len(self._documents)
        self._avg_doc_length = sum(self._doc_lengths) / num_docs if num_docs > 0 else 0

        for token, df in doc_freq.items():
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1)
            self._idf_cache[token] = idf

    def _bm25_score(self, tokens: List[str], doc_index: int) -> float:
        """
        Calculate BM25 score for a document given query tokens.

        Args:
            tokens: Query tokens
            doc_index: Index of document to score

        Returns:
            BM25 relevance score
        """
        import math

        if doc_index >= len(self._documents):
            return 0.0

        content = self._documents[doc_index].get('content', '')
        doc_tokens = self._tokenize(content)
        doc_length = len(doc_tokens)

        # Calculate term frequency
        tf = {}
        for token in doc_tokens:
            tf[token] = tf.get(token, 0) + 1

        # Calculate BM25 score
        score = 0.0
        for token in tokens:
            if token not in self._idf_cache:
                continue

            idf = self._idf_cache[token]
            term_freq = tf.get(token, 0)

            # BM25 formula: IDF * ((f * (k1 + 1)) / (f + k1 * (1 - b + b * dl/avgdl)))
            numerator = term_freq * (self.K1 + 1)
            denominator = term_freq + self.K1 * (1 - self.B + self.B * doc_length / self._avg_doc_length)

            if denominator > 0:
                score += idf * (numerator / denominator)

        return score

    def execute(self,
                query: str,
                k: int = None,
                similarity_threshold: float = None,
                metadata_filter: Dict[str, Any] = None,
                **kwargs) -> ToolResult:
        """
        Execute BM25 keyword search.

        Args:
            query: Search query string
            k: Number of results to return (default from config)
            similarity_threshold: Minimum BM25 score (default from config)
            metadata_filter: Optional metadata filters

        Returns:
            ToolResult with list of search results
        """
        try:
            # Load config defaults
            k = k or self.config.get('tools.bm25.k', 5)
            similarity_threshold = similarity_threshold or self.config.get('tools.bm25.score_threshold', 0.5)

            # Build index if needed
            if not self._ensure_index():
                return ToolResult(success=True, data=[])

            # Tokenize query
            query_tokens = self._tokenize(query)
            if not query_tokens:
                return ToolResult(success=True, data=[])

            # Score all documents
            scored_docs = []
            for doc_idx in range(len(self._documents)):
                # Apply metadata filter
                if metadata_filter:
                    doc_meta = self._documents[doc_idx].get('metadata', {})
                    if not all(doc_meta.get(key) == value for key, value in metadata_filter.items()):
                        continue

                score = self._bm25_score(query_tokens, doc_idx)
                if score >= similarity_threshold:
                    scored_docs.append({
                        'content': self._documents[doc_idx]['content'],
                        'score': float(score),
                        'source': self._documents[doc_idx].get('metadata', {}).get('source', 'unknown'),
                        'metadata': self._documents[doc_idx].get('metadata', {})
                    })

            # Sort by score and limit to k
            scored_docs.sort(key=lambda x: x['score'], reverse=True)
            scored_docs = scored_docs[:k]

            logger.debug(f'BM25 search returned {len(scored_docs)} results')
            return ToolResult(success=True, data=scored_docs)

        except Exception as e:
            logger.error(f'BM25 search failed: {e}', exc_info=True)
            return ToolResult(success=False, error=str(e))


# Global instance (lazy-loaded)
bm25_search = BM25Tool()
