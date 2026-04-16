"""
Query Router Rules for Agentic RAG system.

Provides keyword-based and pattern-based routing rules:
- Agentic keywords that trigger complex query handling
- Simple keywords for direct retrieval
- Pattern matching for common query types
"""
import logging
import re
from typing import Any, Dict, List, Optional, Set

from rag.core.config import get_config

logger = logging.getLogger(__name__)


class RouterRules:
    """
    Rule-based query router.

    Uses keyword matching and regex patterns to classify queries:
    - Agentic queries: require multi-step reasoning, comparison, analysis
    - Simple queries: direct fact lookup, single-topic retrieval
    """

    # Default agentic keywords (can be overridden by config)
    DEFAULT_AGENCY_KEYWORDS = [
        '对比', '比较', '异同', '区别',  # Comparison
        '列出', '列举', '汇总',  # Listing
        '总结', '归纳', '概括',  # Summarization
        '分析', '解析', '解读',  # Analysis
        '推理', '推导', '推论',  # Reasoning
        '多跳', '多步',  # Multi-hop
        '为什么', '原因', '解释',  # Explanation
        '如何', '怎么', '怎样',  # How-to
        '影响', '作用', '意义',  # Impact analysis
    ]

    # Simple query keywords (direct retrieval)
    SIMPLE_KEYWORDS = [
        '是什么', '什么是', '定义',  # Definition
        '谁', '哪里', '何时',  # Basic facts
        '多少', '几年',  # Numbers
    ]

    # Regex patterns for query classification
    PATTERNS = [
        # Comparison queries
        (r'(对比 | 比较 | 区别 | 异同 | 差异|vs|versus)', 'agentic'),
        # Listing queries
        (r'(列出 | 列举 | 汇总 | 所有 | 哪些|list)', 'agentic'),
        # Analysis queries
        (r'(分析 | 解析 | 解读 | 分析 | 评价)', 'agentic'),
        # Summarization queries
        (r'(总结 | 归纳 | 概括 | 概述|summary)', 'agentic'),
        # Reasoning queries
        (r'(推理 | 推导 | 推论 | 蕴含 | 隐含)', 'agentic'),
        # Multi-hop queries
        (r'(多跳 | 多步 | 关联 | 结合|chain)', 'agentic'),
        # Definition queries (simple)
        (r'(是什么 | 什么是 | 定义|define|what is)', 'simple'),
        # Fact queries (simple)
        (r'(谁 | 哪里 | 何时 | 何地|who|when|where)', 'simple'),
    ]

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the router rules.

        Args:
            config: Optional configuration override
        """
        self.config = config or get_config().get('router', {})
        self._compile_patterns()
        self._load_keywords()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for fast matching."""
        self._compiled_patterns = []
        for pattern, route_type in self.PATTERNS:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._compiled_patterns.append((compiled, route_type))
            except re.error as e:
                logger.warning(f'Failed to compile pattern "{pattern}": {e}')

    def _load_keywords(self) -> None:
        """Load keywords from config or use defaults."""
        # Agentic keywords from config
        agentic_keywords = self.config.get('agentic_keywords', self.DEFAULT_AGENCY_KEYWORDS)
        self.agentic_keywords = set(agentic_keywords)

        # Simple keywords from config (if provided)
        simple_keywords = self.config.get('simple_keywords', self.SIMPLE_KEYWORDS)
        self.simple_keywords = set(simple_keywords)

        logger.debug(f'Loaded {len(self.agentic_keywords)} agentic keywords, '
                     f'{len(self.simple_keywords)} simple keywords')

    def classify(self, query: str) -> str:
        """
        Classify a query using rules and patterns.

        Args:
            query: User query text

        Returns:
            'agentic' for complex queries, 'simple' for direct retrieval
        """
        query_lower = query.lower()

        # Step 1: Check agentic keywords first (highest priority)
        for keyword in self.agentic_keywords:
            if keyword.lower() in query_lower:
                logger.debug(f'Query classified as "agentic" by keyword: {keyword}')
                return 'agentic'

        # Step 2: Check simple keywords
        for keyword in self.simple_keywords:
            if keyword.lower() in query_lower:
                logger.debug(f'Query classified as "simple" by keyword: {keyword}')
                return 'simple'

        # Step 3: Check regex patterns
        for pattern, route_type in self._compiled_patterns:
            if pattern.search(query):
                logger.debug(f'Query classified as "{route_type}" by pattern')
                return route_type

        # Default to simple for unmatched queries
        logger.debug('Query classified as "simple" by default')
        return 'simple'

    def is_agentic(self, query: str) -> bool:
        """
        Check if a query requires agentic handling.

        Args:
            query: User query text

        Returns:
            True if query should be routed to agentic system
        """
        return self.classify(query) == 'agentic'

    def get_explanation(self, query: str) -> str:
        """
        Get explanation for why a query was classified a certain way.

        Args:
            query: User query text

        Returns:
            Explanation string
        """
        query_lower = query.lower()

        # Check agentic keywords
        for keyword in self.agentic_keywords:
            if keyword.lower() in query_lower:
                return f'Contains agentic keyword: {keyword}'

        # Check simple keywords
        for keyword in self.simple_keywords:
            if keyword.lower() in query_lower:
                return f'Contains simple keyword: {keyword}'

        # Check patterns
        for pattern, route_type in self._compiled_patterns:
            if pattern.search(query):
                return f'Matches {route_type} pattern'

        return 'Default classification (simple)'


# Global instance
router_rules = RouterRules()
