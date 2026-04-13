# Disable CoreML for ONNX Runtime (fixes macOS CoreML errors)
# MUST be set BEFORE importing any ONNX/chromadb modules
import os
os.environ['ORT_DISABLE_COREML'] = '1'
os.environ['ONNXRUNTIME_DISABLE_CPU'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Force CPU only
os.environ['OMP_NUM_THREADS'] = '1'

# Set offline mode BEFORE importing huggingface modules
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['SENTENCE_TRANSFORMERS_HOME'] = os.path.expanduser("~/.cache/huggingface/hub")

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_experimental.text_splitter import SemanticChunker
from sentence_transformers import CrossEncoder
import pdfplumber
import logging
import hashlib
import threading
import chromadb
from chromadb.config import Settings
from rank_bm25 import BM25Okapi
import re
from collections import Counter
import uuid

from rag.parent_store import parent_store

logger = logging.getLogger(__name__)


class CustomEmbeddingFunction:
    """Custom embedding function using langchain HuggingFaceEmbeddings"""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        try:
            # Use cached model only - no network requests
            # Force CPU usage and disable ONNX GPU acceleration
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={
                    'device': 'cpu',
                    'show_progress': False
                },
                encode_kwargs={
                    'normalize_embeddings': True,
                    'show_progress_bar': False
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

    def embed_query(self, text):
        """Embed a single query"""
        return self.embeddings.embed_query(text)


class RAGUtils:
    # Class-level lock for thread safety
    _lock = threading.Lock()

    # Class-level cache for embedding function (lazy initialization)
    _embedding_fn = None
    _embedding_lock = threading.Lock()

    def __init__(self):
        # Initialize Chroma client with persistent storage
        self.client = chromadb.PersistentClient(path="./chroma_db")

        # Lazy init for embedding - only when needed
        self._embedding_initialized = False

        # Get or create embedding function first
        embedding_fn = self._get_embedding_fn()

        # Get collection with our custom embedding function
        try:
            self.collection = self.client.get_collection(
                name="knowledge",
                embedding_function=embedding_fn
            )
            logger.info('Found existing Chroma collection')
        except ValueError:
            # Collection doesn't exist, create it with our embedding function
            self.collection = self.client.create_collection(
                name="knowledge",
                embedding_function=embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info('Created new Chroma collection with custom embedding function')

        # Track processed document hashes for deduplication (after collection init)
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

    def _get_embedding_fn(self):
        """Get or initialize the embedding function"""
        # Always return if already initialized
        if self._embedding_initialized and self._embedding_fn is not None:
            return self._embedding_fn

        with RAGUtils._embedding_lock:
            if self._embedding_initialized and self._embedding_fn is not None:
                return self._embedding_fn

            try:
                self._embedding_fn = CustomEmbeddingFunction(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info('Using HuggingFace embedding function (all-MiniLM-L6-v2)')
            except Exception as e:
                logger.warning(f'Failed to load HuggingFace embedding: {e}')
                self._embedding_fn = None

            self._embedding_initialized = True
            return self._embedding_fn

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

    def _clean_text(self, text):
        """Clean extracted text from PDF (remove noise like standalone numbers)

        Args:
            text: Raw extracted text

        Returns:
            Cleaned text with noise removed
        """
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            stripped = line.strip()
            # Skip lines that are just numbers with dots (e.g., "1.", "2.", "10.")
            if re.match(r'^\d+\.\s*$', stripped):
                continue
            # Skip very short lines (less than 5 chars) that are likely noise
            if len(stripped) < 5 and re.match(r'^[\d\.\s]+$', stripped):
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _extract_pdf_text_layout_aware(self, file_path):
        """Extract text from PDF using pdfplumber with layout awareness

        Args:
            file_path: Path to PDF file

        Returns:
            list of dicts: [{'text': str, 'page': int, 'section': str}]
        """
        extracted_pages = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text with layout preservation
                    # pdfplumber extracts text in reading order by default
                    page_text = page.extract_text()

                    if page_text:
                        extracted_pages.append({
                            'text': page_text,
                            'page': page_num,
                            'source': os.path.basename(file_path)
                        })

            logger.info(f'Extracted text from {len(extracted_pages)} pages using pdfplumber')
            return extracted_pages

        except Exception as e:
            logger.error(f'Error extracting PDF text with pdfplumber: {e}')
            # Fallback to PyPDFLoader
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            return [
                {'text': doc.page_content, 'page': i+1, 'source': os.path.basename(file_path)}
                for i, doc in enumerate(documents)
            ]

    def _detect_repeated_lines(self, pages, threshold=0.5):
        """Detect header/footer lines that appear in multiple pages

        Args:
            pages: List of page texts
            threshold: Minimum fraction of pages for a line to be considered repeated

        Returns:
            set of repeated lines to filter
        """
        if not pages:
            return set()

        line_counts = Counter()
        for page_text in pages:
            lines = set(page_text.strip().split('\n'))
            for line in lines:
                line_counts[line.strip()] += 1

        # Lines appearing in more than threshold% of pages
        min_count = int(len(pages) * threshold)
        repeated = {line for line, count in line_counts.items()
                   if count >= min_count and len(line) < 100}

        logger.info(f'Detected {len(repeated)} repeated lines (headers/footers)')
        return repeated

    def _remove_headers_footers(self, text, repeated_lines):
        """Remove header and footer lines from text

        Args:
            text: Page text
            repeated_lines: Set of repeated lines to filter

        Returns:
            Cleaned text
        """
        lines = text.split('\n')
        cleaned = []

        for line in lines:
            stripped = line.strip()
            # Skip if it's a detected repeated line
            if stripped in repeated_lines:
                continue
            # Skip page number patterns like "第 1 页" or "- 1 -"
            if re.match(r'^(第\s*\d+\s*页|\s*[-=]+\s*\d+\s*[-=]+\s*)$', stripped):
                continue
            cleaned.append(line)

        return '\n'.join(cleaned)

    def _quality_score(self, text):
        """Score text quality (0-100)

        Args:
            text: Text to score

        Returns:
            Quality score (0-100)
        """
        if not text or not text.strip():
            return 0

        score = 0
        text_len = len(text.strip())

        # Length score (20 points)
        if 100 <= text_len <= 2000:
            score += 20
        elif 50 <= text_len < 100 or 2000 < text_len <= 3000:
            score += 10

        # Sentence completeness (20 points)
        has_punctuation = bool(re.search(r'[,.!?!.:;?]', text))
        if has_punctuation:
            score += 20

        # Information density (20 points)
        # Count meaningful characters (not just numbers/symbols)
        meaningful = len(re.findall(r'[\u4e00-\u9fa5a-zA-Z]', text))
        if text_len > 0 and meaningful / text_len > 0.3:
            score += 20

        # Noise ratio (20 points)
        noise_pattern = r'^[\d\s\.\-\(\)]+$'
        noise_lines = [l for l in text.split('\n') if re.match(noise_pattern, l.strip())]
        if len(noise_lines) / max(len(text.split('\n')), 1) < 0.2:
            score += 20

        # Language detection (20 points) - simplified check
        # Chinese or English characters should dominate
        if meaningful > text_len * 0.5:
            score += 20

        return score

    def _create_semantic_splitter(self, embeddings=None, threshold=0.5):
        """Create semantic chunker based on embedding similarity

        Args:
            embeddings: Embedding function to use (defaults to existing one)
            threshold: Breakpoint threshold (0.1-0.9). Lower = more splits.

        Returns:
            SemanticChunker instance
        """
        if embeddings is None:
            embedding_fn = self._get_embedding_fn()
            if embedding_fn is None:
                raise ValueError("Embeddings not available for semantic chunking")
            embeddings = embedding_fn.embeddings

        logger.info(f'Creating SemanticChunker with threshold={threshold}')

        return SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=threshold,
            min_chunk_size=50  # Minimum characters per chunk
        )

    def _semantic_chunk(self, documents, embeddings=None, threshold=0.5):
        """Semantic chunking based on sentence embedding similarity

        Uses SemanticChunker to split documents at semantic boundaries
        where sentence similarity drops below threshold.

        Args:
            documents: List of document objects with page_content and metadata
            embeddings: Embedding function to use
            threshold: Breakpoint threshold (0.1-0.9). Lower = more splits.

        Returns:
            List of semantically chunked documents
        """
        try:
            splitter = self._create_semantic_splitter(embeddings, threshold)
            chunks = splitter.split_documents(documents)
            logger.info(f'Semantic chunking produced {len(chunks)} chunks with threshold={threshold}')
            return chunks
        except Exception as e:
            logger.warning(f'Semantic chunking failed, falling back to sentence splitter: {e}')
            return self._sentence_chunk(documents)

    def _split_sentences(self, text):
        """Split text into sentences (supports Chinese and English)

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Pattern for Chinese and English sentence boundaries
        # Chinese: 。！？；
        # English: . ! ?
        # Also consider newlines as sentence boundaries for structured text
        pattern = r'(?<=[。！？；.!?\n])\s*'
        sentences = re.split(pattern, text)
        # Filter empty sentences and preserve punctuation
        return [s.strip() for s in sentences if s.strip()]

    def _create_chunk(self, content, metadata):
        """Create a document chunk object

        Args:
            content: Chunk text content
            metadata: Original document metadata

        Returns:
            Document-like object with page_content and metadata
        """
        return type('obj', (object,), {
            'page_content': content,
            'metadata': metadata
        })()

    def _sentence_chunk(self, documents, max_chunk_size=1500):
        """Sentence-level chunking (fallback strategy)

        Splits documents into sentences and merges them into chunks
        while respecting sentence boundaries. Never splits mid-sentence.

        Args:
            documents: List of document objects
            max_chunk_size: Maximum chunk size in characters

        Returns:
            List of chunked documents with preserved sentence boundaries
        """
        chunks = []
        for doc in documents:
            sentences = self._split_sentences(doc.page_content)
            current_chunk = ""
            current_sentences = []

            for sent in sentences:
                # If single sentence exceeds max size, it becomes its own chunk
                if len(sent) > max_chunk_size:
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, doc.metadata))
                        current_chunk = ""
                        current_sentences = []
                    chunks.append(self._create_chunk(sent, doc.metadata))
                    continue

                # Check if adding this sentence would exceed limit
                test_chunk = current_chunk + sent if not current_chunk else current_chunk + " " + sent
                if len(test_chunk) <= max_chunk_size:
                    current_chunk = test_chunk
                    current_sentences.append(sent)
                else:
                    # Save current chunk and start new one
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, doc.metadata))
                    current_chunk = sent
                    current_sentences = [sent]

            # Don't forget the last chunk
            if current_chunk:
                chunks.append(self._create_chunk(current_chunk, doc.metadata))

        logger.info(f'Sentence chunking produced {len(chunks)} chunks')
        return chunks

    def _create_parent_child_chunks(self, documents, parent_size=2000, child_size=400):
        """创建父子文档对（Small-to-Big 检索策略）

        将文档分成大小两种块：
        - 大块（parent）：存储到 ParentDocumentStore，用于返回完整上下文
        - 小块（child）：索引到 ChromaDB，用于精准检索

        Args:
            documents: 原始文档列表（LangChain Document 对象）
            parent_size: 大块大小（字符数），默认 2000
            child_size: 小块大小（字符数），默认 400

        Returns:
            dict: {
                'parent_chunks': [{'id': str, 'content': str, 'metadata': dict}],
                'child_chunks': [{'id': str, 'content': str, 'metadata': dict, 'parent_id': str}],
                'mapping': {child_id -> parent_id}
            }
        """
        parent_chunks = []
        child_chunks = []
        mapping = {}

        # 创建大块分割器
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_size,
            chunk_overlap=min(200, parent_size // 10),  # 10% overlap
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # 创建小块分割器
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_size,
            chunk_overlap=min(50, child_size // 8),  # 12.5% overlap
            length_function=len,
            separators=["\n", ". ", " ", ""]
        )

        # 为每个文档创建父子块
        for doc_idx, document in enumerate(documents):
            source = document.metadata.get('source', 'unknown')
            page = document.metadata.get('page', 0)

            # 生成大块
            parent_docs = parent_splitter.split_documents([document])

            for parent_idx, parent_doc in enumerate(parent_docs):
                parent_id = f"parent_{doc_idx}_{parent_idx}_{uuid.uuid4().hex[:8]}"
                parent_content = parent_doc.page_content

                # 存储大块信息
                parent_chunks.append({
                    'id': parent_id,
                    'content': parent_content,
                    'metadata': {
                        'source': source,
                        'page': page,
                        'parent_idx': parent_idx
                    }
                })

                # 对每个大块分割成小块
                child_docs = child_splitter.split_documents([parent_doc])

                for child_idx, child_doc in enumerate(child_docs):
                    child_id = f"child_{doc_idx}_{parent_idx}_{child_idx}_{uuid.uuid4().hex[:8]}"
                    child_content = child_doc.page_content

                    # 如果小块太短，跳过（通常是边缘情况）
                    if len(child_content) < 20:
                        continue

                    # 存储小块信息，包含 parent_id
                    child_chunks.append({
                        'id': child_id,
                        'content': child_content,
                        'metadata': {
                            'source': source,
                            'page': page,
                            'parent_id': parent_id,  # 关键：关联大块
                            'child_idx': child_idx
                        }
                    })

                    mapping[child_id] = parent_id

        logger.info(f'Parent-child chunking: {len(parent_chunks)} parents, {len(child_chunks)} children')
        return {
            'parent_chunks': parent_chunks,
            'child_chunks': child_chunks,
            'mapping': mapping
        }

    def process_document(self, file_path, strategy='semantic', chunk_size=1500, chunk_overlap=300, semantic_threshold=0.5,
                         use_small_to_big=False, parent_size=2000, child_size=400):
        """Process a document and add it to the Chroma collection (thread-safe)

        Args:
            file_path: Path to the document file
            strategy: Chunking strategy - 'semantic', 'sentence', or 'recursive'
                - 'semantic': Use SemanticChunker (recommended, best quality)
                - 'sentence': Sentence-level chunking (fallback, good quality)
                - 'recursive': Traditional fixed-size chunking (fastest)
            chunk_size: Size of each chunk in characters (for recursive strategy)
            chunk_overlap: Overlap between consecutive chunks (for recursive strategy)
            semantic_threshold: Breakpoint threshold for semantic chunking (0.1-0.9)
            use_small_to_big: Enable Small-to-Big retrieval (small chunks indexed, large chunks returned)
            parent_size: Large chunk size for Small-to-Big (default 2000 chars)
            child_size: Small chunk size for Small-to-Big (default 400 chars)

        Returns:
            dict: {
                'success': bool,
                'chunks_added': int,
                'chunks_total': int,
                'strategy': str,
                'use_small_to_big': bool,
                'error': str (if failed)
            }
        """
        with RAGUtils._lock:
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext == '.pdf':
                    try:
                        # Use pdfplumber for layout-aware extraction
                        pages = self._extract_pdf_text_layout_aware(file_path)

                        # Detect repeated lines (headers/footers) across all pages
                        page_texts = [p['text'] for p in pages]
                        repeated_lines = self._detect_repeated_lines(page_texts)

                        # Process each page
                        documents = []
                        for page_data in pages:
                            # Remove headers/footers
                            cleaned_text = self._remove_headers_footers(
                                page_data['text'], repeated_lines
                            )
                            # Apply basic cleaning (remove numbered lines)
                            cleaned_text = self._clean_text(cleaned_text)

                            if cleaned_text.strip():
                                documents.append(type('obj', (object,), {
                                    'page_content': cleaned_text,
                                    'metadata': {'page': page_data['page'], 'source': page_data['source']}
                                })())

                        logger.info(f'PDF processed with structural cleaning: {len(documents)} pages retained')

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

                # Choose chunking strategy
                logger.info(f'Using chunking strategy: {strategy}, small_to_big: {use_small_to_big}')

                if use_small_to_big:
                    # Small-to-Big 模式：创建父子文档对
                    chunk_result = self._create_parent_child_chunks(
                        documents,
                        parent_size=parent_size,
                        child_size=child_size
                    )

                    parent_chunks = chunk_result['parent_chunks']
                    child_chunks = chunk_result['child_chunks']

                    # 存储大块到 ParentDocumentStore
                    for parent in parent_chunks:
                        parent_store.put(
                            doc_id=parent['id'],
                            content=parent['content'],
                            metadata=parent['metadata']
                        )

                    logger.info(f'Stored {len(parent_chunks)} parent chunks to ParentDocumentStore')

                    # 使用小块作为 chunks（后续存入 ChromaDB）
                    # 创建 Document 对象格式
                    chunks = [
                        type('obj', (object,), {
                            'page_content': c['content'],
                            'metadata': c['metadata']
                        })()
                        for c in child_chunks
                    ]
                    chunks_total = len(chunks)
                    child_ids_map = {c['id']: c['metadata'].get('parent_id') for c in child_chunks}

                elif strategy == 'semantic':
                    # Semantic chunking - best quality, may be slower
                    chunks = self._semantic_chunk(documents, threshold=semantic_threshold)
                    chunks_total = len(chunks)
                elif strategy == 'sentence':
                    # Sentence-level chunking - good quality fallback
                    chunks = self._sentence_chunk(documents, max_chunk_size=chunk_size)
                    chunks_total = len(chunks)
                else:
                    # Recursive chunking - traditional fixed-size (fastest)
                    text_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        length_function=len
                    )
                    chunks = text_splitter.split_documents(documents)
                    chunks_total = len(chunks)

                logger.info(f'Split document into {chunks_total} chunks')

                # Filter low-quality chunks (P4: quality scoring)
                filtered_chunks = []
                for chunk in chunks:
                    score = self._quality_score(chunk.page_content)
                    if score >= 60:  # Quality threshold
                        filtered_chunks.append(chunk)
                    else:
                        logger.debug(f'Filtered low-quality chunk (score={score}): {chunk.page_content[:50]}...')

                if len(filtered_chunks) < chunks_total:
                    logger.info(f'Filtered {chunks_total - len(filtered_chunks)} low-quality chunks, retained {len(filtered_chunks)}')

                chunks = filtered_chunks
                logger.info(f'After quality filter: {len(chunks)} chunks remain')

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

                        # 对于 small_to_big，使用预生成的 ID；否则使用默认 ID
                        if use_small_to_big:
                            doc_id = child_chunks[i]['id']
                        else:
                            doc_id = f"{os.path.basename(file_path)}_{len(self.document_hashes)}"

                        ids_to_add.append(doc_id)

                        # 构建元数据，包含 parent_id（small_to_big 模式）
                        metadata = {
                            "source": os.path.basename(file_path),
                            "filepath": file_path,
                            "content_hash": content_hash,
                            "page": chunk.metadata.get('page', 0) if hasattr(chunk, 'metadata') else 0
                        }

                        # Small-to-Big 模式添加 parent_id
                        if use_small_to_big and hasattr(chunk, 'metadata'):
                            parent_id = chunk.metadata.get('parent_id')
                            if parent_id:
                                metadata["parent_id"] = parent_id

                        metadatas_to_add.append(metadata)
                        new_chunks += 1

                if new_chunks > 0 and documents_to_add:
                    logger.info(f'Adding {new_chunks} chunks to Chroma collection')
                    logger.info(f'IDs to add: {ids_to_add[:3]}...')  # Log first 3 IDs
                    try:
                        self.collection.add(
                            documents=documents_to_add,
                            ids=ids_to_add,
                            metadatas=metadatas_to_add
                        )
                        logger.info(f'Added {new_chunks} new chunks from {file_path} to Chroma')

                        # Verify addition
                        verify_count = self.collection.count()
                        logger.info(f'ChromaDB count after add: {verify_count}')
                    except Exception as e:
                        logger.error(f'Failed to add to Chroma: {e}', exc_info=True)
                        return {'success': False, 'chunks_added': 0, 'error': f'Chroma add failed: {str(e)}'}
                else:
                    logger.info(f'No new chunks added from {file_path} (possibly duplicate or no chunks)')
                    logger.info(f'new_chunks={new_chunks}, documents_to_add={len(documents_to_add)}')

                return {
                    'success': True,
                    'chunks_added': new_chunks,
                    'chunks_total': chunks_total,
                    'strategy': strategy,
                    'use_small_to_big': use_small_to_big,
                    'parent_chunks': len(parent_chunks) if use_small_to_big else 0,
                    'child_chunks': len(child_chunks) if use_small_to_big else 0,
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
                                    'child_content': doc  # 原始小块内容（用于调试）
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

    def get_document_count(self):
        """Get total number of document chunks in the collection"""
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f'Error getting document count: {e}', exc_info=True)
            return 0

    def preview_chunks(self, file_path, strategy='semantic', chunk_size=1500, chunk_overlap=300, semantic_threshold=0.5,
                        use_small_to_big=False, parent_size=2000, child_size=400):
        """Preview document chunking without saving to knowledge base

        Args:
            file_path: Path to the document file
            strategy: Chunking strategy - 'semantic', 'sentence', or 'recursive'
            chunk_size: Size of each chunk in characters (for recursive/sentence strategy)
            chunk_overlap: Overlap between consecutive chunks (for recursive strategy)
            semantic_threshold: Breakpoint threshold for semantic chunking (0.1-0.9)
            use_small_to_big: Enable Small-to-Big preview
            parent_size: Large chunk size for Small-to-Big preview
            child_size: Small chunk size for Small-to-Big preview

        Returns:
            dict: {
                'success': bool,
                'strategy': str,
                'use_small_to_big': bool,
                'total_chunks': int,
                'total_chars': int,
                'avg_chunk_size': int,
                'chunks': [{'index': int, 'content': str, 'char_count': int, 'preview': str}],
                'parent_chunks': list (if use_small_to_big),
                'child_chunks': list (if use_small_to_big),
                'error': str (if failed)
            }
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()

            # Load document based on file type
            if ext == '.pdf':
                try:
                    pages = self._extract_pdf_text_layout_aware(file_path)
                    page_texts = [p['text'] for p in pages]
                    repeated_lines = self._detect_repeated_lines(page_texts)

                    documents = []
                    for page_data in pages:
                        cleaned_text = self._remove_headers_footers(page_data['text'], repeated_lines)
                        cleaned_text = self._clean_text(cleaned_text)
                        if cleaned_text.strip():
                            documents.append(type('obj', (object,), {
                                'page_content': cleaned_text,
                                'metadata': {'page': page_data['page'], 'source': page_data['source']}
                            })())
                except Exception as e:
                    logger.error(f'Error loading PDF for preview: {e}', exc_info=True)
                    return {'success': False, 'error': str(e)}
            elif ext == '.txt':
                try:
                    loader = TextLoader(file_path, encoding='utf-8')
                    documents = loader.load()
                except Exception as e:
                    logger.error(f'Error loading TXT for preview: {e}', exc_info=True)
                    return {'success': False, 'error': str(e)}
            elif ext == '.docx':
                try:
                    loader = Docx2txtLoader(file_path)
                    documents = loader.load()
                except Exception as e:
                    logger.error(f'Error loading DOCX for preview: {e}', exc_info=True)
                    return {'success': False, 'error': str(e)}
            else:
                return {'success': False, 'error': 'Unsupported file type'}

            # Apply chunking strategy
            logger.info(f'Previewing chunks with strategy: {strategy}, semantic_threshold: {semantic_threshold}, small_to_big: {use_small_to_big}')

            if use_small_to_big:
                # Small-to-Big 模式：预览父子文档对
                chunk_result = self._create_parent_child_chunks(
                    documents,
                    parent_size=parent_size,
                    child_size=child_size
                )

                parent_chunks = chunk_result['parent_chunks']
                child_chunks = chunk_result['child_chunks']

                # 格式化大块预览
                parent_preview = []
                for i, parent in enumerate(parent_chunks, 1):
                    content = parent['content']
                    preview_text = content[:300] + '...' if len(content) > 300 else content
                    parent_preview.append({
                        'index': i,
                        'id': parent['id'],
                        'content': content,
                        'char_count': len(content),
                        'preview': preview_text,
                        'page': parent['metadata'].get('page', 0)
                    })

                # 格式化小块预览
                child_preview = []
                for i, child in enumerate(child_chunks, 1):
                    content = child['content']
                    preview_text = content[:150] + '...' if len(content) > 150 else content
                    child_preview.append({
                        'index': i,
                        'id': child['id'],
                        'content': content,
                        'char_count': len(content),
                        'preview': preview_text,
                        'parent_id': child['metadata'].get('parent_id'),
                        'page': child['metadata'].get('page', 0)
                    })

                return {
                    'success': True,
                    'strategy': strategy,
                    'use_small_to_big': True,
                    'parent_size': parent_size,
                    'child_size': child_size,
                    'total_parents': len(parent_chunks),
                    'total_children': len(child_chunks),
                    'total_chars': sum(len(c['content']) for c in child_chunks),
                    'avg_child_size': sum(len(c['content']) for c in child_chunks) // len(child_chunks) if child_chunks else 0,
                    'parent_chunks': parent_preview[:10],  # 只显示前10个大块
                    'child_chunks': child_preview[:20],  # 只显示前20个小块
                    'all_parent_chunks': parent_preview,
                    'all_child_chunks': child_preview
                }

            elif strategy == 'semantic':
                chunks = self._semantic_chunk(documents, threshold=semantic_threshold)
                logger.info(f'Semantic chunking result: {len(chunks)} chunks')
            elif strategy == 'sentence':
                chunks = self._sentence_chunk(documents, max_chunk_size=chunk_size)
            else:
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=len
                )
                chunks = text_splitter.split_documents(documents)

            # Calculate statistics and format chunks for preview
            total_chars = sum(len(c.page_content) for c in chunks)
            avg_chunk_size = total_chars // len(chunks) if chunks else 0

            preview_chunks_list = []
            for i, chunk in enumerate(chunks, 1):
                content = chunk.page_content
                preview_text = content[:200] + '...' if len(content) > 200 else content
                preview_chunks_list.append({
                    'index': i,
                    'content': content,
                    'char_count': len(content),
                    'preview': preview_text,
                    'page': chunk.metadata.get('page', 0) if hasattr(chunk, 'metadata') else 0
                })

            return {
                'success': True,
                'strategy': strategy,
                'use_small_to_big': False,
                'semantic_threshold': semantic_threshold,
                'total_chunks': len(chunks),
                'total_chars': total_chars,
                'avg_chunk_size': avg_chunk_size,
                'chunks': preview_chunks_list
            }

        except Exception as e:
            logger.error(f'Error previewing chunks: {e}', exc_info=True)
            return {'success': False, 'error': str(e)}

    def delete_documents_by_source(self, filename):
        """Delete all chunks from a specific source file (including parent documents)"""
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

                # 同步删除 ParentDocumentStore 中的大块
                parent_deleted = parent_store.delete_by_source(filename)
                logger.info(f'Deleted documents from source: {filename} (parent_docs: {parent_deleted})')
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
