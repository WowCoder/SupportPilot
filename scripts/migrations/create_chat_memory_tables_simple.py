"""
Database Migration Script for Chat Memory System (Simplified Version)

This script creates tables without loading the full application.
Run this script to create the chat_memory and faq_entries tables.

Usage:
    python3 migrations/create_chat_memory_tables_simple.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class ChatMemory(Base):
    __tablename__ = 'chat_memory'

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=False)
    sender_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default='active')
    created_at = Column(DateTime, default=datetime.utcnow)
    compressed_at = Column(DateTime, nullable=True)
    compression_batch_id = Column(String(50), nullable=True)


class FAQEntry(Base):
    __tablename__ = 'faq_entries'

    id = Column(Integer, primary_key=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source_session_id = Column(Integer, nullable=True)
    chroma_doc_id = Column(String(100), nullable=True)
    similarity_checked = Column(Boolean, default=False)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    """Create chat_memory and faq_entries tables"""
    # Use the same database as the main application
    db_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'support_pilot.db')
    db_path = os.path.abspath(db_path)

    engine = create_engine(f'sqlite:///{db_path}')

    print(f"Using database: {db_path}")
    print("Creating chat_memory table...")
    ChatMemory.__table__.create(engine, checkfirst=True)
    print("✓ chat_memory table created (or already exists)")

    print("Creating faq_entries table...")
    FAQEntry.__table__.create(engine, checkfirst=True)
    print("✓ faq_entries table created (or already exists)")

    print("\nMigration completed successfully!")
    print("\nTables created:")
    print("  - chat_memory: Stores conversation records with compression support")
    print("  - faq_entries: Stores FAQ entries extracted from conversations")


def drop_tables():
    """Drop chat_memory and faq_entries tables (rollback)"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'support_pilot.db')
    db_path = os.path.abspath(db_path)

    engine = create_engine(f'sqlite:///{db_path}')

    print(f"Using database: {db_path}")
    print("Dropping faq_entries table...")
    FAQEntry.__table__.drop(engine)
    print("✓ faq_entries table dropped")

    print("Dropping chat_memory table...")
    ChatMemory.__table__.drop(engine)
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
