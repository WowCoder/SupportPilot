"""
API Blueprint for SupportPilot

REST API endpoints for RAG and document operations.
"""
from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required
import logging
import os
import tempfile

from rag.service import rag_service
from rag.cleaning import document_cleaner, CleaningOptions

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/document/count', methods=['GET'])
@login_required
def get_document_count():
    """Get total document count in RAG system"""
    try:
        count = rag_service.get_document_count()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f'Error getting document count: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/test-query', methods=['POST'])
@login_required
def test_query():
    """Test RAG retrieval with a query (tech support only)"""
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    query = data.get('query', '').strip()
    k = int(data.get('k', 3))
    similarity_threshold = float(data.get('similarity_threshold', 0.25))
    use_small_to_big = data.get('use_small_to_big', True)

    if not query:
        logger.error(f'Test query failed: empty query, data={data}')
        return jsonify({'success': False, 'message': 'Query is required'}), 400

    try:
        # Use new RAG service with agentic routing
        session_id = session.get('session_id')  # Get session ID from Flask session if available
        results = rag_service.retrieve(
            query=query,
            k=k,
            similarity_threshold=similarity_threshold,
            use_small_to_big=use_small_to_big,
            session_id=session_id
        )

        retrieval_mode = 'agentic_or_simple'

        return jsonify({
            'success': True,
            'retrieval_mode': retrieval_mode,
            'results': [
                {
                    'content': r.get('content', ''),
                    'similarity': r.get('similarity', 0),
                    'source': r.get('source', 'unknown'),
                    'parent_id': r.get('parent_id')  # Small-to-Big mode has parent_id
                }
                for r in results
            ]
        })
    except Exception as e:
        logger.error(f'Error testing query: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/preview-chunks', methods=['POST'])
@login_required
def preview_chunks():
    """Preview document chunking without saving to knowledge base (tech support only)"""
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Get file and parameters
    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    strategy = request.form.get('strategy', 'semantic')
    chunk_size = int(request.form.get('chunk_size', 1500))
    chunk_overlap = int(request.form.get('chunk_overlap', 300))
    semantic_threshold = float(request.form.get('semantic_threshold', 0.5))

    # Small-to-Big 参数
    use_small_to_big = request.form.get('use_small_to_big', 'false').lower() == 'true'
    parent_size = int(request.form.get('parent_size', 2000))
    child_size = int(request.form.get('child_size', 400))

    logger.info(f'Preview chunks request: strategy={strategy}, semantic_threshold={semantic_threshold}, small_to_big={use_small_to_big}')

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.txt', '.doc', '.docx']:
        return jsonify({'success': False, 'message': 'Unsupported file type'}), 400

    # Save to temporary file for processing
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name

        # Preview chunks
        result = rag_utils.preview_chunks(
            tmp_path,
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            semantic_threshold=semantic_threshold,
            use_small_to_big=use_small_to_big,
            parent_size=parent_size,
            child_size=child_size
        )

        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f'Failed to delete temp file {tmp_path}: {e}')

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f'Error in preview_chunks API: {e}', exc_info=True)
        # Clean up temp file if it exists
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/extract-document', methods=['POST'])
@login_required
def extract_document():
    """Extract raw text and metadata from document (tech support only)

    Returns raw text, PDF metadata, and page information for cleaning preview.
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    file = request.files.get('file')
    if not file:
        return jsonify({'success': False, 'message': 'No file provided'}), 400

    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf', '.txt', '.doc', '.docx']:
        return jsonify({'success': False, 'message': 'Unsupported file type'}), 400

    # Save to temporary file for processing
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name

        # Extract raw text and metadata
        raw_data = document_cleaner.extract_raw(tmp_path)

        # Store temp path in session for later cleaning steps
        session['cleaning_temp_path'] = tmp_path
        session['cleaning_filename'] = file.filename

        # Prepare response
        response = {
            'success': True,
            'filename': file.filename,
            'file_type': raw_data.file_type,
            'total_chars': raw_data.total_chars,
            'total_lines': raw_data.total_lines,
            'total_pages': len(raw_data.pages),
            'pdf_metadata': raw_data.pdf_metadata,
            # Preview first 2000 chars of text for display
            'text_preview': raw_data.text[:2000] if len(raw_data.text) > 2000 else raw_data.text,
            'full_text_length': len(raw_data.text),
        }

        # Include page summaries
        response['pages'] = [
            {
                'page': p['page'],
                'chars': p['chars'],
                'lines': p['lines'],
                'preview': p['text'][:500] if len(p['text']) > 500 else p['text'],
            }
            for p in raw_data.pages[:20]  # Limit to first 20 pages for preview
        ]

        return jsonify(response)

    except Exception as e:
        logger.error(f'Error in extract_document API: {e}', exc_info=True)
        # Clean up temp file if it exists
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/preview-cleaning', methods=['POST'])
@login_required
def preview_cleaning():
    """Preview cleaning effect on extracted document (tech support only)

    Returns before/after comparison with diff visualization.
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Check for temp path from previous extraction
    tmp_path = session.get('cleaning_temp_path')
    if not tmp_path or not os.path.exists(tmp_path):
        return jsonify({'success': False, 'message': 'No document extracted. Please extract first.'}), 400

    # Get cleaning options from request
    data = request.get_json(silent=True) or {}
    options = CleaningOptions(
        remove_headers_footers=data.get('remove_headers_footers', True),
        remove_page_numbers=data.get('remove_page_numbers', True),
        clean_noise_chars=data.get('clean_noise_chars', True),
        normalize_whitespace=data.get('normalize_whitespace', True),
        ocr_postprocess=data.get('ocr_postprocess', True),
        filter_non_content=data.get('filter_non_content', True),
    )

    try:
        # Extract raw data (reuse temp file)
        raw_data = document_cleaner.extract_raw(tmp_path)

        # Preview cleaning effect
        preview_result = document_cleaner.preview(raw_data, options)

        # Store cleaning options in session for later confirmation
        session['cleaning_options'] = {
            'remove_headers_footers': options.remove_headers_footers,
            'remove_page_numbers': options.remove_page_numbers,
            'clean_noise_chars': options.clean_noise_chars,
            'normalize_whitespace': options.normalize_whitespace,
            'ocr_postprocess': options.ocr_postprocess,
            'filter_non_content': options.filter_non_content,
        }

        return jsonify(preview_result)

    except Exception as e:
        logger.error(f'Error in preview_cleaning API: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/confirm-cleaning', methods=['POST'])
