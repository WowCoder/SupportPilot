"""
Agent State and Events for Agentic RAG system.

Defines the state machine states and event types for LangGraph orchestration.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class StateEnum(Enum):
    """Agent execution states."""
    START = "start"
    QUERY_UNDERSTANDING = "query_understanding"
    QUERY_DECOMPOSITION = "query_decomposition"
    TOOL_SELECTION = "tool_selection"
    TOOL_EXECUTION = "tool_execution"
    RELEVANCE_CHECK = "relevance_check"
    QUERY_REFINER = "query_refiner"
    RESULT_AGGREGATION = "result_aggregation"
    ANSWER_GENERATION = "answer_generation"
    FAITHFULNESS_CHECK = "faithfulness_check"
    END = "end"


class EventType(Enum):
    """Event types for agent execution."""
    QUERY_RECEIVED = "query_received"
    QUERY_REWRITTEN = "query_rewritten"
    QUERY_DECOMPOSED = "query_decomposed"
    TOOLS_SELECTED = "tools_selected"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    RELEVANCE_CHECKED = "relevance_checked"
    QUERY_REFINED = "query_refined"
    RESULTS_AGGREGATED = "results_aggregated"
    ANSWER_GENERATED = "answer_generated"
    FAITHFULNESS_CHECKED = "faithfulness_checked"
    ERROR = "error"


@dataclass
class ToolCall:
    """Represents a tool call request."""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class RetrievalPlan:
    """Represents a retrieval plan."""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    iterations: int = 0


@dataclass
class SubQuery:
    """Represents a decomposed sub-query."""
    query: str
    query_type: str = "factual"  # factual, comparison, reasoning, listing
    tools: List[str] = field(default_factory=list)


@dataclass
class AgentState:
    """
    Agent state for LangGraph state machine.

    Fields:
        query: Original user query
        rewritten_query: Query after understanding/pronoun resolution
        plan: Current retrieval plan (deprecated, kept for compat)
        messages: Conversation history
        tool_calls: List of tool calls made
        retrieval_results: Accumulated retrieval results
        final_answer: Generated final answer
        error: Error message if any
        iterations: Number of agent iterations
        current_state: Current state name

        # Query decomposition
        sub_queries: Decomposed sub-queries
        current_sub_query_idx: Index of current sub-query being processed
        all_sub_results: Retrieval results from all sub-queries

        # Self-correction
        retry_count: Current retry count for self-correction loop
        max_retries: Maximum retries before fallback
        relevance_scores: Relevance scores per result set
        query_history: Track attempted queries to prevent loops

        # Faithfulness
        faithfulness_score: Answer faithfulness score
        hallucination_flags: Flagged hallucination segments
    """
    query: str = ""
    rewritten_query: str = ""
    plan: Optional[RetrievalPlan] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    retrieval_results: List[Dict[str, Any]] = field(default_factory=list)
    final_answer: Optional[str] = None
    error: Optional[str] = None
    iterations: int = 0
    current_state: str = StateEnum.START.value

    # Query decomposition
    sub_queries: List[Dict[str, Any]] = field(default_factory=list)
    current_sub_query_idx: int = 0
    all_sub_results: List[Dict[str, Any]] = field(default_factory=list)

    # Self-correction
    retry_count: int = 0
    max_retries: int = 2
    relevance_scores: Dict[str, float] = field(default_factory=dict)
    query_history: List[str] = field(default_factory=list)

    # Faithfulness
    faithfulness_score: float = 0.0
    hallucination_flags: List[str] = field(default_factory=list)

    # Global retry (faithfulness failure triggers full re-retrieval)
    global_retry_count: int = 0
    max_global_retries: int = 1

    # Rerank
    reranked_results: List[Dict[str, Any]] = field(default_factory=list)

    # Parallel retrieval (Phase 1 optimization)
    parallel_sub_results: List[Dict[str, Any]] = field(default_factory=list)
    parallel_errors: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


def add_messages(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge message lists."""
    return left + right


def add_tool_calls(left: List[ToolCall], right: List[ToolCall]) -> List[ToolCall]:
    """Merge tool call lists."""
    return left + right


def add_results(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge retrieval results."""
    return left + right


# TypedDict version for LangGraph compatibility
from typing import TypedDict, Sequence  # noqa: E402


class AgentStateDict(TypedDict):
    """TypedDict version for LangGraph compatibility."""
    query: str
    rewritten_query: str
    plan: Optional[Dict[str, Any]]
    messages: Sequence[Dict[str, Any]]
    tool_calls: Sequence[Dict[str, Any]]
    retrieval_results: Sequence[Dict[str, Any]]
    final_answer: Optional[str]
    error: Optional[str]
    iterations: int
    current_state: str

    # Query decomposition
    sub_queries: Sequence[Dict[str, Any]]
    current_sub_query_idx: int
    all_sub_results: Sequence[Dict[str, Any]]

    # Self-correction
    retry_count: int
    max_retries: int
    relevance_scores: Dict[str, float]
    query_history: Sequence[str]

    # Faithfulness
    faithfulness_score: float
    hallucination_flags: Sequence[str]

    # Global retry (faithfulness failure triggers full re-retrieval)
    global_retry_count: int
    max_global_retries: int

    # Rerank
    reranked_results: Sequence[Dict[str, Any]]

    # Parallel retrieval (Phase 1 optimization)
    parallel_sub_results: Sequence[Dict[str, Any]]
    parallel_errors: Sequence[str]

    # Metadata
    metadata: Dict[str, Any]
