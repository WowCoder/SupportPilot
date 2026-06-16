"""
Query Decomposition Node for Agentic RAG system.

Uses LLM to analyze query complexity and decompose compound queries
into independent sub-queries for parallel retrieval.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class QueryDecompositionNode:
    """
    Decomposes complex queries into sub-queries using LLM reasoning.

    Simple queries (single fact/definition) return a single-element list.
    Compound queries (comparisons, multi-entity, multi-hop) are split.
    """

    def __init__(self):
        self.config = get_config()
        self.max_sub_queries = self.config.get('decomposition.max_sub_queries', 4)
        self.min_query_length = self.config.get('decomposition.min_query_length', 10)
        self.enabled = self.config.get('decomposition.enabled', True)

    def _should_decompose(self, query: str) -> bool:
        """Quick check if decomposition is worth attempting."""
        if not self.enabled:
            return False
        if len(query) < self.min_query_length:
            return False
        return True

    def _decompose_with_llm(self, query: str) -> List[Dict[str, Any]]:
        """Use LLM to decompose query into sub-queries."""
        system_prompt = """你是一个查询分析助手。分析用户查询，判断是否需要拆分为子查询。

规则：
- 简单事实查询（单个概念、定义、属性）→ 不需要拆分，返回原查询
- 对比查询（"A和B的区别"）→ 拆分为每个对象独立查询 + 差异查询
- 多实体查询（"列出X、Y、Z的规则"）→ 每个实体独立查询
- 多跳推理（"A导致B，B影响C"）→ 按推理链拆分
- 综合分析（"总结并分析"）→ 拆分事实查询 + 分析查询

输出JSON格式：
{
  "is_compound": true/false,
  "reasoning": "分析理由",
  "sub_queries": [
    {"query": "子查询1", "type": "factual/comparison/reasoning/listing"},
    ...
  ]
}

重要：
- 子查询数量不超过4个
- 每个子查询必须独立可检索
- 简单查询的sub_queries只包含原查询一个元素
- 只输出JSON，不要其他文字"""

        user_prompt = f"用户查询：{query}\n\n请分析并输出JSON："

        try:
            from llm.llm_client import llm_client

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = llm_client.generate(messages, temperature=0.2, max_tokens=512)
            if not response:
                return [{'query': query, 'type': 'factual'}]

            # Extract JSON from response
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
            result = json.loads(response)

            is_compound = result.get('is_compound', False)
            sub_queries = result.get('sub_queries', [{'query': query, 'type': 'factual'}])

            if not sub_queries:
                sub_queries = [{'query': query, 'type': 'factual'}]

            # Cap sub-query count
            if len(sub_queries) > self.max_sub_queries:
                sub_queries = sub_queries[:self.max_sub_queries]

            if is_compound and len(sub_queries) > 1:
                logger.info(f'Query decomposed into {len(sub_queries)} sub-queries: '
                           f'{[sq["query"][:40] for sq in sub_queries]}')
            else:
                logger.debug(f'Query kept as single: "{query[:50]}..."')

            return sub_queries

        except json.JSONDecodeError:
            logger.warning(f'Failed to parse decomposition JSON, treating as simple query')
            return [{'query': query, 'type': 'factual'}]
        except Exception as e:
            logger.warning(f'Query decomposition failed: {e}')
            return [{'query': query, 'type': 'factual'}]

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Decompose query if needed.

        Args:
            state: Current agent state with rewritten_query

        Returns:
            Updated state with sub_queries populated
        """
        query = state.get('rewritten_query', '') or state.get('query', '')

        if self._should_decompose(query):
            sub_queries = self._decompose_with_llm(query)
        else:
            sub_queries = [{'query': query, 'type': 'factual'}]

        # Convert to list for mutable state
        state['sub_queries'] = list(sub_queries)
        state['current_sub_query_idx'] = 0
        state['all_sub_results'] = []

        return state


query_decomposition_node = QueryDecompositionNode()
