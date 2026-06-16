"""
Add sync_progress field to faq_entries table
"""
import sqlite3
import os

def migrate():
    """Add sync_progress column to faq_entries"""
    # Use the support_pilot.db file
    db_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'support_pilot.db')
    db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        print(f'Database not found at {db_path}')
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(faq_entries)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'sync_progress' not in columns:
        cursor.execute('''
            ALTER TABLE faq_entries ADD COLUMN sync_progress INTEGER DEFAULT 0
        ''')
        conn.commit()
        print('Added sync_progress column to faq_entries')
    else:
        print('sync_progress column already exists')

    if 'sync_error' not in columns:
        cursor.execute('''
            ALTER TABLE faq_entries ADD COLUMN sync_error TEXT
        ''')
        conn.commit()
        print('Added sync_error column to faq_entries')
    else:
        print('sync_error column already exists')

    conn.close()

if __name__ == '__main__':
    migrate()
