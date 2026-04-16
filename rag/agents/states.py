"""
Agent State and Events for Agentic RAG system.

Defines the state machine states and event types for LangGraph orchestration.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Annotated
from enum import Enum

logger = logging.getLogger(__name__)


class StateEnum(Enum):
    """Agent execution states."""
    START = "start"
    QUERY_UNDERSTANDING = "query_understanding"
    PLANNING = "planning"
    TOOL_EXECUTION = "tool_execution"
    SYNTHESIS = "synthesis"
    END = "end"


class EventType(Enum):
    """Event types for agent execution."""
    QUERY_RECEIVED = "query_received"
    QUERY_REWRITTEN = "query_rewritten"
    PLAN_CREATED = "plan_created"
    TOOL_CALLED = "tool_called"
    TOOL_RESULT = "tool_result"
    SYNTHESIS_COMPLETE = "synthesis_complete"
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
class AgentState:
    """
    Agent state for LangGraph state machine.

    Fields:
        query: Original user query
        rewritten_query: Query after understanding/rewriting
        plan: Current retrieval plan
        messages: Conversation history
        tool_calls: List of tool calls made
        retrieval_results: Accumulated retrieval results
        final_answer: Generated final answer
        error: Error message if any
        iterations: Number of agent iterations
        current_state: Current state name
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
from typing import TypedDict, Sequence


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
    metadata: Dict[str, Any]
