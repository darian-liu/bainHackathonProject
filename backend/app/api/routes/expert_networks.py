"""Expert Networks API routes."""

import asyncio
import json
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db.database import get_database
from app.db.queries import projects, experts, emails, dedupe, ingestion_log
from app.services.expert_extraction import ExpertExtractionService
from app.services.expert_commit import ExpertCommitService
from app.services.expert_export import export_experts_to_csv
from app.services.document_context import get_document_context
from app.schemas.expert_extraction import ExtractedExpert

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/expert-networks", tags=["expert-networks"])

# TODO: [SECURITY] Add authentication middleware before production deployment


# Request/Response Models
class ScreenerQuestion(BaseModel):
    id: str
    order: int
    text: str
    idealAnswer: Optional[str] = None
    rubricNotes: Optional[str] = None
    redFlags: Optional[str] = None


class ScreenerConfig(BaseModel):
    questions: List[ScreenerQuestion] = []
    autoScreen: bool = False  # If True, automatically screen experts after ingestion


class CreateProjectRequest(BaseModel):
    name: str
    hypothesisText: str
    networks: Optional[List[str]] = None
    screenerConfig: Optional[ScreenerConfig] = None


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


class UpdateScreenerConfigRequest(BaseModel):
    screenerConfig: ScreenerConfig


class AutoIngestRequest(BaseModel):
    emailText: str
    network: Optional[str] = None
    autoMergeThreshold: float = 0.85  # Score above which to auto-merge


class AutoScanInboxRequest(BaseModel):
    maxEmails: int = 50  # Maximum number of emails to scan


