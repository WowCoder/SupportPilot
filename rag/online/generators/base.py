"""
Base classes for answer generators.

Generators produce the final answer from retrieved context
and the user's query, typically using an LLM.
"""

import logging

logger = logging.getLogger(__name__)


class BaseGenerator:
    """Abstract base class for answer generators."""

    def generate(self, query, context_docs, chat_history=None):
        """Generate an answer given the query and retrieved context.

        Args:
            query: The user's question
            context_docs: List of retrieved documents with 'content' keys
            chat_history: Optional list of prior messages

        Returns:
            Generated answer string
        """
        raise NotImplementedError
