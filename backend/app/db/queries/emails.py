"""Email database queries."""

from datetime import datetime
from typing import Optional, List
import databases
import hashlib
import secrets
import json


def compute_content_hash(network: Optional[str], raw_text: str) -> str:
    """Compute SHA256 hash of network + raw text for idempotency."""
    content = f"{network or ''}|{raw_text}"
    return hashlib.sha256(content.encode()).hexdigest()


async def create_email(
    db: databases.Database,
    project_id: str,
    raw_text: str,
    network: Optional[str] = None,
    received_at: Optional[datetime] = None,
    extraction_result_json: Optional[str] = None,
    extraction_prompt: Optional[str] = None,
    extraction_response: Optional[str] = None
) -> dict:
    """Create a new email record."""
    email_id = secrets.token_urlsafe(16)
    content_hash = compute_content_hash(network, raw_text)
    now = datetime.utcnow()

    query = """
        INSERT INTO Email (
            id, projectId, network, rawText, contentHash, receivedAt,
            extractionResultJson, extractionPrompt, extractionResponse, createdAt
        )
        VALUES (
            :id, :project_id, :network, :raw_text, :content_hash, :received_at,
            :extraction_result_json, :extraction_prompt, :extraction_response, :created_at
        )
    """

    try:
        await db.execute(
            query,
            {
                "id": email_id,
                "project_id": project_id,
                "network": network,
                "raw_text": raw_text,
                "content_hash": content_hash,
                "received_at": received_at,
                "extraction_result_json": extraction_result_json,
                "extraction_prompt": extraction_prompt,
                "extraction_response": extraction_response,
                "created_at": now
            }
        )
    except Exception as e:
        # Check if it's a duplicate
        if "UNIQUE constraint failed" in str(e):
            # Return existing email
            existing = await get_email_by_content_hash(db, project_id, content_hash)
            if existing:
                return existing
        raise

    return {
        "id": email_id,
        "projectId": project_id,
        "network": network,
        "contentHash": content_hash,
        "rawText": raw_text,
        "receivedAt": received_at.isoformat() if received_at else None,
        "extractionResultJson": extraction_result_json,
        "createdAt": now.isoformat()
    }


async def get_email(db: databases.Database, email_id: str) -> Optional[dict]:
    """Get email by ID."""
    query = "SELECT * FROM Email WHERE id = :email_id"
    row = await db.fetch_one(query, {"email_id": email_id})

    if not row:
        return None

    result = dict(row)
    # Parse JSON if present
    if result.get("extractionResultJson"):
        result["extractionResult"] = json.loads(result["extractionResultJson"])
    return result


async def get_email_by_content_hash(
    db: databases.Database,
    project_id: str,
    content_hash: str
) -> Optional[dict]:
    """Get email by content hash (for deduplication)."""
    query = """
        SELECT * FROM Email
        WHERE projectId = :project_id AND contentHash = :content_hash
    """
    row = await db.fetch_one(
        query,
        {"project_id": project_id, "content_hash": content_hash}
    )

    if not row:
        return None

    return dict(row)


async def list_emails(db: databases.Database, project_id: str) -> List[dict]:
    """List all emails for a project."""
    query = """
        SELECT * FROM Email
        WHERE projectId = :project_id
        ORDER BY createdAt DESC
    """
    rows = await db.fetch_all(query, {"project_id": project_id})
    return [dict(row) for row in rows]


async def update_email_extraction(
    db: databases.Database,
    email_id: str,
    extraction_result_json: str,
    extraction_prompt: Optional[str] = None,
    extraction_response: Optional[str] = None
) -> bool:
    """Update email with extraction results."""
    query = """
        UPDATE Email
        SET extractionResultJson = :extraction_result_json,
            extractionPrompt = :extraction_prompt,
            extractionResponse = :extraction_response
        WHERE id = :email_id
    """

    result = await db.execute(
        query,
        {
            "email_id": email_id,
            "extraction_result_json": extraction_result_json,
            "extraction_prompt": extraction_prompt,
            "extraction_response": extraction_response
        }
    )

    return result > 0
