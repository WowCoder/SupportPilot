"""
Query Rewriter Service for SupportPilot

Rewrites user queries by incorporating conversation history context
to resolve pronouns and ellipses for better RAG retrieval.
"""
import logging
from typing import List, Optional, Dict
import re

from ..extensions import db
from ..models.chat_memory import ChatMemory
from ..models.conversation import Conversation
from ..config import get_config

logger = logging.getLogger(__name__)


class QueryRewriter:
    """
    Service for rewriting user queries with conversation context.

    Features:
    - Pronoun resolution: replaces pronouns with specific nouns from history
    - Ellipsis completion: adds missing context from previous turns
    - Multi-turn coherence: maintains topic consistency across turns
    """

    def __init__(self):
        self.config = get_config()
        self.enabled = getattr(self.config, 'CHAT_MEMORY_QUERY_REWRITE_ENABLED', True)
        self.timeout_seconds = getattr(self.config, 'CHAT_MEMORY_QUERY_REWRITE_TIMEOUT_SECONDS', 5)
        self.window_size = getattr(self.config, 'CHAT_MEMORY_WINDOW_SIZE', 5)

    def rewrite_query(self, query: str, session_id: int, window_size: int = None) -> str:
        """
        Rewrite a user query by incorporating conversation history.

        Args:
            query: Original user query
            session_id: Conversation session ID
            window_size: Number of recent messages to use as context

        Returns:
            Rewritten query with context incorporated
        """
        if not self.enabled:
            logger.debug('Query rewrite is disabled, using original query')
            return query

        if window_size is None:
            window_size = self.window_size

        # Get recent conversation history
        history = self._get_history(session_id, window_size)
        if not history:
            return query

        # Build context string
        context_str = self._build_context(history)

        # Try to rewrite using LLM
        rewritten = self._rewrite_with_llm(query, context_str)

        if rewritten and rewritten.strip() != query.strip():
            logger.info(f'Query rewritten: "{query[:50]}..." -> "{rewritten[:50]}..."')
            return rewritten
        else:
            logger.debug('No rewrite needed, using original query')
            return query

    def _get_history(self, session_id: int, window_size: int) -> List[Dict]:
        """
        Get recent conversation history for a session.

        Args:
            session_id: Conversation session ID
            window_size: Number of recent messages to retrieve

        Returns:
            List of dicts with sender_type and content
        """
        records = ChatMemory.query.filter_by(
            session_id=session_id,
            status='active'
        ).order_by(ChatMemory.created_at.desc()).limit(window_size).all()

        # Return in chronological order (oldest first)
        return [
            {'sender_type': r.sender_type, 'content': r.content}
            for r in reversed(records)
        ]

    def _build_context(self, history: List[Dict]) -> str:
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
            sender = msg['sender_type']
            content = msg['content'][:200]  # Truncate long messages
            lines.append(f"{sender}: {content}")

        return "\n".join(lines)

    def _rewrite_with_llm(self, query: str, context: str) -> str:
        """
        Rewrite query using LLM with context.

        Args:
            query: Original user query
            context: Conversation history context

        Returns:
            Rewritten query
        """
        # Import here to avoid circular imports
        from api.qwen_api import qwen_api

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
            # Use Qwen API with timeout
            import requests
            import os

            api_key = os.environ.get('QWEN_API_KEY')
            if not api_key:
                logger.warning('QWEN_API_KEY not configured, using original query')
                return query

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
                "temperature": 0.3,  # Lower temperature for more deterministic output
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
                rewritten = result['choices'][0]['message']['content'].strip()
                # Remove any quotes or extra formatting
                rewritten = rewritten.strip('"\'').strip()
                return rewritten
            else:
                logger.warning(f'Unexpected API response format: {result}')
                return query

        except requests.exceptions.Timeout:
            logger.warning(f'Query rewrite timeout ({self.timeout_seconds}s), using original query')
            return query
        except Exception as e:
            logger.warning(f'Query rewrite failed: {e}, using original query')
            return query

    def rewrite_with_rules(self, query: str, history: List[Dict]) -> str:
        """
        Rewrite query using rule-based approach (fallback).

        Args:
            query: Original user query
            history: Conversation history

        Returns:
            Rewritten query
        """
        rewritten = query

        # Common pronouns to resolve
        pronouns = ['它', '这个', '那个', '他们', '她们', '它们', 'its', 'this', 'that', 'they']

        # Check if query contains pronouns
        has_pronoun = any(pronoun in rewritten.lower() for pronoun in pronouns)

        if has_pronoun and history:
            # Find the last mentioned subject from history
            last_subject = self._extract_subject(history[-1]['content'] if history else "")
            if last_subject:
                for pronoun in pronouns:
                    if pronoun in rewritten.lower():
                        rewritten = rewritten.replace(pronoun, last_subject)
                        break

        return rewritten

    def _extract_subject(self, text: str) -> Optional[str]:
        """
        Extract subject/topic from a text (simple heuristic).

        Args:
            text: Input text

        Returns:
            Extracted subject or None
        """
        # Simple pattern: extract first noun phrase before verb indicators
        # This is a very simplified approach
        patterns = [
            r'^(.+?) (?:的)?(?:支持 | 功能 | 怎么 | 如何 | 是什么 | 包括)',  # Chinese patterns
            r'^(.+?) (?:support|feature|how|what)',  # English patterns
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None


# Global instance
query_rewriter = QueryRewriter()
