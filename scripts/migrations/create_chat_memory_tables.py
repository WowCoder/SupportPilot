"""
Database Migration Script for Chat Memory System

Run this script to create the chat_memory and faq_entries tables.

Usage:
    python migrations/create_chat_memory_tables.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.chat_memory import ChatMemory
from app.models.faq_entry import FAQEntry


def create_tables():
    """Create chat_memory and faq_entries tables"""
    app = create_app()

    with app.app_context():
        # Create tables (checkfirst=True to avoid errors if tables exist)
        print("Creating chat_memory table...")
        ChatMemory.__table__.create(db.engine, checkfirst=True)
        print("✓ chat_memory table created (or already exists)")

        print("Creating faq_entries table...")
        FAQEntry.__table__.create(db.engine, checkfirst=True)
        print("✓ faq_entries table created (or already exists)")

        print("\nMigration completed successfully!")
        print("\nTables created:")
        print("  - chat_memory: Stores conversation records with compression support")
        print("  - faq_entries: Stores FAQ entries extracted from conversations")


def drop_tables():
    """Drop chat_memory and faq_entries tables (rollback)"""
    app = create_app()

    with app.app_context():
        print("Dropping faq_entries table...")
        FAQEntry.__table__.drop(db.engine)
        print("✓ faq_entries table dropped")

        print("Dropping chat_memory table...")
        ChatMemory.__table__.drop(db.engine)
        print("✓ chat_memory table dropped")

        print("\nRollback completed!")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        if input("Are you sure you want to drop the tables? (yes/no): ") == 'yes':
            drop_tables()
        else:
            print("Cancelled")
    else:
        create_tables()
