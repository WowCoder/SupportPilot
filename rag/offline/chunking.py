from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
import re
import uuid
import logging

logger = logging.getLogger(__name__)


def split_sentences(text):
    """Split text into sentences (supports Chinese and English)"""
    pattern = r'(?<=[。！？；.!?\n])\s*'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def create_chunk(content, metadata):
    """Create a document chunk object"""
    return type('obj', (object,), {
        'page_content': content,
        'metadata': metadata
    })()


def sentence_chunk(documents, max_chunk_size=1500):
    """Sentence-level chunking (fallback strategy)

    Splits documents into sentences and merges them into chunks
    while respecting sentence boundaries. Never splits mid-sentence.
    """
    chunks = []
    for doc in documents:
        sentences = split_sentences(doc.page_content)
        current_chunk = ""
        current_sentences = []

        for sent in sentences:
            if len(sent) > max_chunk_size:
                if current_chunk:
                    chunks.append(create_chunk(current_chunk, doc.metadata))
                    current_chunk = ""
                    current_sentences = []
                chunks.append(create_chunk(sent, doc.metadata))
                continue

            test_chunk = current_chunk + sent if not current_chunk else current_chunk + " " + sent
            if len(test_chunk) <= max_chunk_size:
                current_chunk = test_chunk
                current_sentences.append(sent)
            else:
                if current_chunk:
                    chunks.append(create_chunk(current_chunk, doc.metadata))
                current_chunk = sent
                current_sentences = [sent]

        if current_chunk:
            chunks.append(create_chunk(current_chunk, doc.metadata))

    logger.info(f'Sentence chunking produced {len(chunks)} chunks')
    return chunks


def create_semantic_splitter(embeddings, threshold=0.5):
    """Create semantic chunker based on embedding similarity"""
    logger.info(f'Creating SemanticChunker with threshold={threshold}')
    return SemanticChunker(
        embeddings=embeddings,
        breakpoint_threshold_type="percentile",
        breakpoint_threshold_amount=threshold,
        min_chunk_size=50
    )


def semantic_chunk(documents, embeddings, threshold=0.5):
    """Semantic chunking based on sentence embedding similarity"""
    try:
        splitter = create_semantic_splitter(embeddings, threshold)
        chunks = splitter.split_documents(documents)
        logger.info(f'Semantic chunking produced {len(chunks)} chunks with threshold={threshold}')
        return chunks
    except Exception as e:
        logger.warning(f'Semantic chunking failed, falling back to sentence splitter: {e}')
        return sentence_chunk(documents)


def create_parent_child_chunks(documents, parent_size=2000, child_size=400):
    """Create parent-child document pairs (Small-to-Big retrieval strategy)"""
    parent_chunks = []
    child_chunks = []
    mapping = {}

    parent_splitter = RecursiveCharacterTextSplitter(
        chunk_size=parent_size,
        chunk_overlap=min(200, parent_size // 10),
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    child_splitter = RecursiveCharacterTextSplitter(
        chunk_size=child_size,
        chunk_overlap=min(50, child_size // 8),
        length_function=len,
        separators=["\n", ". ", " ", ""]
    )

    for doc_idx, document in enumerate(documents):
        source = document.metadata.get('source', 'unknown')
        page = document.metadata.get('page', 0)

        parent_docs = parent_splitter.split_documents([document])

        for parent_idx, parent_doc in enumerate(parent_docs):
            parent_id = f"parent_{doc_idx}_{parent_idx}_{uuid.uuid4().hex[:8]}"
            parent_content = parent_doc.page_content

            parent_chunks.append({
                'id': parent_id,
                'content': parent_content,
                'metadata': {
                    'source': source,
                    'page': page,
                    'parent_idx': parent_idx
                }
            })

            child_docs = child_splitter.split_documents([parent_doc])

            for child_idx, child_doc in enumerate(child_docs):
                child_id = f"child_{doc_idx}_{parent_idx}_{child_idx}_{uuid.uuid4().hex[:8]}"
                child_content = child_doc.page_content

                if len(child_content) < 20:
                    continue

                child_chunks.append({
                    'id': child_id,
                    'content': child_content,
                    'metadata': {
                        'source': source,
                        'page': page,
                        'parent_id': parent_id,
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
