"""
Migration: Add rag_semantic_cache table for query-answer caching.

Usage:
    python scripts/migrations/add_semantic_cache.py
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from app import create_app
from app.extensions import db
from app.models.rag_semantic_cache import RagSemanticCache  # noqa: F401


def main():
    app = create_app()
    with app.app_context():
        print('Creating rag_semantic_cache table...')
        db.create_all()
        print('Done. Table "rag_semantic_cache" created (if not exists).')


if __name__ == '__main__':
    main()
