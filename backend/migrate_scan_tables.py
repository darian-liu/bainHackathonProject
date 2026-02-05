#!/usr/bin/env python3
"""
Database migration script for auto-scan reliability fixes.

This script adds the ScanRun table and updates the ScannedEmail table
to support robust auto-scan tracking and deduplication.

Run this script after updating the Prisma schema to create the new tables.
"""

import asyncio
import sqlite3
from pathlib import Path

DATABASE_PATH = "backend/expert_networks.db"

async def migrate_database():
    """Apply database migrations for scan reliability fixes."""
    
    # Check if database exists
    db_path = Path(DATABASE_PATH)
    if not db_path.exists():
        print(f"Database not found at {DATABASE_PATH}")
        print("Please run create_database.py first to create the initial database.")
        return
    
    print("Starting database migration for auto-scan reliability fixes...")
    
    # Connect to SQLite database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if ScanRun table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='ScanRun'
        """)
        
        if cursor.fetchone():
            print("✓ ScanRun table already exists")
        else:
            print("Creating ScanRun table...")
            cursor.execute("""
                CREATE TABLE ScanRun (
                    id TEXT PRIMARY KEY,
                    projectId TEXT NOT NULL,
                    startedAt TEXT NOT NULL DEFAULT (datetime('now')),
                    completedAt TEXT,
                    status TEXT NOT NULL DEFAULT 'running',
                    maxEmails INTEGER NOT NULL,
                    messagesConsidered INTEGER NOT NULL DEFAULT 0,
                    messagesProcessed INTEGER NOT NULL DEFAULT 0,
                    messagesSkipped INTEGER NOT NULL DEFAULT 0,
                    messagesFailed INTEGER NOT NULL DEFAULT 0,
                    expertsAdded INTEGER NOT NULL DEFAULT 0,
                    expertsUpdated INTEGER NOT NULL DEFAULT 0,
                    expertsMerged INTEGER NOT NULL DEFAULT 0,
                    errorMessage TEXT,
                    errorDetails TEXT,
                    ingestionLogId TEXT,
                    createdAt TEXT NOT NULL DEFAULT (datetime('now')),
                    updatedAt TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (projectId) REFERENCES Project(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for ScanRun table
            cursor.execute("CREATE INDEX idx_scanrun_project ON ScanRun(projectId)")
            cursor.execute("CREATE INDEX idx_scanrun_status ON ScanRun(status)")
            cursor.execute("CREATE INDEX idx_scanrun_started ON ScanRun(startedAt)")
            
            print("✓ ScanRun table created successfully")
        
        # Check if ScannedEmail table needs updates
        cursor.execute("PRAGMA table_info(ScannedEmail)")
        columns = [column[1] for column in cursor.fetchall()]
        
        missing_columns = []
        if 'internet_message_id' not in columns:
            missing_columns.append('internet_message_id')
        if 'subject_hash' not in columns:
            missing_columns.append('subject_hash')
        if 'status' not in columns:
            missing_columns.append('status')
        
        if missing_columns:
            print(f"Adding missing columns to ScannedEmail table: {missing_columns}")
            
            for column in missing_columns:
                if column == 'internet_message_id':
                    cursor.execute("ALTER TABLE ScannedEmail ADD COLUMN internet_message_id TEXT")
                elif column == 'subject_hash':
                    cursor.execute("ALTER TABLE ScannedEmail ADD COLUMN subject_hash TEXT")
                elif column == 'status':
                    cursor.execute("ALTER TABLE ScannedEmail ADD COLUMN status TEXT DEFAULT 'processed'")
            
            print("✓ ScannedEmail table updated successfully")
        else:
            print("✓ ScannedEmail table already has all required columns")
        
        # Commit all changes
        conn.commit()
        print("✓ Database migration completed successfully")
        
        # Verify tables exist and have correct structure
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('ScanRun', 'ScannedEmail')
            ORDER BY name
        """)
        tables = cursor.fetchall()
        print(f"✓ Verified tables exist: {[table[0] for table in tables]}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main migration function."""
    print("Auto-Scan Reliability Database Migration")
    print("=" * 50)
    
    try:
        asyncio.run(migrate_database())
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Test the auto-scan functionality")
        print("2. Check that scan metrics are now accurate")
        print("3. Verify that duplicate emails are properly handled")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nPlease check the error above and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
