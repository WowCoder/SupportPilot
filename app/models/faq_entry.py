"""
FAQ Entry model for SupportPilot

Stores FAQ entries extracted from closed conversations for RAG retrieval.
"""
from datetime import datetime
from typing import Optional, List

from ..extensions import db


class FAQEntry(db.Model):
    """
    FAQ Entry model for storing Q&A pairs extracted from conversations

    These entries are also synced to ChromaDB for vector retrieval.
    Status workflow:
        - 'pending_review': AI generated, waiting for tech support review
        - 'confirmed': Reviewed and confirmed, synced to ChromaDB
        - 'rejected': Rejected by tech support
        - 'draft': Manually created by tech support
    """

    __tablename__ = 'faq_entries'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True, index=True)
    status = db.Column(db.String(30), default='pending_review', index=True)

    # Vector database linkage
    chroma_doc_ids = db.Column(db.Text, nullable=True)  # JSON array of ChromaDB doc IDs (for Small-to-Big)

    # Audit fields
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    confirmed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Source conversation (optional for manually created FAQs)
    source_session_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=True)

    # Sync progress tracking (for vectorization progress indicator)
    sync_progress = db.Column(db.Integer, default=0)  # 0-100
    sync_error = db.Column(db.Text, nullable=True)

    # Relationships
    source_conversation = db.relationship('Conversation', foreign_keys=[source_session_id])
    creator = db.relationship('User', foreign_keys=[created_by], lazy='joined')
    confirmer = db.relationship('User', foreign_keys=[confirmed_by])

    # Version history
    versions = db.relationship('FAQVersion', backref='faq_entry', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<FAQEntry {self.id}: {self.question[:50]}...>'

    def mark_as_confirmed(self, user_id: int, chroma_doc_ids: List[str] = None):
        """Mark FAQ as confirmed and optionally set ChromaDB doc IDs"""
        self.status = 'confirmed'
        self.confirmed_by = user_id
        self.confirmed_at = datetime.utcnow()
        if chroma_doc_ids:
            import json
            self.chroma_doc_ids = json.dumps(chroma_doc_ids)

    def mark_as_rejected(self):
        """Mark FAQ as rejected"""
        self.status = 'rejected'

    def mark_as_pending_review(self):
        """Mark FAQ as pending review"""
        self.status = 'pending_review'

    def add_version(self, user_id: int, change_reason: str = None):
        """Add a version record for this FAQ"""
        version = FAQVersion(
            faq_id=self.id,
            question=self.question,
            answer=self.answer,
            changed_by=user_id,
            change_reason=change_reason
        )
        return version

    def get_chroma_doc_ids(self) -> List[str]:
        """Get ChromaDB document IDs as list"""
        import json
        if not self.chroma_doc_ids:
            return []
        return json.loads(self.chroma_doc_ids)


class FAQVersion(db.Model):
    """
    FAQ Version model for tracking changes to FAQ entries
    """

    __tablename__ = 'faq_versions'

    id = db.Column(db.Integer, primary_key=True)
    faq_id = db.Column(db.Integer, db.ForeignKey('faq_entries.id'), nullable=False, index=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    change_reason = db.Column(db.String(500), nullable=True)
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f'<FAQVersion {self.id} (faq_id={self.faq_id})>'
