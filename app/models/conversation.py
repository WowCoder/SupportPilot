"""
Conversation model for SupportPilot
"""
from datetime import datetime
from typing import Optional

from ..extensions import db


class Conversation(db.Model):
    """
    Conversation model for tracking user-AI interactions

    Status values:
        - 'active': Conversation is ongoing
        - 'needs_attention': Requires tech support intervention
        - 'closed': Conversation has been closed
    """

    __tablename__ = 'conversation'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')
    message_count = db.Column(db.Integer, default=0)

    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy='dynamic',
                               order_by='Message.timestamp')

    def __repr__(self) -> str:
        return f'<Conversation {self.id} (user={self.user_id}, status={self.status})>'

    def is_active(self) -> bool:
        """Check if conversation is active"""
        return self.status == 'active'

    def needs_attention(self) -> bool:
        """Check if conversation needs tech support attention"""
        return self.status == 'needs_attention'

    def is_closed(self) -> bool:
        """Check if conversation is closed"""
        return self.status == 'closed'
