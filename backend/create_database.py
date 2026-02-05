"""Create Expert Networks SQLite database from schema."""

import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent / "expert_networks.db"

# SQL schema converted from Prisma
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS Project (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    hypothesisText TEXT NOT NULL,
    networks TEXT,
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Email (
    id TEXT PRIMARY KEY,
    projectId TEXT NOT NULL,
    network TEXT,
    networkInferenceConfidence TEXT,
    receivedAt TEXT,
    rawText TEXT NOT NULL,
    contentHash TEXT NOT NULL,
    extractionResultJson TEXT,
    extractionPrompt TEXT,
    extractionResponse TEXT,
    createdAt TEXT NOT NULL,
    FOREIGN KEY (projectId) REFERENCES Project(id) ON DELETE CASCADE,
    UNIQUE (projectId, contentHash)
);

CREATE INDEX IF NOT EXISTS idx_email_projectId ON Email(projectId);

CREATE TABLE IF NOT EXISTS Expert (
    id TEXT PRIMARY KEY,
    projectId TEXT NOT NULL,
    canonicalName TEXT NOT NULL,
    canonicalEmployer TEXT,
    canonicalTitle TEXT,
    status TEXT DEFAULT 'recommended' NOT NULL,
    statusUpdatedAt TEXT NOT NULL,
    conflictStatus TEXT,
    conflictId TEXT,
    interviewDate TEXT,
    leadInterviewer TEXT,
    interviewLength REAL,
    hypothesisNotes TEXT,
    hypothesisMatch TEXT,
    aiRecommendation TEXT,
    aiRecommendationRationale TEXT,
    aiRecommendationConfidence TEXT,
    aiRecommendationRaw TEXT,
    aiRecommendationPrompt TEXT,
    createdAt TEXT NOT NULL,
    updatedAt TEXT NOT NULL,
    FOREIGN KEY (projectId) REFERENCES Project(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expert_projectId ON Expert(projectId);
CREATE INDEX IF NOT EXISTS idx_expert_canonicalName ON Expert(canonicalName);

CREATE TABLE IF NOT EXISTS ExpertSource (
    id TEXT PRIMARY KEY,
    expertId TEXT NOT NULL,
    emailId TEXT NOT NULL,
    network TEXT,
    extractedJson TEXT NOT NULL,
    extractedName TEXT,
    extractedEmployer TEXT,
    extractedTitle TEXT,
    extractedBio TEXT,
    extractedScreener TEXT,
    extractedAvailability TEXT,
    extractedStatusCue TEXT,
    openaiResponse TEXT,
    openaiPrompt TEXT,
    createdAt TEXT NOT NULL,
    FOREIGN KEY (expertId) REFERENCES Expert(id) ON DELETE CASCADE,
    FOREIGN KEY (emailId) REFERENCES Email(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_expertsource_expertId ON ExpertSource(expertId);
CREATE INDEX IF NOT EXISTS idx_expertsource_emailId ON ExpertSource(emailId);

CREATE TABLE IF NOT EXISTS FieldProvenance (
    id TEXT PRIMARY KEY,
    expertSourceId TEXT NOT NULL,
    fieldName TEXT NOT NULL,
    excerptText TEXT NOT NULL,
    charStart INTEGER,
    charEnd INTEGER,
    confidence TEXT,
    FOREIGN KEY (expertSourceId) REFERENCES ExpertSource(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fieldprovenance_expertSourceId ON FieldProvenance(expertSourceId);

CREATE TABLE IF NOT EXISTS DedupeCandidate (
    id TEXT PRIMARY KEY,
    projectId TEXT NOT NULL,
    expertIdA TEXT NOT NULL,
    expertIdB TEXT NOT NULL,
    score REAL NOT NULL,
    matchType TEXT NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL,
    createdAt TEXT NOT NULL,
    resolvedAt TEXT,
    FOREIGN KEY (projectId) REFERENCES Project(id) ON DELETE CASCADE,
    FOREIGN KEY (expertIdA) REFERENCES Expert(id) ON DELETE CASCADE,
    FOREIGN KEY (expertIdB) REFERENCES Expert(id) ON DELETE CASCADE,
    UNIQUE (projectId, expertIdA, expertIdB)
);

CREATE INDEX IF NOT EXISTS idx_dedupecandidate_projectId ON DedupeCandidate(projectId);
CREATE INDEX IF NOT EXISTS idx_dedupecandidate_status ON DedupeCandidate(status);

CREATE TABLE IF NOT EXISTS UserEdit (
    id TEXT PRIMARY KEY,
    expertId TEXT NOT NULL,
    fieldName TEXT NOT NULL,
    userValueJson TEXT NOT NULL,
    previousValueJson TEXT,
    createdAt TEXT NOT NULL,
    FOREIGN KEY (expertId) REFERENCES Expert(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_useredit_expertId ON UserEdit(expertId);

CREATE TABLE IF NOT EXISTS PendingUpdate (
    id TEXT PRIMARY KEY,
    expertId TEXT NOT NULL,
    fieldName TEXT NOT NULL,
    proposedValueJson TEXT NOT NULL,
    currentValueJson TEXT,
    sourceEmailId TEXT NOT NULL,
    status TEXT DEFAULT 'pending' NOT NULL,
    createdAt TEXT NOT NULL,
    resolvedAt TEXT,
    FOREIGN KEY (expertId) REFERENCES Expert(id) ON DELETE CASCADE,
    FOREIGN KEY (sourceEmailId) REFERENCES Email(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_pendingupdate_expertId ON PendingUpdate(expertId);
CREATE INDEX IF NOT EXISTS idx_pendingupdate_status ON PendingUpdate(status);
"""


def create_database():
    """Create database with schema."""
    if DB_PATH.exists():
        print(f"Database already exists at: {DB_PATH}")
        response = input("Do you want to recreate it? (y/N): ")
        if response.lower() != 'y':
            print("Skipping database creation.")
            return

        DB_PATH.unlink()
        print("Deleted existing database.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Execute schema
    cursor.executescript(SCHEMA_SQL)

    conn.commit()
    conn.close()

    print(f"Database created successfully at: {DB_PATH}")


if __name__ == "__main__":
    create_database()
