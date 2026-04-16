"""
Integration tests for Agentic RAG Retrieval Agent

Run with: pytest tests/test_retrieval_agent.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAgentStates:
    """Tests for Agent state definitions"""

    def test_state_enum(self):
        """Test StateEnum definition"""
        from rag.agents.states import StateEnum

        assert StateEnum.START.value == "start"
        assert StateEnum.QUERY_UNDERSTANDING.value == "query_understanding"
        assert StateEnum.PLANNING.value == "planning"
        assert StateEnum.TOOL_EXECUTION.value == "tool_execution"
        assert StateEnum.SYNTHESIS.value == "synthesis"
        assert StateEnum.END.value == "end"

    def test_event_type_enum(self):
        """Test EventType enum"""
        from rag.agents.states import EventType

        assert EventType.QUERY_RECEIVED.value == "query_received"
        assert EventType.SYNTHESIS_COMPLETE.value == "synthesis_complete"

    def test_agent_state_dict(self):
        """Test AgentStateDict typed dict"""
        from rag.agents.states import AgentStateDict

        state: AgentStateDict = {
            'query': 'test query',
            'rewritten_query': '',
            'plan': None,
            'messages': [],
            'tool_calls': [],
            'retrieval_results': [],
            'final_answer': None,
            'error': None,
            'iterations': 0,
            'current_state': 'start',
            'metadata': {}
        }

        assert state['query'] == 'test query'
        assert state['iterations'] == 0


class TestQueryUnderstandingNode:
    """Tests for Query Understanding Node"""

    def test_node_initialization(self):
        """Test QueryUnderstandingNode initializes correctly"""
        from rag.agents.nodes.query_understanding import QueryUnderstandingNode

        node = QueryUnderstandingNode()
        assert node.window_size is not None
        assert node.timeout_seconds is not None

    def test_process_without_history(self):
        """Test processing query without conversation history"""
        from rag.agents.nodes.query_understanding import query_understanding_node

        state = {
            'query': 'test query',
            'rewritten_query': '',
            'plan': None,
            'messages': [],
            'tool_calls': [],
            'retrieval_results': [],
            'final_answer': None,
            'error': None,
            'iterations': 0,
            'current_state': 'query_understanding',
            'metadata': {}
        }

        result = query_understanding_node.process(state)
        assert result['rewritten_query'] == 'test query'  # No change without history

    def test_process_with_session_id(self):
        """Test processing with session ID (no actual history)"""
        from rag.agents.nodes.query_understanding import query_understanding_node

        state = {
            'query': 'test query',
            'rewritten_query': '',
            'plan': None,
            'messages': [],
            'tool_calls': [],
            'retrieval_results': [],
            'final_answer': None,
            'error': None,
            'iterations': 0,
            'current_state': 'query_understanding',
            'metadata': {'session_id': 'test_session'}
        }

        # Should not raise error even without actual history
        result = query_understanding_node.process(state)
        assert 'rewritten_query' in result


class TestPlanningNode:
    """Tests for Planning Node"""

    def test_node_initialization(self):
        """Test PlanningNode initializes correctly"""
        from rag.agents.nodes.planning import PlanningNode

        node = PlanningNode()
        assert node.config is not None

    def test_create_plan_single_tool(self):
        """Test plan creation with single tool"""
        from rag.agents.nodes.planning import planning_node

        state = {
            'query': 'simple query',
            'rewritten_query': 'simple query',
            'plan': None,
            'messages': [],
            'tool_calls': [],
            'retrieval_results': [],
            'final_answer': None,
            'error': None,
            'iterations': 0,
            'current_state': 'planning',
            'metadata': {}
        }

        result = planning_node.process(state)
        assert result['plan'] is not None
        assert 'steps' in result['plan']
        assert 'tools' in result['plan']

    def test_create_plan_multi_tool(self):
        """Test plan creation with multiple tools"""
        from rag.agents.nodes.planning import PlanningNode

        node = PlanningNode()
        # Mock a query that would trigger multiple tools
        tools = node._determine_tools("complex query with multiple keywords and concepts")

        assert 'vector_search' in tools  # Always enabled


class TestToolExecutionNode:
    """Tests for Tool Execution Node"""

    def test_node_initialization(self):
        """Test ToolExecutionNode initializes correctly"""
        from rag.agents.nodes.tool_execution import ToolExecutionNode

        node = ToolExecutionNode()
        assert 'vector_search' in node._tools
        assert 'bm25_search' in node._tools

    def test_execute_unknown_tool(self):
        """Test executing unknown tool"""
        from rag.agents.nodes.tool_execution import ToolExecutionNode

        node = ToolExecutionNode()
        tool_call = node._execute_tool('unknown_tool', {})

        assert tool_call.success is False
        assert 'Unknown tool' in tool_call.error

    def test_process_without_plan(self):
        """Test processing without a plan"""
        from rag.agents.nodes.tool_execution import tool_execution_node

        state = {
            'query': 'test',
            'rewritten_query': 'test',
            'plan': None,
            'messages': [],
            'tool_calls': [],
            'retrieval_results': [],
            'final_answer': None,
            'error': None,
            'iterations': 0,
            'current_state': 'tool_execution',
            'metadata': {}
        }

        result = tool_execution_node.process(state)
        # Should return state unchanged
        assert result['retrieval_results'] == []


class TestSynthesisNode:
    """Tests for Synthesis Node"""

    def test_node_initialization(self):
        """Test SynthesisNode initializes correctly"""
        from rag.agents.nodes.synthesis import SynthesisNode

        node = SynthesisNode()
        assert node.timeout_seconds is not None

    def test_generate_no_results(self):
        """Test synthesis with no retrieval results"""
        from rag.agents.nodes.synthesis import synthesis_node

        state = {
            'query': 'test query',
            'rewritten_query': 'test query',
            'plan': None,
            'messages': [],
            'tool_calls': [],
            'retrieval_results': [],
            'final_answer': None,
            'error': None,
            'iterations': 0,
            'current_state': 'synthesis',
            'metadata': {}
        }

        result = synthesis_node.process(state)
        assert result['final_answer'] is not None
        assert '抱歉' in result['final_answer'] or '未找到' in result['final_answer']

    def test_format_no_results_response(self):
        """Test formatting no-results response"""
        from rag.agents.nodes.synthesis import SynthesisNode

        node = SynthesisNode()
        response = node._format_no_results_response("test query")

        assert response is not None
        assert len(response) > 0


class TestRetrievalAgent:
    """Tests for Retrieval Agent"""

    def test_agent_initialization(self):
        """Test RetrievalAgent initializes correctly"""
        from rag.agents.retrieval_agent import RetrievalAgent

        agent = RetrievalAgent()
        assert agent._graph is not None
        assert agent.max_iterations is not None
        assert agent.timeout_seconds is not None

    def test_run_simple_query(self):
        """Test running a simple query"""
        from rag.agents.retrieval_agent import retrieval_agent

        result = retrieval_agent.run(query="test query")

        assert 'success' in result
        assert 'answer' in result
        assert 'retrieval_results' in result
        assert 'metadata' in result

    def test_run_with_session_id(self):
        """Test running query with session ID"""
        from rag.agents.retrieval_agent import retrieval_agent

        result = retrieval_agent.run(
            query="test query",
            session_id="test_session_123"
        )

        assert result['metadata']['mode'] == 'agentic'

    def test_timeout_protection(self):
        """Test timeout protection"""
        from rag.agents.retrieval_agent import timeout_handler, TimeoutError
        import signal

        # Test that timeout handler works (module-level function)
        with pytest.raises(TimeoutError):
            with timeout_handler(1):
                import time
                time.sleep(2)

    def test_run_with_fallback(self):
        """Test run_with_fallback method"""
        from rag.agents.retrieval_agent import retrieval_agent

        result = retrieval_agent.run_with_fallback(query="test")

        assert 'success' in result
        assert 'metadata' in result


class TestAgentIntegration:
    """Integration tests for full agent workflow"""

    def test_end_to_end_workflow(self):
        """Test complete agent workflow"""
        from rag.agents.retrieval_agent import retrieval_agent

        # Test various query types
        queries = [
            "简单查询",
            "对比 A 和 B",
            "总结主要内容",
        ]

        for query in queries:
            result = retrieval_agent.run(query=query)

            assert result['success'] is True
            assert 'metadata' in result
            assert result['metadata']['mode'] == 'agentic'

    def test_agent_state_transitions(self):
        """Test that agent transitions through correct states"""
        from rag.agents.retrieval_agent import RetrievalAgent

        agent = RetrievalAgent()

        # The graph should have all required nodes
        graph_nodes = list(agent._graph.nodes.keys())

        assert 'query_understanding' in graph_nodes
        assert 'planning' in graph_nodes
        assert 'tool_execution' in graph_nodes
        assert 'synthesis' in graph_nodes


class TestAgentTimeout:
    """Tests for agent timeout and error handling"""

    def test_graceful_error_handling(self):
        """Test that agent handles errors gracefully"""
        from rag.agents.retrieval_agent import retrieval_agent

        # Should not raise, should return error result
        result = retrieval_agent.run(query="")

        assert 'success' in result
        assert isinstance(result, dict)

    def test_iteration_limit(self):
        """Test iteration limit is enforced"""
        from rag.agents.retrieval_agent import RetrievalAgent

        agent = RetrievalAgent()
        assert agent.max_iterations > 0
        assert agent.max_iterations <= 10  # Reasonable limit
