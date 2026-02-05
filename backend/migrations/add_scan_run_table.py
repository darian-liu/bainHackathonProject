"""Migration to add ScanRun table for tracking auto-scan executions."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "expert_networks.db"

MIGRATION_SQL = """
-- Add new columns to ScannedEmail if they don't exist
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we check first

-- ScanRun tracks each auto-scan execution for authoritative metrics
CREATE TABLE IF NOT EXISTS ScanRun (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT DEFAULT 'running' NOT NULL,
    
    -- Query parameters used
    max_emails INTEGER,
    sender_domains TEXT,
    keywords TEXT,
    
    -- Message counts
    messages_fetched INTEGER DEFAULT 0,
    messages_filtered INTEGER DEFAULT 0,
    messages_already_scanned INTEGER DEFAULT 0,
    messages_processed INTEGER DEFAULT 0,
    messages_skipped INTEGER DEFAULT 0,
    messages_failed INTEGER DEFAULT 0,
    
    -- Expert counts (authoritative)
    experts_added INTEGER DEFAULT 0,
    experts_updated INTEGER DEFAULT 0,
    experts_merged INTEGER DEFAULT 0,
    
    -- Details (JSON)
    added_experts_json TEXT,
    updated_experts_json TEXT,
    skipped_reasons_json TEXT,
    errors_json TEXT,
    processed_details_json TEXT,
    
    -- Linked ingestion log
    ingestion_log_id TEXT,
    
    -- Error info
    error_message TEXT,
    
    FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scanrun_project ON ScanRun(project_id);
CREATE INDEX IF NOT EXISTS idx_scanrun_started ON ScanRun(started_at);
"""


def run_migration():
    """Run the migration to add ScanRun table."""
    if not DB_PATH.exists():
        print(f"Database not found at: {DB_PATH}")
        print("Please run create_database.py first.")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Check if ScanRun table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ScanRun'")
    if cursor.fetchone():
        print("ScanRun table already exists. Migration skipped.")
        conn.close()
        return True
    
    print("Adding ScanRun table...")
    
    try:
        cursor.executescript(MIGRATION_SQL)
        conn.commit()
        print("Migration completed successfully!")
        
        # Also try to add new columns to ScannedEmail
        try:
            cursor.execute("ALTER TABLE ScannedEmail ADD COLUMN scan_run_id TEXT")
            print("Added scan_run_id column to ScannedEmail")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE ScannedEmail ADD COLUMN status TEXT DEFAULT 'processed'")
            print("Added status column to ScannedEmail")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute("ALTER TABLE ScannedEmail ADD COLUMN extraction_count INTEGER DEFAULT 0")
            print("Added extraction_count column to ScannedEmail")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
