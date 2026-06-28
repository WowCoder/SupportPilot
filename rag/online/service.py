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
from rag.utils.semantic_cache import semantic_cache
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service wrapper for backward compatibility.

    Routes queries to either simple or agentic retrieval based on router.
    """

    def __init__(self):
        """Initialize the RAG service."""
        self.last_trace = None       # Trace from most recent retrieve() call
        self.last_metadata = None    # Metadata from most recent retrieve() call

    def retrieve(
        self, query: str, k: int = 3, similarity_threshold: float = 0.25,
        use_small_to_big: bool = True, session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant information for a query.

        Args:
            query: Search query
            k: Number of results to return
            similarity_threshold: Minimum similarity score
            use_small_to_big: Use Small-to-Big retrieval
            session_id: Optional session ID for chat history

        Returns:
            List of retrieval results (each dict has 'log_id' injected for feedback)

        Side effects:
            Sets self.last_trace and self.last_metadata for callers to read.
        """
        start_time = time.time()
        route_type = 'simple'
        results = []
        trace_data = None
        agentic_metadata = {}
        final_answer = None
        cached = False

        try:
            # 🆕 Phase 1: Semantic cache lookup (before routing)
            if semantic_cache.is_enabled():
                cache_hit = semantic_cache.lookup(query)
                if cache_hit:
                    results = cache_hit.get('results', [])
                    final_answer = cache_hit.get('answer')
                    agentic_metadata = cache_hit.get('metadata', {})
                    route_type = 'cached'
                    cached = True
                    logger.info(
                        'Semantic cache hit for: "%s" → %d results',
                        query[:50], len(results),
                    )

            if not cached:
                # Determine routing
                route_type, route_meta = query_router.route(query)

                if route_type == 'agentic':
                    # Use agentic retrieval
                    logger.info(
                        'Routing query to agentic path: %s', query[:50],
                    )
                    result = retrieval_agent.run(query, session_id)

                    if result['success'] and result['answer']:
                        results = result.get('retrieval_results', [])
                        trace_data = result.get('trace')
                        agentic_metadata = result.get('metadata', {})
                        final_answer = result.get('answer')
                    else:
                        logger.warning(
                            'Agentic retrieval failed, '
                            'falling back to simple: %s',
                            result.get('error'),
                        )
                        trace_data = result.get('trace')
                        route_type = 'simple'
                        # Fall through to simple retrieval

                if route_type == 'simple' or not results:
                    # Simple retrieval
                    logger.info(
                        'Routing query to simple path: %s', query[:50],
                    )
                    from rag.offline.pipeline import rag_utils
                    results = rag_utils.retrieve_relevant_info(
                        query=query,
                        k=k,
                        similarity_threshold=similarity_threshold,
                    )

        except Exception as e:
            logger.error(f'Retrieval error: {e}', exc_info=True)
        finally:
            # Auto-log retrieval regardless of success/failure
            duration_ms = round((time.time() - start_time) * 1000, 1)
            try:
                self._log_retrieval(query, results, duration_ms, route_type,
                                    trace=trace_data, metadata=agentic_metadata)
            except Exception as e:
                logger.error(f'Failed to log retrieval: {e}')

            # 🆕 Phase 1: Store result in semantic cache for future queries
            if not cached and results and semantic_cache.is_enabled():
                try:
                    semantic_cache.store(
                        query=query,
                        answer=final_answer or '',
                        results=results,
                        metadata={
                            'route_type': route_type,
                            'mode': agentic_metadata.get('mode', 'simple'),
                        },
                    )
                except Exception as e:
                    logger.warning('Failed to store semantic cache: %s', e)

        # Expose trace/metadata for callers (e.g. chat API)
        self.last_trace = trace_data
        self.last_metadata = {
            'route_type': route_type,
            'duration_ms': duration_ms,
            'sub_query_count': agentic_metadata.get('sub_query_count', 0),
            'retry_count': agentic_metadata.get('retry_count', 0),
            'faithfulness_score': agentic_metadata.get('faithfulness_score'),
            'mode': agentic_metadata.get('mode', 'simple'),
            'cached': cached,
            'parallel_enabled': (
                get_config().get('parallel.enabled', True)
                and agentic_metadata.get('sub_query_count', 0) > 1
            ),
        }

        return results

    def _log_retrieval(
        self, query: str, results: list, duration_ms: float,
        route_type: str, trace: dict = None, metadata: dict = None,
    ):
        """Record retrieval log to database with trace data."""
        from app.extensions import db
        from app.models.rag_log import RagRetrievalLog

        top1 = results[0].get('similarity', 0) if results else 0
        meta = metadata or {}

        log = RagRetrievalLog(
            query=query,
            result_count=len(results),
            top1_similarity=round(top1, 4),
            duration_ms=duration_ms,
            route_type=route_type,
            results_json=json.dumps(results, ensure_ascii=False) if results else None,
            trace_json=json.dumps(trace, ensure_ascii=False) if trace else None,
            sub_query_count=meta.get('sub_query_count', 0),
            retry_count=meta.get('retry_count', 0),
            faithfulness_score=meta.get('faithfulness_score'),
        )
        db.session.add(log)
        db.session.commit()

        # Inject log_id into results for feedback association
        for r in results:
            r['log_id'] = log.id

        logger.debug(
            f'Retrieval log #{log.id}: query="{query[:50]}..." '
            f'results={len(results)} top1={top1:.3f} '
            f'{duration_ms}ms [{route_type}] '
            f'sub_queries={meta.get("sub_query_count", 0)} '
            f'retries={meta.get("retry_count", 0)}'
        )

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
