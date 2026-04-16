"""
Ensemble Retrieval Tool for Agentic RAG system.

Supports multi-path retrieval fusion using RRF (Reciprocal Rank Fusion):
- Combines results from multiple retrieval tools (vector, BM25, etc.)
- Uses RRF algorithm for robust ranking fusion
- Configurable weights and fusion parameters
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from rag.core.tool import BaseTool, ToolResult
from rag.core.config import get_config

logger = logging.getLogger(__name__)


class EnsembleTool(BaseTool):
    """
    Ensemble retrieval tool with RRF fusion.

    Features:
    - Combine results from multiple retrieval sources
    - Reciprocal Rank Fusion (RRF) for robust ranking
    - Configurable weights per retrieval method
    - Deduplication of identical content
    """

    name = "ensemble_retrieval"
    description = "Combine results from multiple retrieval methods (vector, BM25, etc.) using Reciprocal Rank Fusion (RRF) for robust ranking."

    # RRF constant (typically 60, range 40-100)
    RRF_K = 60

    def __init__(self):
        """Initialize the ensemble retrieval tool."""
        self.config = get_config()

    def _rrf_score(self, ranked_results: List[Dict[str, Any]], weight: float = 1.0) -> Dict[str, float]:
        """
        Calculate RRF scores for ranked results.

        Args:
            ranked_results: List of results in rank order
            weight: Weight for this retrieval method

        Returns:
            Dictionary mapping content to RRF score
        """
        scores = {}
        for rank, result in enumerate(ranked_results, start=1):
            content = result.get('content', '')
            if content:
                rrf_score = weight / (rank + self.RRF_K)
                scores[content] = scores.get(content, 0) + rrf_score
        return scores

    def _normalize_scores(self, scores: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """
        Normalize scores to 0-1 range.

        Args:
            scores: List of (content, score) tuples

        Returns:
            List of (content, normalized_score) tuples
        """
        if not scores:
            return []

        max_score = max(score for _, score in scores)
        if max_score == 0:
            return [(content, 0.0) for content, _ in scores]

        return [(content, score / max_score) for content, score in scores]

    def execute(self,
                retrieval_results: List[Dict[str, Any]],
                k: int = None,
                weights: List[float] = None,
                rrf_k: int = None,
                **kwargs) -> ToolResult:
        """
        Execute ensemble retrieval with RRF fusion.

        Args:
            retrieval_results: List of retrieval results, each containing:
                - 'name': Retrieval method name
                - 'results': List of documents with 'content' key
                - 'weight': Optional weight for this method (default: 1.0)
            k: Number of final results to return (default from config)
            weights: Default weights for each method (if not provided in results)
            rrf_k: RRF constant (default: 60)

        Returns:
            ToolResult with fused and ranked documents
        """
        try:
            # Load config defaults
            k = k or self.config.get('tools.ensemble.k', 10)
            rrf_k = rrf_k or self.config.get('tools.ensemble.rrf_k', self.RRF_K)
            self.RRF_K = rrf_k

            if not retrieval_results:
                return ToolResult(success=True, data=[])

            # Aggregate RRF scores from all retrieval methods
            combined_scores = {}
            content_to_doc = {}

            for idx, result_entry in enumerate(retrieval_results):
                results = result_entry.get('results', [])
                if not results:
                    continue

                # Get weight for this retrieval method
                weight = result_entry.get('weight')
                if weight is None:
                    if weights and idx < len(weights):
                        weight = weights[idx]
                    else:
                        weight = 1.0

                # Calculate RRF scores
                rrf_scores = self._rrf_score(results, weight)

                # Aggregate scores
                for content, score in rrf_scores.items():
                    combined_scores[content] = combined_scores.get(content, 0) + score
                    # Store document reference (use first occurrence)
                    if content not in content_to_doc:
                        content_to_doc[content] = results[0] if results else {}

            # Sort by combined RRF score
            sorted_scores = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

            # Normalize scores
            normalized_scores = self._normalize_scores(sorted_scores)

            # Build final results
            fused_results = []
            seen_content = set()

            for i, (content, original_score) in enumerate(sorted_scores):
                if content in seen_content:
                    continue
                seen_content.add(content)

                # Get normalized score from the same index
                _, normalized_score = normalized_scores[i]

                doc_template = content_to_doc.get(content, {})
                fused_results.append({
                    'content': content,
                    'score': float(normalized_score),
                    'rrf_score': float(original_score),
                    'source': doc_template.get('source', 'ensemble'),
                    'metadata': doc_template.get('metadata', {})
                })

                if len(fused_results) >= k:
                    break

            logger.debug(f'Ensemble retrieval: fused {len(retrieval_results)} sources -> {len(fused_results)} results')
            return ToolResult(success=True, data=fused_results)

        except Exception as e:
            logger.error(f'Ensemble retrieval failed: {e}', exc_info=True)
            return ToolResult(success=False, error=str(e))


# Global instance
ensemble_retrieval = EnsembleTool()
