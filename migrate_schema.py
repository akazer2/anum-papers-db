"""Migration script to add new columns to existing database."""

import sqlite3
import sys

def migrate_database(db_path="anum_papers.db"):
    """Add new columns to entries table if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check which columns exist
    cursor.execute("PRAGMA table_info(entries)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = {
        'abstract': 'TEXT',
        'url': 'TEXT',
        'keywords': 'TEXT',
        'subject_area': 'TEXT',
        'citation_count': 'INTEGER',
        'anum_position': 'INTEGER',
        'project_area': 'TEXT'
    }
    
    added = []
    for column, col_type in new_columns.items():
        if column not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE entries ADD COLUMN {column} {col_type}")
                added.append(column)
                print(f"✅ Added column: {column}")
            except sqlite3.OperationalError as e:
                print(f"⚠️  Error adding {column}: {e}")
    
    conn.commit()
    conn.close()
    
    if added:
        print(f"\n✅ Migration complete! Added {len(added)} column(s): {', '.join(added)}")
    else:
        print("\n✅ Database is up to date - all columns already exist")
    
    return len(added) > 0

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "anum_papers.db"
    migrate_database(db_path)

