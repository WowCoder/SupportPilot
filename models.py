"""
Backward compatibility layer - imports from new app package

This file allows existing code to continue working during migration.
Deprecated: Use 'from app.models import ...' instead.
"""
from app.models import User, Conversation, Message, Document

__all__ = ['User', 'Conversation', 'Message', 'Document']
