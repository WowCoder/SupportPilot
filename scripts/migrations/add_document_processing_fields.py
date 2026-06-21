"""
Add document processing metadata fields to document table.

Fields added:
  - mode: 'auto' or 'manual'
  - strategy: chunking strategy used
  - chunk_size: configured chunk size
  - chunk_overlap: configured overlap
  - chunks_count: number of chunks indexed
  - status: pending/processing/completed/failed
  - error_message: error details if failed
"""
import sqlite3
import os
import sys


def migrate():
    """Add processing metadata columns to document table."""
    # Try possible db paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, '..', '..')
    candidates = [
        os.path.join(project_root, 'instance', 'app.db'),
        os.path.join(os.getcwd(), 'instance', 'app.db'),
    ]

    db_path = None
    for path in candidates:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print(f'Database not found. Checked: {candidates}')
        sys.exit(1)

    print(f'Using database: {db_path}')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(document)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f'Existing columns: {columns}')

    new_columns = [
        ('mode', 'TEXT', "'auto'"),
        ('strategy', 'TEXT', "'auto'"),
        ('chunk_size', 'INTEGER', None),
        ('chunk_overlap', 'INTEGER', None),
        ('chunks_count', 'INTEGER', '0'),
        ('status', 'TEXT', "'completed'"),
        ('error_message', 'TEXT', None),
    ]

    for col_name, col_type, default_val in new_columns:
        if col_name not in columns:
            if default_val:
                sql = (
                    f'ALTER TABLE document ADD COLUMN {col_name} '
                    f'{col_type} DEFAULT {default_val}'
                )
            else:
                sql = f'ALTER TABLE document ADD COLUMN {col_name} {col_type}'
            cursor.execute(sql)
            conn.commit()
            print(f'  ✓ Added {col_name} ({col_type})')
        else:
            print(f'  - {col_name} already exists, skipping')

    conn.close()
    print('Migration complete.')


if __name__ == '__main__':
    migrate()
