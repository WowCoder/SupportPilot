"""
Ticket API routes for SupportPilot

Handles ticket operations: handoff, close, status.
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
import logging

from ..extensions import db
from ..services.ticket_service import ticket_service

logger = logging.getLogger(__name__)

ticket_bp = Blueprint('ticket', __name__, url_prefix='/api/ticket')


@ticket_bp.route('/<int:session_id>/status', methods=['GET'])
@login_required
def get_ticket_status(session_id):
    """
    Get ticket status and round count.

    Returns:
        JSON with status and round_count
    """
    try:
        status, round_count = ticket_service.get_ticket_status(session_id)

        return jsonify({
            'success': True,
            'status': status,
            'round_count': round_count
        })
    except Exception as e:
        logger.error(f'Error getting ticket status: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<int:session_id>/handoff', methods=['POST'])
@login_required
def request_handoff(session_id):
    """
    Request human handoff for a ticket.

    Returns:
        JSON with success status
    """
    try:
        success = ticket_service.request_human_handoff(session_id)

        if success:
            logger.info(f'User {current_user.id} requested handoff for session {session_id}')
            return jsonify({
                'success': True,
                'message': '已请求人工介入，技术支持将尽快为您服务'
            })
        else:
            return jsonify({
                'success': False,
                'message': '无法请求人工介入，工单可能已关闭或不存在'
            }), 400

    except Exception as e:
        logger.error(f'Error requesting handoff: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@ticket_bp.route('/<int:session_id>/close', methods=['POST'])
@login_required
def close_ticket(session_id):
    """
    Close a ticket.

    Returns:
        JSON with success status
    """
    try:
        # Determine who is closing
        closed_by = 'tech_support' if current_user.role == 'tech_support' else 'user'

        success = ticket_service.close_ticket(
            session_id,
            closed_by=closed_by,
            user_id=current_user.id
        )

        if success:
            logger.info(f'Ticket {session_id} closed by {closed_by}')
            return jsonify({
                'success': True,
                'message': '工单已关闭'
            })
        else:
            return jsonify({
                'success': False,
                'message': '无法关闭工单，工单可能不存在或已关闭'
            }), 400

    except Exception as e:
        logger.error(f'Error closing ticket: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
