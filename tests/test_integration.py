"""
Integration tests for RAG retrieval functionality

Run with: pytest tests/test_integration.py -v
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSimpleQueryRetrieval:
    """Tests for simple query retrieval (task 7.2)"""

    def test_vector_search_basic(self):
        """Test basic vector search functionality"""
        from rag.tools.vector_tool import vector_search

        # Test with mocked ChromaDB
        with patch.object(vector_search, '_get_collection') as mock_collection:
            mock_collection.return_value.query.return_value = {
                'documents': [['test document content']],
                'distances': [[0.3]],
                'metadatas': [[{'source': 'test.pdf'}]]
            }

            result = vector_search.execute(query="test", k=1, use_small_to_big=False)

            assert result.success is True
            assert len(result.data) > 0
            assert 'content' in result.data[0]

    def test_vector_search_small_to_big(self):
        """Test vector search with Small-to-Big mode"""
        from rag.tools.vector_tool import vector_search

        with patch.object(vector_search, '_get_collection') as mock_collection:
            with patch('rag.tools.vector_tool.parent_store') as mock_store:
                mock_collection.return_value.query.return_value = {
                    'documents': [['small chunk']],
                    'distances': [[0.3]],
                    'metadatas': [[{'parent_id': 'parent_1'}]]
                }
                mock_store.get.return_value = {
                    'content': 'large parent content',
                    'metadata': {'source': 'test.pdf'}
                }

                result = vector_search.execute(query="test", k=1, use_small_to_big=True)

                assert result.success is True
                if len(result.data) > 0:
                    # Should have parent content
                    assert 'content' in result.data[0]

    def test_bm25_search_basic(self):
        """Test basic BM25 search functionality"""
        from rag.tools.bm25_tool import BM25Tool

        documents = [
            {'content': 'Python programming language', 'metadata': {'source': 'doc1.txt'}},
            {'content': 'Java programming language', 'metadata': {'source': 'doc2.txt'}},
            {'content': 'Machine learning with Python', 'metadata': {'source': 'doc3.txt'}},
            {'content': 'Python is great for data science', 'metadata': {'source': 'doc4.txt'}},
            {'content': 'JavaScript for web development', 'metadata': {'source': 'doc5.txt'}},
        ]

        bm25_tool = BM25Tool(documents=documents)
        result = bm25_tool.execute(query="Python", k=2)

        assert result.success is True
        assert len(result.data) > 0

    def test_service_simple_retrieval(self):
        """Test simple retrieval through RAG service"""
        from rag.service import rag_service

        with patch('rag.service.vector_search') as mock_vector:
            mock_vector.execute.return_value = Mock(
                success=True,
                data=[{'content': 'test result', 'similarity': 0.8, 'source': 'test.pdf'}]
            )

            results = rag_service.retrieve(
                query="简单查询",
                k=3,
                use_small_to_big=True
            )

            # Should return results from vector search
            assert isinstance(results, list)


class TestComplexQueryAgenticRAG:
    """Tests for complex query with Agentic RAG (task 7.3)"""

    def test_router_agentic_classification(self):
        """Test that agentic queries are correctly classified"""
        from rag.agents.router import query_router

        agentic_queries = [
            "对比 A 和 B 的异同",
            "比较这两个方案的优缺点",
            "总结一下这篇文章的主要内容",
            "分析一下问题的根本原因",
            "列出所有相关的功能",
        ]

        for query in agentic_queries:
            route_type, metadata = query_router.route(query)
            assert route_type == "agentic", f"Query '{query}' should be agentic"

    def test_agent_complex_query_handling(self):
        """Test agent handles complex queries"""
        from rag.agents.retrieval_agent import retrieval_agent

        complex_queries = [
            "对比向量检索和关键词检索的区别",
            "总结 RAG 系统的核心优势",
        ]

        for query in complex_queries:
            result = retrieval_agent.run(query=query)

            assert result['success'] is True
            assert 'metadata' in result
            assert result['metadata']['mode'] == 'agentic'

    def test_agent_state_machine_flow(self):
        """Test agent state machine processes all nodes"""
        from rag.agents.retrieval_agent import RetrievalAgent

        agent = RetrievalAgent()

        # Verify all nodes are present in the graph
        nodes = list(agent._graph.nodes.keys())

        expected_nodes = [
            'query_understanding',
            'planning',
            'tool_execution',
            'synthesis'
        ]

        for node in expected_nodes:
            assert node in nodes, f"Node {node} should be in the graph"

    def test_multi_tool_planning(self):
        """Test that agent plans to use multiple tools for complex queries"""
        from rag.agents.nodes.planning import planning_node

        state = {
            'query': '对比分析多个方案的优缺点',
            'rewritten_query': '对比分析多个方案的优缺点',
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
        assert 'tools' in result['plan']
        # Vector search should always be included
        assert 'vector_search' in result['plan']['tools']


class TestPerformanceAndLatency:
    """Tests for performance and latency benchmarks (task 7.4)"""

    def test_tool_execution_latency(self):
        """Test tool execution latency is within acceptable range"""
        import time
        from rag.tools.vector_tool import vector_search

        with patch.object(vector_search, '_get_collection') as mock_collection:
            mock_collection.return_value.query.return_value = {
                'documents': [['test'] * 10],
                'distances': [[0.3] * 10],
                'metadatas': [[{'source': 'test.pdf'}] * 10]
            }

            start = time.time()
            result = vector_search.execute(query="test", k=5)
            elapsed_ms = (time.time() - start) * 1000

            assert result.success is True
            # Tool execution should be < 100ms (excluding embedding)
            assert elapsed_ms < 100, f"Tool execution took {elapsed_ms}ms"

    def test_router_latency(self):
        """Test query router latency"""
        import time
        from rag.agents.router import query_router

        start = time.time()
        route_type, metadata = query_router.route("test query")
        elapsed_ms = (time.time() - start) * 1000

        # Router should be very fast (< 10ms)
        assert elapsed_ms < 10, f"Router took {elapsed_ms}ms"

    def test_agent_initialization_latency(self):
        """Test agent initialization latency"""
        import time
        from rag.agents.retrieval_agent import RetrievalAgent

        start = time.time()
        agent = RetrievalAgent()
        elapsed_ms = (time.time() - start) * 1000

        # Agent initialization should be < 500ms
        assert elapsed_ms < 500, f"Agent initialization took {elapsed_ms}ms"

    def test_concurrent_tool_execution(self):
        """Test concurrent tool execution"""
        import threading
        from rag.tools.vector_tool import vector_search

        results = []
        errors = []

        def execute_query(query):
            try:
                with patch.object(vector_search, '_get_collection') as mock_collection:
                    mock_collection.return_value.query.return_value = {
                        'documents': [[query]],
                        'distances': [[0.3]],
                        'metadatas': [[{'source': 'test.pdf'}]]
                    }
                    result = vector_search.execute(query=query)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Execute multiple queries concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=execute_query, args=(f"query {i}",))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent execution had errors: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"


class TestEndToEndWorkflow:
    """End-to-end workflow tests (task 7.1)"""

    def test_full_retrieval_workflow(self):
        """Test complete retrieval workflow from query to answer"""
        from rag.agents.retrieval_agent import retrieval_agent

        result = retrieval_agent.run(query="高并发的原则是什么")

        # Should complete successfully
        assert result['success'] is True
        assert 'metadata' in result

    def test_error_handling_in_workflow(self):
        """Test error handling throughout workflow"""
        from rag.agents.retrieval_agent import retrieval_agent

        # Empty query should handle gracefully
        result = retrieval_agent.run(query="")

        # Should not crash, may return error result
        assert isinstance(result, dict)
        assert 'success' in result

    def test_session_tracking(self):
        """Test session ID tracking through workflow"""
        from rag.agents.retrieval_agent import retrieval_agent

        result = retrieval_agent.run(
            query="test query",
            session_id="test_session_123"
        )

        assert result['metadata']['mode'] == 'agentic'
