from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
import os
import logging
import hashlib
import threading
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class RAGUtils:
    # Class-level lock for thread safety
    _lock = threading.Lock()

    def __init__(self):
        # Initialize Chroma client with persistent storage
        self.client = chromadb.PersistentClient(path="./chroma_db")

        # Get or create collection with cosine similarity
        # Try to get existing collection first
        try:
            self.collection = self.client.get_collection(name="knowledge")
            logger.info('Found existing Chroma collection')
        except ValueError:
            # Collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name="knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info('Created new Chroma collection')

        # Track processed document hashes for deduplication
        self.document_hashes = set()
        self._load_document_hashes()

    def _load_document_hashes(self):
        """Load existing document hashes from Chroma for deduplication"""
        try:
            # Get all metadata from collection to rebuild hash set
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

    def process_document(self, file_path, chunk_size=1000, chunk_overlap=200):
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
                # Determine loader based on file extension
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

                # Load and split document
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    length_function=len
                )
                chunks = text_splitter.split_documents(documents)
                chunks_total = len(chunks)

                # Add to Chroma collection (with deduplication)
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
                        # Generate unique ID using file path and chunk index
                        doc_id = f"{os.path.basename(file_path)}_{len(self.document_hashes)}"
                        ids_to_add.append(doc_id)
                        metadatas_to_add.append({
                            "source": os.path.basename(file_path),
                            "filepath": file_path,
                            "content_hash": content_hash
                        })
                        new_chunks += 1

                # Batch add to Chroma (efficient)
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

    def retrieve_relevant_info(self, query, k=3, similarity_threshold=0.1):
        """
        Retrieve relevant information using Chroma vector search

        Args:
            query: Search query
            k: Number of top results to return
            similarity_threshold: Minimum similarity score to include results
                                  (cosine distance <= 1 - threshold)

        Returns:
            List of relevant document chunks with similarity scores
        """
        try:
            # Query Chroma (automatically vectorizes the query)
            results = self.collection.query(
                query_texts=[query],
                n_results=k * 2,  # Get more to filter by threshold
                include=["documents", "distances", "metadatas"]
            )

            # Process results with threshold filtering
            # Chroma returns cosine distance, convert to similarity
            retrieved = []
            if results and results.get('documents') and results['documents'][0]:
                for i, (doc, distance, meta) in enumerate(zip(
                    results['documents'][0],
                    results['distances'][0],
                    results['metadatas'][0]
                )):
                    # Convert cosine distance to similarity (cosine distance = 1 - cosine similarity)
                    similarity = 1 - distance

                    if similarity >= similarity_threshold:
                        retrieved.append({
                            'content': doc,
                            'similarity': float(similarity),
                            'source': meta.get('source', 'unknown') if meta else 'unknown'
                        })

                    if len(retrieved) >= k:
                        break

            if retrieved:
                logger.debug(f'Retrieved {len(retrieved)} relevant chunks for query: {query[:50]}...')
            else:
                logger.debug(f'No relevant chunks found for query: {query[:50]}...')

            return retrieved

        except Exception as e:
            logger.error(f'Error retrieving relevant info: {e}', exc_info=True)
            return []

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
            # Get all documents with matching source
            existing = self.collection.get(
                where={"source": filename},
                include=["metadatas"]
            )

            if existing and existing.get('ids'):
                self.collection.delete(ids=existing['ids'])
                # Remove hashes from tracking set
                for meta in existing.get('metadatas', []):
                    if meta and 'content_hash' in meta:
                        self.document_hashes.discard(meta['content_hash'])

                logger.info(f'Deleted documents from source: {filename}')
                return True

            return False
        except Exception as e:
            logger.error(f'Error deleting documents: {e}', exc_info=True)
            return False


# Global instance
rag_utils = RAGUtils()
