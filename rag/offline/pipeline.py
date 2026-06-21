# Disable CoreML for ONNX Runtime (fixes macOS CoreML errors)
# MUST be set BEFORE importing any ONNX/chromadb modules
import os
os.environ['ORT_DISABLE_COREML'] = '1'
os.environ['ONNXRUNTIME_DISABLE_CPU'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Force CPU only
os.environ['OMP_NUM_THREADS'] = '1'

# HuggingFace: use mirror for China, then prefer offline cache
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.expanduser("~/.cache/huggingface/hub")

from sentence_transformers import CrossEncoder  # noqa: E402
import logging  # noqa: E402
import threading  # noqa: E402
import chromadb  # noqa: E402
from rank_bm25 import BM25Okapi  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
import uuid  # noqa: E402

from rag.offline.steps.embedding import CustomEmbeddingFunction, EmbeddingStage  # noqa: E402, F401
from rag.offline.steps.cleaning import CleaningStage  # noqa: E402
from rag.offline.steps.chunking import ChunkingStage, ChunkResult  # noqa: E402, F401
from rag.offline.steps.quality import QualityStage, QualityConfig  # noqa: E402
from rag.offline.steps.indexing import IndexingStage  # noqa: E402
from rag.offline.parsers import get_parser  # noqa: E402
from rag.offline.pipeline_config import (  # noqa: E402
    EmbeddingConfig, CleaningConfig, ChunkingConfig, IndexingConfig,
)
from rag.offline.parent_store import parent_store  # noqa: E402

logger = logging.getLogger(__name__)


# ======================================================================
# ETLPipeline — orchestrator that chains parse → clean → chunk → quality → index
# ======================================================================

class ETLPipeline:
    """Orchestrate the full ETL pipeline: parse → clean → chunk → quality → index."""

    def __init__(self, collection, parent_store, embedding_fn):
        self._collection = collection
        self._parent_store = parent_store
        self._embedding_fn = embedding_fn

        self._cleaning = CleaningStage(CleaningConfig())
        self._chunking = ChunkingStage(ChunkingConfig(), embedding_fn)
        self._quality = QualityStage(QualityConfig())
        self._indexing = IndexingStage(IndexingConfig(), collection, parent_store)
        self._indexing.load_hashes()

    def run(self, file_path, strategy='auto', chunk_size=1000, chunk_overlap=150,
            semantic_threshold=0.5, use_small_to_big=False,
            parent_size=2000, child_size=400) -> dict:
        """Execute full ETL pipeline with structured per-stage logging.

        Returns the same dict shape as the original ``process_document``,
        plus ``detected_strategy`` for DB persistence.
        """
        run_id = uuid.uuid4().hex[:12]
        t0 = time.time()
        filename = os.path.basename(file_path)
        logger.info(
            '[%s] Pipeline START — file=%s strategy=%s small_to_big=%s',
            run_id, filename, strategy, use_small_to_big,
        )

        # 1. Parse
        t_stage = time.time()
        logger.info('[%s] Stage 1/5 — Parsing: %s', run_id, filename)
        parser = get_parser(file_path)
        pages = parser.parse(file_path)
        total_chars = sum(len(p.text) for p in pages)
        logger.info(
            '[%s] Stage 1/5 — Parsing complete: %d pages, %d chars (%.2fs)',
            run_id, len(pages), total_chars, time.time() - t_stage,
        )

        # 2. Clean
        t_stage = time.time()
        logger.info(
            '[%s] Stage 2/5 — Cleaning: %d pages', run_id, len(pages),
        )
        cleaned_pages = self._cleaning(pages)
        logger.info(
            '[%s] Stage 2/5 — Cleaning complete: %d→%d pages (%.2fs)',
            run_id, len(pages), len(cleaned_pages), time.time() - t_stage,
        )

        # 3. Convert ParsedPage → Document-like objects
        documents = [self._to_doc(p) for p in cleaned_pages]

        # 4. Chunk
        t_stage = time.time()
        chunk_config = ChunkingConfig(
            strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            semantic_threshold=semantic_threshold, parent_size=parent_size,
            child_size=child_size,
        )
        self._chunking.config = chunk_config
        if use_small_to_big:
            chunk_result = self._chunking(documents, strategy='small_to_big')
        else:
            chunk_result = self._chunking(documents, strategy=strategy)

        detected_strategy = chunk_result.strategy_used
        logger.info(
            '[%s] Stage 3/5 — Chunking: strategy=%s → detected=%s',
            run_id, strategy, detected_strategy,
        )
        logger.info(
            '[%s] Stage 3/5 — Chunking complete: %d chunks (%.2fs)',
            run_id, chunk_result.total, time.time() - t_stage,
        )

        # 5. Quality filter
        t_stage = time.time()
        before_q = len(chunk_result.chunks)
        logger.info('[%s] Stage 4/5 — Quality filtering: %d chunks', run_id, before_q)
        chunks = self._quality(chunk_result.chunks)
        after_q = len(chunks)
        logger.info(
            '[%s] Stage 4/5 — Quality filtering complete: %d→%d chunks (%.2fs)',
            run_id, before_q, after_q, time.time() - t_stage,
        )

        # 6. Index
        t_stage = time.time()
        logger.info(
            '[%s] Stage 5/5 — Indexing: %d candidates', run_id, after_q,
        )
        small_to_big_data = None
        if use_small_to_big:
            small_to_big_data = {
                'parent_chunks': chunk_result.parent_chunks,
                'child_chunks': chunk_result.child_chunks,
            }
        result = self._indexing(
            chunks, file_path,
            use_small_to_big=use_small_to_big,
            small_to_big_data=small_to_big_data,
        )
        logger.info(
            '[%s] Stage 5/5 — Indexing complete: %d new, %d total, %d dup (%.2fs)',
            run_id,
            result.get('chunks_added', 0),
            result.get('chunks_total', 0),
            1 if result.get('is_duplicate') else 0,
            time.time() - t_stage,
        )

        total_time = time.time() - t0
        logger.info(
            '[%s] Pipeline DONE — %d chunks indexed, strategy=%s, total=%.2fs',
            run_id, result.get('chunks_added', 0), detected_strategy, total_time,
        )

        # Add metadata keys
        result['strategy'] = strategy
        result['detected_strategy'] = detected_strategy
        result['use_small_to_big'] = use_small_to_big
        result['run_id'] = run_id
        result['total_time'] = round(total_time, 2)
        result['pages'] = len(pages)
        result['total_chars'] = total_chars
        return result

    def preview(self, file_path, strategy='auto', chunk_size=1000, chunk_overlap=150,
                semantic_threshold=0.5, use_small_to_big=False,
                parent_size=2000, child_size=400) -> dict:
        """Parse + Clean + Chunk only.  No indexing.

        Returns the same dict shape as the original ``preview_chunks``.
        """
        parser = get_parser(file_path)
        pages = parser.parse(file_path)
        cleaned_pages = self._cleaning(pages)
        documents = [self._to_doc(p) for p in cleaned_pages]

        chunk_config = ChunkingConfig(
            strategy=strategy, chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            semantic_threshold=semantic_threshold, parent_size=parent_size,
            child_size=child_size,
        )
        self._chunking.config = chunk_config
        if use_small_to_big:
            chunk_result = self._chunking(documents, strategy='small_to_big')
        else:
            chunk_result = self._chunking(documents, strategy=strategy)

        chunks = chunk_result.chunks

        total_chars = sum(len(c.page_content) for c in chunks)
        avg_chunk_size = total_chars // len(chunks) if chunks else 0

        preview_list = []
        for i, chunk in enumerate(chunks, 1):
            content = chunk.page_content
            preview_text = content[:200] + '...' if len(content) > 200 else content
            preview_list.append({
                'index': i,
                'content': content,
                'char_count': len(content),
                'preview': preview_text,
                'page': chunk.metadata.get('page', 0) if hasattr(chunk, 'metadata') else 0,
            })

        result = {
            'success': True,
            'strategy': strategy,
            'use_small_to_big': use_small_to_big,
            'semantic_threshold': semantic_threshold,
            'total_chunks': len(chunks),
            'total_chars': total_chars,
            'avg_chunk_size': avg_chunk_size,
            'chunks': preview_list,
        }

        if use_small_to_big:
            parent_preview = []
            for i, p in enumerate(chunk_result.parent_chunks, 1):
                content = p['content']
                preview_text = content[:300] + '...' if len(content) > 300 else content
                parent_preview.append({
                    'index': i, 'id': p['id'], 'content': content,
                    'char_count': len(content), 'preview': preview_text,
                    'page': p['metadata'].get('page', 0),
                })
            child_preview = []
            for i, c in enumerate(chunk_result.child_chunks, 1):
                content = c['content']
                preview_text = content[:150] + '...' if len(content) > 150 else content
                child_preview.append({
                    'index': i, 'id': c['id'], 'content': content,
                    'char_count': len(content), 'preview': preview_text,
                    'parent_id': c['metadata'].get('parent_id'),
                    'page': c['metadata'].get('page', 0),
                })
            result.update({
                'total_parents': len(chunk_result.parent_chunks),
                'total_children': len(chunk_result.child_chunks),
                'parent_chunks': parent_preview[:10],
                'child_chunks': child_preview[:20],
                'all_parent_chunks': parent_preview,
                'all_child_chunks': child_preview,
                'parent_size': parent_size,
                'child_size': child_size,
            })

        return result

    @staticmethod
    def _to_doc(page) -> object:
        """Convert ParsedPage to a LangChain Document-like object."""
        return type('obj', (object,), {
            'page_content': page.text,
            'metadata': {'source': page.source, 'page': page.page, **page.metadata},
        })()


# ======================================================================
# RAGUtils — backward-compatible facade with retrieval logic
# ======================================================================

class RAGUtils:
    """RAG utility class for document processing, retrieval, and indexing.

    Public method signatures are identical to the pre-refactoring version for
    full backward compatibility.
    """

    _lock = threading.Lock()

    def __init__(self):
        # Chroma client with persistent storage
        self.client = chromadb.PersistentClient(path="./instance/chroma_db")

        # Embedding stage (lazy init)
        self._embedding_stage = EmbeddingStage(EmbeddingConfig())
        embedding_fn = self._embedding_stage.get_embedding_fn()

        # Get or create Chroma collection
        try:
            self.collection = self.client.get_collection(
                name="knowledge",
                embedding_function=embedding_fn,
            )
            logger.info('Found existing Chroma collection')
        except Exception:
            self.collection = self.client.create_collection(
                name="knowledge",
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info('Created new Chroma collection with custom embedding function')

        # ETL Pipeline orchestrator
        self._pipeline = ETLPipeline(self.collection, parent_store, embedding_fn)

        # BM25 index for hybrid search (built on-demand)
        self.bm25_index = None
        self.bm25_documents = []
        self.bm25_metadatas = []
        self._bm25_initialized = False

        # Cross-Encoder for re-ranking (lazy initialization)
        self.cross_encoder = None
        self._cross_encoder_model = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._cross_encoder_ready = False

    # ------------------------------------------------------------------
    # ETL delegation (process_document / preview_chunks)
    # ------------------------------------------------------------------

    def process_document(self, file_path, strategy='semantic', chunk_size=1500,
                         chunk_overlap=300, semantic_threshold=0.5,
                         use_small_to_big=False, parent_size=2000, child_size=400):
        """Process a document and add it to the Chroma collection (thread-safe).

        Delegates to ``ETLPipeline.run()``.  Returns the same dict shape as
        the original implementation.
        """
        with RAGUtils._lock:
            try:
                return self._pipeline.run(
                    file_path=file_path,
                    strategy=strategy,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    semantic_threshold=semantic_threshold,
                    use_small_to_big=use_small_to_big,
                    parent_size=parent_size,
                    child_size=child_size,
                )
            except Exception as e:
                logger.error(f'Unexpected error processing document {file_path}: {e}', exc_info=True)
                return {'success': False, 'chunks_added': 0, 'error': str(e)}

    def preview_chunks(self, file_path, strategy='semantic', chunk_size=1500,
                       chunk_overlap=300, semantic_threshold=0.5,
                       use_small_to_big=False, parent_size=2000, child_size=400):
        """Preview document chunking without saving to knowledge base.

        Delegates to ``ETLPipeline.preview()``.
        """
        try:
            return self._pipeline.preview(
                file_path=file_path,
                strategy=strategy,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                semantic_threshold=semantic_threshold,
                use_small_to_big=use_small_to_big,
                parent_size=parent_size,
                child_size=child_size,
            )
        except Exception as e:
            logger.error(f'Error previewing chunks: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Backward-compatibility wrappers
    # ------------------------------------------------------------------

    def _create_parent_child_chunks(self, documents, parent_size=2000, child_size=400):
        """Backward-compat wrapper — delegates to ``ChunkingStage``."""
        return self._pipeline._chunking.create_parent_child_chunks(
            documents, parent_size, child_size,
        )

    @staticmethod
    def _quality_score(text):
        """Backward-compat wrapper — delegates to ``QualityStage``."""
        return QualityStage.score_text(text)

    def _split_sentences(self, text):
        """Backward-compat wrapper — delegates to ``ChunkingStage``."""
        return self._pipeline._chunking._split_sentences(text)

    @staticmethod
    def _compute_document_hash(content):
        """Backward-compat wrapper — delegates to ``IndexingStage``."""
        return IndexingStage.compute_hash(content)

    # ------------------------------------------------------------------
    # Query expansion
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Cross-Encoder re-ranking
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # BM25 index
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Hybrid search (BM25 + vector with RRF fusion)
    # ------------------------------------------------------------------

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
                        'metadata': (
                            bm25_result_map.get(doc, {}).get('metadata')
                            or vector_result_map.get(doc, {}).get('metadata', {})
                        ),
                    }

            sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1]['rrf_score'], reverse=True)[:k]

            retrieved = []
            for doc, scores in sorted_results:
                retrieved.append({
                    'content': doc,
                    'similarity': scores['rrf_score'],
                    'source': scores['metadata'].get('source', 'unknown'),
                    'metadata': scores['metadata'],
                    'bm25_score': scores['bm25_score'],
                    'vector_score': scores['vector_score']
                })

            logger.debug(f'Hybrid search retrieved {len(retrieved)} chunks for query: {query[:50]}...')
            return retrieved

        except Exception as e:
            logger.error(f'Error in hybrid search: {e}', exc_info=True)
            return self.retrieve_relevant_info(query, k, use_hybrid=False)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve_relevant_info(self, query, k=3, similarity_threshold=0.25,
                               use_expansion=True, use_hybrid=False,
                               use_reranking=True):
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
                                    'source': meta.get('source', 'unknown') if meta else 'unknown',
                                    'metadata': meta or {},
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

    def retrieve_with_parent(self, query, k=3, similarity_threshold=0.25, use_expansion=True, use_reranking=True):
        """Small-to-Big 检索：小块检索，返回大块

        1. 用小块做向量检索（高精度）
        2. 获取匹配小块的 parent_id
        3. 从 ParentDocumentStore 获取大块
        4. 返回大块内容（完整上下文）

        Args:
            query: 搜索查询
            k: 返回结果数量
            similarity_threshold: 最低相似度阈值
            use_expansion: 是否使用查询扩展
            use_reranking: 是否使用 Cross-Encoder 重排序

        Returns:
            List: [{'content': str, 'similarity': float, 'source': str, 'parent_id': str}]
        """
        # 获取更多候选结果用于重排序
        retrieve_k = k * 3 if use_reranking else k

        try:
            queries_to_search = [query]
            if use_expansion:
                queries_to_search = self._expand_query(query)
                logger.debug(f'Query expansion for Small-to-Big: {query} -> {queries_to_search}')

            all_results = []
            seen_parent_ids = set()  # 去重：同一大块只返回一次

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

                        # 只处理有 parent_id 的结果（Small-to-Big 模式）
                        parent_id = meta.get('parent_id') if meta else None
                        if not parent_id:
                            # 如果没有 parent_id，说明不是 small_to_big 模式，跳过
                            continue

                        if similarity >= similarity_threshold and parent_id not in seen_parent_ids:
                            seen_parent_ids.add(parent_id)

                            # 从 ParentDocumentStore 获取大块
                            parent_doc = parent_store.get(parent_id)
                            if parent_doc:
                                all_results.append({
                                    'content': parent_doc['content'],  # 返回大块内容
                                    'similarity': float(similarity),
                                    'source': parent_doc['metadata'].get('source', 'unknown'),
                                    'parent_id': parent_id,
                                    'child_content': doc,  # 原始小块内容（用于调试）
                                    'metadata': parent_doc.get('metadata', {}),
                                })

            all_results.sort(key=lambda x: x['similarity'], reverse=True)

            # Cross-Encoder 重排序（使用大块内容）
            if use_reranking and all_results and len(all_results) > k:
                all_results = self._rerank_with_cross_encoder(query, all_results, k)
            else:
                all_results = all_results[:k]

            if all_results:
                logger.info(f'Small-to-Big retrieved {len(all_results)} parent chunks for query: {query[:50]}...')
            else:
                logger.info(f'No parent chunks found for query: {query[:50]}...')

            return all_results

        except Exception as e:
            logger.error(f'Error in Small-to-Big retrieval: {e}', exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    def get_document_count(self):
        """Get total number of document chunks in the collection"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f'Error getting document count: {e}', exc_info=True)
            return 0

    def delete_documents_by_source(self, filename):
        """Delete all chunks from a specific source file (including parent documents)

        Delegates ChromaDB deletion to ``IndexingStage`` and rebuilds the BM25
        index if it was initialized.
        """
        try:
            deleted = self._pipeline._indexing.delete_by_source(filename)
            if deleted and self._bm25_initialized:
                self._build_bm25_index()
            if deleted:
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


# ======================================================================
# Global singleton (unchanged)
# ======================================================================

rag_utils = RAGUtils()
