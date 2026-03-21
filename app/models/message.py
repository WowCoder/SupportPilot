"""
Message model for SupportPilot
"""
from datetime import datetime
from typing import Optional

from ..extensions import db


class Message(db.Model):
    """
    Message model for conversation messages

    Sender types:
        - 'user': Message from end user
        - 'ai': Message from AI assistant
        - 'tech_support': Message from tech support personnel
    """

    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_type = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f'<Message {self.id} (conversation={self.conversation_id}, sender={self.sender_type})>'

    def is_from_user(self) -> bool:
        """Check if message is from user"""
        return self.sender_type == 'user'

    def is_from_ai(self) -> bool:
        """Check if message is from AI"""
        return self.sender_type == 'ai'

    def is_from_tech_support(self) -> bool:
        """Check if message is from tech support"""
        return self.sender_type == 'tech_support'
