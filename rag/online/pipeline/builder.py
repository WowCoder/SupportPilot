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
from typing import Any, Dict, Optional, Literal
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
from rag.online.pipeline.nodes.rerank import rerank_node
from rag.online.pipeline.nodes.parallel_retrieval import parallel_retrieval_node
from rag.utils.config import get_config
from rag.utils.tracer import tracer

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


def _save_sub_query_results(state: AgentStateDict) -> None:
    """
    Save current sub-query's retrieval results into all_sub_results.

    Tags each result with its sub_query metadata for downstream aggregation.
    """
    current_results = list(state.get('retrieval_results', []))
    all_sub_results = list(state.get('all_sub_results', []))
    sub_idx = state.get('current_sub_query_idx', 0)
    sub_queries = list(state.get('sub_queries', []))

    sub_query_text = ''
    if sub_idx < len(sub_queries):
        sub_query_text = sub_queries[sub_idx].get('query', '')

    for r in current_results:
        r['sub_query_idx'] = sub_idx
        r['sub_query'] = sub_query_text

    all_sub_results.extend(current_results)
    state['all_sub_results'] = all_sub_results

    logger.info(
        '💾 [Sub-Query Loop] Saved %d results from sub_query[%d/%d] '
        '("…%s") → all_sub_results total: %d',
        len(current_results), sub_idx + 1, len(sub_queries),
        sub_query_text[:40] if sub_query_text else '?',
        len(all_sub_results),
    )


def _move_to_next_sub_query(state: AgentStateDict) -> bool:
    """
    Advance to the next sub-query if available.

    Returns True if there is a next sub-query, False if all done.
    """
    sub_queries = list(state.get('sub_queries', []))
    current_idx = state.get('current_sub_query_idx', 0)

    if current_idx + 1 < len(sub_queries):
        state['current_sub_query_idx'] = current_idx + 1
        state['retry_count'] = 0
        state['retrieval_results'] = []
        state['reranked_results'] = []
        logger.info(f'Moving to sub_query[{current_idx + 1}/{len(sub_queries)}]')
        return True
    return False


def route_after_relevance(
    state: AgentStateDict,
) -> Literal['tool_selection', 'result_aggregation', 'query_refiner']:
    """
    After relevance check, manage sub-query loop and retries.

    - PASS + more sub_queries  → tool_selection (next sub-query)
    - PASS + all done          → result_aggregation
    - FAIL + retries remaining → query_refiner (retry SAME sub-query)
    - FAIL + max retries       → accumulate best-effort, continue to next or aggregate
    """
    retry_count = state.get('retry_count', 0)
    max_retries = state.get('max_retries', 2)
    relevance_scores = state.get('relevance_scores', {})
    current_score = relevance_scores.get(str(retry_count), 0.0)
    threshold = get_config().get('agent.relevance_threshold', 0.4)

    if current_score >= threshold:
        # ✅ PASS: save results, move to next sub-query or aggregate
        logger.info(
            f'Relevance PASS (score={current_score:.3f} >= {threshold})'
        )
        _save_sub_query_results(state)

        if _move_to_next_sub_query(state):
            tracer.record_decision(
                'relevance_check', 'pass_next_sub_query',
                reason=(
                    f'score={current_score:.3f} >= {threshold}, '
                    f'moving to next sub-query'
                ),
                metadata={
                    'score': current_score, 'threshold': threshold,
                    'next_idx': state.get('current_sub_query_idx', 0),
                },
            )
            return 'tool_selection'
        else:
            tracer.record_decision(
                'relevance_check', 'pass_aggregate',
                reason=(
                    f'score={current_score:.3f} >= {threshold}, '
                    f'all sub-queries done'
                ),
                metadata={'score': current_score, 'threshold': threshold},
            )
            logger.info('All sub-queries processed, proceeding to aggregation')
            return 'result_aggregation'

    # ❌ FAIL
    if retry_count < max_retries:
        logger.info(
            f'Relevance FAIL (score={current_score:.3f} < {threshold}), '
            f'retrying sub_query[{state.get("current_sub_query_idx", 0)}] '
            f'({retry_count + 1}/{max_retries})'
        )
        tracer.record_decision(
            'relevance_check', 'fail_retry',
            reason=(
                f'score={current_score:.3f} < {threshold}, '
                f'retry {retry_count + 1}/{max_retries}'
            ),
            metadata={
                'score': current_score, 'threshold': threshold,
                'retry_count': retry_count, 'max_retries': max_retries,
            },
        )
        return 'query_refiner'

    # Max retries exhausted: save best-effort results and move on
    logger.warning(
        f'Relevance FAIL after {max_retries} retries for '
        f'sub_query[{state.get("current_sub_query_idx", 0)}], '
        f'continuing with best-effort results'
    )
    _save_sub_query_results(state)
    tracer.record_decision(
        'relevance_check', 'fail_exhausted',
        reason=(
            f'score={current_score:.3f} < {threshold}, '
            f'max retries ({max_retries}) exhausted'
        ),
        metadata={
            'score': current_score, 'threshold': threshold,
            'retry_count': retry_count,
        },
    )

    if _move_to_next_sub_query(state):
        return 'tool_selection'
    else:
        return 'result_aggregation'


