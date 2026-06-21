"""Embedding stage for RAG offline pipeline.

Provides CustomEmbeddingFunction (sentence_transformers based) and
EmbeddingStage factory with thread-safe lazy initialization.
"""

import logging
import threading

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class CustomEmbeddingFunction:
    """Custom embedding function using sentence_transformers (native, no langchain dep)."""

    def __init__(self, model_name="BAAI/bge-m3"):
        self._model_name = model_name
        try:
            self._model = SentenceTransformer(model_name, device='cpu')
            logger.info('Loaded SentenceTransformer: %s (dim=%d)', model_name,
                        self._model.get_sentence_embedding_dimension())
        except Exception as e:
            logger.error(f'Failed to load SentenceTransformer: {e}')
            raise

    def name(self):
        """Return model name (required by chromadb >= 1.5)."""
        return self._model_name

    def __call__(self, input):
        """Embed a list of texts (ChromaDB compatibility interface)."""
        return self.embed_documents(input)

    def embed_documents(self, texts):
        """Embed a list of documents."""
        return self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).tolist()

    def embed_query(self, input):
        """Embed a single query or multiple queries.

        ChromaDB passes input as a list of texts.
        """
        if isinstance(input, str):
            embedding = self._model.encode(
                input, normalize_embeddings=True
            ).tolist()
            return [embedding]
        elif isinstance(input, list):
            embeddings = self._model.encode(
                input, normalize_embeddings=True
            ).tolist()
            return embeddings
        else:
            logger.warning(f'Unexpected input type for embed_query: {type(input)}')
            return []


class EmbeddingStage:
    """Factory for embedding function with lazy init + thread safety."""

    def __init__(self, config):
        self.config = config
        self._fn = None
        self._lock = threading.Lock()

    def get_embedding_fn(self) -> CustomEmbeddingFunction:
        """Get or create the embedding function (thread-safe lazy init)."""
        if self._fn is None:
            with self._lock:
                if self._fn is None:
                    self._fn = CustomEmbeddingFunction(self.config.model_name)
        return self._fn
