"""Project database queries."""

from datetime import datetime
from typing import Optional, List
import databases
import json


async def create_project(
    db: databases.Database,
    name: str,
    hypothesis_text: str,
    networks: Optional[List[str]] = None
) -> dict:
    """Create a new project."""
    import secrets

    project_id = secrets.token_urlsafe(16)
    networks_json = json.dumps(networks) if networks else None
    now = datetime.utcnow()

    query = """
        INSERT INTO Project (id, name, hypothesisText, networks, createdAt, updatedAt)
        VALUES (:id, :name, :hypothesis_text, :networks, :created_at, :updated_at)
    """

    await db.execute(
        query,
        {
            "id": project_id,
            "name": name,
            "hypothesis_text": hypothesis_text,
            "networks": networks_json,
            "created_at": now,
            "updated_at": now
        }
    )

    return {
        "id": project_id,
        "name": name,
        "hypothesisText": hypothesis_text,
        "networks": networks,
        "createdAt": now.isoformat(),
        "updatedAt": now.isoformat()
    }


async def get_project(db: databases.Database, project_id: str) -> Optional[dict]:
    """Get project by ID."""
    query = "SELECT * FROM Project WHERE id = :project_id"
    row = await db.fetch_one(query, {"project_id": project_id})

    if not row:
        return None

    return {
        "id": row["id"],
        "name": row["name"],
        "hypothesisText": row["hypothesisText"],
        "networks": json.loads(row["networks"]) if row["networks"] else None,
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"]
    }


async def list_projects(db: databases.Database) -> List[dict]:
    """List all projects."""
    query = "SELECT * FROM Project ORDER BY createdAt DESC"
    rows = await db.fetch_all(query)

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "hypothesisText": row["hypothesisText"],
            "networks": json.loads(row["networks"]) if row["networks"] else None,
            "createdAt": row["createdAt"],
            "updatedAt": row["updatedAt"]
        }
        for row in rows
    ]


async def update_project(
    db: databases.Database,
    project_id: str,
    name: Optional[str] = None,
    hypothesis_text: Optional[str] = None,
    networks: Optional[List[str]] = None
) -> bool:
    """Update project fields."""
    updates = []
    values = {"project_id": project_id, "updated_at": datetime.utcnow()}

    if name is not None:
        updates.append("name = :name")
        values["name"] = name

    if hypothesis_text is not None:
        updates.append("hypothesisText = :hypothesis_text")
        values["hypothesis_text"] = hypothesis_text

    if networks is not None:
        updates.append("networks = :networks")
        values["networks"] = json.dumps(networks)

    if not updates:
        return False

    updates.append("updatedAt = :updated_at")

    query = f"UPDATE Project SET {', '.join(updates)} WHERE id = :project_id"
    result = await db.execute(query, values)

    return result > 0


async def delete_project(db: databases.Database, project_id: str) -> bool:
    """Delete project and cascade delete all related records."""
    query = "DELETE FROM Project WHERE id = :project_id"
    result = await db.execute(query, {"project_id": project_id})
    return result > 0
