"""
Chat API v1 — Session and Message endpoints for Vue SPA frontend.

Uses JWT authentication and unified JSON response format.
"""
import logging
from flask import Blueprint, request, g
from ...extensions import db
from ...models import Conversation, Message
from ...utils.auth import jwt_required
from ...utils.response import api_success, api_error, api_paginated
from ...utils.sanitize import sanitize_input
from rag.online.service import rag_service
from llm.llm_client import llm_client

logger = logging.getLogger(__name__)

chat_v1_bp = Blueprint('chat_v1', __name__, url_prefix='/api/v1/chat')


def _conversation_to_dict(conv):
    """Serialize a Conversation for API response."""
    return {
        'id': conv.id,
        'user_id': conv.user_id,
        'status': conv.status,
        'message_count': conv.message_count,
        'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None,
        'created_at': conv.created_at.isoformat(),
    }


def _message_to_dict(msg):
    """Serialize a Message for API response."""
    return {
        'id': msg.id,
        'conversation_id': msg.conversation_id,
        'sender_type': msg.sender_type,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
    }


@chat_v1_bp.route('/sessions', methods=['GET'])
@jwt_required
def list_sessions():
    """List conversations for the current user."""
    user = g.current_user

    if user.role == 'tech_support':
        conversations = Conversation.query.order_by(
            Conversation.last_message_at.desc()
        ).limit(50).all()
    else:
        conversations = Conversation.query.filter_by(user_id=user.id).order_by(
            Conversation.last_message_at.desc()
        ).limit(50).all()

    return api_success([_conversation_to_dict(c) for c in conversations])


@chat_v1_bp.route('/sessions', methods=['POST'])
@jwt_required
def create_session():
    """Create a new conversation session."""
    user = g.current_user

    if user.role != 'user':
        return api_error(403, 'Only regular users can create sessions')

    conversation = Conversation(user_id=user.id)
    db.session.add(conversation)
    db.session.commit()

    logger.info(f'User {user.username} created session {conversation.id}')
    return api_success(_conversation_to_dict(conversation), code=201)


@chat_v1_bp.route('/sessions/<int:session_id>', methods=['GET'])
@jwt_required
def get_session(session_id):
    """Get a single session's details."""
    user = g.current_user
    conversation = Conversation.query.get_or_404(session_id)

    if conversation.user_id != user.id and user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    return api_success(_conversation_to_dict(conversation))


@chat_v1_bp.route('/sessions/<int:session_id>/messages', methods=['GET'])
@jwt_required
def list_messages(session_id):
    """Get messages for a session (paginated)."""
    user = g.current_user
    conversation = Conversation.query.get_or_404(session_id)

    if conversation.user_id != user.id and user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    page = request.args.get('page', type=int, default=1)
    page_size = request.args.get('page_size', type=int, default=50)
    pagination = Message.query.filter_by(conversation_id=session_id).order_by(
        Message.timestamp.asc()
    ).paginate(page=page, per_page=page_size, error_out=False)

    return api_paginated(
        [_message_to_dict(m) for m in pagination.items],
        pagination.total,
        page=page,
        page_size=page_size,
    )


