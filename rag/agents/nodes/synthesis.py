"""
Synthesis Node for Agentic RAG system.

Generates final answers from retrieval results.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.agents.states import AgentStateDict
from rag.core.config import get_config

logger = logging.getLogger(__name__)


class SynthesisNode:
    """
    Synthesis node for LangGraph state machine.

    Responsibilities:
    - Generate answer from retrieval results
    - Format response with citations
    - Handle cases where no relevant results found
    """

    def __init__(self):
        """Initialize the synthesis node."""
        self.config = get_config()
        self.timeout_seconds = self.config.get('agent.timeout_seconds', 30)

    def _generate_answer(self, query: str, results: List[Dict[str, Any]]) -> Optional[str]:
        """
        Generate answer from retrieval results.

        Args:
            query: User query
            results: List of retrieval results

        Returns:
            Generated answer or None if generation failed
        """
        if not results:
            return None

        # Build context from results
        context_parts = []
        for i, result in enumerate(results, 1):
            content = result.get('content', '')
            source = result.get('source', 'unknown')
            context_parts.append(f"[Source {i}: {source}]\n{content}")

        context = "\n\n".join(context_parts)

        # Generate answer using LLM
        system_prompt = """你是一个专业的 SupportPilot 助手。请根据提供的上下文信息回答用户问题。

规则：
- 只使用提供的上下文中的信息，不要编造
- 如果上下文不足以回答问题，请说明
- 引用来源时使用 [Source N] 格式
- 回答简洁明了，结构清晰
- 使用与问题相同的语言回答"""

        user_prompt = f"""上下文：
{context}

用户问题：{query}

请根据上下文回答用户问题："""

        try:
            import requests
            import os

            api_key = os.environ.get('QWEN_API_KEY')
            if not api_key:
                logger.warning('QWEN_API_KEY not configured')
                return None

            api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            data = {
                "model": "qwen-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1024
            }

            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=self.timeout_seconds
            )
            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                answer = result['choices'][0]['message']['content'].strip()
                return answer
            else:
                logger.warning(f'Unexpected API response format: {result}')
                return None

        except requests.exceptions.Timeout:
            logger.warning(f'Answer generation timeout ({self.timeout_seconds}s)')
            return None
        except Exception as e:
            logger.warning(f'Answer generation failed: {e}')
            return None

    def _format_no_results_response(self, query: str) -> str:
        """
        Format response when no relevant results found.

        Args:
            query: User query

        Returns:
            Formatted response
        """
        return f"抱歉，未找到与您的问题「{query}」相关的信息。请尝试换一种问法或联系技术支持。"

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Generate final answer.

        Args:
            state: Current agent state

        Returns:
            Updated state with final answer
        """
        query = state.get('query', '')
        results = state.get('retrieval_results', [])

        logger.info(f'Generating answer for: "{query[:50]}..." with {len(results)} results')

        if not results:
            logger.debug('No retrieval results, generating no-results response')
            state['final_answer'] = self._format_no_results_response(query)
            return state

        # Generate answer
        answer = self._generate_answer(query, results)

        if answer:
            logger.info('Answer generated successfully')
            state['final_answer'] = answer
        else:
            logger.warning('Answer generation failed, using no-results response')
            state['final_answer'] = self._format_no_results_response(query)

        return state


# Global instance
synthesis_node = SynthesisNode()
