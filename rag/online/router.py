"""
Query Router for Agentic RAG system.

Routes queries using a two-tier strategy:
1. Config override (force simple/agentic)
2. Keyword rules (fast path, high confidence)
3. LLM-based routing (fallback for unmatched queries)
"""
import json
import logging
from typing import Any, Dict, Optional, Tuple

from rag.utils.config import get_config
from rag.online.router_rules import RouterRules

logger = logging.getLogger(__name__)


class QueryRouter:
    """
    Query router that decides between simple and agentic retrieval.

    Routing strategy:
    1. Config override (force simple or agentic mode)
    2. Keyword rules (fast, matches known patterns)
    3. LLM-based routing (handles ambiguous/unmatched queries)

    Returns:
        - 'simple': Use direct vector retrieval
        - 'agentic': Use LangGraph agent for multi-step reasoning
    """

    def __init__(self, rules: RouterRules = None):
        """
        Initialize the query router.

        Args:
            rules: Optional RouterRules instance
        """
        self.config = get_config()
        self.rules = rules or RouterRules()
        self.use_llm_routing = self.config.get('router.use_llm_routing', True)

    def _llm_route(self, query: str) -> Tuple[str, float]:
        """
        Use lightweight LLM prompt to decide query complexity.

        Returns:
            Tuple of (route_type, confidence)
        """
        prompt = f"""判断这个查询是"简单查询"还是"复杂查询"。
简单查询：单个事实查询、定义查询、基本属性查询，一次检索即可回答。
复杂查询：对比分析、多实体查询、多跳推理、总结归纳，需要多步检索或分析。

查询：{query}

只回复一个词：simple 或 agentic"""

        try:
            from llm.llm_client import llm_client

            messages = [{"role": "user", "content": prompt}]
            response = llm_client.generate(messages, temperature=0, max_tokens=16)
            if response:
                response = response.strip().lower()
                if 'agentic' in response:
                    return 'agentic', 0.8
                elif 'simple' in response:
                    return 'simple', 0.8
        except Exception as e:
            logger.warning(f'LLM routing failed: {e}')

        return 'simple', 0.5

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
            return 'simple', {
                'method': 'config_override', 'confidence': 1.0,
                'explanation': 'Config forces simple mode'
            }
        elif router_mode == 'agentic':
            return 'agentic', {
                'method': 'config_override', 'confidence': 1.0,
                'explanation': 'Config forces agentic mode'
            }

        # Tier 1: Rule-based classification (fast, no LLM cost)
        rule_classification = self.rules.classify(query)
        rule_explanation = self.rules.get_explanation(query)

        if rule_classification == 'agentic':
            return 'agentic', {
                'method': 'rules',
                'confidence': 0.9,
                'explanation': rule_explanation
            }

        # Tier 2: For queries classified as 'simple' by rules (or unmatched),
        # optionally verify with LLM that it's truly simple
        if self.use_llm_routing:
            llm_label, llm_confidence = self._llm_route(query)
            if llm_label == 'agentic':
                return 'agentic', {
                    'method': 'llm_override',
                    'confidence': llm_confidence,
                    'explanation': f'LLM override: query requires agentic handling'
                }

        # Default to simple
        return 'simple', {
            'method': 'rules',
            'confidence': 0.7,
            'explanation': 'Default classification (simple)'
        }

    def is_agentic(self, query: str) -> bool:
        """Check if a query should be routed to agentic system."""
        route_type, _ = self.route(query)
        return route_type == 'agentic'

    def get_routing_decision(self, query: str) -> str:
        """Get a human-readable routing decision explanation."""
        route_type, metadata = self.route(query)
        return (f"Route: {route_type} | "
                f"Method: {metadata['method']} | "
                f"Confidence: {metadata['confidence']:.0%} | "
                f"Reason: {metadata['explanation']}")


# Global instance
query_router = QueryRouter()
