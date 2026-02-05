"""Service for committing extracted experts to the database."""

import json
from typing import List, Dict
import databases

from app.db.queries.experts import create_expert
from app.db.queries.dedupe import create_expert_source, create_dedupe_candidate, check_existing_candidate
from app.schemas.expert_extraction import ExtractedExpert
from app.services.expert_dedupe import ExpertDedupeService


def map_status_cue_to_status(status_cue: str | None) -> str:
    """Map status cue from extraction to expert status."""
    if not status_cue:
        return "recommended"

    mapping = {
        "available": "recommended",
        "declined": "declined",
        "conflict": "conflict",
        "not_a_fit": "screened_out",
        "no_longer_available": "declined",
        "pending": "awaiting_screeners",
        "interested": "recommended",
        "unknown": "recommended",
    }

    return mapping.get(status_cue, "recommended")


class ExpertCommitService:
    """Service for committing extracted experts to database."""

    def __init__(self):
        self.dedupe_service = ExpertDedupeService()

    async def commit_experts(
        self,
        db: databases.Database,
        project_id: str,
        email_id: str,
        selected_experts: List[ExtractedExpert],
        email_network: str | None,
        raw_openai_response: str,
        openai_prompt: str
    ) -> Dict:
        """
        Commit selected experts from extraction to database.

        1. For each expert, create Expert record
        2. Create ExpertSource linking expert to email
        3. Store FieldProvenance for each field
        4. Run deduplication check
        5. Create DedupeCandidate records for matches

        Returns dict with created expert IDs.
        """
        created_expert_ids = []

        for extracted in selected_experts:
            # Create expert record
            expert = await create_expert(
                db=db,
                project_id=project_id,
                canonical_name=extracted.fullName,
                canonical_employer=extracted.employer,
                canonical_title=extracted.title,
                status=map_status_cue_to_status(extracted.statusCue)
            )

            # Set conflict status if present
            if extracted.conflictStatus:
                await db.execute(
                    "UPDATE Expert SET conflictStatus = :status, conflictId = :id WHERE id = :expert_id",
                    {
                        "status": extracted.conflictStatus,
                        "id": extracted.conflictId,
                        "expert_id": expert["id"]
                    }
                )

            # Create expert source
            expert_source = await create_expert_source(
                db=db,
                expert_id=expert["id"],
                email_id=email_id,
                network=email_network,
                extracted_json=json.dumps(extracted.dict()),
                extracted_name=extracted.fullName,
                extracted_employer=extracted.employer,
                extracted_title=extracted.title,
                extracted_bio="\n".join(extracted.relevanceBullets) if extracted.relevanceBullets else None,
                extracted_screener=json.dumps([r.dict() for r in extracted.screenerResponses]) if extracted.screenerResponses else None,
                extracted_availability=", ".join(extracted.availabilityWindows) if extracted.availabilityWindows else None,
                extracted_status_cue=extracted.statusCue,
                openai_response=raw_openai_response,
                openai_prompt=openai_prompt
            )

            # Create field provenance records
            provenance_records = []

            if extracted.fullNameProvenance:
                provenance_records.append({
                    "expertSourceId": expert_source["id"],
                    "fieldName": "fullName",
                    "excerptText": extracted.fullNameProvenance.excerptText,
                    "charStart": extracted.fullNameProvenance.charStart,
                    "charEnd": extracted.fullNameProvenance.charEnd,
                    "confidence": extracted.fullNameProvenance.confidence
                })

            if extracted.employerProvenance:
                provenance_records.append({
                    "expertSourceId": expert_source["id"],
                    "fieldName": "employer",
                    "excerptText": extracted.employerProvenance.excerptText,
                    "charStart": extracted.employerProvenance.charStart,
                    "charEnd": extracted.employerProvenance.charEnd,
                    "confidence": extracted.employerProvenance.confidence
                })

            if extracted.titleProvenance:
                provenance_records.append({
                    "expertSourceId": expert_source["id"],
                    "fieldName": "title",
                    "excerptText": extracted.titleProvenance.excerptText,
                    "charStart": extracted.titleProvenance.charStart,
                    "charEnd": extracted.titleProvenance.charEnd,
                    "confidence": extracted.titleProvenance.confidence
                })

            if extracted.relevanceBulletsProvenance:
                provenance_records.append({
                    "expertSourceId": expert_source["id"],
                    "fieldName": "relevanceBullets",
                    "excerptText": extracted.relevanceBulletsProvenance.excerptText,
                    "charStart": extracted.relevanceBulletsProvenance.charStart,
                    "charEnd": extracted.relevanceBulletsProvenance.charEnd,
                    "confidence": extracted.relevanceBulletsProvenance.confidence
                })

            # Insert provenance records
            for record in provenance_records:
                import secrets
                await db.execute(
                    """
                    INSERT INTO FieldProvenance (
                        id, expertSourceId, fieldName, excerptText,
                        charStart, charEnd, confidence
                    )
                    VALUES (
                        :id, :expertSourceId, :fieldName, :excerptText,
                        :charStart, :charEnd, :confidence
                    )
                    """,
                    {
                        "id": secrets.token_urlsafe(16),
                        **record
                    }
                )

            created_expert_ids.append(expert["id"])

        # Run deduplication check for all experts in project
        all_experts_rows = await db.fetch_all(
            "SELECT * FROM Expert WHERE projectId = :project_id",
            {"project_id": project_id}
        )
        all_experts = [dict(row) for row in all_experts_rows]

        # Check each newly created expert against all existing experts
        for new_expert_id in created_expert_ids:
            new_expert = next(e for e in all_experts if e["id"] == new_expert_id)
            other_experts = [e for e in all_experts if e["id"] != new_expert_id]

            matches = await self.dedupe_service.find_duplicate_candidates(
                new_expert,
                other_experts
            )

            # Create dedupe candidate records
            for match in matches:
                # Check if already exists
                existing = await check_existing_candidate(
                    db,
                    project_id,
                    match.expert_id_a,
                    match.expert_id_b
                )

                if not existing:
                    await create_dedupe_candidate(
                        db,
                        project_id,
                        match.expert_id_a,
                        match.expert_id_b,
                        match.score,
                        match.match_type
                    )

        return {
            "success": True,
            "expertsCreated": len(created_expert_ids),
            "expertIds": created_expert_ids
        }
