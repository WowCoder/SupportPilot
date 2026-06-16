"""
Base classes for re-rankers.

Re-rankers take retrieved documents and re-score/re-order them
for improved relevance.
"""

import logging

logger = logging.getLogger(__name__)


class BaseReranker:
    """Abstract base class for re-rankers."""

    def rerank(self, query, documents, k=None):
        """Re-rank a list of documents for a given query.

        Args:
            query: The search query string
            documents: List of document dicts with at minimum {'content': str}
            k: Number of top results to return (default: all)

        Returns:
            Re-ranked list of document dicts
        """
        raise NotImplementedError
