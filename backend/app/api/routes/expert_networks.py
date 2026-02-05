"""Expert Networks API routes."""

import json
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.database import get_database
from app.db.queries import projects, experts, emails, dedupe
from app.services.expert_extraction import ExpertExtractionService
from app.services.expert_commit import ExpertCommitService
from app.services.expert_export import export_experts_to_csv
from app.services.document_context import get_document_context
from app.schemas.expert_extraction import ExtractedExpert

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/expert-networks", tags=["expert-networks"])

# TODO: [SECURITY] Add authentication middleware before production deployment


# Request/Response Models
class CreateProjectRequest(BaseModel):
    name: str
    hypothesisText: str
    networks: Optional[List[str]] = None


class ExtractEmailRequest(BaseModel):
    emailText: str
    network: Optional[str] = None


class CommitExpertsRequest(BaseModel):
    emailId: str
    selectedIndices: List[int]  # Indices of experts to commit


class UpdateExpertRequest(BaseModel):
    updates: dict  # Field updates


class RecommendExpertRequest(BaseModel):
    projectId: str
    include_document_context: bool = False


# ============== Projects ============== #

@router.get("/projects")
async def list_projects():
    """List all projects."""
    db = await get_database()
    project_list = await projects.list_projects(db)
    return {"projects": project_list}


@router.post("/projects")
async def create_project(req: CreateProjectRequest):
    """Create new project."""
    db = await get_database()
    project = await projects.create_project(
        db,
        name=req.name,
        hypothesis_text=req.hypothesisText,
        networks=req.networks
    )
    return project


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details."""
    db = await get_database()
    project = await projects.get_project(db, project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.patch("/projects/{project_id}")
async def update_project(
    project_id: str,
    name: Optional[str] = None,
    hypothesis_text: Optional[str] = None,
    networks: Optional[List[str]] = None
):
    """Update project fields."""
    db = await get_database()
    success = await projects.update_project(
        db,
        project_id,
        name=name,
        hypothesis_text=hypothesis_text,
        networks=networks
    )

    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True}


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete project."""
    db = await get_database()
    success = await projects.delete_project(db, project_id)

    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True}


# ============== Email Extraction & Commit ============== #

