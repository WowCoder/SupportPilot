from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
import os
import logging
import hashlib
import threading
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
import re

logger = logging.getLogger(__name__)


class CustomEmbeddingFunction:
    """Custom embedding function using langchain HuggingFaceEmbeddings"""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info('Loaded HuggingFaceEmbeddings successfully')
        except Exception as e:
            logger.error(f'Failed to load HuggingFaceEmbeddings: {e}')
            raise

    def __call__(self, input):
        """Embed a list of texts"""
        return self.embeddings.embed_documents(input)

    def embed_documents(self, texts):
        """Embed a list of documents"""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text):
        """Embed a single query"""
        return self.embeddings.embed_query(text)


class RAGUtils:
    # Class-level lock for thread safety
    _lock = threading.Lock()

    def __init__(self):
        # Initialize Chroma client with persistent storage
        self.client = chromadb.PersistentClient(path="./chroma_db")

        # Use HuggingFace embedding function (uses sentence-transformers)
        cache_dir = os.path.expanduser("~/.cache/huggingface")
        os.makedirs(cache_dir, exist_ok=True)

        self.embedding_fn = None
        load_error = None

        try:
            self.embedding_fn = CustomEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info('Using HuggingFace embedding function (all-MiniLM-L6-v2)')
        except Exception as e:
            load_error = str(e)
            logger.warning(f'Failed to load HuggingFace embedding: {e}')

        # Get or create collection with cosine similarity
        try:
            if self.embedding_fn:
                self.collection = self.client.get_collection(
                    name="knowledge",
                    embedding_function=self.embedding_fn
                )
            else:
                self.collection = self.client.get_collection(name="knowledge")
            logger.info('Found existing Chroma collection')
        except ValueError:
            # Collection doesn't exist, create it
            if self.embedding_fn:
                self.collection = self.client.create_collection(
                    name="knowledge",
                    metadata={"hnsw:space": "cosine"},
                    embedding_function=self.embedding_fn
                )
            else:
                self.collection = self.client.create_collection(
                    name="knowledge",
                    metadata={"hnsw:space": "cosine"}
                )
            logger.info(f'Created new Chroma collection. Embedding: {self.embedding_fn is not None}')
            if load_error:
                logger.error(f'Embedding not available: {load_error}')
                logger.error('Please download the model. See instructions above.')

        # Track processed document hashes for deduplication
        self.document_hashes = set()
        self._load_document_hashes()

        # BM25 index for hybrid search (built on-demand)
        self.bm25_index = None
        self.bm25_documents = []
        self.bm25_metadatas = []
        self._bm25_initialized = False

        # Cross-Encoder for re-ranking (lazy initialization)
        self.cross_encoder = None
        self._cross_encoder_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._cross_encoder_ready = False

    def _load_document_hashes(self):
        """Load existing document hashes from Chroma for deduplication"""
        try:
            existing = self.collection.get(include=["metadatas"])
            for meta in existing.get("metadatas", []):
                if meta and "content_hash" in meta:
                    self.document_hashes.add(meta["content_hash"])
            logger.info(f'Loaded {len(self.document_hashes)} document hashes from Chroma')
        except Exception as e:
            logger.error(f'Error loading document hashes: {e}', exc_info=True)

    def _compute_document_hash(self, content):
        """Compute hash of document content for deduplication"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def process_document(self, file_path, chunk_size=1500, chunk_overlap=300):
        """Process a document and add it to the Chroma collection (thread-safe)

        Args:
            file_path: Path to the document file
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between consecutive chunks

        Returns:
            dict: {
                'success': bool,
                'chunks_added': int,
                'chunks_total': int,
                'error': str (if failed)
            }
        """
        with RAGUtils._lock:
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.pdf':
                    try:
                        loader = PyPDFLoader(file_path)
                        documents = loader.load()
                    except FileNotFoundError as e:
                        logger.error(f'PDF file not found: {file_path}')
                        return {'success': False, 'chunks_added': 0, 'error': 'File not found'}
                    except Exception as e:
                        logger.error(f'Error loading PDF {file_path}: {e}', exc_info=True)
                        return {'success': False, 'chunks_added': 0, 'error': str(e)}
                elif ext == '.txt':
                    try:
                        loader = TextLoader(file_path, encoding='utf-8')
                        documents = loader.load()
                    except FileNotFoundError as e:
                        logger.error(f'TXT file not found: {file_path}')
                        return {'success': False, 'chunks_added': 0, 'error': 'File not found'}
                    except UnicodeDecodeError as e:
                        logger.error(f'Encoding error loading TXT {file_path}: {e}')
                        return {'success': False, 'chunks_added': 0, 'error': 'Encoding error'}
                    except Exception as e:
                        logger.error(f'Error loading TXT {file_path}: {e}', exc_info=True)
                        return {'success': False, 'chunks_added': 0, 'error': str(e)}
                elif ext == '.docx':
                    try:
                        loader = Docx2txtLoader(file_path)
                        documents = loader.load()
                    except FileNotFoundError as e:
                        logger.error(f'DOCX file not found: {file_path}')
                        return {'success': False, 'chunks_added': 0, 'error': 'File not found'}
                    except Exception as e:
                        logger.error(f'Error loading DOCX {file_path}: {e}', exc_info=True)
                        return {'success': False, 'chunks_added': 0, 'error': str(e)}
                else:
                    logger.warning(f'Unsupported file extension: {ext}')
                    return {'success': False, 'chunks_added': 0, 'error': 'Unsupported file type'}

                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=len
                )
                chunks = text_splitter.split_documents(documents)
                chunks_total = len(chunks)

                new_chunks = 0
                documents_to_add = []
                ids_to_add = []
                metadatas_to_add = []

                for i, chunk in enumerate(chunks):
                    content = chunk.page_content
                    content_hash = self._compute_document_hash(content)

                    if content_hash not in self.document_hashes:
                        self.document_hashes.add(content_hash)
                        documents_to_add.append(content)
                        doc_id = f"{os.path.basename(file_path)}_{len(self.document_hashes)}"
                        ids_to_add.append(doc_id)
                        metadatas_to_add.append({
                            "source": os.path.basename(file_path),
                            "filepath": file_path,
                            "content_hash": content_hash
                        })
                        new_chunks += 1

                if new_chunks > 0 and documents_to_add:
                    self.collection.add(
                        documents=documents_to_add,
                        ids=ids_to_add,
                        metadatas=metadatas_to_add
                    )
                    logger.info(f'Added {new_chunks} new chunks from {file_path} to Chroma')
                else:
                    logger.info(f'No new chunks added from {file_path} (possibly duplicate)')

                return {
                    'success': True,
                    'chunks_added': new_chunks,
                    'chunks_total': chunks_total,
                    'is_duplicate': new_chunks == 0 and chunks_total > 0
                }

            except Exception as e:
                logger.error(f'Unexpected error processing document {file_path}: {e}', exc_info=True)
                return {'success': False, 'chunks_added': 0, 'error': str(e)}

    def _expand_query(self, query):
        """Expand query with synonyms and related terms for better recall

        Args:
            query: Original query string

        Returns:
            List of expanded queries including the original
        """
        expanded = [query]

        expansions = {
            'account': ['user', 'profile', 'login', 'registration'],
            'password': ['credential', 'authentication', 'reset', 'change'],
            'error': ['issue', 'problem', 'bug', 'failure', 'exception'],
            'payment': ['billing', 'invoice', 'transaction', 'charge'],
            'subscription': ['plan', 'pricing', 'renewal', 'upgrade', 'downgrade'],
            'feature': ['functionality', 'capability', 'option'],
            'issue': ['problem', 'error', 'bug', 'difficulty'],
            'help': ['support', 'assistance', 'guide', 'tutorial'],
            'setup': ['installation', 'configuration', 'initialize', 'start'],
            'api': ['endpoint', 'integration', 'webhook', 'request'],
        }

        query_lower = query.lower()
        for keyword, synonyms in expansions.items():
            if keyword in query_lower:
                for synonym in synonyms[:2]:
                    expanded_query = query_lower.replace(keyword, synonym)
                    if expanded_query != query_lower:
                        expanded.append(expanded_query)
                break

        return expanded

    def _init_cross_encoder(self):
        """Initialize Cross-Encoder model for re-ranking (lazy loading)"""
        if self._cross_encoder_ready:
            return True

        try:
            logger.info(f'Loading Cross-Encoder model: {self._cross_encoder_model}')
            self.cross_encoder = CrossEncoder(self._cross_encoder_model)
            self._cross_encoder_ready = True
            logger.info('Cross-Encoder model loaded successfully')
            return True
        except Exception as e:
            logger.error(f'Failed to load Cross-Encoder: {e}')
            self._cross_encoder_ready = False
            return False

    def _rerank_with_cross_encoder(self, query, results, k=3):
        """Re-rank results using Cross-Encoder

        Args:
            query: Original query
            results: List of retrieved chunks with similarity scores
            k: Number of top results to return after re-ranking

        Returns:
            Re-ranked list of results
        """
        if not results:
            return results

        # Try to initialize cross-encoder, fall back to original ranking if failed
        if not self._init_cross_encoder():
            logger.warning('Cross-Encoder not available, using original ranking')
            return results[:k]

        try:
            # Prepare pairs for cross-encoder
            pairs = [[query, result['content']] for result in results]

            # Get cross-encoder scores
            scores = self.cross_encoder.predict(pairs)

            # Attach scores to results
            for i, result in enumerate(results):
                result['rerank_score'] = float(scores[i])

            # Sort by rerank score
            results.sort(key=lambda x: x['rerank_score'], reverse=True)

            logger.debug(f'Cross-Encoder re-ranking completed for {len(results)} results')
            return results[:k]

        except Exception as e:
            logger.error(f'Error in Cross-Encoder re-ranking: {e}')
            return results[:k]

    def _tokenize(self, text):
        """Simple tokenizer for BM25"""
        return re.findall(r'\b\w+\b', text.lower())

    def _build_bm25_index(self):
        """Build BM25 index from Chroma collection (lazy initialization)"""
        try:
            all_docs = self.collection.get(include=["documents", "metadatas"])

            if not all_docs or not all_docs.get('documents'):
                logger.info('No documents to build BM25 index')
                return False

            self.bm25_documents = all_docs['documents']
            self.bm25_metadatas = all_docs.get('metadatas', [])

            tokenized_docs = [self._tokenize(doc) for doc in self.bm25_documents]
            self.bm25_index = BM25Okapi(tokenized_docs)

            self._bm25_initialized = True
            logger.info(f'Built BM25 index with {len(self.bm25_documents)} documents')
            return True

        except Exception as e:
            logger.error(f'Error building BM25 index: {e}', exc_info=True)
            return False

    def _hybrid_search(self, query, k=3, alpha=0.5):
        """Hybrid search combining BM25 and vector search with RRF fusion

        Args:
            query: Search query
            k: Number of results to return
            alpha: Weight for vector search (0.5 = equal weight)

        Returns:
            List of results with reciprocal rank fusion scores
        """
        try:
            if not self._bm25_initialized:
                if not self._build_bm25_index():
                    return self.retrieve_relevant_info(query, k, use_hybrid=False)

            tokenized_query = self._tokenize(query)
            bm25_scores = self.bm25_index.get_scores(tokenized_query)

            vector_results = self.collection.query(
                query_texts=[query],
                n_results=len(self.bm25_documents) if self.bm25_documents else k,
                include=["documents", "distances", "metadatas"]
            )

            bm25_result_map = {}
            vector_result_map = {}

            for i, (doc, score) in enumerate(zip(self.bm25_documents, bm25_scores)):
                if score > 0:
                    bm25_result_map[doc] = {
                        'score': float(score),
                        'metadata': self.bm25_metadatas[i] if i < len(self.bm25_metadatas) else {}
                    }

            if vector_results and vector_results.get('documents') and vector_results['documents'][0]:
                for doc, distance, meta in zip(
                    vector_results['documents'][0],
                    vector_results['distances'][0],
                    vector_results['metadatas'][0]
                ):
                    similarity = 1 - distance
                    vector_result_map[doc] = {
                        'score': float(similarity),
                        'metadata': meta or {}
                    }

            rrf_scores = {}
            all_docs = set(bm25_result_map.keys()) | set(vector_result_map.keys())

            for doc in all_docs:
                rrf_score = 0

                if doc in bm25_result_map:
                    bm25_rank = sum(1 for d, s in bm25_result_map.items()
                                   if s['score'] > bm25_result_map[doc]['score']) + 1
                    rrf_score += alpha / (bm25_rank + 60)

                if doc in vector_result_map:
                    vector_rank = sum(1 for d, s in vector_result_map.items()
                                     if s['score'] > vector_result_map[doc]['score']) + 1
                    rrf_score += (1 - alpha) / (vector_rank + 60)

                if rrf_score > 0:
                    rrf_scores[doc] = {
                        'rrf_score': rrf_score,
                        'bm25_score': bm25_result_map.get(doc, {}).get('score', 0),
                        'vector_score': vector_result_map.get(doc, {}).get('score', 0),
                        'metadata': bm25_result_map.get(doc, {}).get('metadata') or
                                   vector_result_map.get(doc, {}).get('metadata', {})
                    }

            sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1]['rrf_score'], reverse=True)[:k]

            retrieved = []
            for doc, scores in sorted_results:
                retrieved.append({
                    'content': doc,
                    'similarity': scores['rrf_score'],
                    'source': scores['metadata'].get('source', 'unknown'),
                    'bm25_score': scores['bm25_score'],
                    'vector_score': scores['vector_score']
                })

            logger.debug(f'Hybrid search retrieved {len(retrieved)} chunks for query: {query[:50]}...')
            return retrieved

        except Exception as e:
            logger.error(f'Error in hybrid search: {e}', exc_info=True)
            return self.retrieve_relevant_info(query, k, use_hybrid=False)

    def retrieve_relevant_info(self, query, k=3, similarity_threshold=0.25, use_expansion=True, use_hybrid=False, use_reranking=True):
        """Retrieve relevant information using Chroma vector search or hybrid search

        Args:
            query: Search query
            k: Number of top results to return
            similarity_threshold: Minimum similarity score to include results
            use_expansion: Whether to use query expansion for better recall
            use_hybrid: Whether to use hybrid search (BM25 + vector)
            use_reranking: Whether to use Cross-Encoder re-ranking (only applies if k > 3)

        Returns:
            List of relevant document chunks with similarity scores
        """
        # Get more candidates for re-ranking
        retrieve_k = k * 3 if use_reranking else k

        # Use hybrid search if enabled
        if use_hybrid:
            results = self._hybrid_search(query, retrieve_k)
        else:
            try:
                queries_to_search = [query]
                if use_expansion:
                    queries_to_search = self._expand_query(query)
                    logger.debug(f'Query expansion: {query} -> {queries_to_search}')

                all_results = []
                seen_contents = set()

                for search_query in queries_to_search:
                    results = self.collection.query(
                        query_texts=[search_query],
                        n_results=retrieve_k,
                        include=["documents", "distances", "metadatas"]
                    )

                    if results and results.get('documents') and results['documents'][0]:
                        for doc, distance, meta in zip(
                            results['documents'][0],
                            results['distances'][0],
                            results['metadatas'][0]
                        ):
                            similarity = 1 - distance
                            if similarity >= similarity_threshold and doc not in seen_contents:
                                seen_contents.add(doc)
                                all_results.append({
                                    'content': doc,
                                    'similarity': float(similarity),
                                    'source': meta.get('source', 'unknown') if meta else 'unknown'
                                })

                all_results.sort(key=lambda x: x['similarity'], reverse=True)
                results = all_results

            except Exception as e:
                logger.error(f'Error retrieving relevant info: {e}', exc_info=True)
                return []

        # Apply Cross-Encoder re-ranking if enabled and we have results
        if use_reranking and results and len(results) > k:
            results = self._rerank_with_cross_encoder(query, results, k)
        else:
            results = results[:k]

        if results:
            logger.debug(f'Retrieved {len(results)} relevant chunks for query: {query[:50]}...')
        else:
            logger.debug(f'No relevant chunks found for query: {query[:50]}...')

        return results

    def get_document_count(self):
        """Get total number of document chunks in the collection"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f'Error getting document count: {e}', exc_info=True)
            return 0

    def delete_documents_by_source(self, filename):
        """Delete all chunks from a specific source file"""
        try:
            existing = self.collection.get(
                where={"source": filename},
                include=["metadatas"]
            )

            if existing and existing.get('ids'):
                self.collection.delete(ids=existing['ids'])
                for meta in existing.get('metadatas', []):
                    if meta and 'content_hash' in meta:
                        self.document_hashes.discard(meta['content_hash'])

                if self._bm25_initialized:
                    self._build_bm25_index()

                logger.info(f'Deleted documents from source: {filename}')
                return True

            return False
        except Exception as e:
            logger.error(f'Error deleting documents: {e}', exc_info=True)
            return False

    def clear_bm25_index(self):
        """Clear BM25 index (use when documents are updated externally)"""
        self.bm25_index = None
        self.bm25_documents = []
        self.bm25_metadatas = []
        self._bm25_initialized = False
        logger.info('Cleared BM25 index')


# Global instance
rag_utils = RAGUtils()