class ScreenExpertRequest(BaseModel):
    projectId: str


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
    screener_config_dict = req.screenerConfig.model_dump() if req.screenerConfig else None
    project = await projects.create_project(
        db,
        name=req.name,
        hypothesis_text=req.hypothesisText,
        networks=req.networks,
        screener_config=screener_config_dict
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


@router.put("/projects/{project_id}/screener-config")
async def update_screener_config(project_id: str, req: UpdateScreenerConfigRequest):
    """Update project screener configuration."""
    db = await get_database()
    
    # Verify project exists
    project = await projects.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    success = await projects.update_project(
        db,
        project_id,
        screener_config=req.screenerConfig.model_dump()
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update screener config")
    
    # Return updated project
    updated_project = await projects.get_project(db, project_id)
    return updated_project


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
            extraction_result_json=result.model_dump_json(),
            extraction_prompt=prompt,
            extraction_response=raw_response
        )

        return {
            "emailId": email["id"],
            "result": result.model_dump(),
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


@router.post("/projects/{project_id}/auto-ingest")
@limiter.limit("10/minute")
async def auto_ingest(request: Request, project_id: str, req: AutoIngestRequest):
    """
    Auto-ingest: Extract, commit, and merge in one step.
    
    This is the preferred flow:
    1. Extract experts from email
    2. Auto-commit all extracted experts
    3. Auto-merge duplicates above threshold
    4. Return change summary with undo capability
    """
    from app.services.auto_ingestion import AutoIngestionService
    
    db = await get_database()
    
    # Verify project exists
    project = await projects.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        service = AutoIngestionService()
        result = await service.auto_ingest(
            db=db,
            project_id=project_id,
            email_text=req.emailText,
            network=req.network,
            project_hypothesis=project["hypothesisText"],
            screener_config=project.get("screenerConfig"),
            auto_merge_threshold=req.autoMergeThreshold
        )
        
        return result
        
    except Exception as e:
        import traceback
        print(f"Auto-ingest error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auto-ingest failed: {str(e)}")


@router.post("/projects/{project_id}/auto-scan-inbox")
@limiter.limit("5/minute")
async def auto_scan_inbox(request: Request, project_id: str, req: AutoScanInboxRequest = AutoScanInboxRequest()):
    """
    Auto-scan Outlook inbox for expert network emails and ingest them.
    
    Scans recent emails, filters by sender domain and keywords,
    and feeds qualifying emails into the auto-ingestion pipeline.
    """
    from app.services.outlook_scanning import outlook_scanning_service
    
    db = await get_database()
    
    # Verify project exists
    project = await projects.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        result = await outlook_scanning_service.scan_inbox(
            db=db,
            project_id=project_id,
            max_emails=req.maxEmails,
        )
        
        return result
        
    except Exception as e:
        import traceback
        print(f"Auto-scan inbox error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Auto-scan failed: {str(e)}")


# NOTE: Undo/Redo endpoints REMOVED - they were fundamentally broken
# Users should use explicit delete instead (multi-select delete in UI)


@router.get("/projects/{project_id}/ingestion-logs")
async def list_ingestion_logs_route(project_id: str, limit: int = 10):
    """Get recent ingestion logs for a project."""
    db = await get_database()
    logs = await ingestion_log.list_ingestion_logs(db, project_id, limit)
    return {"logs": logs}


@router.get("/projects/{project_id}/scan-runs/latest")
async def get_latest_scan_run_route(project_id: str):
    """Get the most recent scan run for a project (authoritative scan metrics)."""
    from app.db.queries import scan_runs
    
    db = await get_database()
    
    try:
        scan_run = await scan_runs.get_latest_scan_run(db, project_id)
        return {"scanRun": scan_run}
    except Exception as e:
        # Table may not exist yet
        return {"scanRun": None, "error": str(e)}


@router.get("/projects/{project_id}/scan-runs")
async def list_scan_runs_route(project_id: str, limit: int = 10):
    """List recent scan runs for a project."""
    from app.db.queries import scan_runs
    
    db = await get_database()
    
    try:
        runs = await scan_runs.list_scan_runs(db, project_id, limit)
        return {"scanRuns": runs}
    except Exception as e:
        # Table may not exist yet
        return {"scanRuns": [], "error": str(e)}


@router.get("/projects/{project_id}/ingestion-logs/latest")
async def get_latest_ingestion_log_route(project_id: str):
    """Get the most recent ingestion log."""
    db = await get_database()
    log = await ingestion_log.get_latest_ingestion_log(db, project_id)
    if not log:
        return {"log": None}
    
    # Get full log with entries
    full_log = await ingestion_log.get_ingestion_log(db, log["id"])
    return {"log": full_log}


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


@router.get("/experts/{expert_id}/details")
async def get_expert_details(expert_id: str):
    """
    Get expert with full details including sources, provenance, and user edits.
    
    This endpoint returns all information needed for the expert detail panel,
    including which email each field value came from.
    """
    db = await get_database()
    expert = await experts.get_expert_with_full_details(db, expert_id)

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


@router.post("/projects/{project_id}/experts/bulk-delete")
async def bulk_delete_experts(project_id: str, request: Request):
    """Delete multiple experts at once."""
    db = await get_database()
    
    body = await request.json()
    expert_ids = body.get("expertIds", [])
    
    if not expert_ids:
        raise HTTPException(status_code=400, detail="No expert IDs provided")
    
    deleted = []
    failed = []
    
    for expert_id in expert_ids:
        try:
            success = await experts.delete_expert(db, expert_id)
            if success:
                deleted.append(expert_id)
            else:
                failed.append({"id": expert_id, "reason": "Not found"})
        except Exception as e:
            failed.append({"id": expert_id, "reason": str(e)})
    
    return {
        "success": True,
        "deleted": deleted,
        "deletedCount": len(deleted),
        "failed": failed,
        "failedCount": len(failed),
    }


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

            return result.model_dump()
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

            return result.model_dump()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")


@router.post("/experts/{expert_id}/screen")
@limiter.limit("20/minute")
async def screen_expert(request: Request, expert_id: str, req: ScreenExpertRequest):
    """
    Generate Smart Fit Assessment for expert.
    
    Evaluates expert against project needs using all available information:
    - Expert background (employer, title, bio)
    - Project hypothesis
    - Screener rubric and responses (if available)
    """
    db = await get_database()
    
    # Get expert
    expert = await experts.get_expert(db, expert_id)
    if not expert:
        raise HTTPException(status_code=404, detail="Expert not found")
    
    # Get project with screener config and hypothesis
    project = await projects.get_project(db, req.projectId)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    screener_config = project.get("screenerConfig")
    # Note: screener_config is now optional - we can assess based on background alone
    
    # Get expert sources (for bio and screener responses)
    sources = await experts.get_expert_sources(db, expert_id)
    screener_responses = sources[0].get("extractedScreener") if sources else None
    expert_bio = sources[0].get("extractedBio") if sources else None
    
    try:
        # Generate Smart Fit Assessment
        extraction_service = ExpertExtractionService()
        result, raw_response, prompt = await extraction_service.screen_expert(
            expert_name=expert["canonicalName"],
            expert_employer=expert.get("canonicalEmployer"),
            expert_title=expert.get("canonicalTitle"),
            expert_bio=expert_bio,
            screener_responses=screener_responses,
            screener_config=screener_config,
            project_hypothesis=project["hypothesisText"]
        )
        
        # Update expert with screening result
        await experts.update_expert(
            db,
            expert_id,
            aiScreeningGrade=result.grade,
            aiScreeningScore=result.score,
            aiScreeningRationale=result.rationale,
            aiScreeningConfidence=result.confidence,
            aiScreeningMissingInfo=json.dumps(result.missingInfo) if result.missingInfo else None,
            aiScreeningRaw=raw_response,
            aiScreeningPrompt=prompt
        )
        
        return result.model_dump()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening failed: {str(e)}")


class ScreenAllResponse(BaseModel):
    screened: int
    failed: int
    skipped: int
    results: List[dict]


@router.post("/projects/{project_id}/screen-all")
@limiter.limit("5/minute")
async def screen_all_experts(request: Request, project_id: str, force: bool = False):
    """
    Screen all experts in a project using Smart Fit Assessment.
    
    Args:
        project_id: Project ID
        force: If True, re-screen experts even if they already have screening results
    
    Returns:
        Summary of screening results
    """
    db = await get_database()
    
    # Get project
    project = await projects.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    screener_config = project.get("screenerConfig")
    project_hypothesis = project["hypothesisText"]
    
    # Get all experts in project
    all_experts = await experts.list_experts(db, project_id)
    
    # Filter to unscreened experts (unless force=True)
    if force:
        experts_to_screen = all_experts
    else:
        experts_to_screen = [e for e in all_experts if not e.get("aiScreeningGrade")]
    
    if not experts_to_screen:
        return ScreenAllResponse(
            screened=0, 
            failed=0, 
            skipped=len(all_experts),
            results=[]
        )
    
    extraction_service = ExpertExtractionService()

    # Use semaphore to limit concurrent LLM calls (avoid rate limits)
    semaphore = asyncio.Semaphore(5)

    async def screen_one_expert(expert: dict) -> dict:
        """Screen a single expert with rate limiting."""
        async with semaphore:
            try:
                # Get expert sources for bio and screener responses
                sources = await experts.get_expert_sources(db, expert["id"])
                screener_responses = sources[0].get("extractedScreener") if sources else None
                expert_bio = sources[0].get("extractedBio") if sources else None

                # Run screening
                result, raw_response, prompt = await extraction_service.screen_expert(
                    expert_name=expert["canonicalName"],
                    expert_employer=expert.get("canonicalEmployer"),
                    expert_title=expert.get("canonicalTitle"),
                    expert_bio=expert_bio,
                    screener_responses=screener_responses,
                    screener_config=screener_config,
                    project_hypothesis=project_hypothesis
                )

                # Update expert with screening result
                await experts.update_expert(
                    db,
                    expert["id"],
                    aiScreeningGrade=result.grade,
                    aiScreeningScore=result.score,
                    aiScreeningRationale=result.rationale,
                    aiScreeningConfidence=result.confidence,
                    aiScreeningMissingInfo=json.dumps(result.missingInfo) if result.missingInfo else None,
                    aiScreeningRaw=raw_response,
                    aiScreeningPrompt=prompt
                )

                return {
                    "expertId": expert["id"],
                    "expertName": expert["canonicalName"],
                    "grade": result.grade,
                    "score": result.score,
                    "success": True
                }

            except Exception as e:
                return {
                    "expertId": expert["id"],
                    "expertName": expert["canonicalName"],
                    "success": False,
                    "error": str(e)
                }

    # Process all experts in parallel (with semaphore limiting concurrency)
    results = await asyncio.gather(*[screen_one_expert(e) for e in experts_to_screen])

    # Count successes and failures
    screened = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    skipped = len(all_experts) - len(experts_to_screen)
    
    return ScreenAllResponse(
        screened=screened,
        failed=failed,
        skipped=skipped,
        results=results
    )


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
