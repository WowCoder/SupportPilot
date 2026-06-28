"""
Semantic Cache for RAG queries.

Uses BGE-M3 embeddings to find semantically similar historical queries
and return cached answers, avoiding redundant LLM calls.

Architecture:
- Same BGE-M3 embedding model as the existing RAG pipeline (shared singleton)
- SQLite-backed via RagSemanticCache model
- Cosine similarity threshold for cache hit/miss decision
- TTL-based expiration + max entries enforcement
"""
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from rag.utils.config import get_config

logger = logging.getLogger(__name__)


def _cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Compute cosine similarity between two normalized vectors."""
    if len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    # BGE-M3 outputs L2-normalized vectors, so dot product ≈ cosine similarity
    return max(0.0, min(1.0, dot))


class SemanticCache:
    """
    Semantic cache using BGE-M3 embeddings for similarity lookup.

    Features:
    - Lazy-loads the embedding model (shared with RAG pipeline)
    - Caches final answers + retrieval results
    - TTL-based expiration with automatic cleanup
    - Max entries enforcement to prevent unbounded growth

    Usage:
        cache = SemanticCache()
        hit = cache.lookup("如何退货")
        if hit:
            return hit['results']
        # ... run RAG pipeline ...
        cache.store("如何退货", answer, results, metadata)
    """

    def __init__(self):
        self._config = get_config()
        self._model = None
        self._lock = threading.Lock()
        self._enabled = self._config.get('semantic_cache.enabled', True)
        self._threshold = self._config.get(
            'semantic_cache.similarity_threshold', 0.95,
        )
        self._ttl_seconds = self._config.get(
            'semantic_cache.ttl_seconds', 86400,
        )
        self._max_entries = self._config.get(
            'semantic_cache.max_entries', 10000,
        )

    def _get_model(self):
        """Lazy-load BGE-M3 embedding model (shared singleton)."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                        model_name = 'BAAI/bge-m3'
                        self._model = SentenceTransformer(
                            model_name, device='cpu',
                        )
                        logger.info(
                            'SemanticCache loaded embedding model: %s',
                            model_name,
                        )
                    except Exception as e:
                        logger.error(
                            'Failed to load embedding model for '
                            'SemanticCache: %s', e,
                        )
                        self._model = False  # Sentinel: failed to load
        return self._model if self._model is not False else None

    def _embed(self, text: str) -> Optional[list]:
        """Compute normalized embedding for a query text."""
        model = self._get_model()
        if model is None:
            return None
        try:
            embedding = model.encode(
                text, normalize_embeddings=True,
            )
            return embedding.tolist()
        except Exception as e:
            logger.warning('Failed to embed query for cache: %s', e)
            return None

    def lookup(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Look up a query in the semantic cache.

        Args:
            query: User's original query text

        Returns:
            Dict with 'answer', 'results', 'metadata' if cache hit,
            None if cache miss.
        """
        if not self._enabled:
            return None

        query_embedding = self._embed(query)
        if query_embedding is None:
            return None

        try:
            from app.models.rag_semantic_cache import RagSemanticCache

            # Cleanup expired entries before lookup
            RagSemanticCache.cleanup_expired()

            candidates = RagSemanticCache.get_all_valid()
            if not candidates:
                logger.debug('SemanticCache: no valid cache entries')
                return None

            best_score = 0.0
            best_entry = None
            for entry in candidates:
                try:
                    stored_embedding = json.loads(entry.query_embedding)
                    score = _cosine_similarity(
                        query_embedding, stored_embedding,
                    )
                    if score > best_score:
                        best_score = score
                        best_entry = entry
                except (json.JSONDecodeError, TypeError):
                    continue

            if best_entry and best_score >= self._threshold:
                logger.info(
                    'SemanticCache HIT: score=%.4f threshold=%.2f '
                    'query="%s" → cached="%s"',
                    best_score, self._threshold,
                    query[:60], best_entry.query[:60],
                )
                best_entry.record_hit()

                results = []
                if best_entry.results_json:
                    try:
                        results = json.loads(best_entry.results_json)
                    except json.JSONDecodeError:
                        pass

                return {
                    'answer': best_entry.answer,
                    'results': results,
                    'metadata': {
                        'cached': True,
                        'cached_query': best_entry.query,
                        'cache_score': best_score,
                        'cache_hit_count': best_entry.hit_count,
                    },
                }

            logger.debug(
                'SemanticCache MISS: best_score=%.4f < threshold=%.2f '
                'for query="%s"',
                best_score, self._threshold, query[:60],
            )
            return None

        except Exception as e:
            logger.warning('SemanticCache lookup error: %s', e)
            return None

    def store(
        self, query: str, answer: str,
        results: list, metadata: dict = None,
    ):
        """
        Store a query-answer pair in the semantic cache.

        Args:
            query: Original user query text
            answer: Generated answer
            results: Retrieval results list
            metadata: Optional metadata dict
        """
        if not self._enabled:
            return

        query_embedding = self._embed(query)
        if query_embedding is None:
            return

        try:
            from app.extensions import db
            from app.models.rag_semantic_cache import RagSemanticCache

            # Enforce max entries
            RagSemanticCache.enforce_max_entries(self._max_entries)

            entry = RagSemanticCache(
                query=query,
                query_embedding=json.dumps(query_embedding),
                answer=answer,
                results_json=json.dumps(results, ensure_ascii=False),
                metadata_json=json.dumps(
                    metadata or {}, ensure_ascii=False,
                ),
                hit_count=0,
                created_at=datetime.utcnow(),
                expires_at=(
                    datetime.utcnow() +
                    timedelta(seconds=self._ttl_seconds)
                ),
            )
            db.session.add(entry)
            db.session.commit()

            logger.info(
                'SemanticCache stored: query="%s" answer_len=%d '
                'results=%d ttl=%ds',
                query[:60], len(answer or ''), len(results),
                self._ttl_seconds,
            )

        except Exception as e:
            logger.warning('SemanticCache store error: %s', e)
            try:
                db.session.rollback()
            except Exception:
                pass

    def is_enabled(self) -> bool:
        """Check if semantic cache is enabled."""
        return self._enabled


# Global singleton
semantic_cache = SemanticCache()
