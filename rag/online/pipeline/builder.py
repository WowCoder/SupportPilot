"""
Retrieval Agent using LangGraph for Agentic RAG system.

Agentic graph with self-correction loops:

    START -> query_understanding -> query_decomposition
                                        |
                    [simple]    [compound: sub_query_loop]
                        |               |
                        v               v
                    tool_selection <----+
                        |
                        v
                    tool_execution
                        |
                        v
                    relevance_check
                   /                \
            [pass]                  [fail, retry<max]
              |                         |
              v                         v
         result_aggregation        query_refiner
              |                         |
              v                         v
         answer_generation         tool_selection (loop)
              |
              v
         faithfulness_check
         /                \
    [pass]              [fail]
      |                   |
      v                   v
     END             query_refiner (re-retrieve)

Features:
- Self-correction loop with configurable max retries
- LLM-driven query decomposition for compound queries
- Relevance check gate before answer generation
- Faithfulness verification to prevent hallucinations
- Timeout protection and fallback to simple retrieval
"""
import logging
import signal
from typing import Any, Dict, List, Optional, Literal
from contextlib import contextmanager

from langgraph.graph import StateGraph, END
from rag.online.pipeline.state import AgentStateDict
from rag.online.pipeline.nodes.query_understanding import query_understanding_node
from rag.online.pipeline.nodes.query_decomposition import query_decomposition_node
from rag.online.pipeline.nodes.tool_selection import tool_selection_node
from rag.online.pipeline.nodes.tool_execution import tool_execution_node
from rag.online.pipeline.nodes.relevance_check import relevance_check_node
from rag.online.pipeline.nodes.query_refiner import query_refiner_node
from rag.online.pipeline.nodes.result_aggregation import result_aggregation_node
from rag.online.pipeline.nodes.synthesis import synthesis_node
from rag.online.pipeline.nodes.faithfulness_check import faithfulness_check_node
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Custom timeout error for agent execution."""
    pass


@contextmanager
def timeout_handler(seconds: int):
    """Context manager for timeout protection."""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    original_handler = signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


# ---- Conditional Edge Functions ----

def route_after_decomposition(state: AgentStateDict) -> Literal['tool_selection', 'sub_query_loop']:
    """
    After decomposition, decide whether to enter sub-query loop.

    sub_queries length == 1: go directly to tool_selection
    sub_queries length > 1: enter sub_query_loop (process each via tool_selection)
    """
    sub_queries = state.get('sub_queries', [])
    if len(sub_queries) <= 1:
        return 'tool_selection'
    return 'tool_selection'  # Both go to tool_selection; sub-query loop managed by state


def route_after_tool_execution(state: AgentStateDict) -> Literal['relevance_check']:
    """After tool execution, always go to relevance check."""
    return 'relevance_check'


def route_after_relevance(state: AgentStateDict) -> Literal['result_aggregation', 'query_refiner']:
    """
    After relevance check, decide next step.

    - If score >= threshold: proceed to result_aggregation
    - If score < threshold and retries remaining: go to query_refiner
    - If score < threshold and max retries: go to result_aggregation (degraded)
    """
    retry_count = state.get('retry_count', 0)
    max_retries = state.get('max_retries', 2)
    relevance_scores = state.get('relevance_scores', {})

    current_score = relevance_scores.get(str(retry_count), 0.0)
    threshold = get_config().get('agent.relevance_threshold', 0.3)

    if current_score >= threshold:
        logger.info(f'Relevance PASS (score={current_score:.3f} >= {threshold}), proceeding to aggregation')
        return 'result_aggregation'

    if retry_count < max_retries:
        logger.info(f'Relevance FAIL (score={current_score:.3f} < {threshold}), '
                   f'retrying ({retry_count + 1}/{max_retries})')
        return 'query_refiner'

    logger.warning(f'Relevance FAIL after {max_retries} retries, falling back to best-effort aggregation')
    return 'result_aggregation'


def route_after_refine(state: AgentStateDict) -> Literal['tool_selection']:
    """After query refinement, go back to tool selection."""
    # Check if there are more sub-queries to process
    sub_queries = state.get('sub_queries', [])
    current_idx = state.get('current_sub_query_idx', 0)
    retry_count = state.get('retry_count', 0)
    max_retries = state.get('max_retries', 2)

    # If we still have sub-queries to process and haven't exhausted retries
    if current_idx < len(sub_queries) - 1 and retry_count <= max_retries:
        state['current_sub_query_idx'] = current_idx + 1

    return 'tool_selection'


def route_after_faithfulness(state: AgentStateDict) -> Literal['__end__', 'query_refiner']:
    """
    After faithfulness check, decide whether to end or re-retrieve.

    - If score >= threshold: END
    - If score < threshold and retries remaining: re-retrieve
    - If score < threshold and no retries: END anyway (best effort)
    """
    score = state.get('faithfulness_score', 1.0)
    threshold = get_config().get('agent.faithfulness_threshold', 0.8)
    retry_count = state.get('retry_count', 0)
    max_retries = state.get('max_retries', 2)

    if score >= threshold:
        logger.info(f'Faithfulness PASS (score={score:.2f}), ending')
        return '__end__'

    if retry_count < max_retries:
        logger.warning(f'Faithfulness FAIL (score={score:.2f} < {threshold}), re-retrieving')
        return 'query_refiner'

    logger.warning(f'Faithfulness FAIL with no retries remaining, ending with best effort')
    return '__end__'


class RetrievalAgent:
    """
    Agentic RAG retrieval agent with self-correction.

    Graph flow:
    START -> query_understanding -> query_decomposition -> tool_selection
      -> tool_execution -> relevance_check
         ├─ [pass] -> result_aggregation -> answer_generation -> faithfulness_check
         │     ├─ [pass] -> END
         │     └─ [fail] -> query_refiner -> tool_selection (loop)
         └─ [fail] -> query_refiner -> tool_selection (loop)

    Protection features:
    - Max retry limits prevent infinite loops
    - Query history tracking prevents duplicate attempts
    - Timeout protection for the entire graph execution
    - Fallback to simple retrieval on catastrophic failure
    """

    def __init__(self):
        """Initialize the retrieval agent and build the graph."""
        self.config = get_config()
        self.max_iterations = self.config.get('agent.max_iterations', 3)
        self.timeout_seconds = self.config.get('agent.timeout_seconds', 30)
        self.max_retries = self.config.get('agent.max_retries', 2)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine with conditional edges."""
        builder = StateGraph(AgentStateDict)

        # Add all nodes
        builder.add_node('query_understanding', self._run_query_understanding)
        builder.add_node('query_decomposition', self._run_query_decomposition)
        builder.add_node('tool_selection', self._run_tool_selection)
        builder.add_node('tool_execution', self._run_tool_execution)
        builder.add_node('relevance_check', self._run_relevance_check)
        builder.add_node('query_refiner', self._run_query_refiner)
        builder.add_node('result_aggregation', self._run_result_aggregation)
        builder.add_node('answer_generation', self._run_synthesis)
        builder.add_node('faithfulness_check', self._run_faithfulness_check)

        # Entry point
        builder.set_entry_point('query_understanding')

        # Fixed edges
        builder.add_edge('query_understanding', 'query_decomposition')
        builder.add_edge('query_decomposition', 'tool_selection')
        builder.add_edge('tool_selection', 'tool_execution')
        builder.add_edge('tool_execution', 'relevance_check')

        # Conditional edges: the self-correction loop
        builder.add_conditional_edges(
            'relevance_check',
            route_after_relevance,
            {
                'result_aggregation': 'result_aggregation',
                'query_refiner': 'query_refiner',
            }
        )

        # After refinement, loop back to tool selection
        builder.add_edge('query_refiner', 'tool_selection')

        # Aggregation -> answer generation -> faithfulness check
        builder.add_edge('result_aggregation', 'answer_generation')
        builder.add_edge('answer_generation', 'faithfulness_check')

        # Faithfulness: either end or re-retrieve
        builder.add_conditional_edges(
            'faithfulness_check',
            route_after_faithfulness,
            {
                '__end__': END,
                'query_refiner': 'query_refiner',
            }
        )

        return builder.compile()

    # ---- Node Runners ----

    def _run_query_understanding(self, state: AgentStateDict) -> AgentStateDict:
        return query_understanding_node.process(state)

    def _run_query_decomposition(self, state: AgentStateDict) -> AgentStateDict:
        return query_decomposition_node.process(state)

    def _run_tool_selection(self, state: AgentStateDict) -> AgentStateDict:
        return tool_selection_node.process(state)

    def _run_tool_execution(self, state: AgentStateDict) -> AgentStateDict:
        return tool_execution_node.process(state)

    def _run_relevance_check(self, state: AgentStateDict) -> AgentStateDict:
        return relevance_check_node.process(state)

    def _run_query_refiner(self, state: AgentStateDict) -> AgentStateDict:
        return query_refiner_node.process(state)

    def _run_result_aggregation(self, state: AgentStateDict) -> AgentStateDict:
        return result_aggregation_node.process(state)

    def _run_synthesis(self, state: AgentStateDict) -> AgentStateDict:
        return synthesis_node.process(state)

    def _run_faithfulness_check(self, state: AgentStateDict) -> AgentStateDict:
        return faithfulness_check_node.process(state)

    # ---- Public API ----

    def run(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the agentic retrieval graph on a query.

        Args:
            query: User query text
            session_id: Optional session ID for conversation history

        Returns:
            Dict with 'success', 'answer', 'retrieval_results', 'metadata'
        """
        logger.info(f'Running agentic retrieval: "{query[:50]}..."')

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

            # Query decomposition
            'sub_queries': [],
            'current_sub_query_idx': 0,
            'all_sub_results': [],

            # Self-correction
            'retry_count': 0,
            'max_retries': self.max_retries,
            'relevance_scores': {},
            'query_history': [],

            # Faithfulness
            'faithfulness_score': 0.0,
            'hallucination_flags': [],

            # Metadata
            'metadata': {'session_id': session_id}
        }

        try:
            with timeout_handler(self.timeout_seconds):
                final_state = self._graph.invoke(initial_state)

            iterations = final_state.get('iterations', 0)
            retry_count = final_state.get('retry_count', 0)

            if iterations > self.max_iterations:
                logger.warning(f'Agent exceeded max iterations ({iterations} > {self.max_iterations})')

            answer = final_state.get('final_answer')
            results = final_state.get('retrieval_results', [])
            relevance_scores = final_state.get('relevance_scores', {})
            faithfulness = final_state.get('faithfulness_score', 0.0)

            logger.info(f'Agent complete: answer={bool(answer)} results={len(results)} '
                       f'retries={retry_count} relevance={relevance_scores} faithfulness={faithfulness:.2f}')

            return {
                'success': True,
                'answer': answer,
                'retrieval_results': list(results),
                'metadata': {
                    'rewritten_query': final_state.get('rewritten_query'),
                    'iterations': iterations,
                    'retry_count': retry_count,
                    'relevance_scores': relevance_scores,
                    'faithfulness_score': faithfulness,
                    'hallucination_flags': list(final_state.get('hallucination_flags', [])),
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

        If agentic retrieval fails, caller can use simple vector search.
        """
        result = self.run(query, session_id)

        if result['success'] and result['answer']:
            return result

        logger.warning('Agentic retrieval failed, caller should fall back to simple retrieval')
        return result


# Global instance
retrieval_agent = RetrievalAgent()
