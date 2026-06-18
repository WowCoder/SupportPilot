"""
Query Understanding Node for Agentic RAG system.

Handles conversation context integration:
- Pronoun resolution using chat history
- Ellipsis completion
- Prepares query for downstream nodes (decomposition, tool selection)

Note: LLM-based query rewriting is handled by query_refiner node
when retrieval results are insufficient.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class QueryUnderstandingNode:
    """
    Query understanding node for LangGraph state machine.

    Responsibilities:
    - Load recent conversation history
    - Resolve pronouns and ellipsis using context
    - Attach context to state for downstream use
    """

    def __init__(self):
        """Initialize the query understanding node."""
        self.config = get_config()
        self.window_size = self.config.get('chat_memory.window_size', 5)

    def _get_chat_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conversation history for context."""
        if not session_id:
            return []

        try:
            from app.models.chat_memory import ChatMemory

            records = ChatMemory.query.filter_by(
                session_id=session_id,
                status='active'
            ).order_by(ChatMemory.created_at.desc()).limit(self.window_size).all()

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

    def _resolve_references(self, query: str, history: List[Dict[str, Any]]) -> str:
        """
        Quick pronoun/ellipsis resolution using LLM.

        Only triggers when query appears to have unresolved references
        (short queries, pronouns, etc.). Supports both Chinese and English.
        """
        if not history:
            return query

        # Quick heuristic: detect unresolved pronouns/references
        cn_refs = ['它', '这个', '那个', '这些', '那些', '其', '该', '上面', '刚才']
        en_refs = ['it', 'this', 'that', 'these', 'those', 'they', 'them',
                   'he', 'she', 'his', 'her', 'its', 'their',
                   'above', 'previously', 'earlier', 'before',
                   'the former', 'the latter', 'the same']
        all_refs = cn_refs + en_refs

        has_reference = any(
            kw in query.lower() if kw.isascii() else kw in query
            for kw in all_refs
        )
        if not has_reference and len(query) > 10:
            return query

        context = '\n'.join(
            f"{msg.get('sender_type', 'unknown')}: {msg.get('content', '')[:200]}"
            for msg in history[-3:]
        )

        prompt = f"""根据对话历史，如果用户最新 query 包含代词或省略，将其替换为具体内容。
如果 query 已经完整，返回原 query。
只返回改写后的 query 或原 query，不要解释。

对话历史：
{context}

用户 query: {query}

输出："""

        try:
            from llm.llm_client import llm_client

            logger.info(
                '🔍 [Query Understanding] Resolving references via LLM '
                '(history=%d msgs, query="%s")',
                len(history), query[:60],
            )

            messages = [{"role": "user", "content": prompt}]
            resolved = llm_client.generate(messages, temperature=0.2, max_tokens=128)
            if resolved and resolved.strip() != query:
                clean = resolved.strip().strip('"\'').strip()
                logger.info(
                    '✅ [Query Understanding] Reference resolved: '
                    '"%s" → "%s"', query[:50], clean[:50],
                )
                return clean
            logger.debug(
                '[Query Understanding] LLM kept query unchanged: "%s"',
                query[:50],
            )
        except Exception as e:
            logger.warning(f'Reference resolution failed: {e}')

        return query

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Load conversation context and resolve references.

        Args:
            state: Current agent state

        Returns:
            Updated state with rewritten_query (may equal original)
        """
        query = state.get('query', '')
        session_id = state.get('metadata', {}).get('session_id')

        logger.info(f'Query understanding: "{query[:50]}..."')

        # Load chat history into state messages
        history = self._get_chat_history(session_id)
        if history:
            existing_messages = list(state.get('messages', []))
            state['messages'] = list(existing_messages) + history

        # Resolve references in query
        resolved = self._resolve_references(query, history)
        state['rewritten_query'] = resolved

        if resolved != query:
            logger.info(f'Query resolved: "{query[:40]}..." -> "{resolved[:40]}..."')

        return state


query_understanding_node = QueryUnderstandingNode()
