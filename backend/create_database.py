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
    screenerConfigJson TEXT,
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
    aiScreeningGrade TEXT,
    aiScreeningScore INTEGER,
    aiScreeningRationale TEXT,
    aiScreeningConfidence TEXT,
    aiScreeningMissingInfo TEXT,
    aiScreeningRaw TEXT,
    aiScreeningPrompt TEXT,
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
);

CREATE INDEX IF NOT EXISTS idx_ingestionlog_projectId ON IngestionLog(projectId);
CREATE INDEX IF NOT EXISTS idx_ingestionlog_emailId ON IngestionLog(emailId);

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
);

CREATE INDEX IF NOT EXISTS idx_ingestionlogentry_ingestionLogId ON IngestionLogEntry(ingestionLogId);

CREATE TABLE IF NOT EXISTS OutlookConnection (
    id TEXT PRIMARY KEY,
    user_email TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at TEXT NOT NULL,
    last_connected_at TEXT NOT NULL,
    last_test_at TEXT,
    is_active INTEGER DEFAULT 1,
    allowed_sender_domains TEXT,
    last_sync_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_outlookconnection_is_active ON OutlookConnection(is_active);

CREATE TABLE IF NOT EXISTS ScannedEmail (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    outlook_message_id TEXT NOT NULL,
    email_subject TEXT,
    sender TEXT,
    received_at TEXT,
    ingested_at TEXT NOT NULL,
    ingestion_log_id TEXT,
    scan_run_id TEXT,
    status TEXT DEFAULT 'processed',
    extraction_count INTEGER DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES Project(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scannedemail_project ON ScannedEmail(project_id);
CREATE INDEX IF NOT EXISTS idx_scannedemail_message_id ON ScannedEmail(outlook_message_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scannedemail_unique ON ScannedEmail(project_id, outlook_message_id);

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
