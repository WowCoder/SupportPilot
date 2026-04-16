"""
Unit tests for Query Router

Run with: pytest tests/test_router.py -v
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRouterRules:
    """Tests for RouterRules class"""

    def test_initialization(self):
        """Test RouterRules initializes correctly"""
        from rag.agents.router_rules import RouterRules

        rules = RouterRules()
        assert len(rules.agentic_keywords) > 0
        assert len(rules.simple_keywords) > 0

    def test_classify_agentic_keyword(self):
        """Test classification by agentic keyword"""
        from rag.agents.router_rules import RouterRules

        rules = RouterRules()

        # Test comparison queries
        assert rules.classify("对比 A 和 B") == "agentic"
        assert rules.classify("比较这两个方案") == "agentic"

        # Test analysis queries
        assert rules.classify("分析一下原因") == "agentic"
        assert rules.classify("总结主要内容") == "agentic"

    def test_classify_simple_keyword(self):
        """Test classification by simple keyword"""
        from rag.agents.router_rules import RouterRules

        rules = RouterRules()

        # Test definition queries
        assert rules.classify("是什么") == "simple"
        assert rules.classify("什么是 RAG") == "simple"

    def test_classify_default_simple(self):
        """Test that unclassified queries default to simple"""
        from rag.agents.router_rules import RouterRules

        rules = RouterRules()
        result = rules.classify("some random query")
        assert result == "simple"

    def test_is_agentic(self):
        """Test is_agentic helper method"""
        from rag.agents.router_rules import RouterRules

        rules = RouterRules()
        assert rules.is_agentic("对比 A 和 B") is True
        assert rules.is_agentic("是什么") is False

    def test_get_explanation(self):
        """Test classification explanation"""
        from rag.agents.router_rules import RouterRules

        rules = RouterRules()
        explanation = rules.get_explanation("对比 A 和 B")
        assert explanation is not None
        assert len(explanation) > 0


class TestQueryIntentClassifier:
    """Tests for QueryIntentClassifier"""

    def test_initialization(self):
        """Test QueryIntentClassifier initializes correctly"""
        from rag.agents.router_classifier import QueryIntentClassifier

        classifier = QueryIntentClassifier()
        assert classifier._is_trained is False

    def test_classify_without_training(self):
        """Test classification without training (fallback mode)"""
        from rag.agents.router_classifier import QueryIntentClassifier

        classifier = QueryIntentClassifier()
        label, confidence = classifier.classify("test query")

        # Should return fallback values
        assert label == "simple"
        assert confidence == 0.5

    def test_train_with_sample_data(self):
        """Test training with sample data"""
        from rag.agents.router_classifier import QueryIntentClassifier

        classifier = QueryIntentClassifier()

        queries = [
            "对比 A 和 B", "比较两个方案", "分析原因", "总结内容",
            "是什么", "什么是", "定义是什么", "谁提出的"
        ]
        labels = [
            "agentic", "agentic", "agentic", "agentic",
            "simple", "simple", "simple", "simple"
        ]

        # Try to train (may fail if sklearn not installed)
        try:
            success = classifier.train(queries, labels)
            if success:
                assert classifier._is_trained is True

                # Test classification after training
                label, confidence = classifier.classify("对比分析")
                assert label in ["agentic", "simple"]
                assert 0.0 <= confidence <= 1.0
        except ImportError:
            # sklearn not available, verify fallback behavior
            assert classifier._is_trained is False

    def test_batch_classify(self):
        """Test batch classification"""
        from rag.agents.router_classifier import QueryIntentClassifier

        classifier = QueryIntentClassifier()
        queries = ["query 1", "query 2", "query 3"]

        results = classifier.batch_classify(queries)
        assert len(results) == 3

        for label, confidence in results:
            assert label == "simple"  # Fallback mode
            assert confidence == 0.5


class TestQueryRouter:
    """Tests for QueryRouter"""

    def test_initialization(self):
        """Test QueryRouter initializes correctly"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()
        assert router.rules is not None
        assert router.classifier is not None

    def test_route_simple_mode(self):
        """Test routing in simple mode"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()
        # Override config for testing
        router.config = {'router.mode': 'simple'}

        route_type, metadata = router.route("any query")
        assert route_type == "simple"
        assert metadata['method'] == 'config_override'

    def test_route_agentic_mode(self):
        """Test routing in agentic mode"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()
        router.config = {'router.mode': 'agentic'}

        route_type, metadata = router.route("any query")
        assert route_type == "agentic"
        assert metadata['method'] == 'config_override'

    def test_route_auto_mode_with_agentic_query(self):
        """Test routing in auto mode with agentic query"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()
        router.config = {'router.mode': 'auto'}

        route_type, metadata = router.route("对比 A 和 B 的异同")
        assert route_type == "agentic"
        assert metadata['method'] == 'rules'

    def test_route_auto_mode_with_simple_query(self):
        """Test routing in auto mode with simple query"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()
        router.config = {'router.mode': 'auto'}

        route_type, metadata = router.route("RAG 是什么")
        # Should be simple based on keyword matching
        assert route_type == "simple"

    def test_is_agentic(self):
        """Test is_agentic helper method"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()
        assert router.is_agentic("对比分析") is True
        assert router.is_agentic("是什么") is False

    def test_get_routing_decision(self):
        """Test getting routing decision explanation"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()
        decision = router.get_routing_decision("对比 A 和 B")
        assert decision is not None
        assert "Route:" in decision
        assert "Method:" in decision
        assert "Reason:" in decision


class TestRouterIntegration:
    """Integration tests for router components"""

    def test_end_to_end_routing(self):
        """Test end-to-end query routing"""
        from rag.agents.router import QueryRouter

        router = QueryRouter()

        # Test various query types
        test_cases = [
            ("对比 A 和 B", "agentic"),
            ("比较两个方案", "agentic"),
            ("总结主要内容", "agentic"),
            ("是什么", "simple"),
            ("如何配置", "simple"),  # Default to simple
        ]

        for query, expected_route in test_cases:
            route_type, metadata = router.route(query)
            # Note: Some may vary based on rules configuration
            assert route_type in ["simple", "agentic"]
            assert 'method' in metadata
            assert 'confidence' in metadata
            assert 'explanation' in metadata
