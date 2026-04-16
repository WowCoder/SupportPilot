"""
Query Router for Agentic RAG system.

Combines rule-based and ML-based classification to route queries:
- Simple queries: direct to retrieval (vector search + Small-to-Big)
- Agentic queries: routed to LangGraph agent for multi-step reasoning
"""
import logging
from typing import Any, Dict, Optional, Tuple

from rag.core.config import get_config
from rag.agents.router_rules import RouterRules
from rag.agents.router_classifier import QueryIntentClassifier

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Query router that decides between simple and agentic retrieval.

    Routing strategy:
    1. Rule-based classification (keywords, patterns) - primary
    2. ML-based classification (logistic regression) - secondary
    3. Config-driven override (force simple or agentic mode)

    Returns:
        - 'simple': Use direct vector retrieval
        - 'agentic': Use LangGraph agent for multi-step reasoning
    """

    def __init__(self, rules: RouterRules = None, classifier: QueryIntentClassifier = None):
        """
        Initialize the query router.

        Args:
            rules: Optional RouterRules instance
            classifier: Optional QueryIntentClassifier instance
        """
        self.config = get_config()
        self.rules = rules or RouterRules()
        self.classifier = classifier or QueryIntentClassifier()

    def route(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Route a query to simple or agentic path.

        Args:
            query: User query text

        Returns:
            Tuple of (route_type, metadata)
            route_type: 'simple' or 'agentic'
            metadata: {'method': str, 'confidence': float, 'explanation': str}
        """
        # Check config for forced mode
        router_mode = self.config.get('router.mode', 'auto')
        if router_mode == 'simple':
            return 'simple', {'method': 'config_override', 'confidence': 1.0, 'explanation': 'Config forces simple mode'}
        elif router_mode == 'agentic':
            return 'agentic', {'method': 'config_override', 'confidence': 1.0, 'explanation': 'Config forces agentic mode'}

        # Rule-based classification (primary)
        rule_classification = self.rules.classify(query)
        rule_explanation = self.rules.get_explanation(query)

        # High confidence rule match - use it directly
        if rule_classification == 'agentic':
            return 'agentic', {
                'method': 'rules',
                'confidence': 0.9,
                'explanation': rule_explanation
            }

        # For simple classification by rules, check ML confidence
        ml_label, ml_confidence = self.classifier.classify(query)

        # If ML strongly disagrees with rules, use ML
        if ml_label == 'agentic' and ml_confidence > 0.7:
            return 'agentic', {
                'method': 'ml_override',
                'confidence': ml_confidence,
                'explanation': f'ML override: {ml_label} (confidence: {ml_confidence:.2f})'
            }

        # Default to rule-based classification
        return rule_classification, {
            'method': 'rules',
            'confidence': 0.7,
            'explanation': rule_explanation
        }

    def is_agentic(self, query: str) -> bool:
        """
        Check if a query should be routed to agentic system.

        Args:
            query: User query text

        Returns:
            True if query should use agentic path
        """
        route_type, _ = self.route(query)
        return route_type == 'agentic'

    def get_routing_decision(self, query: str) -> str:
        """
        Get a human-readable routing decision explanation.

        Args:
            query: User query text

        Returns:
            Explanation string
        """
        route_type, metadata = self.route(query)
        return (f"Route: {route_type} | "
                f"Method: {metadata['method']} | "
                f"Confidence: {metadata['confidence']:.0%} | "
                f"Reason: {metadata['explanation']}")


# Global instance
query_router = QueryRouter()
