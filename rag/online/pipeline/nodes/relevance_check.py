"""
Relevance Check Node for Agentic RAG system.

Evaluates retrieval result quality and decides whether to:
- Proceed to result aggregation (pass)
- Retry with refined query (fail, retries remaining)
- Fall back to best-effort aggregation (fail, max retries exceeded)
"""
import logging
from typing import Any, Dict, List

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class RelevanceCheckNode:
    """
    Checks relevance of retrieval results and routes accordingly.

    Uses three signals:
    1. Average of top-3 similarity scores (more robust than top-1)
    2. Result count penalty (too few results = lower confidence)
    3. LLM quick relevance judgment for borderline cases
    """

    def __init__(self):
        self.config = get_config()
        self.threshold = self.config.get('agent.relevance_threshold', 0.4)
        self.max_retries = self.config.get('agent.max_retries', 2)
        self.top_n_avg = self.config.get('relevance.top_n_avg', 3)
        self.min_results = self.config.get('relevance.min_results_for_pass', 2)
        self.sim_weight = self.config.get('relevance.sim_weight', 0.6)
        self.llm_weight = self.config.get('relevance.llm_weight', 0.4)

    def _top_n_avg_similarity(self, results: List[Dict[str, Any]], n: int = 3) -> float:
        """
        Get the average of top-N similarity scores.

        More robust than top-1: a single lucky high-score result won't
        mask that the rest are irrelevant.
        """
        if not results:
            return 0.0
        scores = sorted(
            [
                r.get('rerank_score',
                      r.get('similarity',
                            r.get('score', 0.0)))
                for r in results
            ],
            reverse=True,
        )
        top_n = scores[:n]
        return sum(top_n) / len(top_n) if top_n else 0.0

    def _quick_relevance_check(self, query: str, results: List[Dict[str, Any]]) -> float:
        """
        Use lightweight LLM prompt to judge relevance.

        Returns a score 0.0-1.0 where 1.0 = fully relevant.
        """
        if not results:
            return 0.0

        # Build short context from top results
        snippets = []
        for i, r in enumerate(results[:3]):
            content = r.get('content', '')[:200]
            snippets.append(f"[{i+1}] {content}")

        context = '\n'.join(snippets)

        prompt = f"""评估检索结果是否包含回答问题的关键信息。只回复一个0到1之间的分数。

问题：{query}

检索结果片段：
{context}

相关性分数（0-1）："""

        try:
            from llm.llm_client import llm_client

            messages = [{"role": "user", "content": prompt}]
            response = llm_client.generate(messages, temperature=0, max_tokens=16)
            if response:
                # Extract float from response
                import re
                match = re.search(r'(\d+\.?\d*)', response.strip())
                if match:
                    return min(1.0, max(0.0, float(match.group(1))))
        except Exception as e:
            logger.warning(f'LLM relevance check failed: {e}')

        return self._top_n_avg_similarity(results)

    def _compute_score(self, query: str, results: List[Dict[str, Any]]) -> float:
        """Compute composite relevance score with result count penalty."""
        if not results:
            return 0.0

        avg_sim = self._top_n_avg_similarity(results, n=self.top_n_avg)

        # Penalty for too few results
        if len(results) < self.min_results:
            avg_sim *= 0.5
            logger.debug(
                'Result count penalty applied: %d < %d (score: %.3f)',
                len(results), self.min_results, avg_sim,
            )

        # For high-confidence scores, skip LLM check to save cost
        if avg_sim >= 0.6:
            return avg_sim

        # For borderline scores, use LLM as secondary judge
        llm_score = self._quick_relevance_check(query, results)

        # Weighted composite
        return self.sim_weight * avg_sim + self.llm_weight * llm_score

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Evaluate retrieval relevance and set routing decision.

        Updates state with relevance_scores and routing metadata.
        The conditional edge function reads these to decide routing.
        """
        query = state.get('rewritten_query', '') or state.get('query', '')
        results = list(state.get('retrieval_results', []))
        retry_count = state.get('retry_count', 0)

        score = self._compute_score(query, results)

        # Store scores
        relevance_scores = dict(state.get('relevance_scores', {}))
        relevance_scores[str(retry_count)] = score
        state['relevance_scores'] = relevance_scores

        sub_idx = state.get('current_sub_query_idx', 0)
        logger.info(
            'Relevance check: score=%.3f retry=%d/%d threshold=%.2f '
            'results=%d sub_query=%d',
            score, retry_count, self.max_retries, self.threshold,
            len(results), sub_idx,
        )

        return state


relevance_check_node = RelevanceCheckNode()
