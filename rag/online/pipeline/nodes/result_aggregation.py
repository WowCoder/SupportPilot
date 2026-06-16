"""
Result Aggregation Node for Agentic RAG system.

Merges retrieval results from multiple sub-queries or correction attempts
using RRF-based deduplication and ranking.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class ResultAggregationNode:
    """
    Aggregates results from multiple sub-queries.

    - Combines results with RRF (Reciprocal Rank Fusion)
    - Deduplicates by content hash
    - Sorts by combined score
    - Truncates to top-k
    """

    RRF_K = 60

    def __init__(self):
        self.config = get_config()
        self.top_k = self.config.get('tools.ensemble.k', 10)

    def _content_key(self, content: str) -> str:
        """Generate a normalized key for deduplication."""
        return content.strip()[:100]

    def _rrf_merge(self, all_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge results from multiple sub-queries using RRF.

        Args:
            all_results: List of result dicts, each with 'content', 'similarity', etc.

        Returns:
            Deduplicated and ranked results
        """
        if not all_results:
            return []

        # Group by sub-query (use source as proxy for sub-query grouping)
        # First, just rank all results by their existing score
        scored = {}
        content_map = {}

        for i, result in enumerate(all_results):
            content = result.get('content', '')
            key = self._content_key(content)

            # RRF: 1 / (rank + K)
            rank = i + 1
            rrf_score = 1.0 / (rank + self.RRF_K)

            if key not in scored:
                scored[key] = rrf_score
                content_map[key] = result
            else:
                scored[key] += rrf_score
                # Keep the result with higher original similarity
                existing_sim = content_map[key].get('similarity', 0)
                new_sim = result.get('similarity', 0)
                if new_sim > existing_sim:
                    content_map[key] = result

        # Sort by combined RRF score
        sorted_keys = sorted(scored.keys(), key=lambda k: scored[k], reverse=True)

        merged = []
        for key in sorted_keys[:self.top_k]:
            result = content_map[key].copy()
            result['rrf_score'] = float(scored[key])
            merged.append(result)

        return merged

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Aggregate results from all sub-queries.

        Args:
            state: Current agent state with all_sub_results

        Returns:
            Updated state with merged retrieval_results
        """
        all_sub_results = list(state.get('all_sub_results', []))
        current_results = list(state.get('retrieval_results', []))

        # Combine all results: sub-query results + current results
        combined = list(all_sub_results) + list(current_results)

        if not combined:
            logger.warning('No results to aggregate')
            return state

        # Merge and deduplicate
        merged = self._rrf_merge(combined)

        logger.info(f'Aggregation: {len(combined)} results from '
                   f'{len(all_sub_results) > 0 and "sub-queries" or "single query"} '
                   f'-> {len(merged)} after dedup')

        state['retrieval_results'] = merged
        state['all_sub_results'] = merged  # Sync

        return state


result_aggregation_node = ResultAggregationNode()
