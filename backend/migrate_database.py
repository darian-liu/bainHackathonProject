"""Database migrations for Expert Networks upgrades.

Run this to add new columns/tables without losing existing data.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "expert_networks.db"


def run_migrations():
    """Run all pending migrations."""
    if not DB_PATH.exists():
        print("Database does not exist. Run create_database.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    print("Running migrations...")

    # Migration 1: Add screenerConfigJson to Project
    try:
        cursor.execute("ALTER TABLE Project ADD COLUMN screenerConfigJson TEXT")
        print("  ✓ Added screenerConfigJson to Project")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  - screenerConfigJson already exists in Project")
        else:
            raise

    # Migration 2: Add Smart Screening fields to Expert
    screening_fields = [
        ("aiScreeningGrade", "TEXT"),  # strong/mixed/weak
        ("aiScreeningScore", "INTEGER"),  # 0-100
        ("aiScreeningRationale", "TEXT"),
        ("aiScreeningConfidence", "TEXT"),  # low/medium/high
        ("aiScreeningMissingInfo", "TEXT"),  # JSON array
        ("aiScreeningRaw", "TEXT"),  # Raw LLM response
        ("aiScreeningPrompt", "TEXT"),  # Prompt used
    ]

    for field_name, field_type in screening_fields:
        try:
            cursor.execute(f"ALTER TABLE Expert ADD COLUMN {field_name} {field_type}")
            print(f"  ✓ Added {field_name} to Expert")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"  - {field_name} already exists in Expert")
            else:
                raise

    # Migration 3: Create IngestionLog table for change tracking & undo
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS IngestionLog (
            id TEXT PRIMARY KEY,
            projectId TEXT NOT NULL,
            emailId TEXT NOT NULL,
            status TEXT DEFAULT 'completed' NOT NULL,
            summaryJson TEXT NOT NULL,
            snapshotJson TEXT,
            createdAt TEXT NOT NULL,
            undoneAt TEXT,
            FOREIGN KEY (projectId) REFERENCES Project(id) ON DELETE CASCADE,
            FOREIGN KEY (emailId) REFERENCES Email(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingestionlog_projectId ON IngestionLog(projectId)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingestionlog_emailId ON IngestionLog(emailId)")
    print("  ✓ Created IngestionLog table")

    # Migration 4: Create IngestionLogEntry for detailed change records
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS IngestionLogEntry (
            id TEXT PRIMARY KEY,
            ingestionLogId TEXT NOT NULL,
            action TEXT NOT NULL,
            expertId TEXT,
            expertName TEXT,
            mergedFromExpertId TEXT,
            fieldsChanged TEXT,
            previousValuesJson TEXT,
            newValuesJson TEXT,
            createdAt TEXT NOT NULL,
            FOREIGN KEY (ingestionLogId) REFERENCES IngestionLog(id) ON DELETE CASCADE,
            FOREIGN KEY (expertId) REFERENCES Expert(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingestionlogentry_ingestionLogId ON IngestionLogEntry(ingestionLogId)")
    print("  ✓ Created IngestionLogEntry table")

    conn.commit()
    conn.close()

    print("\nMigrations completed successfully!")


if __name__ == "__main__":
    run_migrations()
