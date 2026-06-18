"""
Query Refiner Node for Agentic RAG system.

Rewrites queries based on retrieval feedback when initial results
are not relevant enough. Tries progressive strategies:
1. Expand keywords (add synonyms, related terms)
2. Narrow scope (focus on specific aspect)
3. Rephrase angle (approach from different direction)
"""
import logging
from typing import List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class QueryRefinerNode:
    """
    Refines queries based on retrieval feedback.

    Tracks query history to prevent infinite loops and duplicate attempts.
    Uses progressive refinement strategies.
    """

    def __init__(self):
        self.config = get_config()
        self.max_history = self.config.get('correction.max_query_history', 5)
        self.strategies = self.config.get('correction.refinement_strategies', [
            'expand_keywords',
            'narrow_scope',
            'rephrase_angle'
        ])

    def _get_strategy(self, retry_count: int) -> str:
        """
        Get the refinement strategy for current retry.

        Progressive strategy: first broaden, then re-angle, finally narrow.
        """
        if retry_count == 0:
            return 'expand_keywords'    # First retry: try broader terms
        elif retry_count == 1:
            return 'rephrase_angle'     # Second retry: different phrasing
        else:
            return 'narrow_scope'       # Final retry: focus on core keywords

    def _refine_with_llm(self, original_query: str, current_query: str,
                         retry_count: int, results_snippet: str,
                         query_history: List[str],
                         relevance_score: float = 0.0) -> Optional[str]:
        """Use LLM to refine the query based on feedback."""
        strategy = self._get_strategy(retry_count)
        history_str = '\n'.join(f'- {q}' for q in query_history[-5:]) if query_history else '(无)'

        strategy_instructions = {
            'expand_keywords': '扩展查询关键词，添加同义词、相关术语或更宽泛的概念，以覆盖更多可能的相关文档。',
            'narrow_scope': '缩小查询范围，聚焦到问题的某个具体方面或最核心的关键词。',
            'rephrase_angle': '从不同角度重新表述问题，改变措辞方式或提问视角。',
        }

        instruction = strategy_instructions.get(strategy, strategy_instructions['expand_keywords'])

        system_prompt = f"""你是一个查询优化助手。当前检索结果不理想（相似度仅 {relevance_score:.2f}），说明查询与文档库匹配度低。

改写策略：{instruction}

规则：
- 改写后的查询必须独立可检索
- 不要与历史查询重复
- 保持原始问题的核心意图
- 只输出改写后的查询文本，不要解释"""

        user_prompt = f"""原始问题：{original_query}
当前查询：{current_query}
检索相似度：{relevance_score:.2f}
检索到的内容片段（不理想）：{results_snippet}

已尝试的查询历史：
{history_str}

请输出改写后的查询："""

        try:
            from llm.llm_client import llm_client

            logger.info(
                '🔄 [Query Refiner] Refining query via LLM '
                '(retry=%d strategy=%s score=%.2f): "%s"',
                retry_count, strategy, relevance_score, current_query[:60],
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            refined = llm_client.generate(messages, temperature=0.4, max_tokens=256)
            if refined:
                refined = refined.strip().strip('"\'').strip()
                # Don't reuse previous queries
                if refined in query_history:
                    logger.warning(
                        '🔄 [Query Refiner] Refined query duplicates history, '
                        'skipping: "%s"', refined[:60],
                    )
                    return None
                logger.info(
                    '✅ [Query Refiner] Refined: "%s" → "%s" (strategy=%s)',
                    current_query[:50], refined[:50], strategy,
                )
                return refined
        except Exception as e:
            logger.warning(f'Query refinement failed: {e}')

        return None

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Refine query based on retrieval feedback.

        Args:
            state: Current agent state with failed retrieval results

        Returns:
            Updated state with refined query and incremented retry count
        """
        original_query = state.get('query', '')
        current_query = state.get('rewritten_query', '') or original_query
        retry_count = state.get('retry_count', 0)
        results = list(state.get('retrieval_results', []))
        query_history = list(state.get('query_history', []))

        # Get current relevance score for diagnosis
        relevance_scores = state.get('relevance_scores', {})
        current_score = relevance_scores.get(str(retry_count), 0.0)

        # Build results snippet for context
        if results:
            snippets = [r.get('content', '')[:100] for r in results[:2]]
            results_snippet = ' | '.join(snippets)
        else:
            results_snippet = '(无检索结果)'

        # Track current query in history
        if current_query not in query_history:
            query_history.append(current_query)
        if len(query_history) > self.max_history:
            query_history = query_history[-self.max_history:]

        # Refine query
        refined = self._refine_with_llm(
            original_query, current_query, retry_count,
            results_snippet, query_history,
            relevance_score=current_score,
        )

        if refined:
            logger.info(
                f'Query refined (retry {retry_count + 1}): '
                f'"{current_query[:40]}..." -> "{refined[:40]}..."'
            )
            state['rewritten_query'] = refined
            if refined not in query_history:
                query_history.append(refined)
        else:
            logger.warning('Query refinement produced no result, keeping current query')

        # Update state
        state['query_history'] = query_history
        state['retry_count'] = retry_count + 1

        return state


query_refiner_node = QueryRefinerNode()