@router.post("/projects/{project_id}/extract")
@limiter.limit("10/minute")
async def extract_email(request: Request, project_id: str, req: ExtractEmailRequest):
    """Extract experts from email using AI."""
    db = await get_database()

    # Verify project exists
    project = await projects.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Create email record
        email = await emails.create_email(
            db,
            project_id=project_id,
            raw_text=req.emailText,
            network=req.network
        )

        # Run AI extraction
        extraction_service = ExpertExtractionService()
        result, raw_response, prompt = await extraction_service.extract_experts_from_email(
            email_text=req.emailText,
            project_hypothesis=project["hypothesisText"],
            network_hint=req.network
        )

        # Store extraction result in email
        await emails.update_email_extraction(
            db,
            email["id"],
            extraction_result_json=result.json(),
            extraction_prompt=prompt,
            extraction_response=raw_response
        )

        return {
            "emailId": email["id"],
            "result": result.dict(),
            "extractionNotes": result.extractionNotes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/projects/{project_id}/commit")
async def commit_experts(project_id: str, req: CommitExpertsRequest):
    """Commit selected experts from extraction to tracker."""
    db = await get_database()

    # Get email with extraction result
    email = await emails.get_email(db, req.emailId)
    if not email or email["projectId"] != project_id:
        raise HTTPException(status_code=404, detail="Email not found")

    if not email.get("extractionResultJson"):
        raise HTTPException(
            status_code=400,
            detail="No extraction result found. Please re-extract the email."
        )

    # Parse extraction result
    result_data = json.loads(email["extractionResultJson"])
    all_experts = [ExtractedExpert(**e) for e in result_data["experts"]]

    # Filter selected experts
    selected_experts = [
        all_experts[idx]
        for idx in req.selectedIndices
        if 0 <= idx < len(all_experts)
    ]

    if not selected_experts:
        raise HTTPException(status_code=400, detail="No valid experts selected")

    try:
        # Commit experts
        commit_service = ExpertCommitService()
        result = await commit_service.commit_experts(
            db=db,
            project_id=project_id,
            email_id=req.emailId,
            selected_experts=selected_experts,
            email_network=email.get("network"),
            raw_openai_response=email.get("extractionResponse", ""),
            openai_prompt=email.get("extractionPrompt", "")
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Commit failed: {str(e)}")


# ============== Experts ============== #

@router.get("/projects/{project_id}/experts")
async def list_experts(project_id: str, status: Optional[str] = None):
    """List experts with optional status filter."""
    db = await get_database()
    expert_list = await experts.list_experts(db, project_id, status)
    return {"experts": expert_list}


@router.get("/experts/{expert_id}")
async def get_expert(expert_id: str):
    """Get expert details."""
    db = await get_database()
    expert = await experts.get_expert(db, expert_id)

    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    return expert


@router.patch("/experts/{expert_id}")
async def update_expert(expert_id: str, req: UpdateExpertRequest):
    """Update expert field."""
    db = await get_database()

    # Track user edit
    import secrets
    from datetime import datetime

    for field_name, value in req.updates.items():
        # Get current value
        expert = await experts.get_expert(db, expert_id)
        if not expert:
            raise HTTPException(status_code=404, detail="Expert not found")

        previous_value = expert.get(field_name)

        # Create user edit record
        await db.execute(
            """
            INSERT INTO UserEdit (id, expertId, fieldName, userValueJson, previousValueJson, createdAt)
            VALUES (:id, :expert_id, :field_name, :user_value, :previous_value, :created_at)
            """,
            {
                "id": secrets.token_urlsafe(16),
                "expert_id": expert_id,
                "field_name": field_name,
                "user_value": json.dumps(value),
                "previous_value": json.dumps(previous_value) if previous_value else None,
                "created_at": datetime.utcnow().isoformat()
            }
        )

    # Update expert
    success = await experts.update_expert(db, expert_id, **req.updates)

    if not success:
        raise HTTPException(status_code=404, detail="Expert not found")

    return {"success": True}


@router.delete("/experts/{expert_id}")
async def delete_expert(expert_id: str):
    """Delete expert."""
    db = await get_database()
    success = await experts.delete_expert(db, expert_id)

    if not success:
        raise HTTPException(status_code=404, detail="Expert not found")

    return {"success": True}


@router.get("/experts/{expert_id}/sources")
async def get_expert_sources(expert_id: str):
    """Get all sources for an expert."""
    db = await get_database()
    sources = await experts.get_expert_sources(db, expert_id)
    return {"sources": sources}


@router.post("/experts/{expert_id}/recommend")
@limiter.limit("20/minute")
async def recommend_expert(request: Request, expert_id: str, req: RecommendExpertRequest):
    """Generate AI recommendation for expert.

    When include_document_context is True, uses enhanced scoring with document relevance:
    - Background Fit: 30%
    - Screener Quality: 30%
    - Document Relevance: 25%
    - Red Flags: 15%
    """
    db = await get_database()

    # Get expert
    expert = await experts.get_expert(db, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")

    # Get project
    project = await projects.get_project(db, req.projectId)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get expert bio from sources
    sources = await experts.get_expert_sources(db, expert_id)
    bio = sources[0].get("extractedBio") if sources else None
    screener = sources[0].get("extractedScreener") if sources else None

    try:
        extraction_service = ExpertExtractionService()

        if req.include_document_context:
            # Enhanced screening with document context
            doc_context = get_document_context()

            # Build search query from expert info
            search_terms = []
            if expert.get("canonicalEmployer"):
                search_terms.append(expert["canonicalEmployer"])
            if expert.get("canonicalTitle"):
                search_terms.append(expert["canonicalTitle"])
            if bio:
                search_terms.append(bio[:200])  # First 200 chars of bio

            search_query = " ".join(search_terms) if search_terms else expert["canonicalName"]

            # Search for relevant document chunks
            search_results = doc_context.search(search_query, n_results=10)
            document_chunks = [
                {
                    "text": r.text,
                    "metadata": {
                        "filename": r.filename,
                        "file_id": r.file_id,
                        "chunk_index": r.chunk_index
                    }
                }
                for r in search_results
            ]

            result, raw_response, prompt = await extraction_service.screen_expert_with_documents(
                expert_name=expert["canonicalName"],
                employer=expert.get("canonicalEmployer"),
                title=expert.get("canonicalTitle"),
                bio=bio,
                screener_responses=screener,
                project_hypothesis=project["hypothesisText"],
                document_chunks=document_chunks
            )

            # Update expert with enhanced recommendation
            await experts.update_expert(
                db,
                expert_id,
                aiRecommendation=result.recommendation,
                aiRecommendationRationale=result.rationale,
                aiRecommendationConfidence=result.confidence,
                aiRecommendationRaw=raw_response,
                aiRecommendationPrompt=prompt
            )

            return result.dict()
        else:
            # Standard recommendation without document context
            result, raw_response, prompt = await extraction_service.recommend_expert(
                expert_name=expert["canonicalName"],
                employer=expert.get("canonicalEmployer"),
                title=expert.get("canonicalTitle"),
                bio=bio,
                screener_responses=screener,
                project_hypothesis=project["hypothesisText"]
            )

            # Update expert with recommendation
            await experts.update_expert(
                db,
                expert_id,
                aiRecommendation=result.recommendation,
                aiRecommendationRationale=result.rationale,
                aiRecommendationConfidence=result.confidence,
                aiRecommendationRaw=raw_response,
                aiRecommendationPrompt=prompt
            )

            return result.dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


# ============== Deduplication ============== #

@router.get("/projects/{project_id}/duplicates")
async def get_duplicates(project_id: str, status: Optional[str] = "pending"):
    """Get duplicate candidates for review."""
    db = await get_database()
    candidates = await dedupe.list_dedupe_candidates(db, project_id, status)
    return {"candidates": candidates}


@router.post("/duplicates/{candidate_id}/merge")
async def merge_duplicates(candidate_id: str):
    """Confirm merge of duplicate experts."""
    db = await get_database()

    # Get candidate
    candidate = await dedupe.get_dedupe_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    try:
        # Perform merge
        from app.services.expert_dedupe import ExpertDedupeService
        dedupe_service = ExpertDedupeService()

        await dedupe_service.merge_experts(
            db,
            candidate["expertIdA"],
            candidate["expertIdB"]
        )

        # Update candidate status
        await dedupe.update_dedupe_status(db, candidate_id, "merged")

        return {"success": True}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merge failed: {str(e)}")


@router.post("/duplicates/{candidate_id}/not-same")
async def mark_not_same(candidate_id: str):
    """Mark candidates as different people."""
    db = await get_database()
    success = await dedupe.update_dedupe_status(db, candidate_id, "not_same")

    if not success:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return {"success": True}


# ============== Export ============== #

@router.get("/projects/{project_id}/export")
async def export_csv(project_id: str):
    """Export experts to CSV with audit trail."""
    db = await get_database()

    # Verify project exists
    project = await projects.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Generate CSV
    csv_content = await export_experts_to_csv(db, project_id)

    # Return as file download
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=experts_{project['name']}.csv"
        }
    )
