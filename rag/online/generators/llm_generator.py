"""
LLM-based answer generator.

Uses the configured LLM client to synthesize answers from
retrieved context documents and conversation history.
"""

import logging
from rag.online.generators.base import BaseGenerator

logger = logging.getLogger(__name__)


class LLMGenerator(BaseGenerator):
    """Answer generator using an LLM for synthesis."""

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM client instance. If None, will use
                        the global llm_client from llm.llm_client.
        """
        self._llm_client = llm_client

    @property
    def llm_client(self):
        if self._llm_client is None:
            from llm.llm_client import llm_client
            self._llm_client = llm_client
        return self._llm_client

    def generate(self, query, context_docs, chat_history=None):
        """Generate an answer using the LLM with retrieved context.

        Args:
            query: The user's question
            context_docs: List of retrieved document dicts
            chat_history: Optional conversation history

        Returns:
            Generated answer string
        """
        # Build context from documents
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            source = doc.get('source', 'unknown')
            content = doc.get('content', '')
            context_parts.append(f"[{i}] Source: {source}\n{content}")

        context_text = "\n\n".join(context_parts)

        # Build prompt
        system_prompt = (
            "You are a helpful support assistant. Answer the user's question "
            "based on the provided context. If the context doesn't contain "
            "relevant information, say so honestly. Always cite sources "
            "using the [N] notation."
        )

        user_message = f"Context:\n\n{context_text}\n\nQuestion: {query}"

        messages = [{"role": "system", "content": system_prompt}]

        if chat_history:
            messages.extend(chat_history)

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.llm_client.chat(messages)
            return response
        except Exception as e:
            logger.error(f'LLM generation error: {e}')
            return "I'm sorry, I encountered an error generating the answer. Please try again."
