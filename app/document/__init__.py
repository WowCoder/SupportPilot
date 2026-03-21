"""
Document Blueprint for SupportPilot

Handles document upload and management for tech support.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
import os
import logging

from ..extensions import db
from ..models import Document
from rag.rag_utils import rag_utils

logger = logging.getLogger(__name__)
document_bp = Blueprint('document', __name__, url_prefix='/')


@document_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Upload a document to the knowledge base (tech support only)"""
    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized upload attempt by user: {current_user.username}')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if 'file' not in request.files:
            logger.warning('Upload failed: no file part')
            if is_ajax:
                return jsonify({'success': False, 'message': 'No file part'})
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            logger.warning('Upload failed: no selected file')
            if is_ajax:
                return jsonify({'success': False, 'message': 'No selected file'})
            flash('No selected file')
            return redirect(request.url)

        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']:
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                logger.info(f'File uploaded: {filename} by user {current_user.username}')

                # Get chunking parameters from request (with defaults)
                chunk_size = request.form.get('chunk_size', 1000, type=int)
                chunk_overlap = request.form.get('chunk_overlap', 200, type=int)

                # Process document for RAG
                result = rag_utils.process_document(filepath, chunk_size, chunk_overlap)

                if result.get('success'):
                    # Add to database
                    document = Document(
                        filename=filename,
                        filepath=filepath,
                        uploaded_by=current_user.id
                    )
                    db.session.add(document)
                    db.session.commit()
                    logger.info(f'Document processed successfully: {filename}')

                    chunks_added = result.get('chunks_added', 0)
                    chunks_total = result.get('chunks_total', 0)
                    is_duplicate = result.get('is_duplicate', False)

                    if is_ajax:
                        return jsonify({
                            'success': True,
                            'message': f'文件 "{filename}" 上传并处理成功',
                            'chunks_added': chunks_added,
                            'chunks_total': chunks_total,
                            'is_duplicate': is_duplicate
                        })
                    flash(f'File uploaded and processed successfully ({chunks_added} chunks added)')
                    return redirect(url_for('document.upload'))
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f'Document processing failed: {filename} - {error_msg}')
                    if is_ajax:
                        return jsonify({'success': False, 'message': f'处理失败：{error_msg}'}), 500
                    flash(f'File uploaded but processing failed: {error_msg}')
                    return redirect(url_for('document.upload'))

            except Exception as e:
                logger.error(f'Upload error: {str(e)}', exc_info=True)
                if is_ajax:
                    return jsonify({'success': False, 'message': str(e)}), 500
                flash('An error occurred during file upload')
                return redirect(url_for('document.upload'))
        else:
            logger.warning(f'Upload failed: invalid file type {file.filename}')
            if is_ajax:
                return jsonify({'success': False, 'message': 'Invalid file type'}), 400
            flash('Allowed file types are txt, pdf, doc, docx')
            return redirect(request.url)

    # GET request - show documents with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    documents = Document.query.filter_by(uploaded_by=current_user.id)\
        .order_by(Document.uploaded_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('upload.html', documents=documents.items, pagination=documents)


@document_bp.route('/document/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete a document (tech support only)"""
    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized delete attempt by user {current_user.username}')
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    document = Document.query.get_or_404(document_id)

    # Only allow deleting own documents
    if document.uploaded_by != current_user.id:
        logger.warning(f'User {current_user.username} tried to delete document owned by user {document.uploaded_by}')
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    try:
        filename = document.filename
        filepath = document.filepath

        # Delete from Chroma vector database
        rag_utils.delete_documents_by_source(filename)

        # Delete physical file
        if os.path.exists(filepath):
            os.remove(filepath)

        # Delete from database
        db.session.delete(document)
        db.session.commit()

        logger.info(f'Document deleted: {filename} by {current_user.username}')
        return jsonify({'success': True, 'message': f'Document "{filename}" deleted successfully'})

    except Exception as e:
        logger.error(f'Error deleting document {document_id}: {e}', exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