def route_after_refine(state: AgentStateDict) -> Literal['tool_selection']:
    """
    After query refinement, loop back to tool selection.

    NOTE: sub_query_idx is NOT incremented here — we're retrying the
    SAME sub-query with a refined query. The sub-query loop advances
    only on relevance PASS in route_after_relevance.
    """
    return 'tool_selection'


def route_after_faithfulness(
    state: AgentStateDict,
) -> Literal['__end__', 'query_refiner']:
    """
    After faithfulness check, decide whether to end or trigger global re-retrieval.

    - score >= threshold → END
    - score < threshold + global retries remaining → reset and re-retrieve all sub-queries
    - score < threshold + no global retries → END (best effort)
    """
    score = state.get('faithfulness_score', 1.0)
    threshold = get_config().get('agent.faithfulness_threshold', 0.7)
    global_retry = state.get('global_retry_count', 0)
    max_global = state.get('max_global_retries', 1)

    if score >= threshold:
        logger.info(f'Faithfulness PASS (score={score:.2f} >= {threshold}), ending')
        tracer.record_decision(
            'faithfulness_check', 'pass_end',
            reason=(
                f'score={score:.2f} >= {threshold}, '
                f'answer accepted'
            ),
            metadata={'score': score, 'threshold': threshold},
        )
        return '__end__'

    if global_retry < max_global:
        logger.warning(
            f'Faithfulness FAIL (score={score:.2f} < {threshold}), '
            f'triggering global re-retrieval ({global_retry + 1}/{max_global})'
        )
        tracer.record_decision(
            'faithfulness_check', 'fail_global_retry',
            reason=(
                f'score={score:.2f} < {threshold}, '
                f'global retry {global_retry + 1}/{max_global}'
            ),
            metadata={
                'score': score, 'threshold': threshold,
                'global_retry': global_retry, 'max_global': max_global,
            },
        )
        # Reset sub-query state for full re-retrieval
        state['global_retry_count'] = global_retry + 1
        state['current_sub_query_idx'] = 0
        state['retry_count'] = 0
        state['all_sub_results'] = []
        state['retrieval_results'] = []
        state['reranked_results'] = []
        return 'query_refiner'

    logger.warning(
        f'Faithfulness FAIL with no global retries remaining, '
        f'ending with best effort (score={score:.2f})'
    )
    tracer.record_decision(
        'faithfulness_check', 'fail_exhausted',
        reason=(
            f'score={score:.2f} < {threshold}, '
            f'no global retries left, best effort'
        ),
        metadata={
            'score': score, 'threshold': threshold,
            'global_retry': global_retry,
        },
    )
    return '__end__'


