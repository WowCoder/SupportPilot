"""
FAQ Vector Sync Tool for SupportPilot

Handles synchronization between FAQ entries and ChromaDB.
"""
import logging
from typing import List, Optional

from rag.offline.parent_store import parent_store
from rag.offline.pipeline import rag_utils

logger = logging.getLogger(__name__)


def sync_faq_to_chroma(faq) -> Optional[List[str]]:
    """
    Sync FAQ entry to ChromaDB for vector retrieval.

    Uses Small-to-Big strategy:
    - FAQ is stored as a parent document
    - Child chunks are created for indexing

    Args:
        faq: FAQEntry object

    Returns:
        List of ChromaDB document IDs (parent and children), or None if failed
    """
    try:
        from langchain_core.documents import Document

        # Build document content
        content = f"问题：{faq.question}\n\n答案：{faq.answer}"

        # Create metadata
        metadata = {
            'source': 'faq',
            'faq_id': faq.id,
            'category': faq.category or '',
            'question': faq.question,
            'answer': faq.answer
        }

        # Use Small-to-Big strategy
        # FAQ is typically short, so we use smaller chunks
        parent_size = 2000  # FAQ fits in one parent
        child_size = 400    # Split into smaller chunks for retrieval

        # Create LangChain Document and pass to chunker
        doc = Document(page_content=content, metadata=metadata)
        chunk_result = rag_utils._create_parent_child_chunks(
            documents=[doc],
            parent_size=parent_size,
            child_size=child_size
        )

        if not chunk_result or not chunk_result.get('child_chunks'):
            logger.error(f'Failed to create chunks for FAQ {faq.id}')
            return None

        parent_chunks = chunk_result['parent_chunks']
        child_chunks = chunk_result['child_chunks']

        # Store parent chunks to ParentDocumentStore
        for parent in parent_chunks:
            parent_store.put(
                doc_id=parent['id'],
                content=parent['content'],
                metadata=parent['metadata']
            )

        # Add child chunks to ChromaDB
        child_ids = [c['id'] for c in child_chunks]
        child_contents = [c['content'] for c in child_chunks]
        child_metadatas = [c['metadata'] for c in child_chunks]

        rag_utils.collection.add(
            documents=child_contents,
            ids=child_ids,
            metadatas=child_metadatas
        )

        all_ids = [p['id'] for p in parent_chunks] + child_ids
        logger.info(f'Synced FAQ {faq.id} to ChromaDB: {len(parent_chunks)} parents, {len(child_chunks)} children')
        return all_ids

    except Exception as e:
        logger.error(f'Error syncing FAQ {faq.id} to ChromaDB: {e}', exc_info=True)
        return None


def update_faq_in_chroma(faq) -> bool:
    """
    Update FAQ entry in ChromaDB.

    Args:
        faq: FAQEntry object

    Returns:
        True if successful
    """
    try:
        # First remove existing entries
        remove_faq_from_chroma(faq)

        # Then add updated entries
        result = sync_faq_to_chroma(faq)
        return result is not None

    except Exception as e:
        logger.error(f'Error updating FAQ {faq.id} in ChromaDB: {e}', exc_info=True)
        return False


def remove_faq_from_chroma(faq) -> bool:
    """
    Remove FAQ entry from ChromaDB.

    Args:
        faq: FAQEntry object

    Returns:
        True if successful
    """
    try:
        # Parse existing doc IDs
        doc_ids = faq.get_chroma_doc_ids()
        if not doc_ids:
            logger.info(f'FAQ {faq.id} has no ChromaDB IDs to remove')
            return True

        # Remove from parent_store (which handles ChromaDB)
        for doc_id in doc_ids:
            parent_store.delete(doc_id)

        # Clear stored IDs
        faq.chroma_doc_ids = None

        logger.info(f'Removed FAQ {faq.id} from ChromaDB: {doc_ids}')
        return True

    except Exception as e:
        logger.error(f'Error removing FAQ {faq.id} from ChromaDB: {e}', exc_info=True)
        return False


def search_faqs(query: str, k: int = 5, similarity_threshold: float = 0.25) -> List[dict]:
    """
    Search FAQ entries using vector similarity.

    Args:
        query: Search query
        k: Number of results to return
        similarity_threshold: Minimum similarity score

    Returns:
        List of dicts with faq_id, question, answer, similarity
    """
    try:
        from rag.online.service import rag_service

        # Use RAG service to search
        results = rag_service.retrieve(
            query=query,
            k=k,
            similarity_threshold=similarity_threshold,
            use_small_to_big=True
        )

        # Filter for FAQ sources only
        faq_results = []
        for r in results:
            metadata = r.get('metadata', {})
            if metadata.get('source') == 'faq':
                faq_results.append({
                    'faq_id': metadata.get('faq_id'),
                    'question': metadata.get('question', ''),
                    'answer': metadata.get('answer', ''),
                    'similarity': r.get('similarity', 0),
                    'category': metadata.get('category', '')
                })

        return faq_results

    except Exception as e:
        logger.error(f'Error searching FAQs: {e}', exc_info=True)
        return []
