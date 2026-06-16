import os
os.environ['ORT_DISABLE_COREML'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.expanduser("~/.cache/huggingface/hub")

from langchain_huggingface import HuggingFaceEmbeddings
import logging

logger = logging.getLogger(__name__)


class CustomEmbeddingFunction:
    """Custom embedding function using langchain HuggingFaceEmbeddings"""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={
                    'device': 'cpu'
                },
                encode_kwargs={
                    'normalize_embeddings': True
                }
            )
            logger.info('Loaded HuggingFaceEmbeddings successfully from local cache')
        except Exception as e:
            logger.error(f'Failed to load HuggingFaceEmbeddings: {e}')
            raise

    def __call__(self, input):
        """Embed a list of texts"""
        return self.embeddings.embed_documents(input)

    def embed_documents(self, texts):
        """Embed a list of documents"""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, input):
        """Embed a single query or multiple queries

        Note: ChromaDB passes input as a list of texts, and expects a list of embeddings back.
        For a single query ['query'], should return [[embedding_vector]].
        For multiple queries ['q1', 'q2'], should return [[embedding1], [embedding2]].
        """
        if isinstance(input, str):
            embedding = self.embeddings.embed_query(input)
            return [embedding]
        elif isinstance(input, list):
            embeddings = []
            for text in input:
                embedding = self.embeddings.embed_query(text)
                embeddings.append(embedding)
            return embeddings
        else:
            logger.warning(f'Unexpected input type for embed_query: {type(input)}')
            return []
