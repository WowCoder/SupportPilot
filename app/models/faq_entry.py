"""
FAQ Entry model for SupportPilot

Stores FAQ entries extracted from closed conversations for RAG retrieval.
"""
from datetime import datetime
from typing import Optional

from ..extensions import db


class FAQEntry(db.Model):
    """
    FAQ Entry model for storing Q&A pairs extracted from conversations

    These entries are also synced to ChromaDB for vector retrieval.
    """

    __tablename__ = 'faq_entries'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    source_session_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    chroma_doc_id = db.Column(db.String(100), nullable=True, unique=True)  # ID in ChromaDB
    similarity_checked = db.Column(db.Boolean, default=False)
    is_duplicate = db.Column(db.Boolean, default=False)
    duplicate_of = db.Column(db.Integer, db.ForeignKey('faq_entries.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    source_conversation = db.relationship('Conversation', foreign_keys=[source_session_id])
    duplicate_conversation = db.relationship('FAQEntry', remote_side=[id], foreign_keys=[duplicate_of])

    def __repr__(self) -> str:
        return f'<FAQEntry {self.id}: {self.question[:50]}...>'

    def mark_as_duplicate(self, original_id: int):
        """Mark this FAQ as a duplicate of another"""
        self.is_duplicate = True
        self.duplicate_of = original_id
        self.similarity_checked = True

    def mark_as_unique(self, chroma_doc_id: str = None):
        """Mark this FAQ as unique and optionally set ChromaDB doc ID"""
        self.is_duplicate = False
        self.similarity_checked = True
        if chroma_doc_id:
            self.chroma_doc_id = chroma_doc_id
