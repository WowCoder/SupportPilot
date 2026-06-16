import hashlib
import logging

logger = logging.getLogger(__name__)


def compute_document_hash(content):
    """Compute hash of document content for deduplication"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()


def load_document_hashes(collection):
    """Load existing document hashes from Chroma for deduplication"""
    hashes = set()
    try:
        existing = collection.get(include=["metadatas"])
        for meta in existing.get("metadatas", []):
            if meta and "content_hash" in meta:
                hashes.add(meta["content_hash"])
        logger.info(f'Loaded {len(hashes)} document hashes from Chroma')
    except Exception as e:
        logger.error(f'Error loading document hashes: {e}', exc_info=True)
    return hashes
