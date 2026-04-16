"""
Query Understanding Node for Agentic RAG system.

Integrates QueryRewriter functionality:
- Pronoun resolution using conversation history
- Ellipsis completion
- Query clarification and refinement
"""
import logging
from typing import Any, Dict, List, Optional

from rag.agents.states import AgentState, AgentStateDict, ToolCall
from rag.core.config import get_config

logger = logging.getLogger(__name__)


class QueryUnderstandingNode:
    """
    Query understanding node for LangGraph state machine.

    Responsibilities:
    - Rewrite queries using conversation history (pronoun resolution, ellipsis completion)
    - Detect query type and intent
    - Prepare query for planning phase
    """

    def __init__(self):
        """Initialize the query understanding node."""
        self.config = get_config()
        self.window_size = self.config.get('chat_memory.window_size', 5)
        self.timeout_seconds = self.config.get('chat_memory.timeout_seconds', 5)

    def _get_chat_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get conversation history for query rewriting.

        Args:
            session_id: Optional session identifier

        Returns:
            List of message dicts with 'sender_type' and 'content'
        """
        if not session_id:
            return []

        try:
            # Import chat memory models
            from app.models.chat_memory import ChatMemory
            from app.models.conversation import Conversation

            # Get recent messages
            records = ChatMemory.query.filter_by(
                session_id=session_id,
                status='active'
            ).order_by(ChatMemory.created_at.desc()).limit(self.window_size).all()

            # Return in chronological order (oldest first)
            return [
                {'sender_type': r.sender_type, 'content': r.content}
                for r in reversed(records)
            ]

        except ImportError:
            logger.warning('Chat memory models not available')
            return []
        except Exception as e:
            logger.error(f'Failed to get chat history: {e}')
            return []

    def _build_context(self, history: List[Dict[str, Any]]) -> str:
        """
        Build context string from conversation history.

        Args:
            history: List of message dicts

        Returns:
            Formatted context string
        """
        if not history:
            return ""

        lines = []
        for msg in history:
            sender = msg.get('sender_type', 'unknown')
            content = msg.get('content', '')[:200]  # Truncate long messages
            lines.append(f"{sender}: {content}")

        return "\n".join(lines)

    def _rewrite_with_llm(self, query: str, context: str) -> Optional[str]:
        """
        Rewrite query using LLM with context.

        Args:
            query: Original user query
            context: Conversation history context

        Returns:
            Rewritten query or None if rewrite failed
        """
        system_prompt = """你是一个 query 改写助手。你的任务是根据对话历史，改写用户的最新 query，使其更清晰完整。

规则：
- 如果 query 包含代词（如"它"、"这个"、"那个"），从历史中找到具体指代的内容并替换
- 如果 query 有省略（如缺少主语），从历史中补全
- 如果 query 已经很完整，不需要改写，返回原 query
- 只返回改写后的 query，不要添加任何解释"""

        user_prompt = f"""对话历史：
{context}

用户最新 query: {query}

请改写 query（如果不需要改写，返回原 query）："""

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
                "max_tokens": 256
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
                rewritten = result['choices'][0]['message']['content'].strip().strip('"\'').strip()
                return rewritten if rewritten and rewritten != query else None
            else:
                logger.warning(f'Unexpected API response format: {result}')
                return None

        except requests.exceptions.Timeout:
            logger.warning(f'Query rewrite timeout ({self.timeout_seconds}s)')
            return None
        except Exception as e:
            logger.warning(f'Query rewrite failed: {e}')
            return None

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Process query understanding.

        Args:
            state: Current agent state

        Returns:
            Updated state with rewritten_query
        """
        query = state.get('query', '')
        session_id = state.get('metadata', {}).get('session_id')

        logger.info(f'Processing query understanding: "{query[:50]}..."')

        # Get chat history
        history = self._get_chat_history(session_id)

        if not history:
            logger.debug('No chat history available, using original query')
            state['rewritten_query'] = query
            return state

        # Build context
        context = self._build_context(history)

        # Try LLM-based rewrite
        rewritten = self._rewrite_with_llm(query, context)

        if rewritten:
            logger.info(f'Query rewritten: "{query[:50]}..." -> "{rewritten[:50]}..."')
            state['rewritten_query'] = rewritten
        else:
            logger.debug('No rewrite needed, using original query')
            state['rewritten_query'] = query

        return state


# Global instance
query_understanding_node = QueryUnderstandingNode()
