"""
Backward compatibility layer - imports from new app package

This file allows existing code to continue working during migration.
Deprecated: Use 'from app.extensions import ...' instead.
"""
from app.extensions import db, login_manager, csrf

__all__ = ['db', 'login_manager', 'csrf']
