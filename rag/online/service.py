"""
RAG Service - Compatibility layer for new Agentic RAG architecture.

Provides backward-compatible API for existing routes while using new architecture.
"""
import json
import logging
import time
from typing import Any, Dict, List, Optional

from rag.online.pipeline.builder import retrieval_agent
from rag.online.router import query_router
from rag.online.retrievers.dense import vector_search

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
        start_time = time.time()
        route_type = 'simple'
        results = []

        try:
            # Determine routing
            route_type, metadata = query_router.route(query)

            if route_type == 'agentic':
                # Use agentic retrieval
                logger.info(f'Routing query to agentic path: {query[:50]}...')
                result = retrieval_agent.run(query, session_id)

                if result['success'] and result['answer']:
                    results = result.get('retrieval_results', [])
                else:
                    logger.warning(f'Agentic retrieval failed, falling back to simple: {result.get("error")}')
                    route_type = 'simple'
                    # Fall through to simple retrieval

            if route_type == 'simple' or not results:
                # Simple retrieval using vector search
                logger.info(f'Routing query to simple path: {query[:50]}...')
                result = vector_search.execute(
                    query=query,
                    k=k,
                    similarity_threshold=similarity_threshold,
                    use_small_to_big=use_small_to_big
                )
                results = result.data if result and result.success else []

        except Exception as e:
            logger.error(f'Retrieval error: {e}', exc_info=True)
        finally:
            # Auto-log retrieval regardless of success/failure
            duration_ms = round((time.time() - start_time) * 1000, 1)
            try:
                self._log_retrieval(query, results, duration_ms, route_type)
            except Exception as e:
                logger.error(f'Failed to log retrieval: {e}')

        return results

    def _log_retrieval(self, query: str, results: list, duration_ms: float, route_type: str):
        """Record retrieval log to database."""
        from app.extensions import db
        from app.models.rag_log import RagRetrievalLog

        top1 = results[0].get('similarity', 0) if results else 0

        log = RagRetrievalLog(
            query=query,
            result_count=len(results),
            top1_similarity=round(top1, 4),
            duration_ms=duration_ms,
            route_type=route_type,
            results_json=json.dumps(results, ensure_ascii=False) if results else None
        )
        db.session.add(log)
        db.session.commit()

        # Inject log_id into results for feedback association
        for r in results:
            r['log_id'] = log.id

        logger.debug(f'Retrieval log #{log.id}: query="{query[:50]}..." '
                     f'results={len(results)} top1={top1:.3f} {duration_ms}ms [{route_type}]')

    def get_document_count(self) -> int:
        """Get total document count in ChromaDB."""
        try:
            from rag.offline.pipeline import rag_utils
            return rag_utils.get_document_count()
        except Exception as e:
            logger.error(f'Error getting document count: {e}')
            return 0


# Global instance
rag_service = RAGService()
