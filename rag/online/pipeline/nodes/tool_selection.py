"""
Tool Selection Node for Agentic RAG system.

LLM-driven tool selection that analyzes sub-query characteristics
and selects optimal retrieval tools and parameters. Replaces the
previous heuristic-based planning.py.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)

AVAILABLE_TOOLS = [
    {
        'name': 'vector_search',
        'description': '语义向量搜索，适合概念性、含义相近的查询。不适合精确关键词匹配。',
        'best_for': ['概念查询', '同义表达', '语义相似', '抽象问题']
    },
    {
        'name': 'bm25_search',
        'description': 'BM25 关键词搜索，适合精确术语匹配、专业名词、代码等。',
        'best_for': ['精确匹配', '专业术语', '代码/编号', '多关键词组合']
    },
    {
        'name': 'metadata_filter',
        'description': '按来源、日期等元数据过滤文档。适合限定范围的查询。',
        'best_for': ['限定来源', '日期范围', '特定文档类型']
    },
    {
        'name': 'ensemble_retrieval',
        'description': '多路召回融合(RRF)，综合多种检索方法的优点。适合复杂查询。',
        'best_for': ['综合查询', '需要多种检索互补', '高召回需求']
    },
]


class ToolSelectionNode:
    """
    LLM-driven tool selection for each sub-query.

    Analyzes query characteristics (language, specificity, domain)
    and selects the best tool combination rather than using hardcoded
    heuristics like word count.
    """

    def __init__(self):
        self.config = get_config()

    def _select_with_llm(self, query: str) -> Dict[str, Any]:
        """Use LLM to select tools and parameters for the query."""
        tools_desc = '\n'.join(
            f"- {t['name']}: {t['description']} 适用: {', '.join(t['best_for'])}"
            for t in AVAILABLE_TOOLS
        )

        system_prompt = f"""你是一个检索策略选择助手。根据查询特征选择最合适的检索工具。

可用工具：
{tools_desc}

分析查询后，输出JSON格式的检索方案：
{{
  "query_type": "factual/comparison/reasoning/listing",
  "reasoning": "选择理由",
  "tools": ["tool_name_1", "tool_name_2"],
  "params": {{
    "k": 5,
    "similarity_threshold": 0.25
  }}
}}

规则：
- vector_search 总是基础工具（除非查询只需要精确匹配）
- bm25_search 适用于含有专业术语、代码、编号等需要精确匹配的查询
- ensemble_retrieval 在选择了2个以上工具时启用，用于融合结果
- k 默认5，复杂查询可用7-10
- similarity_threshold 精确匹配查询可用0.3-0.5，语义查询用0.2-0.25
- 只输出JSON，不要其他文字"""

        user_prompt = f"查询：{query}\n\n请选择检索方案："

        try:
            from llm.llm_client import llm_client

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = llm_client.generate(messages, temperature=0.2, max_tokens=384)

            if response:
                response = response.strip()
                if response.startswith('```'):
                    lines = response.split('\n')
                    response = '\n'.join(lines[1:-1])
                result = json.loads(response)

                # Ensure vector_search is always included as base
                tools = result.get('tools', ['vector_search'])
                if 'vector_search' not in tools:
                    tools.insert(0, 'vector_search')

                # Auto-add ensemble if multiple tools selected
                if len(tools) > 1 and 'ensemble_retrieval' not in tools:
                    tools.append('ensemble_retrieval')

                logger.debug(f'LLM selected tools for "{query[:40]}...": {tools}')
                return {
                    'tools': tools,
                    'params': result.get('params', {'k': 5, 'similarity_threshold': 0.25}),
                    'query_type': result.get('query_type', 'factual'),
                    'reasoning': result.get('reasoning', '')
                }

        except Exception as e:
            logger.warning(f'LLM tool selection failed, using defaults: {e}')

        # Fallback: default to vector + ensemble
        return {
            'tools': ['vector_search', 'ensemble_retrieval'],
            'params': {'k': 5, 'similarity_threshold': 0.25},
            'query_type': 'factual',
            'reasoning': 'fallback default'
        }

    def _build_plan(self, query: str, selection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build execution steps from tool selection."""
        tools = selection.get('tools', [])
        params = selection.get('params', {})

        steps = []
        parallel_tools = [t for t in tools if t != 'ensemble_retrieval']

        if len(parallel_tools) == 1:
            # Single tool: direct execution
            steps.append({
                'tool': parallel_tools[0],
                'arguments': {'query': query, **params}
            })
        else:
            # Multiple tools: parallel execution then ensemble fusion
            for tool in parallel_tools:
                steps.append({
                    'tool': tool,
                    'arguments': {'query': query, **params},
                    'parallel': True
                })
            steps.append({
                'tool': 'ensemble_retrieval',
                'arguments': {'retrieval_results': []},
                'depends_on': parallel_tools
            })

        return steps

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Select tools for the current sub-query using LLM reasoning.

        Args:
            state: Current agent state with sub_queries

        Returns:
            Updated state with plan and retrieval strategy
        """
        sub_queries = list(state.get('sub_queries', []))
        current_idx = state.get('current_sub_query_idx', 0)

        # Get current sub-query
        if current_idx < len(sub_queries):
            current_sub = sub_queries[current_idx]
            query = current_sub.get('query', state.get('rewritten_query', ''))
        else:
            query = state.get('rewritten_query', '') or state.get('query', '')

        logger.info(f'Selecting tools for sub-query [{current_idx}]: "{query[:50]}..."')

        # LLM-driven tool selection
        selection = self._select_with_llm(query)

        # Build execution plan
        steps = self._build_plan(query, selection)

        # Update state
        state['plan'] = {
            'steps': steps,
            'tools': selection['tools'],
            'iterations': 0,
            'query_type': selection.get('query_type', 'factual'),
            'reasoning': selection.get('reasoning', '')
        }

        return state


tool_selection_node = ToolSelectionNode()
