import sqlite3
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python delete_story.py <story_id>")
        sys.exit(1)
        
    try:
        story_id = int(sys.argv[1])
    except ValueError:
        print("Story ID must be an integer.")
        sys.exit(1)
        
    db_path = "config/library.db"
    if not os.path.exists(db_path):
        # try defaults
        db_path = "library.db"
        if not os.path.exists(db_path):
            print("Database not found in config/library.db or library.db")
            sys.exit(1)
            
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys=ON")
    
    print(f"Starting deletion of story {story_id}...")
    try:
        # Check download_history rows before delete
        cursor.execute("SELECT id FROM chapters WHERE story_id = ?", (story_id,))
        chap_ids = [row[0] for row in cursor.fetchall()]
        print(f"Chapters found in DB for story {story_id}: {len(chap_ids)}")
        
        if chap_ids:
            placeholders = ','.join('?' for _ in chap_ids)
            cursor.execute(f"SELECT id, chapter_id, story_id FROM download_history WHERE chapter_id IN ({placeholders})", chap_ids)
            print(f"Matching download_history rows before delete: {cursor.fetchall()}")
            
        # 1. Delete download_history
        cursor.execute(
            "DELETE FROM download_history WHERE story_id = ? OR chapter_id IN (SELECT id FROM chapters WHERE story_id = ?)",
            (story_id, story_id)
        )
        print(f"Deleted {cursor.rowcount} rows from download_history.")
        
        # Check download_history rows after delete but before committing
        if chap_ids:
            placeholders = ','.join('?' for _ in chap_ids)
            cursor.execute(f"SELECT id, chapter_id, story_id FROM download_history WHERE chapter_id IN ({placeholders})", chap_ids)
            print(f"Matching download_history rows inside transaction: {cursor.fetchall()}")

        # 2. Delete chapters
        cursor.execute(
            "DELETE FROM chapters WHERE story_id = ?",
            (story_id,)
        )
        print(f"Deleted {cursor.rowcount} rows from chapters.")
        
        # 3. Delete stories
        cursor.execute(
            "DELETE FROM stories WHERE id = ?",
            (story_id,)
        )
        print(f"Deleted {cursor.rowcount} rows from stories.")
        
        conn.commit()
        print("Transaction committed successfully. Story deleted.")
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"SQLite error occurred: {e}")
        # Run diagnostics
        print("Running foreign key check...")
        cursor.execute("PRAGMA foreign_key_check")
        print(f"Violations: {cursor.fetchall()}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
