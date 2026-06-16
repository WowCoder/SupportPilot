"""
Relevance Check Node for Agentic RAG system.

Evaluates retrieval result quality and decides whether to:
- Proceed to result aggregation (pass)
- Retry with refined query (fail, retries remaining)
- Fall back to best-effort aggregation (fail, max retries exceeded)
"""
import logging
from typing import Any, Dict, List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class RelevanceCheckNode:
    """
    Checks relevance of retrieval results and routes accordingly.

    Uses two signals:
    1. Top-1 similarity score (from vector search)
    2. LLM quick relevance judgment (does content cover the question?)
    """

    def __init__(self):
        self.config = get_config()
        self.threshold = self.config.get('agent.relevance_threshold', 0.3)
        self.max_retries = self.config.get('agent.max_retries', 2)

    def _top1_similarity(self, results: List[Dict[str, Any]]) -> float:
        """Get the highest similarity score from results."""
        if not results:
            return 0.0
        scores = [r.get('similarity', r.get('score', 0.0)) for r in results]
        return max(scores) if scores else 0.0

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

        return self._top1_similarity(results)

    def _compute_score(self, query: str, results: List[Dict[str, Any]]) -> float:
        """Compute composite relevance score."""
        if not results:
            return 0.0

        top1 = self._top1_similarity(results)

        # For high top1 scores, skip LLM check to save cost
        if top1 >= 0.5:
            return top1

        # For borderline scores, use LLM as secondary judge
        llm_score = self._quick_relevance_check(query, results)

        # Weighted composite: 60% similarity, 40% LLM
        return 0.6 * top1 + 0.4 * llm_score

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

        logger.info(f'Relevance check: score={score:.3f} retry={retry_count}/{self.max_retries} '
                    f'threshold={self.threshold} results={len(results)}')

        return state


relevance_check_node = RelevanceCheckNode()