@chat_v1_bp.route('/sessions/<int:session_id>/messages', methods=['POST'])
@jwt_required
def send_message(session_id):
    """
    Send a message and get AI response.

    If `Accept: text/event-stream` is present, returns SSE stream.
    Otherwise returns JSON with the AI response.
    """
    user = g.current_user
    conversation = Conversation.query.get_or_404(session_id)

    if conversation.user_id != user.id and user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    if conversation.status == 'closed':
        return api_error(400, 'Conversation is closed')

    data = request.get_json(silent=True) or {}
    content = sanitize_input(data.get('content', ''))

    if not content:
        return api_error(400, 'Message content is required')

    sender_type = 'user' if user.role == 'user' else 'tech_support'

    # Create user/tech message
    message = Message(
        conversation_id=session_id,
        sender_type=sender_type,
        content=content,
    )
    db.session.add(message)
    conversation.message_count += 1
    conversation.last_message_at = message.timestamp
    db.session.commit()

    # AI response for user messages (only when conversation is active)
    ai_message = None
    if user.role == 'user' and conversation.status == 'active':
        try:
            relevant_info = rag_service.retrieve(
                query=content, k=3, use_small_to_big=True,
                session_id=str(session_id),
            )

            logger.info(
                f'RAG retrieval: query="{content[:50]}...", '
                f'results={len(relevant_info)}, '
                f'top_score={relevant_info[0]["similarity"]:.3f}'
                if relevant_info else f'RAG retrieval: query="{content[:50]}...", results=0'
            )

            ai_response = llm_client.chat(content, relevant_info)
            ai_message = Message(
                conversation_id=session_id,
                sender_type='ai',
                content=ai_response,
            )
            db.session.add(ai_message)
            conversation.message_count += 1
            conversation.last_message_at = ai_message.timestamp
            db.session.commit()

        except Exception as e:
            logger.error(f'Error generating AI response: {e}', exc_info=True)
            # Return user message even if AI fails — don't lose the user's message
            resp_data = {
                'user_message': _message_to_dict(message),
                'ai_message': None,
                'ai_error': 'AI response temporarily unavailable',
            }
            return api_success(resp_data, code=201)

    # Auto-escalate after threshold (AFTER AI response generation)
    if conversation.message_count >= 3 and conversation.status == 'active':
        conversation.status = 'needs_attention'
        db.session.commit()

    resp_data = {
        'user_message': _message_to_dict(message),
    }
    if ai_message:
        resp_data['ai_message'] = _message_to_dict(ai_message)

    return api_success(resp_data, code=201)


@chat_v1_bp.route('/sessions/<int:session_id>/close', methods=['POST'])
@jwt_required
def close_session(session_id):
    """Close a session (tech support or session owner)."""
    user = g.current_user
    conversation = Conversation.query.get_or_404(session_id)

    if conversation.user_id != user.id and user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    conversation.status = 'closed'
    db.session.commit()

    logger.info(f'Session {session_id} closed by {user.username}')
    return api_success(_conversation_to_dict(conversation))


@chat_v1_bp.route('/sessions/<int:session_id>/reopen', methods=['POST'])
@jwt_required
def reopen_session(session_id):
    """Reopen a closed session (tech support only)."""
    user = g.current_user
    conversation = Conversation.query.get_or_404(session_id)

    if user.role != 'tech_support':
        return api_error(403, 'Only tech support can reopen sessions')

    conversation.status = 'active'
    conversation.message_count = 0
    db.session.commit()

    logger.info(f'Session {session_id} reopened by {user.username}')
    return api_success(_conversation_to_dict(conversation))


@chat_v1_bp.route('/sessions/<int:session_id>/mark-attention', methods=['POST'])
@jwt_required
def mark_attention(session_id):
    """Mark a session as needs_attention (tech support only)."""
    user = g.current_user
    conversation = Conversation.query.get_or_404(session_id)

    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    conversation.status = 'needs_attention'
    db.session.commit()

    logger.info(f'Session {session_id} marked needs_attention by {user.username}')
    return api_success(_conversation_to_dict(conversation))


@chat_v1_bp.route('/stats', methods=['GET'])
@jwt_required
def session_stats():
    """Get session statistics for the tech dashboard."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    total = Conversation.query.count()
    active = Conversation.query.filter_by(status='active').count()
    needs_attention = Conversation.query.filter_by(status='needs_attention').count()
    closed = Conversation.query.filter_by(status='closed').count()

    # Recent sessions for the table
    recent = Conversation.query.order_by(
        Conversation.last_message_at.desc()
    ).limit(20).all()

    return api_success({
        'total': total,
        'active': active,
        'needs_attention': needs_attention,
        'closed': closed,
        'recent_sessions': [_conversation_to_dict(c) for c in recent],
    })
