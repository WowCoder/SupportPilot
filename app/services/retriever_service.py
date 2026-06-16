"""
Unified RAG retrieval service for the Flask application.

This is the single entry point for all app-layer RAG calls.
Routes should call this service instead of importing rag modules directly.
"""

import logging

logger = logging.getLogger(__name__)


class RetrieverService:
    """Thin wrapper around rag.online.service for app-layer consumption."""

    def __init__(self):
        self._rag_service = None

    @property
    def rag_service(self):
        if self._rag_service is None:
            from rag.online.service import rag_online_service
            self._rag_service = rag_online_service
        return self._rag_service

    def search(self, query, k=3, use_hybrid=False, use_reranking=True):
        """Search the knowledge base.

        Args:
            query: Search query string
            k: Number of results
            use_hybrid: Use hybrid (BM25 + vector) search
            use_reranking: Apply cross-encoder re-ranking

        Returns:
            List of search result dicts
        """
        return self.rag_service.retrieve(query, k=k,
                                         use_hybrid=use_hybrid,
                                         use_reranking=use_reranking)

    def search_with_parent(self, query, k=3, use_reranking=True):
        """Search using Small-to-Big retrieval strategy.

        Args:
            query: Search query string
            k: Number of results
            use_reranking: Apply cross-encoder re-ranking

        Returns:
            List of parent document dicts
        """
        return self.rag_service.retrieve_with_parent(query, k=k,
                                                      use_reranking=use_reranking)

    def process_document(self, file_path, strategy='semantic', **kwargs):
        """Process and index a document.

        Args:
            file_path: Path to the document
            strategy: Chunking strategy
            **kwargs: Additional parameters

        Returns:
            Processing result dict
        """
        from rag.offline.pipeline import rag_utils
        return rag_utils.process_document(file_path, strategy=strategy, **kwargs)

    def preview_chunks(self, file_path, strategy='semantic', **kwargs):
        """Preview document chunking without indexing.

        Args:
            file_path: Path to the document
            strategy: Chunking strategy
            **kwargs: Additional parameters

        Returns:
            Preview result dict
        """
        from rag.offline.pipeline import rag_utils
        return rag_utils.preview_chunks(file_path, strategy=strategy, **kwargs)

    def delete_document(self, filename):
        """Delete all chunks from a source file.

        Args:
            filename: Source filename to delete

        Returns:
            True if deleted, False otherwise
        """
        from rag.offline.pipeline import rag_utils
        return rag_utils.delete_documents_by_source(filename)

    def get_document_count(self):
        """Get total chunk count in the knowledge base."""
        from rag.offline.pipeline import rag_utils
        return rag_utils.get_document_count()


# Global singleton
retriever_service = RetrieverService()
