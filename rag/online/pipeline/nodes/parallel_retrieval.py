"""
Parallel Retrieval Node for Agentic RAG system.

Processes multiple sub-queries concurrently using ThreadPoolExecutor,
replacing the serial sub-query loop in the original graph.

Each sub-query runs a mini-pipeline:
    tool_selection → tool_execution → rerank → relevance_check
    ↻ retry (max_retries) via query_refiner

When parallel.enabled is false or there's only 1 sub-query, falls back
to serial execution using the same existing node logic.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Any, Dict, List

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config
from rag.utils.tracer import tracer

logger = logging.getLogger(__name__)


class ParallelRetrievalNode:
    """
    Parallel sub-query retrieval with per-sub-query retry loop.

    Replaces the LangGraph-level sub-query loop (tool_selection →
    tool_execution → rerank → relevance_check → query_refiner → ...)
    with a single node that handles all sub-queries concurrently.

    Features:
    - ThreadPoolExecutor-based parallelism for multiple sub-queries
    - Per-sub-query retry loop (relevance fail → refine → retry)
    - Configurable max_workers and per-sub-query timeout
    - Graceful fallback to serial when disabled or single sub-query
    """

    def __init__(self):
        self.config = get_config()
        self._parallel_enabled = self.config.get('parallel.enabled', True)
        self._max_workers = self.config.get('parallel.max_workers', 4)
        self._per_sub_timeout = self.config.get(
            'parallel.per_sub_query_timeout', 15,
        )
        self._max_retries = self.config.get('agent.max_retries', 2)
        self._relevance_threshold = self.config.get(
            'agent.relevance_threshold', 0.4,
        )

    def _process_single_sub_query(
        self,
        sub_query: Dict[str, Any],
        sub_idx: int,
        base_state: AgentStateDict,
    ) -> Dict[str, Any]:
        """
        Process a single sub-query through the mini-pipeline.

        Mini-pipeline:
            1. tool_selection → select tools for query
            2. tool_execution → execute tools
            3. rerank → Cross-Encoder rerank
            4. relevance_check → evaluate quality
            5. if FAIL and retries remain → query_refiner → goto 1

        Args:
            sub_query: Sub-query dict with 'query' and 'type'
            sub_idx: Index of this sub-query in the list
            base_state: The original agent state (for context)

        Returns:
            Dict with 'results', 'sub_query_idx', 'retry_count',
            'relevance_score', 'error' (if any)
        """
        query_text = sub_query.get('query', '')

        retry_count = 0
        current_query = query_text
        all_results = []

        while retry_count <= self._max_retries:
            try:
                # Create a minimal state for this sub-query
                temp_state: AgentStateDict = {
                    'query': query_text,
                    'rewritten_query': current_query,
                    'plan': None,
                    'messages': list(base_state.get('messages', [])),
                    'tool_calls': [],
                    'retrieval_results': [],
                    'final_answer': None,
                    'error': None,
                    'iterations': 0,
                    'current_state': 'tool_selection',
                    'sub_queries': [sub_query],
                    'current_sub_query_idx': 0,
                    'all_sub_results': [],
                    'retry_count': retry_count,
                    'max_retries': self._max_retries,
                    'relevance_scores': {},
                    'query_history': list(base_state.get('query_history', [])),
                    'faithfulness_score': 0.0,
                    'hallucination_flags': [],
                    'global_retry_count': 0,
                    'max_global_retries': 0,
                    'reranked_results': [],
                    'metadata': dict(base_state.get('metadata', {})),
                }

                # Step 1: Tool selection
                from rag.online.pipeline.nodes.tool_selection import (
                    tool_selection_node,
                )
                temp_state = tool_selection_node.process(temp_state)

                # Step 2: Tool execution
                from rag.online.pipeline.nodes.tool_execution import (
                    tool_execution_node,
                )
                temp_state = tool_execution_node.process(temp_state)

                # Step 3: Rerank
                from rag.online.pipeline.nodes.rerank import rerank_node
                temp_state = rerank_node.process(temp_state)

                # Step 4: Relevance check
                from rag.online.pipeline.nodes.relevance_check import (
                    relevance_check_node,
                )
                temp_state = relevance_check_node.process(temp_state)

                results = list(temp_state.get('retrieval_results', []))
                relevance_scores = temp_state.get('relevance_scores', {})
                current_score = relevance_scores.get(
                    str(retry_count), 0.0,
                )

                if current_score >= self._relevance_threshold:
                    # PASS: save and exit retry loop
                    for r in results:
                        r['sub_query_idx'] = sub_idx
                        r['sub_query'] = query_text
                    all_results = results

                    logger.info(
                        '✅ [Parallel] sub_query[%d/%d] PASS '
                        '(score=%.3f, results=%d, retries=%d) '
                        '"%s"',
                        sub_idx + 1, 1, current_score,
                        len(results), retry_count,
                        query_text[:50],
                    )
                    break
                else:
                    # FAIL: refine and retry
                    if retry_count < self._max_retries:
                        logger.info(
                            '🔄 [Parallel] sub_query[%d] FAIL '
                            '(score=%.3f < %.2f), retry %d/%d: "%s"',
                            sub_idx, current_score,
                            self._relevance_threshold,
                            retry_count + 1, self._max_retries,
                            query_text[:50],
                        )

                        from rag.online.pipeline.nodes.query_refiner import (
                            query_refiner_node,
                        )
                        temp_state = query_refiner_node.process(temp_state)
                        current_query = (
                            temp_state.get('rewritten_query', '')
                            or current_query
                        )
                        retry_count += 1
                    else:
                        # Max retries: save best-effort results
                        for r in results:
                            r['sub_query_idx'] = sub_idx
                            r['sub_query'] = query_text
                        all_results = results

                        logger.warning(
                            '⚠️ [Parallel] sub_query[%d] exhausted '
                            'retries (score=%.3f), using best-effort '
                            '(%d results): "%s"',
                            sub_idx, current_score,
                            len(results),
                            query_text[:50],
                        )
                        break

            except Exception as e:
                logger.error(
                    '❌ [Parallel] sub_query[%d] error: %s '
                    '(query="%s")',
                    sub_idx, e, query_text[:50],
                )
                return {
                    'results': [],
                    'sub_query_idx': sub_idx,
                    'retry_count': retry_count,
                    'relevance_score': 0.0,
                    'error': str(e),
                }

        return {
            'results': all_results,
            'sub_query_idx': sub_idx,
            'retry_count': retry_count,
            'relevance_score': (
                temp_state.get('relevance_scores', {})
                .get(str(retry_count), 0.0)
            ),
            'error': None,
        }

    def _run_serial(
        self,
        sub_queries: List[Dict[str, Any]],
        base_state: AgentStateDict,
    ) -> List[Dict[str, Any]]:
        """Run sub-queries serially (fallback / single sub-query)."""
        all_results = []
        for idx, sq in enumerate(sub_queries):
            result = self._process_single_sub_query(sq, idx, base_state)
            all_results.append(result)
        return all_results

    def _run_parallel(
        self,
        sub_queries: List[Dict[str, Any]],
        base_state: AgentStateDict,
    ) -> List[Dict[str, Any]]:
        """Run sub-queries in parallel via ThreadPoolExecutor."""
        num_workers = min(len(sub_queries), self._max_workers)
        results_by_idx: Dict[int, Dict[str, Any]] = {}

        logger.info(
            '🚀 [Parallel] Processing %d sub-queries with %d workers '
            '(timeout=%ds each)',
            len(sub_queries), num_workers,
            self._per_sub_timeout,
        )

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {}
            for idx, sq in enumerate(sub_queries):
                future = executor.submit(
                    self._process_single_sub_query,
                    sq, idx, base_state,
                )
                futures[future] = idx

            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result(
                        timeout=self._per_sub_timeout,
                    )
                    results_by_idx[idx] = result
                except TimeoutError:
                    logger.error(
                        '⏰ [Parallel] sub_query[%d] timed out '
                        'after %ds: "%s"',
                        idx, self._per_sub_timeout,
                        sub_queries[idx].get('query', '')[:50],
                    )
                    results_by_idx[idx] = {
                        'results': [],
                        'sub_query_idx': idx,
                        'retry_count': 0,
                        'relevance_score': 0.0,
                        'error': 'timeout',
                    }
                except Exception as e:
                    logger.error(
                        '❌ [Parallel] sub_query[%d] failed: %s',
                        idx, e,
                    )
                    results_by_idx[idx] = {
                        'results': [],
                        'sub_query_idx': idx,
                        'retry_count': 0,
                        'relevance_score': 0.0,
                        'error': str(e),
                    }

        # Return results in original sub-query order
        return [
            results_by_idx.get(i, {
                'results': [],
                'sub_query_idx': i,
                'retry_count': 0,
                'relevance_score': 0.0,
                'error': 'missing',
            })
            for i in range(len(sub_queries))
        ]

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Process all sub-queries (parallel or serial).

        Args:
            state: Agent state with sub_queries populated

        Returns:
            Updated state with all_sub_results populated
        """
        sub_queries = list(state.get('sub_queries', []))
        if not sub_queries:
            logger.warning('[Parallel] No sub-queries to process')
            return state

        tracer.start_node('parallel_retrieval', {
            'sub_query_count': len(sub_queries),
            'parallel_enabled': self._parallel_enabled,
        })

        # Choose execution mode
        if self._parallel_enabled and len(sub_queries) > 1:
            per_sub_results = self._run_parallel(sub_queries, state)
        else:
            per_sub_results = self._run_serial(sub_queries, state)

        # Collect all results
        all_results = []
        total_retries = 0
        errors = []
        for r in per_sub_results:
            all_results.extend(r.get('results', []))
            total_retries += r.get('retry_count', 0)
            if r.get('error'):
                errors.append(
                    f"sub_query[{r['sub_query_idx']}]: {r['error']}",
                )

        state['all_sub_results'] = all_results
        state['parallel_sub_results'] = per_sub_results
        state['parallel_errors'] = errors

        tracer.end_node('parallel_retrieval', {
            'total_results': len(all_results),
            'total_retries': total_retries,
            'errors': errors,
            'parallel': self._parallel_enabled and len(sub_queries) > 1,
        })

        logger.info(
            '[Parallel] Complete: %d sub-queries → %d results '
            '(retries=%d, errors=%d, parallel=%s)',
            len(sub_queries), len(all_results),
            total_retries, len(errors),
            self._parallel_enabled and len(sub_queries) > 1,
        )

        return state


# Global instance
parallel_retrieval_node = ParallelRetrievalNode()
