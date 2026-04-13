"""
Chat Memory API Routes for SupportPilot

Provides REST API endpoints for chat memory management and FAQ operations.
"""
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
import logging

from ..extensions import db
from ..models import Conversation, ChatMemory, FAQEntry
from ..services.chat_memory_service import chat_memory_service
from ..services.query_rewriter import query_rewriter
from ..services.faq_generator import faq_generator
from ..utils import sanitize_input

logger = logging.getLogger(__name__)
chat_memory_bp = Blueprint('chat_memory', __name__, url_prefix='/api')


@chat_memory_bp.route('/chat-memory/<int:session_id>/window', methods=['GET'])
@login_required
def get_window(session_id):
    """
    Get window of recent chat records for a session.

    Query params:
        limit: Optional override for window size (default: 5)

    Returns:
        JSON list of chat memory records
    """
    # Check permission
    conversation = Conversation.query.get(session_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return jsonify({'error': 'Permission denied'}), 403

    # Get limit from query params
    limit = request.args.get('limit', type=int, default=5)

    # Get window records
    records = chat_memory_service.get_window(session_id, limit=limit)

    return jsonify({
        'session_id': session_id,
        'window_size': len(records),
        'records': [
            {
                'id': r.id,
                'sender_type': r.sender_type,
                'content': r.content,
                'created_at': r.created_at.isoformat()
            }
            for r in records
        ]
    }), 200


@chat_memory_bp.route('/chat-memory/<int:session_id>/summary', methods=['GET'])
@login_required
def get_summary(session_id):
    """
    Get compressed summaries for a session.

    Query params:
        start_date: Optional start date filter (ISO format)
        end_date: Optional end date filter (ISO format)

    Returns:
        JSON list of summary records
    """
    # Check permission
    conversation = Conversation.query.get(session_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return jsonify({'error': 'Permission denied'}), 403

    # Parse date filters
    from datetime import datetime
    start_date = None
    end_date = None

    if request.args.get('start_date'):
        try:
            start_date = datetime.fromisoformat(request.args['start_date'])
        except ValueError:
            return jsonify({'error': 'Invalid start_date format'}), 400

    if request.args.get('end_date'):
        try:
            end_date = datetime.fromisoformat(request.args['end_date'])
        except ValueError:
            return jsonify({'error': 'Invalid end_date format'}), 400

    # Get summaries
    summaries = chat_memory_service.get_session_summaries(session_id, start_date, end_date)

    return jsonify({
        'session_id': session_id,
        'summary_count': len(summaries),
        'summaries': [
            {
                'id': s.id,
                'summary': s.summary,
                'compressed_at': s.compressed_at.isoformat() if s.compressed_at else None,
                'batch_id': s.compression_batch_id
            }
            for s in summaries
        ]
    }), 200


@chat_memory_bp.route('/chat-memory/<int:session_id>/context', methods=['GET'])
@login_required
def get_context(session_id):
    """
    Get full context for a session (window + summaries).

    Returns:
        JSON with window records and summaries
    """
    # Check permission
    conversation = Conversation.query.get(session_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return jsonify({'error': 'Permission denied'}), 403

    # Get full context
    context = chat_memory_service.get_full_context(session_id)

    return jsonify({
        'session_id': session_id,
        'window_records': [
            {
                'id': r.id,
                'sender_type': r.sender_type,
                'content': r.content,
                'created_at': r.created_at.isoformat()
            }
            for r in context['window_records']
        ],
        'summaries': context['summaries'],
        'total_records': context['total_records']
    }), 200


@chat_memory_bp.route('/faq/generate', methods=['POST'])
@login_required
def generate_faq():
    """
    Generate FAQ entries from a closed conversation.

    Request body:
        session_id: Conversation session ID

    Returns:
        JSON with generation result
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    # Check permission
    conversation = Conversation.query.get(session_id)
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404

    if current_user.role != 'tech_support':
        return jsonify({'error': 'Only tech support can generate FAQ'}), 403

    # Check conversation is closed
    if not conversation.is_closed():
        return jsonify({'error': 'Conversation must be closed before generating FAQ'}), 400

    # Generate FAQ
    result = faq_generator.generate_from_session(session_id)

    if result['success']:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@chat_memory_bp.route('/faq/search', methods=['POST'])
@login_required
def search_faq():
    """
    Search FAQ entries using vector retrieval.

    Request body:
        query: Search query string
        k: Optional number of results (default: 5)

    Returns:
        JSON list of matching FAQ entries
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'query required'}), 400

    k = data.get('k', type=int, default=5)

    # Rewrite query using conversation history if available
    session_id = data.get('session_id')
    if session_id and query_rewriter.enabled:
        rewritten_query = query_rewriter.rewrite_query(query, session_id)
        logger.info(f'FAQ search query rewritten: "{query[:50]}..." -> "{rewritten_query[:50]}..."')
        query = rewritten_query

    # Search in ChromaDB with FAQ filter
    from rag.rag_utils import rag_utils

    try:
        results = rag_utils.retrieve_relevant_info(query, k=k, similarity_threshold=0.3)

        # Filter for FAQ entries only
        faq_results = [
            r for r in results
            if r.get('metadata', {}).get('source') == 'faq_from_session'
        ]

        return jsonify({
            'query': query,
            'results': [
                {
                    'content': r['content'],
                    'similarity': r['similarity'],
                    'source': r.get('source', 'unknown')
                }
                for r in faq_results
            ],
            'total': len(faq_results)
        }), 200

    except Exception as e:
        logger.error(f'FAQ search error: {e}', exc_info=True)
        return jsonify({'error': 'Search failed', 'details': str(e)}), 500


@chat_memory_bp.route('/faq/list', methods=['GET'])
@login_required
def list_faq():
    """
    List all FAQ entries (admin/tech_support only).

    Query params:
        page: Page number (default: 1)
        per_page: Items per page (default: 20)

    Returns:
        JSON list of FAQ entries
    """
    if current_user.role != 'tech_support':
        return jsonify({'error': 'Permission denied'}), 403

    page = request.args.get('page', type=int, default=1)
    per_page = request.args.get('per_page', type=int, default=20)

    pagination = FAQEntry.query.filter_by(is_duplicate=False).order_by(
        FAQEntry.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'page': page,
        'per_page': per_page,
        'total': pagination.total,
        'pages': pagination.pages,
        'entries': [
            {
                'id': faq.id,
                'question': faq.question,
                'answer': faq.answer,
                'source_session_id': faq.source_session_id,
                'created_at': faq.created_at.isoformat()
            }
            for faq in pagination.items
        ]
    }), 200


@chat_memory_bp.route('/faq/<int:faq_id>', methods=['DELETE'])
@login_required
def delete_faq(faq_id):
    """
    Delete a FAQ entry (admin/tech_support only).

    Returns:
        JSON with deletion result
    """
    if current_user.role != 'tech_support':
        return jsonify({'error': 'Permission denied'}), 403

    faq = FAQEntry.query.get(faq_id)
    if not faq:
        return jsonify({'error': 'FAQ not found'}), 404

    # Delete FAQ
    success = faq_generator.delete_faq(faq_id)

    if success:
        return jsonify({'message': 'FAQ deleted successfully'}), 200
    else:
        return jsonify({'error': 'Failed to delete FAQ'}), 500
