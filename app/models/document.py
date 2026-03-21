"""
Document model for SupportPilot
"""
from datetime import datetime
from typing import Optional

from ..extensions import db


class Document(db.Model):
    """
    Document model for uploaded knowledge base files

    Supported file types: txt, pdf, doc, docx
    """

    __tablename__ = 'document'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

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
