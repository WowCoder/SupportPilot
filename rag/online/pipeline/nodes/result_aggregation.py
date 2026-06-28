"""
Result Aggregation Node for Agentic RAG system.

Merges retrieval results from multiple sub-queries or correction attempts
using RRF-based deduplication and ranking, then applies MMR (Maximal
Marginal Relevance) for diversity-aware selection.
"""
import logging
import threading
from typing import Any, Dict, List

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class ResultAggregationNode:
    """
    Aggregates results from multiple sub-queries.

    Pipeline:
    1. RRF (Reciprocal Rank Fusion) — merge + deduplicate
    2. MMR (Maximal Marginal Relevance) — diversity-aware selection

    MMR balances relevance and diversity:
        MMR(d_i) = λ × rel(d_i) - (1-λ) × max_{d_j ∈ selected} sim(d_i, d_j)

    This prevents similar documents from dominating the top results.
    """

    RRF_K = 60

    def __init__(self):
        self.config = get_config()
        self.top_k = self.config.get('tools.ensemble.k', 10)
        self._diversity_enabled = self.config.get('diversity.enabled', True)
        self._lambda = self.config.get('diversity.lambda', 0.7)
        self._mmr_pool_size = self.config.get('diversity.mmr_pool_size', 20)
        self._mmr_final_k = self.config.get('diversity.mmr_final_k', 10)
        self._embed_model = None
        self._embed_lock = threading.Lock()

    def _get_embed_model(self):
        """Lazy-load BGE-M3 for document embedding (shared singleton)."""
        if self._embed_model is None:
            with self._embed_lock:
                if self._embed_model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                        self._embed_model = SentenceTransformer(
                            'BAAI/bge-m3', device='cpu',
                        )
                        logger.info(
                            'MMR: loaded BGE-M3 embedding model',
                        )
                    except Exception as e:
                        logger.error(
                            'MMR: failed to load embedding model: %s', e,
                        )
                        self._embed_model = False
        return self._embed_model if self._embed_model is not False else None

    def _embed_documents(
        self, docs: List[Dict[str, Any]],
    ) -> List[List[float]]:
        """Embed document content for MMR similarity computation."""
        model = self._get_embed_model()
        if model is None:
            return []
        try:
            contents = [
                d.get('content', '')[:400] for d in docs
            ]
            embeddings = model.encode(
                contents,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return embeddings.tolist()
        except Exception as e:
            logger.warning('MMR: embedding failed: %s', e)
            return []

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity between two normalized vectors."""
        if len(a) != len(b):
            return 0.0
        return max(0.0, min(1.0, sum(x * y for x, y in zip(a, b))))

    def _content_key(self, content: str) -> str:
        """Generate a normalized key for deduplication (first 200 chars)."""
        return content.strip()[:200]

    def _rrf_merge(self, all_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge results from multiple sub-queries using RRF.

        Args:
            all_results: List of result dicts, each with 'content', 'similarity', etc.

        Returns:
            Deduplicated and ranked results
        """
        if not all_results:
            return []

        scored = {}
        content_map = {}

        for i, result in enumerate(all_results):
            content = result.get('content', '')
            key = self._content_key(content)

            # RRF: 1 / (rank + K)
            rank = i + 1
            rrf_score = 1.0 / (rank + self.RRF_K)

            if key not in scored:
                scored[key] = rrf_score
                content_map[key] = result
            else:
                scored[key] += rrf_score
                # Keep the result with higher original similarity
                existing_sim = content_map[key].get('similarity', 0)
                new_sim = result.get('similarity', 0)
                if new_sim > existing_sim:
                    content_map[key] = result

        # Sort by combined RRF score
        sorted_keys = sorted(
            scored.keys(), key=lambda k: scored[k], reverse=True,
        )

        merged = []
        for key in sorted_keys:
            result = content_map[key].copy()
            result['rrf_score'] = float(scored[key])
            merged.append(result)

        return merged

    def _mmr_select(
        self,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Apply MMR (Maximal Marginal Relevance) for diversity-aware selection.

        Greedy algorithm: iteratively select the document that maximizes
        λ × relevance - (1-λ) × max_similarity_to_already_selected.

        Args:
            candidates: RRF-merged results (already sorted by relevance)

        Returns:
            MMR-selected diverse results
        """
        if not self._diversity_enabled:
            return candidates[:self._mmr_final_k]

        pool_size = min(self._mmr_pool_size, len(candidates))
        if pool_size <= self._mmr_final_k:
            return candidates[:self._mmr_final_k]

        pool = candidates[:pool_size]

        # Embed candidates for diversity computation
        embeddings = self._embed_documents(pool)
        if not embeddings or len(embeddings) != len(pool):
            # Embedding failed: fall back to top-K by relevance
            logger.warning(
                'MMR: embedding unavailable, falling back to top-%d',
                self._mmr_final_k,
            )
            return candidates[:self._mmr_final_k]

        selected_indices = []
        remaining_indices = list(range(len(pool)))

        # First selection: most relevant document
        selected_indices.append(remaining_indices.pop(0))

        # Greedy MMR selection
        while len(selected_indices) < self._mmr_final_k and remaining_indices:
            best_idx = None
            best_score = float('-inf')

            for idx in remaining_indices:
                relevance = pool[idx].get('rrf_score', pool[idx].get('similarity', 0))

                # Max similarity to any already-selected document
                max_sim = max(
                    self._cosine_sim(embeddings[idx], embeddings[s])
                    for s in selected_indices
                )

                mmr_score = (
                    self._lambda * relevance -
                    (1 - self._lambda) * max_sim
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
            else:
                break

        selected = [pool[i] for i in selected_indices]

        # Log diversity improvement
        sources_before = set(
            c.get('source', '')[:40]
            for c in pool[:self._mmr_final_k]
        )
        sources_after = set(
            c.get('source', '')[:40] for c in selected
        )
        logger.info(
            'MMR: pool=%d → selected=%d | unique sources: %d→%d '
            '(λ=%.1f)',
            pool_size, len(selected),
            len(sources_before), len(sources_after),
            self._lambda,
        )

        return selected

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Aggregate results from all sub-queries with RRF + MMR.

        Args:
            state: Current agent state with all_sub_results

        Returns:
            Updated state with merged + diversity-selected retrieval_results
        """
        all_sub_results = list(state.get('all_sub_results', []))
        current_results = list(state.get('retrieval_results', []))

        # Combine all results: sub-query results + current results
        combined = list(all_sub_results) + list(current_results)

        if not combined:
            logger.warning('No results to aggregate')
            return state

        # Step 1: RRF merge and deduplicate
        merged = self._rrf_merge(combined)

        logger.info(
            'Aggregation (RRF): %d raw → %d merged',
            len(combined), len(merged),
        )

        # Step 2: MMR diversity selection
        diverse = self._mmr_select(merged)

        state['retrieval_results'] = diverse
        state['all_sub_results'] = diverse  # Sync

        return state


result_aggregation_node = ResultAggregationNode()
