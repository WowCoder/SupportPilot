"""
Add trace and observability fields to rag_retrieval_logs table.

Fields added:
  - trace_json: JSON string of full pipeline trace (node events, decisions)
  - sub_query_count: number of sub-queries generated
  - retry_count: total retries across all sub-queries
  - faithfulness_score: answer faithfulness ratio
"""
import sqlite3
import os
import sys


def migrate():
    """Add trace columns to rag_retrieval_logs table."""
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
    cursor.execute("PRAGMA table_info(rag_retrieval_logs)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f'Existing columns: {columns}')

    new_columns = [
        ('trace_json', 'TEXT', None),
        ('sub_query_count', 'INTEGER', '0'),
        ('retry_count', 'INTEGER', '0'),
        ('faithfulness_score', 'REAL', None),
    ]

    for col_name, col_type, default_val in new_columns:
        if col_name not in columns:
            if default_val is not None:
                sql = (
                    f'ALTER TABLE rag_retrieval_logs ADD COLUMN {col_name} '
                    f'{col_type} DEFAULT {default_val}'
                )
            else:
                sql = f'ALTER TABLE rag_retrieval_logs ADD COLUMN {col_name} {col_type}'
            cursor.execute(sql)
            conn.commit()
            print(f'  ✓ Added {col_name} ({col_type})')
        else:
            print(f'  - {col_name} already exists, skipping')

    conn.close()
    print('Migration complete.')


if __name__ == '__main__':
    migrate()
