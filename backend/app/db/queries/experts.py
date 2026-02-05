"""Expert database queries."""

from datetime import datetime
from typing import Optional, List
import databases
import secrets


async def create_expert(
    db: databases.Database,
    project_id: str,
    canonical_name: str,
    canonical_employer: Optional[str] = None,
    canonical_title: Optional[str] = None,
    status: str = "recommended"
) -> dict:
    """Create a new expert."""
    expert_id = secrets.token_urlsafe(16)
    now = datetime.utcnow()

    query = """
        INSERT INTO Expert (
            id, projectId, canonicalName, canonicalEmployer, canonicalTitle,
            status, statusUpdatedAt, createdAt, updatedAt
        )
        VALUES (
            :id, :project_id, :canonical_name, :canonical_employer, :canonical_title,
            :status, :status_updated_at, :created_at, :updated_at
        )
    """

    await db.execute(
        query,
        {
            "id": expert_id,
            "project_id": project_id,
            "canonical_name": canonical_name,
            "canonical_employer": canonical_employer,
            "canonical_title": canonical_title,
            "status": status,
            "status_updated_at": now,
            "created_at": now,
            "updated_at": now
        }
    )

    return {
        "id": expert_id,
        "projectId": project_id,
        "canonicalName": canonical_name,
        "canonicalEmployer": canonical_employer,
        "canonicalTitle": canonical_title,
        "status": status,
        "statusUpdatedAt": now.isoformat(),
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat()
    }


async def get_expert(db: databases.Database, expert_id: str) -> Optional[dict]:
    """Get expert by ID."""
    query = "SELECT * FROM Expert WHERE id = :expert_id"
    row = await db.fetch_one(query, {"expert_id": expert_id})

    if not row:
        return None

    return dict(row)


async def list_experts(
    db: databases.Database,
    project_id: str,
    status: Optional[str] = None
) -> List[dict]:
    """List experts for a project with optional status filter."""
    if status:
        query = """
            SELECT * FROM Expert
            WHERE projectId = :project_id AND status = :status
            ORDER BY createdAt DESC
        """
        rows = await db.fetch_all(query, {"project_id": project_id, "status": status})
    else:
        query = """
            SELECT * FROM Expert
            WHERE projectId = :project_id
            ORDER BY createdAt DESC
        """
        rows = await db.fetch_all(query, {"project_id": project_id})

    return [dict(row) for row in rows]


async def update_expert(
    db: databases.Database,
    expert_id: str,
    **fields
) -> bool:
    """Update expert fields dynamically."""
    if not fields:
        return False

    # Always update updatedAt
    fields["updatedAt"] = datetime.utcnow()

    # Update statusUpdatedAt if status is being changed
    if "status" in fields:
        fields["statusUpdatedAt"] = datetime.utcnow()

    # Build dynamic SQL
    updates = []
    values = {"expert_id": expert_id}

    for field_name, value in fields.items():
        updates.append(f"{field_name} = :{field_name}")
        values[field_name] = value

    query = f"UPDATE Expert SET {', '.join(updates)} WHERE id = :expert_id"
    result = await db.execute(query, values)

    return result > 0


async def delete_expert(db: databases.Database, expert_id: str) -> bool:
    """Delete expert."""
    query = "DELETE FROM Expert WHERE id = :expert_id"
    result = await db.execute(query, {"expert_id": expert_id})
    return result > 0


async def find_experts_by_name(
    db: databases.Database,
    project_id: str,
    name: str
) -> List[dict]:
    """Find experts by name (case-insensitive partial match)."""
    query = """
        SELECT * FROM Expert
        WHERE projectId = :project_id
        AND LOWER(canonicalName) LIKE LOWER(:name_pattern)
        ORDER BY canonicalName
    """
    rows = await db.fetch_all(
        query,
        {"project_id": project_id, "name_pattern": f"%{name}%"}
    )

    return [dict(row) for row in rows]


async def get_expert_sources(
    db: databases.Database,
    expert_id: str
) -> List[dict]:
    """Get all sources for an expert."""
    query = """
        SELECT es.*, e.emailId, e.network, e.rawText
        FROM ExpertSource es
        JOIN Email e ON es.emailId = e.id
        WHERE es.expertId = :expert_id
        ORDER BY es.createdAt DESC
    """
    rows = await db.fetch_all(query, {"expert_id": expert_id})
    return [dict(row) for row in rows]
