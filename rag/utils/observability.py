"""
Logging and Metrics Collection for Agentic RAG system.

Provides structured logging and metrics collection for observability.
"""
import logging
import time
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collect and track metrics for the RAG system.

    Metrics collected:
    - Tool call count and latency
    - Agent iteration count
    - Query count and response time
    """

    _instance: Optional['MetricsCollector'] = None
    _metrics: Dict[str, Any] = {}

    def __new__(cls) -> 'MetricsCollector':
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = {
                'tool_calls': [],
                'agent_runs': [],
                'queries': []
            }
        return cls._instance

    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool, result_count: int = 0) -> None:
        """
        Record a tool call metric.

        Args:
            tool_name: Name of the tool called
            duration_ms: Execution time in milliseconds
            success: Whether the call succeeded
            result_count: Number of results returned
        """
        self._metrics['tool_calls'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'tool_name': tool_name,
            'duration_ms': duration_ms,
            'success': success,
            'result_count': result_count
        })
        logger.debug(f'Tool call: {tool_name} ({duration_ms:.1f}ms, success={success})')

    def record_agent_run(self, iterations: int, duration_ms: float, success: bool) -> None:
        """
        Record an agent run metric.

        Args:
            iterations: Number of agent iterations
            duration_ms: Total execution time
            success: Whether the run succeeded
        """
        self._metrics['agent_runs'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'iterations': iterations,
            'duration_ms': duration_ms,
            'success': success
        })
        logger.info(f'Agent run: {iterations} iterations, {duration_ms:.1f}ms')

    def record_query(self, query: str, duration_ms: float, result_count: int) -> None:
        """
        Record a user query metric.

        Args:
            query: The user query text
            duration_ms: Total response time
            result_count: Number of results returned
        """
        self._metrics['queries'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'query': query[:100],  # Truncate long queries
            'duration_ms': duration_ms,
            'result_count': result_count
        })

    def get_summary(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get a summary of collected metrics.

        Args:
            limit: Maximum number of recent records to include

        Returns:
            Dictionary with metric summaries
        """
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0

        tool_calls = self._metrics['tool_calls'][-limit:]
        agent_runs = self._metrics['agent_runs'][-limit:]
        queries = self._metrics['queries'][-limit:]

        return {
            'tool_calls': {
                'total': len(tool_calls),
                'avg_duration_ms': avg([t['duration_ms'] for t in tool_calls]),
                'success_rate': sum(1 for t in tool_calls if t['success']) / len(tool_calls) if tool_calls else 0
            },
            'agent_runs': {
                'total': len(agent_runs),
                'avg_iterations': avg([r['iterations'] for r in agent_runs]),
                'avg_duration_ms': avg([r['duration_ms'] for r in agent_runs])
            },
            'queries': {
                'total': len(queries),
                'avg_duration_ms': avg([q['duration_ms'] for q in queries]),
                'avg_result_count': avg([q['result_count'] for q in queries])
            }
        }

    def clear(self) -> None:
        """Clear all metrics."""
        self._metrics = {
            'tool_calls': [],
            'agent_runs': [],
            'queries': []
        }


# Decorator for timing tool calls
def timed_tool(func: Callable) -> Callable:
    """Decorator to automatically time and log tool execution."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start = time.time()
        try:
            result = func(self, *args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            MetricsCollector().record_tool_call(
                tool_name=getattr(self, 'name', 'unknown'),
                duration_ms=duration_ms,
                success=True,
                result_count=len(result.data) if hasattr(result, 'data') and result.data else 0
            )
            return result
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            MetricsCollector().record_tool_call(
                tool_name=getattr(self, 'name', 'unknown'),
                duration_ms=duration_ms,
                success=False
            )
            raise
    return wrapper


# Global metrics collector
metrics = MetricsCollector()
