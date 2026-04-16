"""
Planning Node for Agentic RAG system.

Creates retrieval plans based on query type and available tools.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.agents.states import AgentStateDict, RetrievalPlan
from rag.core.config import get_config

logger = logging.getLogger(__name__)


class PlanningNode:
    """
    Planning node for LangGraph state machine.

    Responsibilities:
    - Analyze rewritten query
    - Determine which tools to use
    - Create multi-step retrieval plan if needed
    """

    def __init__(self):
        """Initialize the planning node."""
        self.config = get_config()

    def _determine_tools(self, query: str) -> List[str]:
        """
        Determine which tools to use for this query.

        Args:
            query: Rewritten query text

        Returns:
            List of tool names to use
        """
        tools = []

        # Always use vector search by default
        if self.config.get('tools.vector.enabled', True):
            tools.append('vector_search')

        # Use BM25 for keyword-heavy queries
        if self.config.get('tools.bm25.enabled', True):
            # Simple heuristic: queries with 3+ words may benefit from BM25
            if len(query.split()) >= 3:
                tools.append('bm25_search')

        # Use ensemble for multi-tool scenarios
        if len(tools) > 1 and self.config.get('tools.ensemble.enabled', True):
            tools.append('ensemble_retrieval')

        logger.debug(f'Selected tools for query: {tools}')
        return tools

    def _create_plan(self, query: str, tools: List[str]) -> RetrievalPlan:
        """
        Create a retrieval plan.

        Args:
            query: Rewritten query text
            tools: List of tools to use

        Returns:
            RetrievalPlan object
        """
        steps = []

        # Single tool: direct execution
        if len(tools) == 1:
            steps.append({
                'tool': tools[0],
                'arguments': {'query': query}
            })
        # Multiple tools: parallel execution then fusion
        elif len(tools) > 1:
            # Parallel tool execution
            for tool in tools:
                if tool != 'ensemble_retrieval':
                    steps.append({
                        'tool': tool,
                        'arguments': {'query': query},
                        'parallel': True
                    })
            # Fusion step
            steps.append({
                'tool': 'ensemble_retrieval',
                'arguments': {'retrieval_results': []},
                'depends_on': [s['tool'] for s in steps if s.get('parallel')]
            })

        return RetrievalPlan(
            steps=steps,
            tools=tools,
            iterations=0
        )

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Create retrieval plan.

        Args:
            state: Current agent state

        Returns:
            Updated state with plan
        """
        query = state.get('rewritten_query', '')

        logger.info(f'Creating retrieval plan for: "{query[:50]}..."')

        # Determine tools
        tools = self._determine_tools(query)

        # Create plan
        plan = self._create_plan(query, tools)

        # Update state
        state['plan'] = {
            'steps': plan.steps,
            'tools': plan.tools,
            'iterations': plan.iterations
        }

        logger.debug(f'Retrieval plan created: {plan.tools}')
        return state


# Global instance
planning_node = PlanningNode()
