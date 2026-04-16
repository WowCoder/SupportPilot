"""
Unit tests for Agentic RAG retrieval tools

Run with: pytest tests/test_rag_tools.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVectorSearchTool:
    """Tests for VectorSearchTool"""

    def test_tool_initialization(self):
        """Test VectorSearchTool initializes correctly"""
        from rag.tools.vector_tool import VectorSearchTool

        tool = VectorSearchTool()
        assert tool.name == "vector_search"
        assert tool.description is not None
        assert tool.config is not None

    def test_execute_empty_query(self):
        """Test execution with empty query"""
        from rag.tools.vector_tool import VectorSearchTool
        from rag.core.tool import ToolResult

        tool = VectorSearchTool()
        # Mock the collection to avoid actual ChromaDB calls
        tool._collection = Mock()
        tool._collection.query.return_value = {'documents': [[]], 'distances': [[]], 'metadatas': [[]]}

        result = tool.execute(query="")
        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data == []

    def test_execute_returns_tool_result(self):
        """Test execution returns proper ToolResult"""
        from rag.tools.vector_tool import VectorSearchTool
        from rag.core.tool import ToolResult

        tool = VectorSearchTool()
        tool._collection = Mock()
        tool._collection.query.return_value = {
            'documents': [['test content']],
            'distances': [[0.2]],
            'metadatas': [[{'source': 'test.pdf'}]]
        }

        result = tool.execute(query="test", k=1, use_small_to_big=False)
        assert isinstance(result, ToolResult)
        assert result.success is True

    def test_similarity_threshold_filtering(self):
        """Test that results below threshold are filtered"""
        from rag.tools.vector_tool import VectorSearchTool

        tool = VectorSearchTool()
        tool._collection = Mock()
        # Low similarity (high distance)
        tool._collection.query.return_value = {
            'documents': [['test content']],
            'distances': [[0.9]],  # similarity = 0.1, below 0.25 threshold
            'metadatas': [[{'source': 'test.pdf'}]]
        }

        result = tool.execute(query="test", k=1, use_small_to_big=False)
        assert result.success is True
        assert len(result.data) == 0  # Filtered out

    def test_small_to_big_mode(self):
        """Test Small-to-Big retrieval mode"""
        from rag.tools.vector_tool import VectorSearchTool

        tool = VectorSearchTool()
        tool._collection = Mock()
        tool._collection.query.return_value = {
            'documents': [['small chunk']],
            'distances': [[0.3]],  # similarity = 0.7
            'metadatas': [[{'parent_id': 'parent_123'}]]
        }

        with patch('rag.tools.vector_tool.parent_store') as mock_store:
            mock_store.get.return_value = {
                'content': 'large parent content',
                'metadata': {'source': 'test.pdf'}
            }

            result = tool.execute(query="test", k=1, use_small_to_big=True)
            assert result.success is True
            if len(result.data) > 0:
                assert 'content' in result.data[0]
                assert 'parent_id' in result.data[0]


class TestBM25Tool:
    """Tests for BM25Tool"""

    def test_tool_initialization(self):
        """Test BM25Tool initializes correctly"""
        from rag.tools.bm25_tool import BM25Tool

        tool = BM25Tool()
        assert tool.name == "bm25_search"
        assert tool.description is not None

    def test_tokenize(self):
        """Test tokenization"""
        from rag.tools.bm25_tool import BM25Tool

        tool = BM25Tool()
        tokens = tool._tokenize("Hello World! This is a test.")
        assert 'hello' in tokens
        assert 'world' in tokens
        assert 'test' in tokens
        assert len(tokens) == 6

    def test_execute_no_documents(self):
        """Test execution without documents"""
        from rag.tools.bm25_tool import BM25Tool

        tool = BM25Tool()
        result = tool.execute(query="test")
        assert result.success is True
        assert result.data == []

    def test_execute_with_documents(self):
        """Test execution with documents"""
        from rag.tools.bm25_tool import BM25Tool

        documents = [
            {'content': 'Python is a programming language', 'metadata': {'source': 'test.txt'}},
            {'content': 'Java is also a programming language', 'metadata': {'source': 'test2.txt'}},
        ]

        tool = BM25Tool(documents=documents)
        result = tool.execute(query="Python programming", k=2)

        assert result.success is True
        assert len(result.data) > 0
        assert 'content' in result.data[0]
        assert 'score' in result.data[0]


class TestMetadataFilterTool:
    """Tests for MetadataFilterTool"""

    def test_tool_initialization(self):
        """Test MetadataFilterTool initializes correctly"""
        from rag.tools.filter_tool import MetadataFilterTool

        tool = MetadataFilterTool()
        assert tool.name == "metadata_filter"

    def test_filter_by_source(self):
        """Test filtering by source"""
        from rag.tools.filter_tool import MetadataFilterTool

        tool = MetadataFilterTool()
        documents = [
            {'content': 'doc1', 'metadata': {'source': 'a.pdf'}},
            {'content': 'doc2', 'metadata': {'source': 'b.pdf'}},
            {'content': 'doc3', 'metadata': {'source': 'a.pdf'}},
        ]

        result = tool.execute(documents=documents, source='a.pdf')
        assert result.success is True
        assert len(result.data) == 2

    def test_filter_by_page_range(self):
        """Test filtering by page range"""
        from rag.tools.filter_tool import MetadataFilterTool

        tool = MetadataFilterTool()
        documents = [
            {'content': 'doc1', 'metadata': {'page': 1}},
            {'content': 'doc2', 'metadata': {'page': 5}},
            {'content': 'doc3', 'metadata': {'page': 10}},
            {'content': 'doc4', 'metadata': {'page': 15}},
        ]

        result = tool.execute(documents=documents, pages="1-10")
        assert result.success is True
        assert len(result.data) == 3  # pages 1, 5, 10

    def test_filter_empty_documents(self):
        """Test filtering empty document list"""
        from rag.tools.filter_tool import MetadataFilterTool

        tool = MetadataFilterTool()
        result = tool.execute(documents=[])
        assert result.success is True
        assert result.data == []


class TestEnsembleTool:
    """Tests for EnsembleTool"""

    def test_tool_initialization(self):
        """Test EnsembleTool initializes correctly"""
        from rag.tools.ensemble_tool import EnsembleTool

        tool = EnsembleTool()
        assert tool.name == "ensemble_retrieval"

    def test_rrf_fusion(self):
        """Test RRF fusion of multiple retrieval results"""
        from rag.tools.ensemble_tool import EnsembleTool

        tool = EnsembleTool()

        # Simulate results from two retrieval methods
        retrieval_results = [
            {
                'name': 'vector',
                'results': [
                    {'content': 'doc A', 'score': 0.9},
                    {'content': 'doc B', 'score': 0.8},
                    {'content': 'doc C', 'score': 0.7},
                ]
            },
            {
                'name': 'bm25',
                'results': [
                    {'content': 'doc B', 'score': 0.95},
                    {'content': 'doc A', 'score': 0.85},
                    {'content': 'doc D', 'score': 0.75},
                ]
            },
        ]

        result = tool.execute(retrieval_results=retrieval_results, k=3)
        assert result.success is True
        assert len(result.data) <= 3
        # Doc A and B should be highly ranked since they appear in both

    def test_empty_results(self):
        """Test handling empty results"""
        from rag.tools.ensemble_tool import EnsembleTool

        tool = EnsembleTool()
        result = tool.execute(retrieval_results=[])
        assert result.success is True
        assert result.data == []

    def test_deduplication(self):
        """Test that duplicate content is deduplicated"""
        from rag.tools.ensemble_tool import EnsembleTool

        tool = EnsembleTool()

        retrieval_results = [
            {
                'name': 'vector',
                'results': [
                    {'content': 'same content', 'score': 0.9},
                ]
            },
            {
                'name': 'bm25',
                'results': [
                    {'content': 'same content', 'score': 0.95},
                ]
            },
        ]

        result = tool.execute(retrieval_results=retrieval_results, k=5)
        assert result.success is True
        # Same content should appear only once
        contents = [r['content'] for r in result.data]
        assert contents.count('same content') == 1


class TestToolResult:
    """Tests for ToolResult class"""

    def test_success_result(self):
        """Test successful ToolResult"""
        from rag.core.tool import ToolResult

        result = ToolResult(success=True, data=[{'content': 'test'}])
        assert result.success is True
        assert result.data is not None
        assert result.error is None

    def test_error_result(self):
        """Test error ToolResult"""
        from rag.core.tool import ToolResult

        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"


class TestMetricsCollector:
    """Tests for MetricsCollector"""

    def test_singleton_pattern(self):
        """Test that MetricsCollector is a singleton"""
        from rag.core.observability import MetricsCollector

        collector1 = MetricsCollector()
        collector2 = MetricsCollector()
        assert collector1 is collector2

    def test_record_tool_call(self):
        """Test recording tool call metrics"""
        from rag.core.observability import MetricsCollector

        collector = MetricsCollector()
        initial_count = len(collector._metrics['tool_calls'])

        collector.record_tool_call('test_tool', 100.0, True, 5)

        assert len(collector._metrics['tool_calls']) == initial_count + 1

    def test_get_summary(self):
        """Test getting metrics summary"""
        from rag.core.observability import MetricsCollector

        collector = MetricsCollector()
        collector.clear()
        collector.record_tool_call('test_tool', 100.0, True, 5)

        summary = collector.get_summary()
        assert 'tool_calls' in summary
        assert summary['tool_calls']['total'] >= 1
        assert 'avg_duration_ms' in summary['tool_calls']


class TestConfigLoader:
    """Tests for ConfigLoader"""

    def test_singleton_pattern(self):
        """Test that ConfigLoader is a singleton"""
        from rag.core.config import ConfigLoader

        loader1 = ConfigLoader()
        loader2 = ConfigLoader()
        assert loader1 is loader2

    def test_get_with_default(self):
        """Test getting config value with default"""
        from rag.core.config import ConfigLoader

        loader = ConfigLoader()
        value = loader.get('nonexistent.key', default='default_value')
        assert value == 'default_value'


class TestContainer:
    """Tests for Container"""

    def test_singleton_pattern(self):
        """Test that Container is a singleton"""
        from rag.core.container import Container

        container1 = Container()
        container2 = Container()
        assert container1 is container2

    def test_register_and_get(self):
        """Test registering and getting service"""
        from rag.core.container import Container

        container = Container()
        container.clear()  # Start fresh

        service = Mock()
        container.register('test_service', service)

        retrieved = container.get('test_service')
        assert retrieved is service

    def test_has_service(self):
        """Test checking if service exists"""
        from rag.core.container import Container

        container = Container()
        container.clear()

        assert container.has('nonexistent') is False
        container.register('test', Mock())
        assert container.has('test') is True
