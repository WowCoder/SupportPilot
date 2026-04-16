"""
RAG Service - Compatibility layer for new Agentic RAG architecture.

Provides backward-compatible API for existing routes while using new architecture.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.agents.retrieval_agent import retrieval_agent
from rag.agents.router import query_router
from rag.tools.vector_tool import vector_search
from rag.parent_store import parent_store

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service wrapper for backward compatibility.

    Routes queries to either simple or agentic retrieval based on router.
    """

    def __init__(self):
        """Initialize the RAG service."""
        pass

    def retrieve(self, query: str, k: int = 3, similarity_threshold: float = 0.25,
                 use_small_to_big: bool = True, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information for a query.

        Args:
            query: Search query
            k: Number of results to return
            similarity_threshold: Minimum similarity score
            use_small_to_big: Use Small-to-Big retrieval
            session_id: Optional session ID for chat history

        Returns:
            List of retrieval results
        """
        # Determine routing
        route_type, metadata = query_router.route(query)

        if route_type == 'agentic':
            # Use agentic retrieval
            logger.info(f'Routing query to agentic path: {query[:50]}...')
            result = retrieval_agent.run(query, session_id)

            if result['success'] and result['answer']:
                # Return results from agent
                return result.get('retrieval_results', [])
            else:
                logger.warning(f'Agentic retrieval failed, falling back to simple: {result.get("error")}')
                # Fall through to simple retrieval

        # Simple retrieval using vector search
        logger.info(f'Routing query to simple path: {query[:50]}...')
        result = vector_search.execute(
            query=query,
            k=k,
            similarity_threshold=similarity_threshold,
            use_small_to_big=use_small_to_big
        )

        return result.data if result and result.success else []

    def get_document_count(self) -> int:
        """Get total document count in ChromaDB."""
        try:
            from rag.rag_utils import rag_utils
            return rag_utils.get_document_count()
        except Exception as e:
            logger.error(f'Error getting document count: {e}')
            return 0


# Global instance
rag_service = RAGService()
