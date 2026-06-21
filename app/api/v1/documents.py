"""
Documents API v1 — Upload, list, and delete knowledge base documents.
"""
import os
import logging
from flask import Blueprint, request, g, current_app
from werkzeug.utils import secure_filename

from ...extensions import db
from ...models import Document
from ...utils.auth import jwt_required
from ...utils.response import api_success, api_error, api_paginated
from rag.offline.pipeline import RAGUtils

logger = logging.getLogger(__name__)

doc_v1_bp = Blueprint('documents_v1', __name__, url_prefix='/api/v1/documents')

# Singleton RAG utils instance
_rag_utils = None


def _get_rag_utils():
    global _rag_utils
    if _rag_utils is None:
        _rag_utils = RAGUtils()
    return _rag_utils


@doc_v1_bp.route('', methods=['GET'])
@jwt_required
def list_documents():
    """List uploaded documents with pagination."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)

    query = Document.query.order_by(Document.uploaded_at.desc())
    total = query.count()
    docs = query.offset((page - 1) * page_size).limit(page_size).all()

    return api_paginated(
        [d.to_dict() for d in docs],
        total,
        page=page,
        page_size=page_size,
    )


@doc_v1_bp.route('/stats', methods=['GET'])
@jwt_required
def doc_stats():
    """Get document statistics."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    total = Document.query.count()
    total_chunks = db.session.query(db.func.sum(Document.chunks_count)).scalar() or 0

    return api_success({
        'total_docs': total,
        'total_chunks': total_chunks,
    })


@doc_v1_bp.route('/upload', methods=['POST'])
@jwt_required
def upload_document():
    """
    Upload and process a document through the full pipeline:
    save → parse → clean → chunk → embed → index → persist record.

    Accepts multipart/form-data with:
        - file: The document file
        - strategy: Chunking strategy (default: 'sentence')
        - chunk_size: Chunk size (default: 400)
        - use_small_to_big: 'true' or 'false' (default: 'true')
        - skip_cleaning: 'true' or 'false' (default: 'false')

    Returns chunk count and document metadata.
    """
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    file = request.files.get('file')
    if not file or not file.filename:
        return api_error(400, 'No file provided')

    # Validate extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.pdf', '.txt', '.doc', '.docx'):
        return api_error(400, f'Unsupported file type: {ext}')

    # Parse options
    strategy = request.form.get('strategy', 'sentence')
    chunk_size = int(request.form.get('chunk_size', 400))
    use_small_to_big = request.form.get('use_small_to_big', 'true').lower() == 'true'
    skip_cleaning = request.form.get('skip_cleaning', 'false').lower() == 'true'

    # Save file permanently
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    safe_name = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, safe_name)

    # Avoid overwriting — append a suffix
    counter = 1
    base, ext = os.path.splitext(safe_name)
    while os.path.exists(filepath):
        filepath = os.path.join(upload_folder, f'{base}_{counter}{ext}')
        counter += 1

    file.save(filepath)
    logger.info(f'File saved: {filepath}')

    # Create Document record (processing status)
    doc = Document(
        filename=os.path.basename(filepath),
        filepath=filepath,
        uploaded_by=user.id,
        mode='auto' if skip_cleaning else 'manual',
        strategy=strategy,
        chunk_size=chunk_size,
        status='processing',
    )
    db.session.add(doc)
    db.session.commit()

    # Run the full ETL pipeline
    try:
        rag = _get_rag_utils()
        result = rag.process_document(
            file_path=filepath,
            strategy=strategy,
            chunk_size=chunk_size if not use_small_to_big else 400,
            use_small_to_big=use_small_to_big,
            parent_size=2000,
            child_size=chunk_size if use_small_to_big else 400,
        )

        if result.get('success'):
            doc.status = 'completed'
            doc.chunks_count = result.get('chunks_added', 0)
            doc.strategy = strategy
            db.session.commit()
            logger.info(f'Document {doc.id} processed: {doc.chunks_count} chunks')
            return api_success({
                'document': doc.to_dict(),
                'chunks_added': doc.chunks_count,
            }, code=201)
        else:
            doc.status = 'failed'
            doc.error_message = result.get('error', 'Unknown error')
            db.session.commit()
            return api_error(500, f'Processing failed: {doc.error_message}')

    except Exception as e:
        logger.error(f'Document processing error: {e}', exc_info=True)
        doc.status = 'failed'
        doc.error_message = str(e)
        db.session.commit()
        return api_error(500, f'Processing error: {str(e)}')


@doc_v1_bp.route('/<int:doc_id>', methods=['DELETE'])
@jwt_required
def delete_document(doc_id):
    """Delete a document and its chunks from the knowledge base."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    doc = Document.query.get_or_404(doc_id)

    # Delete the file on disk
    if os.path.exists(doc.filepath):
        try:
            os.unlink(doc.filepath)
        except OSError as e:
            logger.warning(f'Failed to delete file {doc.filepath}: {e}')

    # Remove from ChromaDB (by source filename)
    try:
        rag = _get_rag_utils()
        rag.delete_documents_by_source(doc.filename)
    except Exception as e:
        logger.warning(f'Failed to remove Chroma chunks for {doc.filename}: {e}')

    db.session.delete(doc)
    db.session.commit()

    logger.info(f'Document {doc_id} ({doc.filename}) deleted by {user.username}')
    return api_success(message='Document deleted')
