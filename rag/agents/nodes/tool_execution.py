"""
Tool Execution Node for Agentic RAG system.

Executes retrieval tools based on the planning phase.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.agents.states import AgentStateDict, ToolCall
from rag.core.config import get_config
from rag.tools.vector_tool import vector_search
from rag.tools.bm25_tool import bm25_search
from rag.tools.filter_tool import metadata_filter
from rag.tools.ensemble_tool import ensemble_retrieval

logger = logging.getLogger(__name__)


class ToolExecutionNode:
    """
    Tool execution node for LangGraph state machine.

    Responsibilities:
    - Execute planned tools
    - Collect and aggregate results
    - Handle errors and retries
    """

    def __init__(self):
        """Initialize the tool execution node."""
        self.config = get_config()
        self._tools = {
            'vector_search': vector_search,
            'bm25_search': bm25_search,
            'metadata_filter': metadata_filter,
            'ensemble_retrieval': ensemble_retrieval,
        }

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolCall:
        """
        Execute a single tool.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            ToolCall object with result
        """
        tool = self._tools.get(tool_name)
        if not tool:
            logger.warning(f'Unknown tool: {tool_name}')
            return ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                error=f'Unknown tool: {tool_name}'
            )

        try:
            logger.debug(f'Executing tool: {tool_name} with args: {arguments}')
            result = tool.execute(**arguments)

            return ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                result=result.data if result and result.success else None,
                success=result.success if result else False,
                error=result.error if result and not result.success else None
            )

        except Exception as e:
            logger.error(f'Tool execution failed: {tool_name}: {e}')
            return ToolCall(
                tool_name=tool_name,
                arguments=arguments,
                success=False,
                error=str(e)
            )

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Execute planned tools.

        Args:
            state: Current agent state

        Returns:
            Updated state with tool results
        """
        plan = state.get('plan')
        if not plan:
            logger.warning('No plan found, skipping tool execution')
            return state

        steps = plan.get('steps', [])
        if not steps:
            logger.warning('No steps in plan, skipping tool execution')
            return state

        logger.info(f'Executing {len(steps)} tool steps')

        tool_results = []
        parallel_results = {}

        # Execute parallel steps first
        for step in steps:
            if step.get('parallel'):
                tool_name = step.get('tool')
                arguments = step.get('arguments', {})

                tool_call = self._execute_tool(tool_name, arguments)
                parallel_results[tool_name] = tool_call

                if tool_call.success:
                    tool_results.append({
                        'name': tool_name,
                        'results': tool_call.result or []
                    })
                else:
                    logger.warning(f'Tool {tool_name} failed: {tool_call.error}')

        # Execute fusion step if ensemble is planned
        for step in steps:
            if not step.get('parallel') and step.get('tool') == 'ensemble_retrieval':
                # Collect parallel results for fusion
                step['arguments']['retrieval_results'] = tool_results

                tool_name = step.get('tool')
                arguments = step.get('arguments', {})

                tool_call = self._execute_tool(tool_name, arguments)

                if tool_call.success:
                    state['retrieval_results'] = tool_call.result or []
                    logger.debug(f'Ensemble fusion complete: {len(tool_call.result)} results')
                else:
                    logger.warning(f'Ensemble fusion failed: {tool_call.error}')

                break

        # If no ensemble, use direct results from parallel tools
        if not any(s.get('tool') == 'ensemble_retrieval' for s in steps):
            all_results = []
            for tool_name, tool_call in parallel_results.items():
                if tool_call.success and tool_call.result:
                    all_results.extend(tool_call.result)

            if all_results:
                state['retrieval_results'] = all_results
                logger.debug(f'Collected {len(all_results)} retrieval results')

        return state


# Global instance
tool_execution_node = ToolExecutionNode()
