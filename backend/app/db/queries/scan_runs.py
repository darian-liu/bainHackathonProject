"""Scan run database queries for tracking auto-scan executions."""

from datetime import datetime
from typing import Optional, List
import databases
import json
import secrets


async def create_scan_run(
    db: databases.Database,
    project_id: str,
    max_emails: int,
) -> dict:
    """Create a new scan run record."""
    scan_run_id = secrets.token_urlsafe(16)
    now = datetime.utcnow()

    query = """
        INSERT INTO ScanRun (
            id, projectId, startedAt, status, maxEmails
        ) VALUES (
            :id, :project_id, :started_at, :status, :max_emails
        )
    """

    await db.execute(
        query,
        {
            "id": scan_run_id,
            "project_id": project_id,
            "started_at": now.isoformat(),
            "status": "running",
            "max_emails": max_emails,
        }
    )

    return {
        "id": scan_run_id,
        "projectId": project_id,
        "startedAt": now.isoformat(),
        "status": "running",
        "maxEmails": max_emails,
    }


async def update_scan_run_progress(
    db: databases.Database,
    scan_run_id: str,
    messages_considered: Optional[int] = None,
    messages_processed: Optional[int] = None,
    messages_skipped: Optional[int] = None,
    messages_failed: Optional[int] = None,
) -> bool:
    """Update scan run progress counters."""
    updates = []
    params = {"scan_run_id": scan_run_id}
    
    if messages_considered is not None:
        updates.append("messagesConsidered = :messages_considered")
        params["messages_considered"] = messages_considered
    
    if messages_processed is not None:
        updates.append("messagesProcessed = :messages_processed")
        params["messages_processed"] = messages_processed
    
    if messages_skipped is not None:
        updates.append("messagesSkipped = :messages_skipped")
        params["messages_skipped"] = messages_skipped
    
    if messages_failed is not None:
        updates.append("messagesFailed = :messages_failed")
        params["messages_failed"] = messages_failed
    
    if not updates:
        return True
    
    query = f"""
        UPDATE ScanRun 
        SET {', '.join(updates)}, updatedAt = :updated_at
        WHERE id = :scan_run_id
    """
    params["updated_at"] = datetime.utcnow().isoformat()
    
    result = await db.execute(query, params)
    return result > 0


async def complete_scan_run(
    db: databases.Database,
    scan_run_id: str,
    status: str,  # "completed" or "failed"
    experts_added: int = 0,
    experts_updated: int = 0,
    experts_merged: int = 0,
    ingestion_log_id: Optional[str] = None,
    error_message: Optional[str] = None,
    error_details: Optional[List[str]] = None,
) -> bool:
    """Mark scan run as completed or failed with final results."""
    now = datetime.utcnow()
    
    query = """
        UPDATE ScanRun 
        SET 
            completedAt = :completed_at,
            status = :status,
            expertsAdded = :experts_added,
            expertsUpdated = :experts_updated,
            expertsMerged = :experts_merged,
            ingestionLogId = :ingestion_log_id,
            errorMessage = :error_message,
            errorDetails = :error_details,
            updatedAt = :updated_at
        WHERE id = :scan_run_id
    """
    
    result = await db.execute(query, {
        "scan_run_id": scan_run_id,
        "completed_at": now.isoformat(),
        "status": status,
        "experts_added": experts_added,
        "experts_updated": experts_updated,
        "experts_merged": experts_merged,
        "ingestion_log_id": ingestion_log_id,
        "error_message": error_message,
        "error_details": json.dumps(error_details) if error_details else None,
        "updated_at": now.isoformat(),
    })
    
    return result > 0


async def get_scan_run(db: databases.Database, scan_run_id: str) -> Optional[dict]:
    """Get scan run by ID."""
    query = "SELECT * FROM ScanRun WHERE id = :scan_run_id"
    row = await db.fetch_one(query, {"scan_run_id": scan_run_id})

    if not row:
        return None

    return {
        "id": row["id"],
        "projectId": row["projectId"],
        "startedAt": row["startedAt"],
        "completedAt": row["completedAt"],
        "status": row["status"],
        "maxEmails": row["maxEmails"],
        "messagesConsidered": row["messagesConsidered"],
        "messagesProcessed": row["messagesProcessed"],
        "messagesSkipped": row["messagesSkipped"],
        "messagesFailed": row["messagesFailed"],
        "expertsAdded": row["expertsAdded"],
        "expertsUpdated": row["expertsUpdated"],
        "expertsMerged": row["expertsMerged"],
        "errorMessage": row["errorMessage"],
        "errorDetails": json.loads(row["errorDetails"]) if row["errorDetails"] else None,
        "ingestionLogId": row["ingestionLogId"],
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"],
    }


async def list_scan_runs(
    db: databases.Database,
    project_id: str,
    limit: int = 10
) -> List[dict]:
    """List recent scan runs for a project."""
    query = """
        SELECT * FROM ScanRun
        WHERE projectId = :project_id
        ORDER BY startedAt DESC
        LIMIT :limit
    """
    rows = await db.fetch_all(query, {"project_id": project_id, "limit": limit})

    return [
        {
            "id": row["id"],
            "projectId": row["projectId"],
            "startedAt": row["startedAt"],
            "completedAt": row["completedAt"],
            "status": row["status"],
            "maxEmails": row["maxEmails"],
            "messagesConsidered": row["messagesConsidered"],
            "messagesProcessed": row["messagesProcessed"],
            "messagesSkipped": row["messagesSkipped"],
            "messagesFailed": row["messagesFailed"],
            "expertsAdded": row["expertsAdded"],
            "expertsUpdated": row["expertsUpdated"],
            "expertsMerged": row["expertsMerged"],
            "errorMessage": row["errorMessage"],
            "errorDetails": json.loads(row["errorDetails"]) if row["errorDetails"] else None,
            "ingestionLogId": row["ingestionLogId"],
            "createdAt": row["createdAt"],
            "updatedAt": row["updatedAt"],
        }
        for row in rows
    ]


async def get_latest_scan_run(
    db: databases.Database,
    project_id: str
) -> Optional[dict]:
    """Get the most recent scan run for a project."""
    query = """
        SELECT * FROM ScanRun
        WHERE projectId = :project_id
        ORDER BY startedAt DESC
        LIMIT 1
    """
    row = await db.fetch_one(query, {"project_id": project_id})

    if not row:
        return None

    return {
        "id": row["id"],
        "projectId": row["projectId"],
        "startedAt": row["startedAt"],
        "completedAt": row["completedAt"],
        "status": row["status"],
        "maxEmails": row["maxEmails"],
        "messagesConsidered": row["messagesConsidered"],
        "messagesProcessed": row["messagesProcessed"],
        "messagesSkipped": row["messagesSkipped"],
        "messagesFailed": row["messagesFailed"],
        "expertsAdded": row["expertsAdded"],
        "expertsUpdated": row["expertsUpdated"],
        "expertsMerged": row["expertsMerged"],
        "errorMessage": row["errorMessage"],
        "errorDetails": json.loads(row["errorDetails"]) if row["errorDetails"] else None,
        "ingestionLogId": row["ingestionLogId"],
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"],
    }
