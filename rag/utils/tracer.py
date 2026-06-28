"""
Structured Trace Collector for Agentic RAG Pipeline Observability.

Captures per-node execution events during pipeline runs and produces
a serializable trace dict for persistence and frontend visualization.

Design:
- Each pipeline node emits start/end events with input/output snapshots
- Conditional edges emit decision events (pass/fail + reason)
- Content fields are truncated to prevent oversized traces
- The finish_trace() output is designed for direct JSON serialization
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

MAX_CONTENT_LENGTH = 300       # Truncate document content fields
MAX_TRACE_SIZE_BYTES = 512 * 1024  # Hard cap on serialized trace (~512KB)
MAX_EVENTS = 200               # Safety cap on event count

# Chinese labels for each pipeline node
NODE_LABELS: Dict[str, str] = {
    'query_understanding': '查询理解',
    'query_decomposition': '查询分解',
    'tool_selection': '工具选择',
    'tool_execution': '工具执行',
    'rerank': '重排序',
    'relevance_check': '相关性检查',
    'query_refiner': '查询重写',
    'result_aggregation': '结果聚合',
    'answer_generation': '答案生成',
    'faithfulness_check': '忠实度校验',
}


# ── Data Classes ───────────────────────────────────────────────────────

@dataclass
class TraceEvent:
    """A single event in the pipeline trace."""
    node: str               # Node name (key into NODE_LABELS)
    phase: str              # "start" | "end" | "decision" | "error"
    timestamp_ms: float     # Milliseconds since trace start
    duration_ms: float = 0.0  # Node execution time (end events only)
    input: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Trace:
    """Complete trace of a single pipeline run."""
    trace_id: str
    query: str
    session_id: Optional[str]
    start_time: float       # time.time() epoch
    events: List[TraceEvent] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


# ── Helpers ────────────────────────────────────────────────────────────

def _truncate_text(text: str, max_len: int = MAX_CONTENT_LENGTH) -> str:
    """Truncate long text for trace storage."""
    if not text:
        return ''
    if len(text) <= max_len:
        return text
    return text[:max_len] + '…'


def _safe_snapshot(obj: Any, depth: int = 0) -> Any:
    """
    Create a JSON-safe, size-bounded snapshot of a value.

    Rules:
    - Strings are truncated
    - Lists are capped at 5 items
    - Dicts are recursed with the same rules
    - Max depth = 3 to prevent runaway recursion
    """
    if depth > 3:
        return '<max depth>'

    if isinstance(obj, str):
        return _truncate_text(obj)
    elif isinstance(obj, (int, float, bool, type(None))):
        return obj
    elif isinstance(obj, list):
        return [_safe_snapshot(item, depth + 1) for item in obj[:5]]
    elif isinstance(obj, dict):
        return {
            k: _safe_snapshot(v, depth + 1)
            for k, v in list(obj.items())[:20]
        }
    else:
        return _truncate_text(str(obj))


# ── TraceCollector ─────────────────────────────────────────────────────

class TraceCollector:
    """
    Collects structured trace events during a single pipeline run.

    Usage::

        tracer = TraceCollector()
        tracer.start_trace(query, session_id)

        tracer.start_node('tool_selection', {'sub_query': '...'})
        # ... node executes ...
        tracer.end_node('tool_selection', {'tools': ['vector_search'], 'reasoning': '...'})

        tracer.record_decision('relevance_check', 'pass',
            reason='score=0.65 >= threshold=0.4',
            metadata={'score': 0.65, 'threshold': 0.4})

        trace_dict = tracer.finish_trace()
    """

    def __init__(self):
        self._trace: Optional[Trace] = None
        self._node_starts: Dict[str, float] = {}  # node_name -> start_time
        self._node_counter: Dict[str, int] = {}    # node_name -> visit count (for retry labels)

    # ── Trace Lifecycle ────────────────────────────────────────────

    def start_trace(self, query: str, session_id: Optional[str] = None) -> str:
        """
        Begin a new trace.

        Returns the trace_id.
        """
        trace_id = uuid.uuid4().hex[:12]
        self._trace = Trace(
            trace_id=trace_id,
            query=query,
            session_id=session_id,
            start_time=time.time(),
        )
        self._node_starts.clear()
        self._node_counter.clear()
        logger.debug('Trace %s started for query: "%s"', trace_id, query[:50])
        return trace_id

    def finish_trace(self) -> Dict[str, Any]:
        """
        Finalize the trace and return a JSON-serializable dict.

        Returns an empty dict if no trace was started.
        """
        if self._trace is None:
            logger.warning('finish_trace() called with no active trace')
            return {}

        total_ms = (time.time() - self._trace.start_time) * 1000

        # Compute summary
        node_visits = {}
        total_retries = 0
        for event in self._trace.events:
            if event.phase == 'end':
                node_visits[event.node] = node_visits.get(event.node, 0) + 1
            if event.phase == 'decision' and 'retry' in event.metadata.get('reason', '').lower():
                total_retries += 1

        self._trace.summary = {
            'total_duration_ms': round(total_ms, 1),
            'node_count': len([e for e in self._trace.events if e.phase == 'end']),
            'total_events': len(self._trace.events),
            'node_visits': node_visits,
            'retry_events': total_retries,
        }

        # Serialize events
        events_data = []
        for event in self._trace.events:
            events_data.append({
                'node': event.node,
                'label': NODE_LABELS.get(event.node, event.node),
                'phase': event.phase,
                'timestamp_ms': round(event.timestamp_ms, 1),
                'duration_ms': round(event.duration_ms, 1),
                'input': event.input,
                'output': event.output,
                'metadata': event.metadata,
            })

        result = {
            'trace_id': self._trace.trace_id,
            'query': _truncate_text(self._trace.query, 200),
            'session_id': self._trace.session_id,
            'events': events_data,
            'summary': self._trace.summary,
        }

        # Size guard
        import json
        try:
            serialized = json.dumps(result, ensure_ascii=False)
            if len(serialized) > MAX_TRACE_SIZE_BYTES:
                logger.warning(
                    'Trace %s exceeds size limit (%d > %d bytes), truncating events',
                    self._trace.trace_id, len(serialized), MAX_TRACE_SIZE_BYTES,
                )
                # Keep only first half of events
                result['events'] = events_data[:len(events_data) // 2]
                result['summary']['truncated'] = True
        except Exception:
            pass

        logger.info(
            'Trace %s finished: %d events, %d nodes, %.0fms total',
            self._trace.trace_id,
            len(events_data),
            result['summary']['node_count'],
            total_ms,
        )

        self._trace = None
        return result

    # ── Event Recording ────────────────────────────────────────────

    def start_node(self, node: str, input_snapshot: Optional[Dict[str, Any]] = None) -> None:
        """
        Record the start of a node's execution.

        Args:
            node: Node name (e.g. 'tool_selection')
            input_snapshot: Key input fields for this node
        """
        if self._trace is None:
            return

        if len(self._trace.events) >= MAX_EVENTS:
            logger.warning('Trace event limit reached, skipping start_node(%s)', node)
            return

        now_ms = (time.time() - self._trace.start_time) * 1000

        # Track visit count for retry labeling
        self._node_counter[node] = self._node_counter.get(node, 0) + 1

        # Unique key for this invocation (handles retries: tool_selection#2)
        node_key = f'{node}#{self._node_counter[node]}'

        event = TraceEvent(
            node=node,
            phase='start',
            timestamp_ms=round(now_ms, 1),
            input=_safe_snapshot(input_snapshot or {}),
            metadata={'visit': self._node_counter[node]},
        )
        self._trace.events.append(event)
        self._node_starts[node_key] = time.time()

    def end_node(self, node: str, output_snapshot: Optional[Dict[str, Any]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record the end of a node's execution.

        Args:
            node: Node name (must match a prior start_node call)
            output_snapshot: Key output fields from this node
            metadata: Additional node-specific metadata
        """
        if self._trace is None:
            return

        if len(self._trace.events) >= MAX_EVENTS:
            logger.warning('Trace event limit reached, skipping end_node(%s)', node)
            return

        now_ms = (time.time() - self._trace.start_time) * 1000

        # Find the matching start key
        visit = self._node_counter.get(node, 1)
        node_key = f'{node}#{visit}'
        start_time = self._node_starts.pop(node_key, None)

        duration_ms = 0.0
        if start_time:
            duration_ms = (time.time() - start_time) * 1000

        event = TraceEvent(
            node=node,
            phase='end',
            timestamp_ms=round(now_ms, 1),
            duration_ms=round(duration_ms, 1),
            input={},  # input already captured in start event
            output=_safe_snapshot(output_snapshot or {}),
            metadata=metadata or {},
        )
        self._trace.events.append(event)

    def record_decision(self, node: str, decision: str,
                        reason: str = '',
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a routing/conditional decision.

        Used by conditional edge functions to record which branch was taken.

        Args:
            node: The node that made the decision (e.g. 'relevance_check')
            decision: Short decision label ('pass', 'fail', 'retry', 'next_sub_query', 'aggregate')
            reason: Human-readable explanation
            metadata: Supporting data (scores, thresholds, etc.)
        """
        if self._trace is None:
            return

        if len(self._trace.events) >= MAX_EVENTS:
            return

        now_ms = (time.time() - self._trace.start_time) * 1000

        event = TraceEvent(
            node=node,
            phase='decision',
            timestamp_ms=round(now_ms, 1),
            metadata={
                'decision': decision,
                'reason': reason,
                **(metadata or {}),
            },
        )
        self._trace.events.append(event)

    def record_error(self, node: str, error: str,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an error that occurred during node execution.

        Args:
            node: The node where the error occurred
            error: Error message
            metadata: Additional context
        """
        if self._trace is None:
            return

        if len(self._trace.events) >= MAX_EVENTS:
            return

        now_ms = (time.time() - self._trace.start_time) * 1000

        event = TraceEvent(
            node=node,
            phase='error',
            timestamp_ms=round(now_ms, 1),
            metadata={
                'error': _truncate_text(error, 200),
                **(metadata or {}),
            },
        )
        self._trace.events.append(event)

    @property
    def is_active(self) -> bool:
        """Check if a trace is currently being collected."""
        return self._trace is not None


# ── Global Instance ────────────────────────────────────────────────────

tracer = TraceCollector()