class RetrievalAgent:
    r"""
    Agentic RAG retrieval agent with self-correction and parallel sub-queries.

    Simplified graph (Phase 1 optimization):

        START -> query_understanding -> query_decomposition
                    |
                    v
             parallel_retrieval  <-------------------
                    |                                |
                    v                                |
             result_aggregation (RRF + MMR)          |
                    |                                |
                    v                                |
             answer_generation                       |
                    |                                |
                    v                                |
             faithfulness_check                      |
                /            \                       |
           [pass]            [fail]                  |
             |                 |                     |
             v                 v                     |
            END          query_refiner --------------

    parallel_retrieval internally handles:
    - tool_selection -> tool_execution -> rerank -> relevance_check
      for each sub-query (concurrently via ThreadPoolExecutor)
    - Per-sub-query retry loop (relevance fail -> refine -> retry)

    Protection features:
    - Max retry limits prevent infinite loops
    - Query history tracking prevents duplicate attempts
    - Timeout protection for the entire graph execution
    - Parallel sub-query execution (configurable, falls back to serial)
    """

    def __init__(self):
        """Initialize the retrieval agent and build the graph."""
        self.config = get_config()
        self.max_iterations = self.config.get('agent.max_iterations', 3)
        self.timeout_seconds = self.config.get('agent.timeout_seconds', 30)
        self.max_retries = self.config.get('agent.max_retries', 2)
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        r"""Build the LangGraph state machine with conditional edges.

        Simplified graph with parallel sub-query execution:

            START -> query_understanding -> query_decomposition
                        |
                        v
                 parallel_retrieval  <-------------------
                        |                                |
                        v                                |
                 result_aggregation                      |
                        |                                |
                        v                                |
                 answer_generation                       |
                        |                                |
                        v                                |
                 faithfulness_check                      |
                    /            \                       |
               [pass]            [fail]                  |
                 |                 |                     |
                 v                 v                     |
                END          query_refiner --------------

        When parallel.enabled is false, parallel_retrieval falls back
        to serial execution internally, maintaining backward compatibility.
        """
        builder = StateGraph(AgentStateDict)

        # Add all nodes (simplified: tool_selection/execution/rerank/
        # relevance_check are internal to parallel_retrieval)
        builder.add_node('query_understanding', self._run_query_understanding)
        builder.add_node('query_decomposition', self._run_query_decomposition)
        builder.add_node('parallel_retrieval', self._run_parallel_retrieval)
        builder.add_node('result_aggregation', self._run_result_aggregation)
        builder.add_node('answer_generation', self._run_synthesis)
        builder.add_node('faithfulness_check', self._run_faithfulness_check)
        builder.add_node('query_refiner', self._run_query_refiner)

        # Entry point
        builder.set_entry_point('query_understanding')

        # Fixed edges: understanding → decomposition → parallel_retrieval
        builder.add_edge('query_understanding', 'query_decomposition')
        builder.add_edge('query_decomposition', 'parallel_retrieval')

        # Parallel retrieval → aggregation → answer → faithfulness
        builder.add_edge('parallel_retrieval', 'result_aggregation')
        builder.add_edge('result_aggregation', 'answer_generation')
        builder.add_edge('answer_generation', 'faithfulness_check')

        # After refinement (global retry), loop back to parallel_retrieval
        builder.add_edge('query_refiner', 'parallel_retrieval')

        # Faithfulness: either end or trigger global re-retrieval
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
        tracer.start_node('query_understanding', {
            'query': state.get('query', ''),
            'session_id': state.get('metadata', {}).get('session_id'),
        })
        result = query_understanding_node.process(state)
        tracer.end_node('query_understanding', {
            'rewritten_query': result.get('rewritten_query', ''),
            'was_rewritten': result.get('rewritten_query', '') != result.get('query', ''),
            'history_count': len(result.get('messages', [])),
        })
        return result

    def _run_query_decomposition(self, state: AgentStateDict) -> AgentStateDict:
        tracer.start_node('query_decomposition', {
            'rewritten_query': state.get('rewritten_query', '') or state.get('query', ''),
        })
        result = query_decomposition_node.process(state)
        sub_queries = list(result.get('sub_queries', []))
        tracer.end_node('query_decomposition', {
            'sub_query_count': len(sub_queries),
            'sub_queries': [{'query': sq.get('query', '')[:80],
                             'type': sq.get('type', '')}
                            for sq in sub_queries],
            'is_compound': len(sub_queries) > 1,
        })
        return result

    def _run_tool_selection(self, state: AgentStateDict) -> AgentStateDict:
        sub_idx = state.get('current_sub_query_idx', 0)
        retry = state.get('retry_count', 0)
        tracer.start_node('tool_selection', {
            'sub_query_idx': sub_idx,
            'retry_count': retry,
        })
        result = tool_selection_node.process(state)
        plan = result.get('plan', {})
        tracer.end_node('tool_selection', {
            'tools': plan.get('tools', []),
            'query_type': plan.get('query_type', ''),
            'reasoning': plan.get('reasoning', ''),
            'params': plan.get('steps', [{}])[0].get('arguments', {}) if plan.get('steps') else {},
        })
        return result

    def _run_tool_execution(self, state: AgentStateDict) -> AgentStateDict:
        plan = state.get('plan', {})
        tracer.start_node('tool_execution', {
            'tools': plan.get('tools', []),
            'steps_count': len(plan.get('steps', [])),
        })
        result = tool_execution_node.process(state)
        retrieval_count = len(result.get('retrieval_results', []))
        tracer.end_node('tool_execution', {
            'result_count': retrieval_count,
            'top_scores': [
                {'score': round(r.get('similarity', r.get('score', 0)), 3),
                 'source': str(r.get('source', ''))[:60]}
                for r in list(result.get('retrieval_results', []))[:3]
            ],
        })
        return result

    def _run_relevance_check(self, state: AgentStateDict) -> AgentStateDict:
        tracer.start_node('relevance_check', {
            'results_count': len(state.get('retrieval_results', [])),
            'retry_count': state.get('retry_count', 0),
        })
        result = relevance_check_node.process(state)
        scores = result.get('relevance_scores', {})
        retry = result.get('retry_count', 0)
        tracer.end_node('relevance_check', {
            'score': scores.get(str(retry), 0),
            'threshold': get_config().get('agent.relevance_threshold', 0.4),
            'all_scores': dict(scores),
        })
        return result

    def _run_query_refiner(self, state: AgentStateDict) -> AgentStateDict:
        current = state.get('rewritten_query', '') or state.get('query', '')
        tracer.start_node('query_refiner', {
            'current_query': current,
            'retry_count': state.get('retry_count', 0),
        })
        result = query_refiner_node.process(state)
        refined = result.get('rewritten_query', '')
        tracer.end_node('query_refiner', {
            'was_refined': refined != current,
            'refined_query': refined,
            'new_retry_count': result.get('retry_count', 0),
        })
        return result

    def _run_result_aggregation(self, state: AgentStateDict) -> AgentStateDict:
        all_sub = list(state.get('all_sub_results', []))
        tracer.start_node('result_aggregation', {
            'sub_result_count': len(all_sub),
            'current_result_count': len(state.get('retrieval_results', [])),
        })
        result = result_aggregation_node.process(state)
        merged = len(result.get('retrieval_results', []))
        tracer.end_node('result_aggregation', {
            'merged_count': merged,
        })
        return result

    def _run_synthesis(self, state: AgentStateDict) -> AgentStateDict:
        tracer.start_node('answer_generation', {
            'query': state.get('query', ''),
            'result_count': len(state.get('retrieval_results', [])),
        })
        result = synthesis_node.process(state)
        answer = result.get('final_answer', '') or ''
        tracer.end_node('answer_generation', {
            'answer_length': len(answer),
            'answer_preview': answer[:150] if answer else '(empty)',
        })
        return result

    def _run_faithfulness_check(self, state: AgentStateDict) -> AgentStateDict:
        tracer.start_node('faithfulness_check', {
            'answer_length': len(state.get('final_answer', '') or ''),
            'doc_count': len(state.get('retrieval_results', [])),
        })
        result = faithfulness_check_node.process(state)
        tracer.end_node('faithfulness_check', {
            'score': result.get('faithfulness_score', 0),
            'hallucinations': list(result.get('hallucination_flags', [])),
        })
        return result

    def _run_parallel_retrieval(self, state: AgentStateDict) -> AgentStateDict:
        tracer.start_node('parallel_retrieval', {
            'sub_query_count': len(state.get('sub_queries', [])),
            'parallel_enabled': self.config.get('parallel.enabled', True),
        })
        result = parallel_retrieval_node.process(state)
        all_results = len(result.get('all_sub_results', []))
        errors = list(result.get('parallel_errors', []))
        tracer.end_node('parallel_retrieval', {
            'total_results': all_results,
            'error_count': len(errors),
        })
        return result

    def _run_rerank(self, state: AgentStateDict) -> AgentStateDict:
        results_before = list(state.get('retrieval_results', []))
        tracer.start_node('rerank', {
            'candidate_count': len(results_before),
            'query': state.get('rewritten_query', '') or state.get('query', ''),
        })
        result = rerank_node.process(state)
        results_after = list(result.get('reranked_results', []))
        top_before = 0.0
        if results_before:
            r0 = results_before[0]
            top_before = round(r0.get('similarity', r0.get('score', 0)), 3)
        top_after = 0.0
        if results_after:
            r0 = results_after[0]
            top_after = round(
                r0.get('rerank_score', r0.get('similarity', 0)), 3
            )
        tracer.end_node('rerank', {
            'input_count': len(results_before),
            'output_count': len(results_after),
            'top_score_before': top_before,
            'top_score_after': top_after,
        })
        return result

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

        # Initialize trace
        tracer.start_trace(query, session_id)

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

            # Global retry (faithfulness failure triggers full re-retrieval)
            'global_retry_count': 0,
            'max_global_retries': self.config.get('agent.global_max_retries', 1),

            # Rerank
            'reranked_results': [],

            # Parallel retrieval (Phase 1)
            'parallel_sub_results': [],
            'parallel_errors': [],

            # Metadata
            'metadata': {'session_id': session_id}
        }

        try:
            with timeout_handler(self.timeout_seconds):
                final_state = self._graph.invoke(initial_state)

            iterations = final_state.get('iterations', 0)
            retry_count = final_state.get('retry_count', 0)

            if iterations > self.max_iterations:
                logger.warning(
                    f'Agent exceeded max iterations '
                    f'({iterations} > {self.max_iterations})'
                )

            answer = final_state.get('final_answer')
            results = final_state.get('retrieval_results', [])
            relevance_scores = final_state.get('relevance_scores', {})
            faithfulness = final_state.get('faithfulness_score', 0.0)

            logger.info(
                f'Agent complete: answer={bool(answer)} '
                f'results={len(results)} retries={retry_count} '
                f'relevance={relevance_scores} '
                f'faithfulness={faithfulness:.2f}'
            )

            trace_data = tracer.finish_trace()

            return {
                'success': True,
                'answer': answer,
                'retrieval_results': list(results),
                'trace': trace_data,
                'metadata': {
                    'rewritten_query': final_state.get('rewritten_query'),
                    'iterations': iterations,
                    'retry_count': retry_count,
                    'sub_query_count': len(final_state.get('sub_queries', [])),
                    'relevance_scores': relevance_scores,
                    'faithfulness_score': faithfulness,
                    'hallucination_flags': list(final_state.get('hallucination_flags', [])),
                    'mode': 'agentic'
                }
            }

        except TimeoutError as e:
            logger.warning(f'Agent timed out after {self.timeout_seconds}s')
            trace_data = tracer.finish_trace()
            return {
                'success': False,
                'answer': None,
                'retrieval_results': [],
                'trace': trace_data,
                'error': str(e),
                'metadata': {'mode': 'agentic', 'timeout': True}
            }

        except Exception as e:
            logger.error(f'Agent run failed: {e}', exc_info=True)
            trace_data = tracer.finish_trace()
            return {
                'success': False,
                'answer': None,
                'retrieval_results': [],
                'trace': trace_data,
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
