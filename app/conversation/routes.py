"""
Conversation Blueprint for SupportPilot

Handles conversation creation, viewing, and messaging.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
import logging

from ..extensions import db
from ..models import Conversation, Message
from ..utils import sanitize_input
from rag.rag_utils import rag_utils
from api.qwen_api import qwen_api

logger = logging.getLogger(__name__)
conversation_bp = Blueprint('conversation', __name__, url_prefix='/conversation')


@conversation_bp.route('/new', methods=['POST'])
@login_required
def create_conversation():
    """Create a new conversation"""
    if current_user.role == 'user':
        conversation = Conversation(user_id=current_user.id)
        db.session.add(conversation)
        db.session.commit()
        return redirect(url_for('conversation.view', conversation_id=conversation.id))
    return redirect(url_for('main.index'))


@conversation_bp.route('/<int:conversation_id>')
@login_required
def view(conversation_id):
    """View conversation details"""
    conversation = Conversation.query.get_or_404(conversation_id)

    # Check if user is the owner or tech support
    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return redirect(url_for('main.index'))

    messages = conversation.messages.order_by(Message.timestamp).all()
    return render_template('conversation.html', conversation=conversation, messages=messages)


@conversation_bp.route('/<int:conversation_id>/send', methods=['POST'])
@login_required
def send_message(conversation_id):
    """Send a message in a conversation"""
    conversation = Conversation.query.get_or_404(conversation_id)

    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return redirect(url_for('main.index'))

    content = sanitize_input(request.form.get('content', ''))
    if not content:
        flash('Message content cannot be empty')
        return redirect(url_for('conversation.view', conversation_id=conversation_id))

    sender_type = 'user' if current_user.role == 'user' else 'tech_support'

    # Create user message
    message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        content=content
    )
    db.session.add(message)

    # Add to chat memory for window management
    try:
        from ..services.chat_memory_service import chat_memory_service
        chat_memory_service.add_record(conversation_id, sender_type, content)

        # Increment round count for user messages (for tracking purposes only)
        if sender_type == 'user':
            from ..services.ticket_service import ticket_service
            ticket_service.increment_round(conversation_id)
    except Exception as e:
        logger.warning(f'Failed to add to chat memory: {e}')

    # Update conversation stats
    conversation.message_count += 1
    conversation.last_message_at = message.timestamp

    # Check if needs tech support intervention
    if conversation.message_count >= 3 and conversation.status == 'active':
        conversation.status = 'needs_attention'

    db.session.commit()

    # AI response if user is sending and conversation is active
    if current_user.role == 'user' and conversation.status == 'active':
        try:
            # Get conversation context from chat memory
            from ..services.chat_memory_service import chat_memory_service
            from ..services.query_rewriter import query_rewriter

            # Rewrite query using conversation history
            rewritten_query = query_rewriter.rewrite_query(content, conversation_id)

            # Use RAG to retrieve relevant information with rewritten query
            relevant_info = rag_utils.retrieve_relevant_info(rewritten_query, k=3)

            # Generate response using Qwen API
            ai_response = qwen_api.generate_response(rewritten_query, relevant_info)
            ai_message = Message(
                conversation_id=conversation_id,
                sender_type='ai',
                content=ai_response
            )
            db.session.add(ai_message)

            # Also add AI response to chat memory
            chat_memory_service.add_record(conversation_id, 'ai', ai_response)

            conversation.message_count += 1
            conversation.last_message_at = ai_message.timestamp
            db.session.commit()
            logger.info(f'AI response generated for conversation {conversation_id}')
        except Exception as e:
            logger.error(f'Error generating AI response: {e}', exc_info=True)

    return redirect(url_for('conversation.view', conversation_id=conversation_id))


@conversation_bp.route('/<int:conversation_id>/close', methods=['POST'])
@login_required
def close_conversation(conversation_id):
    """Close a conversation (tech support only) with optional FAQ generation"""
    conversation = Conversation.query.get_or_404(conversation_id)

    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized close attempt by user {current_user.username}')
        flash('Only tech support can close conversations')
        return redirect(url_for('conversation.view', conversation_id=conversation_id))

    # Check if FAQ generation is requested
    generate_faq = request.form.get('generate_faq') == 'on'

    conversation.status = 'closed'
    db.session.commit()
    logger.info(f'Conversation {conversation_id} closed by {current_user.username}')
    flash('Conversation closed successfully')

    # Generate FAQ if requested
    if generate_faq:
        try:
            from ..services.faq_generator import faq_generator
            result = faq_generator.generate_from_session(conversation_id)

            if result['success']:
                flash(f"FAQ generated: {result['faq_count']} entries created ({result['duplicates_skipped']} duplicates skipped)")
                logger.info(f'FAQ generated for conversation {conversation_id}: {result["faq_count"]} entries')
            else:
                flash(f"FAQ generation failed: {result.get('error', 'Unknown error')}")
                logger.warning(f'FAQ generation failed for conversation {conversation_id}: {result.get("error")}')
        except Exception as e:
            flash(f"FAQ generation error: {str(e)}")
            logger.error(f'Error generating FAQ for conversation {conversation_id}: {e}', exc_info=True)

    return redirect(url_for('main.index'))


@conversation_bp.route('/<int:conversation_id>/reopen', methods=['POST'])
@login_required
def reopen_conversation(conversation_id):
    """Reopen a closed conversation (tech support only)"""
    conversation = Conversation.query.get_or_404(conversation_id)

    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized reopen attempt by user {current_user.username}')
        flash('Only tech support can reopen conversations')
        return redirect(url_for('conversation.view', conversation_id=conversation_id))

    conversation.status = 'active'
    conversation.message_count = 0  # Reset message count
    db.session.commit()
    logger.info(f'Conversation {conversation_id} reopened by {current_user.username}')
    flash('Conversation reopened successfully')
    return redirect(url_for('conversation.view', conversation_id=conversation_id))


@conversation_bp.route('/<int:conversation_id>/mark-attention', methods=['POST'])
@login_required
def mark_attention(conversation_id):
    """Mark a conversation as needs attention (tech support only)"""
    conversation = Conversation.query.get_or_404(conversation_id)

    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized mark attempt by user {current_user.username}')
        flash('Permission denied')
        return redirect(url_for('conversation.view', conversation_id=conversation_id))

    conversation.status = 'needs_attention'
    db.session.commit()
    logger.info(f'Conversation {conversation_id} marked as needs_attention by {current_user.username}')
    flash('Conversation marked for attention')
    return redirect(url_for('conversation.view', conversation_id=conversation_id))
