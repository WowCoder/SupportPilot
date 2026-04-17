"""
Support Ticket model for SupportPilot

Tracks support ticket lifecycle including human handoff and closure.
"""
from datetime import datetime
from typing import Optional

from ..extensions import db


class SupportTicket(db.Model):
    """
    Support Ticket model for tracking conversation lifecycle

    Status values:
        - 'open': Ticket is active, AI is handling conversation
        - 'pending_human': User requested human handoff, waiting for tech support
        - 'closed': Ticket is closed by user or tech support
    """

    __tablename__ = 'support_tickets'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False, unique=True, index=True)
    status = db.Column(db.String(30), default='open', index=True)  # 'open', 'pending_human', 'closed'
    round_count = db.Column(db.Integer, default=0)  # Number of conversation rounds
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    closed_by = db.Column(db.String(20), nullable=True)  # 'user', 'tech_support'
    closed_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def __repr__(self) -> str:
        return f'<SupportTicket {self.id} (session={self.session_id}, status={self.status})>'

    def is_open(self) -> bool:
        """Check if ticket is open"""
        return self.status == 'open'

    def is_pending_human(self) -> bool:
        """Check if ticket is waiting for human handoff"""
        return self.status == 'pending_human'

    def is_closed(self) -> bool:
        """Check if ticket is closed"""
        return self.status == 'closed'

    def mark_pending_human(self):
        """Mark ticket as pending human handoff"""
        self.status = 'pending_human'

    def close(self, closed_by: str, user_id: Optional[int] = None):
        """Close the ticket"""
        self.status = 'closed'
        self.closed_at = datetime.utcnow()
        self.closed_by = closed_by
        if user_id:
            self.closed_by_user_id = user_id

    def increment_round(self):
        """Increment conversation round count"""
        self.round_count += 1
