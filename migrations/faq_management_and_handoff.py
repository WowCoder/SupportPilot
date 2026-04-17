"""
Database Migration Script for FAQ Management and Human Handoff Features

This script creates/updates tables for:
- Support tickets (support_tickets)
- FAQ entries with review workflow (faq_entries updated)
- FAQ version history (faq_versions)
- Chat memory ticket tracking (chat_memory updated)

Usage:
    python migrations/faq_management_and_handoff.py
    python migrations/faq_management_and_handoff.py --rollback
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.support_ticket import SupportTicket
from app.models.faq_entry import FAQEntry, FAQVersion
from app.models.chat_memory import ChatMemory


def create_tables():
    """Create new tables and add columns for FAQ management and handoff features"""
    app = create_app()

    with app.app_context():
        # Create support_tickets table
        print("Creating support_tickets table...")
        SupportTicket.__table__.create(db.engine, checkfirst=True)
        print("✓ support_tickets table created (or already exists)")

        # Create faq_versions table
        print("Creating faq_versions table...")
        FAQVersion.__table__.create(db.engine, checkfirst=True)
        print("✓ faq_versions table created (or already exists)")

        # Update faq_entries table (add new columns)
        print("Updating faq_entries table...")
        _update_faq_entries_table(db.engine)
        print("✓ faq_entries table updated")

        # Update chat_memory table (add ticket tracking columns)
        print("Updating chat_memory table...")
        _update_chat_memory_table(db.engine)
        print("✓ chat_memory table updated")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nTables created/updated:")
        print("  - support_tickets: Tracks ticket lifecycle (open/pending_human/closed)")
        print("  - faq_entries: Updated with review workflow fields")
        print("  - faq_versions: Tracks FAQ change history")
        print("  - chat_memory: Updated with ticket_status and round_count")


def _update_faq_entries_table(engine):
    """Add new columns to faq_entries table"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('faq_entries')]

    with engine.connect() as conn:
        # Add category column
        if 'category' not in existing_columns:
            print("  - Adding 'category' column...")
            conn.execute(text("ALTER TABLE faq_entries ADD COLUMN category VARCHAR(100)"))

        # Add status column
        if 'status' not in existing_columns:
            print("  - Adding 'status' column...")
            conn.execute(text("ALTER TABLE faq_entries ADD COLUMN status VARCHAR(30) DEFAULT 'pending_review'"))

        # Add chroma_doc_ids column (replacing chroma_doc_id)
        if 'chroma_doc_ids' not in existing_columns:
            print("  - Adding 'chroma_doc_ids' column...")
            conn.execute(text("ALTER TABLE faq_entries ADD COLUMN chroma_doc_ids TEXT"))

        # Add confirmed_by column
        if 'confirmed_by' not in existing_columns:
            print("  - Adding 'confirmed_by' column...")
            conn.execute(text("ALTER TABLE faq_entries ADD COLUMN confirmed_by INTEGER"))

        # Add confirmed_at column
        if 'confirmed_at' not in existing_columns:
            print("  - Adding 'confirmed_at' column...")
            conn.execute(text("ALTER TABLE faq_entries ADD COLUMN confirmed_at DATETIME"))

        # Add updated_at column
        if 'updated_at' not in existing_columns:
            print("  - Adding 'updated_at' column...")
            conn.execute(text("ALTER TABLE faq_entries ADD COLUMN updated_at DATETIME"))

        # Add source_session_id column (make nullable)
        if 'source_session_id' not in existing_columns:
            print("  - Adding 'source_session_id' column...")
            conn.execute(text("ALTER TABLE faq_entries ADD COLUMN source_session_id INTEGER"))

        conn.commit()


def _update_chat_memory_table(engine):
    """Add ticket tracking columns to chat_memory table"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('chat_memory')]

    with engine.connect() as conn:
        # Add ticket_status column
        if 'ticket_status' not in existing_columns:
            print("  - Adding 'ticket_status' column...")
            conn.execute(text("ALTER TABLE chat_memory ADD COLUMN ticket_status VARCHAR(30) DEFAULT 'open'"))

        # Add round_count column
        if 'round_count' not in existing_columns:
            print("  - Adding 'round_count' column...")
            conn.execute(text("ALTER TABLE chat_memory ADD COLUMN round_count INTEGER DEFAULT 0"))

        conn.commit()


def drop_tables():
    """Drop newly created tables (rollback)"""
    app = create_app()

    with app.app_context():
        from sqlalchemy import text

        print("Dropping faq_versions table...")
        FAQVersion.__table__.drop(db.engine, checkfirst=True)
        print("✓ faq_versions table dropped")

        print("Dropping support_tickets table...")
        SupportTicket.__table__.drop(db.engine, checkfirst=True)
        print("✓ support_tickets table dropped")

        # Note: We don't drop columns from existing tables in rollback
        # as it's complex and may cause data loss

        print("\n" + "=" * 60)
        print("Rollback completed!")
        print("=" * 60)
        print("\nTables dropped:")
        print("  - support_tickets")
        print("  - faq_versions")
        print("\nNote: Columns added to faq_entries and chat_memory are not removed in rollback.")


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        print("WARNING: This will drop the newly created tables.")
        if input("Are you sure? (yes/no): ") == 'yes':
            drop_tables()
        else:
            print("Cancelled")
    else:
        create_tables()
