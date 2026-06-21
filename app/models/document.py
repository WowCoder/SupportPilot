"""
Document model for SupportPilot
"""
from datetime import datetime

from ..extensions import db


class Document(db.Model):
    """
    Document model for uploaded knowledge base files

    Supported file types: txt, pdf, doc, docx

    Processing metadata tracks how each document was chunked and indexed.
    """

    __tablename__ = 'document'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Processing metadata — populated after pipeline completes
    mode = db.Column(db.String(10), default='auto')
    # 'auto' or 'manual'
    strategy = db.Column(db.String(20), default='auto')
    # final strategy used: auto/semantic/sentence/recursive/small_to_big
    chunk_size = db.Column(db.Integer, nullable=True)
    chunk_overlap = db.Column(db.Integer, nullable=True)
    chunks_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='completed')
    # pending / processing / completed / failed
    error_message = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:
        return f'<Document {self.filename} (uploaded by={self.uploaded_by})>'

    def is_pdf(self) -> bool:
        """Check if document is a PDF file"""
        return self.filename.lower().endswith('.pdf')

    def is_text(self) -> bool:
        """Check if document is a text file"""
        return self.filename.lower().endswith('.txt')

    def is_docx(self) -> bool:
        """Check if document is a Word document"""
        return self.filename.lower().endswith('.docx')

    def to_dict(self) -> dict:
        """Serialize document for API responses."""
        return {
            'id': self.id,
            'filename': self.filename,
            'mode': self.mode or 'auto',
            'strategy': self.strategy or 'auto',
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'chunks_count': self.chunks_count or 0,
            'status': self.status or 'completed',
            'error_message': self.error_message,
            'uploaded_at': self.uploaded_at.strftime('%Y-%m-%d %H:%M') if self.uploaded_at else None,
        }
