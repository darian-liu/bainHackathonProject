"""Scanned email database queries for tracking ingested Outlook emails."""

from datetime import datetime
from typing import Optional, List
import databases
import secrets


async def is_message_scanned(
    db: databases.Database,
    project_id: str,
    outlook_message_id: str,
) -> bool:
    """Check if a message has already been scanned for a project."""
    query = """
        SELECT id FROM ScannedEmail 
        WHERE project_id = :project_id AND outlook_message_id = :outlook_message_id
        LIMIT 1
    """
    row = await db.fetch_one(query, {
        "project_id": project_id,
        "outlook_message_id": outlook_message_id,
    })
    return row is not None


async def get_scanned_message_ids(
    db: databases.Database,
    project_id: str,
) -> set:
    """Get all scanned message IDs for a project."""
    query = "SELECT outlook_message_id FROM ScannedEmail WHERE project_id = :project_id"
    rows = await db.fetch_all(query, {"project_id": project_id})
    return {row["outlook_message_id"] for row in rows}


async def record_scanned_email(
    db: databases.Database,
    project_id: str,
    outlook_message_id: str,
    email_subject: Optional[str] = None,
    sender: Optional[str] = None,
    received_at: Optional[str] = None,
    ingestion_log_id: Optional[str] = None,
    internet_message_id: Optional[str] = None,
    subject_hash: Optional[str] = None,
    status: str = "processed",
) -> dict:
    """Record that an email has been scanned."""
    now = datetime.utcnow()
    record_id = secrets.token_urlsafe(16)
    
    query = """
        INSERT OR REPLACE INTO ScannedEmail (
            id, project_id, outlook_message_id, email_subject, 
            sender, received_at, ingested_at, ingestion_log_id,
            internet_message_id, subject_hash, status
        ) VALUES (
            :id, :project_id, :outlook_message_id, :email_subject,
            :sender, :received_at, :ingested_at, :ingestion_log_id,
            :internet_message_id, :subject_hash, :status
        )
    """
    
    await db.execute(query, {
        "id": record_id,
        "project_id": project_id,
        "outlook_message_id": outlook_message_id,
        "email_subject": email_subject,
        "sender": sender,
        "received_at": received_at,
        "ingested_at": now.isoformat(),
        "ingestion_log_id": ingestion_log_id,
        "internet_message_id": internet_message_id,
        "subject_hash": subject_hash,
        "status": status,
    })
    
    return {
        "id": record_id,
        "projectId": project_id,
        "outlookMessageId": outlook_message_id,
        "emailSubject": email_subject,
        "sender": sender,
        "receivedAt": received_at,
        "ingestedAt": now.isoformat(),
        "ingestionLogId": ingestion_log_id,
    }


async def list_scanned_emails(
    db: databases.Database,
    project_id: str,
    limit: int = 100,
) -> List[dict]:
    """List recently scanned emails for a project."""
    query = """
        SELECT * FROM ScannedEmail 
        WHERE project_id = :project_id 
        ORDER BY ingested_at DESC 
        LIMIT :limit
    """
    rows = await db.fetch_all(query, {"project_id": project_id, "limit": limit})
    
    return [
        {
            "id": row["id"],
            "projectId": row["project_id"],
            "outlookMessageId": row["outlook_message_id"],
            "emailSubject": row["email_subject"],
            "sender": row["sender"],
            "receivedAt": row["received_at"],
            "ingestedAt": row["ingested_at"],
            "ingestionLogId": row["ingestion_log_id"],
        }
        for row in rows
    ]


async def get_last_scan_time(
    db: databases.Database,
    project_id: str,
) -> Optional[datetime]:
    """Get the timestamp of the most recent scanned email for a project."""
    query = """
        SELECT MAX(received_at) as last_received 
        FROM ScannedEmail 
        WHERE project_id = :project_id
    """
    row = await db.fetch_one(query, {"project_id": project_id})
    
    if row and row["last_received"]:
        return datetime.fromisoformat(row["last_received"])
    
    return None
