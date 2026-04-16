"""
Retrieval Agent using LangGraph for Agentic RAG system.

Orchestrates the state machine with nodes:
- query_understanding: Rewrite query with conversation history
- planning: Create retrieval plan
- tool_execution: Execute retrieval tools
- synthesis: Generate final answer

Features:
- Timeout protection
- Iteration limits
- Error handling with fallback to simple retrieval
"""
import logging
import signal
from typing import Any, Dict, List, Optional, Annotated
from contextlib import contextmanager

from langgraph.graph import StateGraph, END
from rag.agents.states import AgentStateDict
from rag.agents.nodes.query_understanding import query_understanding_node
from rag.agents.nodes.planning import planning_node
from rag.agents.nodes.tool_execution import tool_execution_node
from rag.agents.nodes.synthesis import synthesis_node
from rag.core.config import get_config

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Custom timeout error for agent execution."""
    pass


@contextmanager
def timeout_handler(seconds: int):
    """Context manager for timeout protection."""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    # Set the signal handler (Unix only)
    original_handler = signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


class RetrievalAgent:
    """
    Agentic RAG retrieval agent using LangGraph.

    State machine flow:
    START -> query_understanding -> planning -> tool_execution -> synthesis -> END

    Protection features:
    - Timeout protection (configurable)
    - Maximum iteration limits
    - Fallback to simple retrieval on error
    """

    def __init__(self):
        """Initialize the retrieval agent."""
        self.config = get_config()
        self.max_iterations = self.config.get('agent.max_iterations', 3)
        self.timeout_seconds = self.config.get('agent.timeout_seconds', 30)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph state machine.

        Returns:
            Compiled StateGraph
        """
        # Create state graph
        builder = StateGraph(AgentStateDict)

        # Add nodes
        builder.add_node('query_understanding', self._run_query_understanding)
        builder.add_node('planning', self._run_planning)
        builder.add_node('tool_execution', self._run_tool_execution)
        builder.add_node('synthesis', self._run_synthesis)

        # Set entry point
        builder.set_entry_point('query_understanding')

        # Add edges
        builder.add_edge('query_understanding', 'planning')
        builder.add_edge('planning', 'tool_execution')
        builder.add_edge('tool_execution', 'synthesis')
        builder.add_edge('synthesis', END)

        # Compile graph
        return builder.compile()

    def _run_query_understanding(self, state: AgentStateDict) -> AgentStateDict:
        """Run query understanding node."""
        return query_understanding_node.process(state)

    def _run_planning(self, state: AgentStateDict) -> AgentStateDict:
        """Run planning node."""
        return planning_node.process(state)

    def _run_tool_execution(self, state: AgentStateDict) -> AgentStateDict:
        """Run tool execution node."""
        return tool_execution_node.process(state)

    def _run_synthesis(self, state: AgentStateDict) -> AgentStateDict:
        """Run synthesis node."""
        return synthesis_node.process(state)

    def run(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the agent on a query.

        Args:
            query: User query text
            session_id: Optional session ID for chat history

        Returns:
            Dict with 'success', 'answer', 'retrieval_results', 'metadata'
        """
        logger.info(f'Running agentic retrieval on query: "{query[:50]}..."')

        # Initialize state
        initial_state: AgentStateDict = {
            'query': query,
            'rewritten_query': '',
            'plan': None,
            'messages': [],
            'tool_calls': [],
            'retrieval_results': [],
            'final_answer': None,
            'error': None,
            'iterations': 0,
            'current_state': 'start',
            'metadata': {'session_id': session_id}
        }

        try:
            # Run state machine with timeout protection
            with timeout_handler(self.timeout_seconds):
                final_state = self._graph.invoke(initial_state)

            # Check iteration count
            iterations = final_state.get('iterations', 0)
            if iterations > self.max_iterations:
                logger.warning(f'Agent exceeded max iterations ({iterations} > {self.max_iterations})')
                final_state['error'] = f'Exceeded maximum iterations ({self.max_iterations})'

            return {
                'success': True,
                'answer': final_state.get('final_answer'),
                'retrieval_results': final_state.get('retrieval_results', []),
                'metadata': {
                    'rewritten_query': final_state.get('rewritten_query'),
                    'iterations': iterations,
                    'mode': 'agentic'
                }
            }

        except TimeoutError as e:
            logger.warning(f'Agent timed out after {self.timeout_seconds}s')
            return {
                'success': False,
                'answer': None,
                'retrieval_results': [],
                'error': str(e),
                'metadata': {'mode': 'agentic', 'timeout': True}
            }

        except Exception as e:
            logger.error(f'Agent run failed: {e}', exc_info=True)
            return {
                'success': False,
                'answer': None,
                'retrieval_results': [],
                'error': str(e),
                'metadata': {'mode': 'agentic'}
            }

    def run_with_fallback(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the agent with fallback to simple retrieval.

        If agentic retrieval fails, falls back to simple vector search.

        Args:
            query: User query text
            session_id: Optional session ID for chat history

        Returns:
            Dict with 'success', 'answer', 'retrieval_results', 'metadata'
        """
        result = self.run(query, session_id)

        if result['success'] and result['answer']:
            return result

        # Fallback: return error result, caller can decide to use simple retrieval
        logger.warning('Agentic retrieval failed, caller may want to use simple retrieval as fallback')
        return result


# Global instance
retrieval_agent = RetrievalAgent()
