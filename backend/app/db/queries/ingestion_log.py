"""Ingestion log database queries for change tracking and undo."""

from datetime import datetime
from typing import Optional, List
import databases
import json
import secrets


async def create_ingestion_log(
    db: databases.Database,
    project_id: str,
    email_id: str,
    summary: dict,
    snapshot: Optional[dict] = None
) -> dict:
    """Create an ingestion log entry."""
    log_id = secrets.token_urlsafe(16)
    now = datetime.utcnow()

    query = """
        INSERT INTO IngestionLog (id, projectId, emailId, status, summaryJson, snapshotJson, createdAt)
        VALUES (:id, :project_id, :email_id, :status, :summary, :snapshot, :created_at)
    """

    await db.execute(
        query,
        {
            "id": log_id,
            "project_id": project_id,
            "email_id": email_id,
            "status": "completed",
            "summary": json.dumps(summary),
            "snapshot": json.dumps(snapshot) if snapshot else None,
            "created_at": now.isoformat()
        }
    )

    return {
        "id": log_id,
        "projectId": project_id,
        "emailId": email_id,
        "status": "completed",
        "summary": summary,
        "createdAt": now.isoformat()
    }


async def create_ingestion_log_entry(
    db: databases.Database,
    ingestion_log_id: str,
    action: str,  # 'added', 'updated', 'merged', 'needs_review'
    expert_id: Optional[str] = None,
    expert_name: Optional[str] = None,
    merged_from_expert_id: Optional[str] = None,
    fields_changed: Optional[List[str]] = None,
    previous_values: Optional[dict] = None,
    new_values: Optional[dict] = None
) -> dict:
    """Create a detailed log entry for a single change."""
    entry_id = secrets.token_urlsafe(16)
    now = datetime.utcnow()

    query = """
        INSERT INTO IngestionLogEntry (
            id, ingestionLogId, action, expertId, expertName,
            mergedFromExpertId, fieldsChanged, previousValuesJson, newValuesJson, createdAt
        )
        VALUES (
            :id, :ingestion_log_id, :action, :expert_id, :expert_name,
            :merged_from_expert_id, :fields_changed, :previous_values, :new_values, :created_at
        )
    """

    await db.execute(
        query,
        {
            "id": entry_id,
            "ingestion_log_id": ingestion_log_id,
            "action": action,
            "expert_id": expert_id,
            "expert_name": expert_name,
            "merged_from_expert_id": merged_from_expert_id,
            "fields_changed": json.dumps(fields_changed) if fields_changed else None,
            "previous_values": json.dumps(previous_values) if previous_values else None,
            "new_values": json.dumps(new_values) if new_values else None,
            "created_at": now.isoformat()
        }
    )

    return {
        "id": entry_id,
        "ingestionLogId": ingestion_log_id,
        "action": action,
        "expertId": expert_id,
        "expertName": expert_name,
        "mergedFromExpertId": merged_from_expert_id,
        "fieldsChanged": fields_changed,
        "previousValues": previous_values,
        "newValues": new_values,
        "createdAt": now.isoformat()
    }


async def get_ingestion_log(db: databases.Database, log_id: str) -> Optional[dict]:
    """Get ingestion log by ID with entries."""
    # Get main log
    log_query = "SELECT * FROM IngestionLog WHERE id = :log_id"
    log_row = await db.fetch_one(log_query, {"log_id": log_id})

    if not log_row:
        return None

    # Get entries
    entries_query = """
        SELECT * FROM IngestionLogEntry
        WHERE ingestionLogId = :log_id
        ORDER BY createdAt
    """
    entry_rows = await db.fetch_all(entries_query, {"log_id": log_id})

    entries = []
    for row in entry_rows:
        entries.append({
            "id": row["id"],
            "action": row["action"],
            "expertId": row["expertId"],
            "expertName": row["expertName"],
            "mergedFromExpertId": row["mergedFromExpertId"],
            "fieldsChanged": json.loads(row["fieldsChanged"]) if row["fieldsChanged"] else None,
            "previousValues": json.loads(row["previousValuesJson"]) if row["previousValuesJson"] else None,
            "newValues": json.loads(row["newValuesJson"]) if row["newValuesJson"] else None,
            "createdAt": row["createdAt"]
        })

    return {
        "id": log_row["id"],
        "projectId": log_row["projectId"],
        "emailId": log_row["emailId"],
        "status": log_row["status"],
        "summary": json.loads(log_row["summaryJson"]),
        "snapshot": json.loads(log_row["snapshotJson"]) if log_row["snapshotJson"] else None,
        "entries": entries,
        "createdAt": log_row["createdAt"],
        "undoneAt": log_row["undoneAt"]
    }


async def list_ingestion_logs(
    db: databases.Database,
    project_id: str,
    limit: int = 10
) -> List[dict]:
    """List recent ingestion logs for a project."""
    query = """
        SELECT * FROM IngestionLog
        WHERE projectId = :project_id
        ORDER BY createdAt DESC
        LIMIT :limit
    """
    rows = await db.fetch_all(query, {"project_id": project_id, "limit": limit})

    return [
        {
            "id": row["id"],
            "projectId": row["projectId"],
            "emailId": row["emailId"],
            "status": row["status"],
            "summary": json.loads(row["summaryJson"]),
            "createdAt": row["createdAt"],
            "undoneAt": row["undoneAt"]
        }
        for row in rows
    ]


async def get_latest_ingestion_log(
    db: databases.Database,
    project_id: str
) -> Optional[dict]:
    """Get the most recent ingestion log for a project (includes undone logs for redo)."""
    query = """
        SELECT * FROM IngestionLog
        WHERE projectId = :project_id AND status IN ('completed', 'undone')
        ORDER BY createdAt DESC
        LIMIT 1
    """
    row = await db.fetch_one(query, {"project_id": project_id})

    if not row:
        return None

    return {
        "id": row["id"],
        "projectId": row["projectId"],
        "emailId": row["emailId"],
        "status": row["status"],
        "summary": json.loads(row["summaryJson"]),
        "createdAt": row["createdAt"],
        "undoneAt": row["undoneAt"]
    }


async def mark_ingestion_undone(db: databases.Database, log_id: str) -> bool:
    """Mark an ingestion as undone."""
    query = """
        UPDATE IngestionLog
        SET status = 'undone', undoneAt = :undone_at
        WHERE id = :log_id
    """
    result = await db.execute(
        query,
        {"log_id": log_id, "undone_at": datetime.utcnow().isoformat()}
    )
    return result > 0


async def mark_ingestion_redone(db: databases.Database, log_id: str) -> bool:
    """Mark an ingestion as redone (completed again after being undone)."""
    query = """
        UPDATE IngestionLog
        SET status = 'completed', undoneAt = NULL
        WHERE id = :log_id
    """
    result = await db.execute(
        query,
        {"log_id": log_id}
    )
    return result > 0
