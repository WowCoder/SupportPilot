"""
Main Blueprint for SupportPilot

Handles index/dashboard routes.
"""
from flask import Blueprint, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Conversation

logger = __import__('logging').getLogger(__name__)
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    """Main dashboard - shows conversations based on user role"""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    if current_user.role == 'tech_support':
        # Tech support dashboard with pagination
        conversations = Conversation.query.order_by(Conversation.last_message_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        needs_attention = Conversation.query.filter_by(status='needs_attention').all()
        return render_template('tech_dashboard.html',
                               conversations=conversations.items,
                               needs_attention=needs_attention,
                               pagination=conversations)
    else:
        # User dashboard with pagination
        conversations = current_user.conversations\
            .order_by(Conversation.last_message_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        return render_template('user_dashboard.html',
                               conversations=conversations.items,
                               pagination=conversations)
