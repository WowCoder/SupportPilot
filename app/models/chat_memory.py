"""
Chat Memory model for SupportPilot

Stores chat conversation records with window management and compression support.
"""
from datetime import datetime
from typing import Optional

from ..extensions import db


class ChatMemory(db.Model):
    """
    Chat Memory model for storing conversation records with memory management

    Status values:
        - 'active': Record is in the active window (full text retained)
        - 'pending_compression': Record exceeded window, waiting to be compressed
        - 'compressed': Record has been compressed, summary stored
    """

    __tablename__ = 'chat_memory'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False, index=True)
    sender_type = db.Column(db.String(20), nullable=False)  # 'user', 'ai', 'tech_support'
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)  # Compressed summary for old records
    status = db.Column(db.String(30), default='active', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    compressed_at = db.Column(db.DateTime, nullable=True)
    compression_batch_id = db.Column(db.String(50), nullable=True)  # Groups records compressed together

    # Ticket tracking fields
    ticket_status = db.Column(db.String(30), default='open', index=True)  # 'open', 'pending_human', 'closed'
    round_count = db.Column(db.Integer, default=0)  # Current round count for this session

    def __repr__(self) -> str:
        return f'<ChatMemory {self.id} (session={self.session_id}, status={self.status})>'

    def is_active(self) -> bool:
        """Check if record is in active window"""
        return self.status == 'active'

    def is_pending_compression(self) -> bool:
        """Check if record is waiting to be compressed"""
        return self.status == 'pending_compression'

    def is_compressed(self) -> bool:
        """Check if record has been compressed"""
        return self.status == 'compressed'

    def mark_for_compression(self):
        """Mark this record for compression"""
        self.status = 'pending_compression'

    def mark_compressed(self, summary: str, batch_id: str = None):
        """Mark this record as compressed with summary"""
        self.status = 'compressed'
        self.summary = summary
        self.compressed_at = datetime.utcnow()
        if batch_id:
            self.compression_batch_id = batch_id

    def update_ticket_status(self, status: str):
        """Update ticket status"""
        self.ticket_status = status

    def increment_round(self):
        """Increment conversation round count"""
        self.round_count += 1

    def should_show_handoff(self, threshold: int = 3) -> bool:
        """Check if human handoff button should be shown"""
        return self.round_count >= threshold and self.ticket_status == 'open'
