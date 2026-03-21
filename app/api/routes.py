"""
API Blueprint for SupportPilot

REST API endpoints for RAG and document operations.
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
import logging

from rag.rag_utils import rag_utils

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/document/count', methods=['GET'])
@login_required
def get_document_count():
    """Get total document count in RAG system"""
    try:
        count = rag_utils.get_document_count()
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

    data = request.get_json()
    query = data.get('query', '')
    k = data.get('k', 3)
    similarity_threshold = data.get('similarity_threshold', 0.1)

    if not query:
        return jsonify({'success': False, 'message': 'Query is required'}), 400

    try:
        results = rag_utils.retrieve_relevant_info(query, k=k, similarity_threshold=similarity_threshold)
        return jsonify({
            'success': True,
            'results': [
                {
                    'content': r['content'],
                    'similarity': r['similarity'],
                    'source': r['source']
                }
                for r in results
            ]
        })
    except Exception as e:
        logger.error(f'Error testing query: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
