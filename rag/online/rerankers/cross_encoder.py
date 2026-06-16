"""
Cross-Encoder re-ranker using SentenceTransformers.

Provides more accurate re-ranking by jointly encoding
the query and each document through a cross-attention model.
"""

import logging
from sentence_transformers import CrossEncoder
from rag.online.rerankers.base import BaseReranker

logger = logging.getLogger(__name__)


class CrossEncoderReranker(BaseReranker):
    """Re-ranker using a Cross-Encoder model for pairwise scoring."""

    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        self._ready = False

    def _init_model(self):
        """Lazy-initialize the CrossEncoder model."""
        if self._ready:
            return True
        try:
            logger.info(f'Loading Cross-Encoder: {self.model_name}')
            self._model = CrossEncoder(self.model_name)
            self._ready = True
            logger.info('Cross-Encoder loaded successfully')
            return True
        except Exception as e:
            logger.error(f'Failed to load Cross-Encoder: {e}')
            return False

    def rerank(self, query, documents, k=None):
        """Re-rank documents using Cross-Encoder scores.

        Args:
            query: The search query
            documents: List of document dicts with 'content' key
            k: Number of top results (default: all)

        Returns:
            Re-ranked documents with 'rerank_score' added
        """
        if not documents:
            return documents

        if not self._init_model():
            logger.warning('Cross-Encoder unavailable, returning original order')
            return documents[:k] if k else documents

        try:
            pairs = [[query, doc['content']] for doc in documents]
            scores = self._model.predict(pairs)

            for i, doc in enumerate(documents):
                doc['rerank_score'] = float(scores[i])

            documents.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)

            return documents[:k] if k else documents

        except Exception as e:
            logger.error(f'Cross-Encoder rerank error: {e}')
            return documents[:k] if k else documents
