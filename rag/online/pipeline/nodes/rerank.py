"""
Cross-Encoder Rerank Node for Agentic RAG system.

Reranks retrieval results using a cross-encoder model to improve precision.
Uses the same ms-marco-MiniLM-L-6-v2 model as the simple retrieval path for
consistency between the two paths.
"""
import logging

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class RerankNode:
    """
    Cross-Encoder based reranking node.

    Re-ranks candidate documents by their actual relevance to the query,
    producing a more accurate ordering than embedding similarity alone.

    Features:
    - Lazy-loads the CrossEncoder model on first use
    - Graceful fallback when model is unavailable
    - Configurable candidate pool size and final output count
    """

    def __init__(self):
        """Initialize the rerank node (model is lazy-loaded)."""
        self.config = get_config()
        self._model = None
        self._model_name = self.config.get(
            'rerank.model',
            'cross-encoder/ms-marco-MiniLM-L-6-v2',
        )

    def _get_model(self):
        """Lazy-load the CrossEncoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info('Loading Cross-Encoder: %s', self._model_name)
                self._model = CrossEncoder(self._model_name)
                logger.info('Cross-Encoder loaded successfully')
            except Exception as e:
                logger.error('Failed to load Cross-Encoder: %s', e)
                self._model = None
        return self._model

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Rerank retrieval results using Cross-Encoder.

        Takes retrieval_results from tool execution, reranks the top
        candidates, and sets both reranked_results and retrieval_results
        to the reranked output for downstream nodes.

        Args:
            state: Current agent state with retrieval_results

        Returns:
            Updated state with reranked results
        """
        query = state.get('rewritten_query', '') or state.get('query', '')
        results = list(state.get('retrieval_results', []))

        top_k = self.config.get('rerank.top_k', 10)
        final_k = self.config.get('rerank.final_k', 5)

        if not results:
            state['reranked_results'] = []
            return state

        # Truncate to top_k candidates to keep inference fast
        candidates = results[:top_k]

        logger.info(
            '📊 [Rerank] Running Cross-Encoder on %d candidates (query="%s")',
            len(candidates), query[:60],
        )

        if len(candidates) <= 1:
            # Single result: no reranking needed
            state['reranked_results'] = candidates
            return state

        model = self._get_model()
        if model is None:
            # Fallback: keep original ranking
            logger.warning(
                'Cross-Encoder unavailable, keeping original ranking '
                '(%d results)', len(candidates[:final_k])
            )
            state['reranked_results'] = candidates[:final_k]
            state['retrieval_results'] = candidates[:final_k]
            return state

        try:
            # Prepare query-document pairs
            pairs = [
                [query, r.get('content', '')]
                for r in candidates
            ]
            scores = model.predict(pairs)

            # Attach rerank scores
            for i, r in enumerate(candidates):
                r['rerank_score'] = float(scores[i])

            # Sort by rerank score (descending)
            candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
            reranked = candidates[:final_k]

            top_score = reranked[0].get('rerank_score', 0) if reranked else 0
            orig_top_score = results[0].get('similarity', results[0].get('score', 0)) if results else 0
            logger.info(
                '📊 [Rerank] Cross-Encoder reranked: %d→%d→%d results '
                '(top score: %.3f→%.3f, +%.0f%%)',
                len(results), len(candidates), len(reranked),
                orig_top_score, top_score,
                ((top_score - orig_top_score) / max(orig_top_score, 0.01)) * 100,
            )

            # Replace retrieval_results with reranked results
            state['reranked_results'] = reranked
            state['retrieval_results'] = reranked

        except Exception as e:
            logger.warning('Rerank failed: %s, keeping original ranking', e)
            state['reranked_results'] = candidates[:final_k]
            state['retrieval_results'] = candidates[:final_k]

        return state


# Global singleton
rerank_node = RerankNode()
