"""ScanRun database queries for tracking auto-scan executions."""

from datetime import datetime
from typing import Optional, List, Dict, Any
import databases
import secrets
import json


async def create_scan_run(
    db: databases.Database,
    project_id: str,
    max_emails: int = 10,
    sender_domains: Optional[str] = None,
    keywords: Optional[str] = None,
) -> dict:
    """Create a new scan run record."""
    scan_run_id = secrets.token_urlsafe(16)
    now = datetime.utcnow().isoformat()
    
    query = """
        INSERT INTO ScanRun (
            id, project_id, started_at, status, max_emails, sender_domains, keywords
        ) VALUES (
            :id, :project_id, :started_at, :status, :max_emails, :sender_domains, :keywords
        )
    """
    
    await db.execute(query, {
        "id": scan_run_id,
        "project_id": project_id,
        "started_at": now,
        "status": "running",
        "max_emails": max_emails,
        "sender_domains": sender_domains,
        "keywords": keywords,
    })
    
    return {
        "id": scan_run_id,
        "projectId": project_id,
        "startedAt": now,
        "status": "running",
        "maxEmails": max_emails,
    }


async def update_scan_run_progress(
    db: databases.Database,
    scan_run_id: str,
    messages_fetched: Optional[int] = None,
    messages_filtered: Optional[int] = None,
    messages_already_scanned: Optional[int] = None,
) -> bool:
    """Update scan run with progress info."""
    updates = []
    values = {"id": scan_run_id}
    
    if messages_fetched is not None:
        updates.append("messages_fetched = :messages_fetched")
        values["messages_fetched"] = messages_fetched
    if messages_filtered is not None:
        updates.append("messages_filtered = :messages_filtered")
        values["messages_filtered"] = messages_filtered
    if messages_already_scanned is not None:
        updates.append("messages_already_scanned = :messages_already_scanned")
        values["messages_already_scanned"] = messages_already_scanned
    
    if not updates:
        return True
    
    query = f"UPDATE ScanRun SET {', '.join(updates)} WHERE id = :id"
    result = await db.execute(query, values)
    return result > 0


async def complete_scan_run(
    db: databases.Database,
    scan_run_id: str,
    messages_processed: int,
    messages_skipped: int,
    messages_failed: int,
    experts_added: int,
    experts_updated: int,
    experts_merged: int,
    added_experts: List[Dict[str, Any]],
    updated_experts: List[Dict[str, Any]],
    skipped_reasons: List[Dict[str, Any]],
    errors: List[str],
    processed_details: List[Dict[str, Any]],
    ingestion_log_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bool:
    """Complete a scan run with final results."""
    now = datetime.utcnow().isoformat()
    status = "completed" if not error_message else "failed"
    
    query = """
        UPDATE ScanRun SET
            completed_at = :completed_at,
            status = :status,
            messages_processed = :messages_processed,
            messages_skipped = :messages_skipped,
            messages_failed = :messages_failed,
            experts_added = :experts_added,
            experts_updated = :experts_updated,
            experts_merged = :experts_merged,
            added_experts_json = :added_experts_json,
            updated_experts_json = :updated_experts_json,
            skipped_reasons_json = :skipped_reasons_json,
            errors_json = :errors_json,
            processed_details_json = :processed_details_json,
            ingestion_log_id = :ingestion_log_id,
            error_message = :error_message
        WHERE id = :id
    """
    
    result = await db.execute(query, {
        "id": scan_run_id,
        "completed_at": now,
        "status": status,
        "messages_processed": messages_processed,
        "messages_skipped": messages_skipped,
        "messages_failed": messages_failed,
        "experts_added": experts_added,
        "experts_updated": experts_updated,
        "experts_merged": experts_merged,
        "added_experts_json": json.dumps(added_experts) if added_experts else None,
        "updated_experts_json": json.dumps(updated_experts) if updated_experts else None,
        "skipped_reasons_json": json.dumps(skipped_reasons) if skipped_reasons else None,
        "errors_json": json.dumps(errors) if errors else None,
        "processed_details_json": json.dumps(processed_details) if processed_details else None,
        "ingestion_log_id": ingestion_log_id,
        "error_message": error_message,
    })
    
    return result > 0


async def get_scan_run(db: databases.Database, scan_run_id: str) -> Optional[dict]:
    """Get a scan run by ID."""
    query = "SELECT * FROM ScanRun WHERE id = :id"
    row = await db.fetch_one(query, {"id": scan_run_id})
    
    if not row:
        return None
    
    return _row_to_dict(row)


async def get_latest_scan_run(db: databases.Database, project_id: str) -> Optional[dict]:
    """Get the most recent scan run for a project."""
    query = """
        SELECT * FROM ScanRun 
        WHERE project_id = :project_id 
        ORDER BY started_at DESC 
        LIMIT 1
    """
    row = await db.fetch_one(query, {"project_id": project_id})
    
    if not row:
        return None
    
    return _row_to_dict(row)


async def list_scan_runs(
    db: databases.Database,
    project_id: str,
    limit: int = 10,
) -> List[dict]:
    """List recent scan runs for a project."""
    query = """
        SELECT * FROM ScanRun 
        WHERE project_id = :project_id 
        ORDER BY started_at DESC 
        LIMIT :limit
    """
    rows = await db.fetch_all(query, {"project_id": project_id, "limit": limit})
    
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row) -> dict:
    """Convert a database row to a dictionary."""
    return {
        "id": row["id"],
        "projectId": row["project_id"],
        "startedAt": row["started_at"],
        "completedAt": row["completed_at"],
        "status": row["status"],
        "maxEmails": row["max_emails"],
        "senderDomains": row["sender_domains"],
        "keywords": row["keywords"],
        "messagesFetched": row["messages_fetched"],
        "messagesFiltered": row["messages_filtered"],
        "messagesAlreadyScanned": row["messages_already_scanned"],
        "messagesProcessed": row["messages_processed"],
        "messagesSkipped": row["messages_skipped"],
        "messagesFailed": row["messages_failed"],
        "expertsAdded": row["experts_added"],
        "expertsUpdated": row["experts_updated"],
        "expertsMerged": row["experts_merged"],
        "addedExperts": json.loads(row["added_experts_json"]) if row["added_experts_json"] else [],
        "updatedExperts": json.loads(row["updated_experts_json"]) if row["updated_experts_json"] else [],
        "skippedReasons": json.loads(row["skipped_reasons_json"]) if row["skipped_reasons_json"] else [],
        "errors": json.loads(row["errors_json"]) if row["errors_json"] else [],
        "processedDetails": json.loads(row["processed_details_json"]) if row["processed_details_json"] else [],
        "ingestionLogId": row["ingestion_log_id"],
        "errorMessage": row["error_message"],
    }
