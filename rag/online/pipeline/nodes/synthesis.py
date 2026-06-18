"""
Synthesis Node for Agentic RAG system.

Generates final answers from retrieval results.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

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
            from llm.llm_client import llm_client

            context_len = len(context)
            logger.info(
                '💬 [Synthesis] Generating answer via LLM '
                '(query="%s", context=%d chars, %d sources)',
                query[:60], context_len, len(results),
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            answer = llm_client.generate(messages, temperature=0.3, max_tokens=1024)
            if answer:
                answer_clean = answer.strip()
                logger.info(
                    '✅ [Synthesis] Answer generated: %d chars (preview: "%s")',
                    len(answer_clean), answer_clean[:80],
                )
                return answer_clean
            logger.warning('[Synthesis] LLM returned empty response')
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

    def _build_fallback_from_results(self, results: List[Dict[str, Any]]) -> str:
        """Build a simple fallback response from top results when LLM fails."""
        parts = []
        for i, r in enumerate(results[:3], 1):
            content = r.get('content', '')[:300]
            source = r.get('source', 'unknown')
            parts.append(f"[来源 {i}: {source}]\n{content}")
        return "根据知识库内容：\n\n" + "\n\n".join(parts)

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Generate final answer.

        Args:
            state: Current agent state

        Returns:
            Updated state with final answer
        """
        query = state.get('query', '')
        results = list(state.get('retrieval_results', []))

        logger.info(f'Generating answer for: "{query[:50]}..." with {len(results)} results')

        if not results:
            logger.debug('No retrieval results, generating no-results response')
            state['final_answer'] = self._format_no_results_response(query)
            return state

        # Generate answer via LLM
        answer = self._generate_answer(query, results)

        if answer:
            logger.info('Answer generated successfully')
            state['final_answer'] = answer
        else:
            # Fallback: build a response directly from results
            logger.warning(
                'LLM synthesis failed, falling back to direct result assembly'
            )
            state['final_answer'] = self._build_fallback_from_results(results)

        return state


# Global instance
synthesis_node = SynthesisNode()