@login_required
def confirm_cleaning():
    """Confirm cleaning and save metadata (tech support only)

    Saves edited metadata and returns cleaned text for chunking.
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    # Check for temp path from previous extraction
    tmp_path = session.get('cleaning_temp_path')
    if not tmp_path or not os.path.exists(tmp_path):
        return jsonify({'success': False, 'message': 'No document extracted. Please extract first.'}), 400

    # Get metadata from request
    data = request.get_json(silent=True) or {}
    edited_metadata = data.get('metadata', {})

    # Get stored cleaning options
    stored_options = session.get('cleaning_options', {})
    options = CleaningOptions(
        remove_headers_footers=stored_options.get('remove_headers_footers', True),
        remove_page_numbers=stored_options.get('remove_page_numbers', True),
        clean_noise_chars=stored_options.get('clean_noise_chars', True),
        normalize_whitespace=stored_options.get('normalize_whitespace', True),
        ocr_postprocess=stored_options.get('ocr_postprocess', True),
        filter_non_content=stored_options.get('filter_non_content', True),
    )

    try:
        # Extract raw data
        raw_data = document_cleaner.extract_raw(tmp_path)

        # Apply cleaning
        cleaning_result = document_cleaner.clean(raw_data, options)

        # Merge edited metadata with extracted metadata
        final_metadata = cleaning_result.metadata.copy()
        if edited_metadata:
            final_metadata.update(edited_metadata)

        # Store cleaned text in session for chunking
        session['cleaned_text'] = cleaning_result.cleaned_text
        session['document_metadata'] = final_metadata

        # Clean up temp file after confirmation
        try:
            os.unlink(tmp_path)
            session.pop('cleaning_temp_path', None)
            session.pop('cleaning_options', None)
        except Exception as e:
            logger.warning(f'Failed to delete temp file: {e}')

        return jsonify({
            'success': True,
            'cleaned_text_length': len(cleaning_result.cleaned_text),
            'metadata': final_metadata,
            'cleaning_stats': cleaning_result.cleaning_stats,
            'reduction_percent': cleaning_result.reduction_percent,
        })

    except Exception as e:
        logger.error(f'Error in confirm_cleaning API: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
