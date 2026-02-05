"""Deduplication database queries."""

from datetime import datetime
from typing import Optional, List
import databases
import secrets


async def create_dedupe_candidate(
    db: databases.Database,
    project_id: str,
    expert_id_a: str,
    expert_id_b: str,
    score: float,
    match_type: str
) -> dict:
    """Create a dedupe candidate record."""
    candidate_id = secrets.token_urlsafe(16)
    now = datetime.utcnow()

    # Ensure consistent ordering (smaller ID first)
    if expert_id_a > expert_id_b:
        expert_id_a, expert_id_b = expert_id_b, expert_id_a

    query = """
        INSERT INTO DedupeCandidate (
            id, projectId, expertIdA, expertIdB, score, matchType, status, createdAt
        )
        VALUES (
            :id, :project_id, :expert_id_a, :expert_id_b, :score, :match_type, :status, :created_at
        )
    """

    try:
        await db.execute(
            query,
            {
                "id": candidate_id,
                "project_id": project_id,
                "expert_id_a": expert_id_a,
                "expert_id_b": expert_id_b,
                "score": score,
                "match_type": match_type,
                "status": "pending",
                "created_at": now
            }
        )
    except Exception as e:
        # Ignore if already exists
        if "UNIQUE constraint failed" in str(e):
            return None
        raise

    return {
        "id": candidate_id,
        "projectId": project_id,
        "expertIdA": expert_id_a,
        "expertIdB": expert_id_b,
        "score": score,
        "matchType": match_type,
        "status": "pending",
        "createdAt": now.isoformat()
    }


async def get_dedupe_candidate(
    db: databases.Database,
    candidate_id: str
) -> Optional[dict]:
    """Get dedupe candidate by ID."""
    query = "SELECT * FROM DedupeCandidate WHERE id = :candidate_id"
    row = await db.fetch_one(query, {"candidate_id": candidate_id})

    if not row:
        return None

    return dict(row)


async def list_dedupe_candidates(
    db: databases.Database,
    project_id: str,
    status: Optional[str] = None
) -> List[dict]:
    """List dedupe candidates for a project."""
    if status:
        query = """
            SELECT dc.*,
                   ea.canonicalName as expertAName,
                   ea.canonicalEmployer as expertAEmployer,
                   eb.canonicalName as expertBName,
                   eb.canonicalEmployer as expertBEmployer
            FROM DedupeCandidate dc
            JOIN Expert ea ON dc.expertIdA = ea.id
            JOIN Expert eb ON dc.expertIdB = eb.id
            WHERE dc.projectId = :project_id AND dc.status = :status
            ORDER BY dc.score DESC, dc.createdAt DESC
        """
        rows = await db.fetch_all(
            query,
            {"project_id": project_id, "status": status}
        )
    else:
        query = """
            SELECT dc.*,
                   ea.canonicalName as expertAName,
                   ea.canonicalEmployer as expertAEmployer,
                   eb.canonicalName as expertBName,
                   eb.canonicalEmployer as expertBEmployer
            FROM DedupeCandidate dc
            JOIN Expert ea ON dc.expertIdA = ea.id
            JOIN Expert eb ON dc.expertIdB = eb.id
            WHERE dc.projectId = :project_id
            ORDER BY dc.score DESC, dc.createdAt DESC
        """
        rows = await db.fetch_all(query, {"project_id": project_id})

    return [dict(row) for row in rows]


async def update_dedupe_status(
    db: databases.Database,
    candidate_id: str,
    status: str
) -> bool:
    """Update dedupe candidate status."""
    query = """
        UPDATE DedupeCandidate
        SET status = :status, resolvedAt = :resolved_at
        WHERE id = :candidate_id
    """

    result = await db.execute(
        query,
        {
            "candidate_id": candidate_id,
            "status": status,
            "resolved_at": datetime.utcnow()
        }
    )

    return result > 0


async def check_existing_candidate(
    db: databases.Database,
    project_id: str,
    expert_id_a: str,
    expert_id_b: str
) -> Optional[dict]:
    """Check if a dedupe candidate already exists for this pair."""
    # Ensure consistent ordering
    if expert_id_a > expert_id_b:
        expert_id_a, expert_id_b = expert_id_b, expert_id_a

    query = """
        SELECT * FROM DedupeCandidate
        WHERE projectId = :project_id
        AND expertIdA = :expert_id_a
        AND expertIdB = :expert_id_b
    """

    row = await db.fetch_one(
        query,
        {
            "project_id": project_id,
            "expert_id_a": expert_id_a,
            "expert_id_b": expert_id_b
        }
    )

    if not row:
        return None

    return dict(row)


async def create_expert_source(
    db: databases.Database,
    expert_id: str,
    email_id: str,
    extracted_json: str,
    network: Optional[str] = None,
    extracted_name: Optional[str] = None,
    extracted_employer: Optional[str] = None,
    extracted_title: Optional[str] = None,
    extracted_bio: Optional[str] = None,
    extracted_screener: Optional[str] = None,
    extracted_availability: Optional[str] = None,
    extracted_status_cue: Optional[str] = None,
    openai_response: Optional[str] = None,
    openai_prompt: Optional[str] = None
) -> dict:
    """Create an expert source record linking expert to email."""
    source_id = secrets.token_urlsafe(16)
    now = datetime.utcnow()

    query = """
        INSERT INTO ExpertSource (
            id, expertId, emailId, network, extractedJson,
            extractedName, extractedEmployer, extractedTitle, extractedBio,
            extractedScreener, extractedAvailability, extractedStatusCue,
            openaiResponse, openaiPrompt, createdAt
        )
        VALUES (
            :id, :expert_id, :email_id, :network, :extracted_json,
            :extracted_name, :extracted_employer, :extracted_title, :extracted_bio,
            :extracted_screener, :extracted_availability, :extracted_status_cue,
            :openai_response, :openai_prompt, :created_at
        )
    """

    await db.execute(
        query,
        {
            "id": source_id,
            "expert_id": expert_id,
            "email_id": email_id,
            "network": network,
            "extracted_json": extracted_json,
            "extracted_name": extracted_name,
            "extracted_employer": extracted_employer,
            "extracted_title": extracted_title,
            "extracted_bio": extracted_bio,
            "extracted_screener": extracted_screener,
            "extracted_availability": extracted_availability,
            "extracted_status_cue": extracted_status_cue,
            "openai_response": openai_response,
            "openai_prompt": openai_prompt,
            "created_at": now
        }
    )

    return {
        "id": source_id,
        "expertId": expert_id,
        "emailId": email_id,
        "network": network,
        "createdAt": now.isoformat()
    }
