"""Auto-ingestion service for streamlined expert ingestion.

This service handles:
1. Extract experts from email
2. Auto-commit all extracted experts
3. Auto-merge duplicates above threshold
4. Create change summary
5. Support undo operations
"""

import json
from typing import List, Optional, Tuple
from datetime import datetime
import databases

from app.db.queries import projects, experts, emails, dedupe, ingestion_log
from app.services.expert_extraction import ExpertExtractionService
from app.services.expert_dedupe import ExpertDedupeService, normalize_name, string_similarity
from app.services.change_detection import (
    values_are_equal,
    is_meaningful_value,
    availability_changed,
    screener_responses_changed,
    format_changed_field,
)
from app.schemas.expert_extraction import ExtractedExpert


class AutoIngestionService:
    """Service for streamlined auto-ingestion workflow."""

    def __init__(self):
        self.extraction_service = ExpertExtractionService()
        self.dedupe_service = ExpertDedupeService()

    async def auto_ingest(
        self,
        db: databases.Database,
        project_id: str,
        email_text: str,
        network: Optional[str],
        project_hypothesis: str,
        screener_config: Optional[dict],
        auto_merge_threshold: float = 0.85,
        skip_log: bool = False
    ) -> dict:
        """
        Perform complete auto-ingestion: extract, commit, dedupe, and log.
        
        Args:
            skip_log: If True, skip creating ingestion log (caller will create unified log)
        
        Returns:
            dict with:
            - ingestionLogId: ID for undo operations (None if skip_log=True)
            - summary: What changed (added, updated, merged, needsReview)
            - experts: List of affected experts
        """
        # Track changes for summary
        changes = {
            "added": [],      # New experts created
            "updated": [],    # Existing experts updated
            "merged": [],     # Experts auto-merged
            "needsReview": [] # Low-confidence duplicates
        }
        
        # Step 1: Create email record
        email = await emails.create_email(
            db,
            project_id=project_id,
            raw_text=email_text,
            network=network
        )
        
        # Step 2: Run AI extraction
        result, raw_response, prompt = await self.extraction_service.extract_experts_from_email(
            email_text=email_text,
            project_hypothesis=project_hypothesis,
            network_hint=network
        )
        
        # Store extraction result
        await emails.update_email_extraction(
            db,
            email["id"],
            extraction_result_json=result.model_dump_json(),
            extraction_prompt=prompt,
            extraction_response=raw_response
        )
        
        # Step 3: Auto-commit all experts
        created_experts = []
        for extracted in result.experts:
            # Check for existing expert with same name (potential update)
            existing = await self._find_matching_expert(db, project_id, extracted)
            
            if existing:
                # Update existing expert
                update_result = await self._update_existing_expert(
                    db, existing, extracted, email["id"], network, raw_response, prompt
                )
                if update_result["updated_fields"]:
                    changes["updated"].append({
                        "expertId": existing["id"],
                        "expertName": existing["canonicalName"],
                        "fieldsUpdated": update_result["updated_fields"],
                        "previousValues": update_result["previous_values"],
                        "newValues": update_result["new_values"]
                    })
            else:
                # Create new expert
                expert = await self._create_expert(
                    db, project_id, extracted, email["id"], network, raw_response, prompt
                )
                created_experts.append(expert)
                changes["added"].append({
                    "expertId": expert["id"],
                    "expertName": expert["canonicalName"]
                })
        
        # Step 4: Find duplicates among newly created experts
        # Get all existing experts for comparison
        all_experts = await experts.list_experts(db, project_id)
        
        for expert in created_experts:
            # Get existing experts (excluding the one we're checking)
            existing_experts = [e for e in all_experts if e["id"] != expert["id"]]
            
            candidates = await self.dedupe_service.find_duplicate_candidates(
                expert, existing_experts
            )
            
            for candidate in candidates:
                if candidate.score >= auto_merge_threshold:
                    # Auto-merge high-confidence duplicates
                    try:
                        await self.dedupe_service.merge_experts(
                            db,
                            candidate.expert_id_a,
                            candidate.expert_id_b
                        )
                        
                        changes["merged"].append({
                            "keptExpertId": candidate.expert_id_a,
                            "mergedExpertId": candidate.expert_id_b,
                            "score": candidate.score,
                            "matchType": candidate.match_type
                        })
                    except Exception as e:
                        # If merge fails, mark for review
                        changes["needsReview"].append({
                            "expertIdA": candidate.expert_id_a,
                            "expertIdB": candidate.expert_id_b,
                            "score": candidate.score,
                            "reason": f"Auto-merge failed: {str(e)}"
                        })
                else:
                    # Low-confidence duplicates need review
                    changes["needsReview"].append({
                        "expertIdA": candidate.expert_id_a,
                        "expertIdB": candidate.expert_id_b,
                        "score": candidate.score,
                        "reason": "Below auto-merge threshold"
                    })
        
        # Step 5: Smart Screening is now run on-demand, not during ingestion
        # This significantly speeds up the ingestion process
        # Users can trigger screening from the tracker page after configuring their rubric
        
        # Step 6: Determine if this is a no-op (duplicate/repeated content)
        is_no_op = (
            len(changes["added"]) == 0 and
            len(changes["updated"]) == 0 and
            len(changes["merged"]) == 0 and
            len(changes["needsReview"]) == 0
        )
        
        # Build extraction notes with no-op message if applicable
        extraction_notes = list(result.extractionNotes) if result.extractionNotes else []
        
        if is_no_op and len(result.experts) > 0:
            extraction_notes.insert(0, 
                f"No changes detected — the {len(result.experts)} expert(s) found in this email "
                "match existing records with no new information."
            )
            if any("thread" in (note or "").lower() or "duplicate" in (note or "").lower() 
                   for note in (result.extractionNotes or [])):
                extraction_notes.append(
                    "This email appears to contain quoted/repeated content from a previous thread."
                )
        
        # Step 7: Build summary
        summary = {
            "addedCount": len(changes["added"]),
            "updatedCount": len(changes["updated"]),
            "mergedCount": len(changes["merged"]),
            "needsReviewCount": len(changes["needsReview"]),
            "extractedCount": len(result.experts),
            "network": result.inferredNetwork,
            "extractionNotes": extraction_notes if extraction_notes else None,
            "isNoOp": is_no_op
        }
        
        # Create snapshot for undo (expert IDs created)
        snapshot = {
            "createdExpertIds": [e["expertId"] for e in changes["added"]],
            "mergedPairs": changes["merged"],
            "updatedExperts": changes["updated"]
        }
        
        # If skip_log is True, caller will create unified log
        if skip_log:
            return {
                "ingestionLogId": None,
                "emailId": email["id"],
                "summary": summary,
                "changes": changes,
                "snapshot": snapshot
            }
        
        # Create ingestion log
        log = await ingestion_log.create_ingestion_log(
            db,
            project_id=project_id,
            email_id=email["id"],
            summary=summary,
            snapshot=snapshot
        )
        
        # Create detailed log entries
        for added in changes["added"]:
            await ingestion_log.create_ingestion_log_entry(
                db,
                ingestion_log_id=log["id"],
                action="added",
                expert_id=added["expertId"],
                expert_name=added["expertName"]
            )
        
        for updated in changes["updated"]:
            await ingestion_log.create_ingestion_log_entry(
                db,
                ingestion_log_id=log["id"],
                action="updated",
                expert_id=updated["expertId"],
                expert_name=updated["expertName"],
                fields_changed=updated.get("fieldsUpdated"),
                previous_values=updated.get("previousValues"),
                new_values=updated.get("newValues")
            )
        
        for merged in changes["merged"]:
            await ingestion_log.create_ingestion_log_entry(
                db,
                ingestion_log_id=log["id"],
                action="merged",
                expert_id=merged["keptExpertId"],
                merged_from_expert_id=merged["mergedExpertId"]
            )
        
        for review in changes["needsReview"]:
            await ingestion_log.create_ingestion_log_entry(
                db,
                ingestion_log_id=log["id"],
                action="needs_review",
                expert_id=review.get("expertIdA"),
                new_values={"expertIdB": review.get("expertIdB"), "score": review.get("score"), "reason": review.get("reason")}
            )
        
        return {
            "ingestionLogId": log["id"],
            "emailId": email["id"],
            "summary": summary,
            "changes": changes
        }

    async def _find_matching_expert(
        self,
        db: databases.Database,
        project_id: str,
        extracted: ExtractedExpert
    ) -> Optional[dict]:
        """Find existing expert that matches the extracted one."""
        # Normalize name for comparison
        name = normalize_name(extracted.fullName)
        
        # Search by name
        matches = await experts.find_experts_by_name(db, project_id, extracted.fullName)
        
        for match in matches:
            match_name = normalize_name(match["canonicalName"])
            if match_name == name:
                return match
            # Also check similarity
            if string_similarity(name, match_name) > 0.9:
                return match
        
        return None

    async def _create_expert(
        self,
        db: databases.Database,
        project_id: str,
        extracted: ExtractedExpert,
        email_id: str,
        network: Optional[str],
        raw_response: str,
        prompt: str
    ) -> dict:
        """Create a new expert from extracted data."""
        import secrets
        
        # Create expert record
        expert = await experts.create_expert(
            db,
            project_id=project_id,
            canonical_name=extracted.fullName,
            canonical_employer=extracted.employer,
            canonical_title=extracted.title,
            status="recommended"
        )
        
        # Update with conflict status if present
        if extracted.conflictStatus:
            await experts.update_expert(
                db,
                expert["id"],
                conflictStatus=extracted.conflictStatus,
                conflictId=extracted.conflictId
            )
        
        # Create expert source
        await self._create_expert_source(
            db, expert["id"], email_id, extracted, network, raw_response, prompt
        )
        
        return expert

    async def _update_existing_expert(
        self,
        db: databases.Database,
        existing: dict,
        extracted: ExtractedExpert,
        email_id: str,
        network: Optional[str],
        raw_response: str,
        prompt: str
    ) -> dict:
        """
        Update existing expert with new information.
        
        IMPORTANT: Only returns fields that ACTUALLY changed.
        Uses strict, conservative change detection to ensure truthful summaries.
        
        Field handling:
        - Global fields (employer, title) update the canonical record
        - Network-specific fields (availability, screenerResponses) are stored per-source
        - User edits are never overwritten
        - No change is reported if values are semantically equal
        
        Returns a dict with:
        - updated_fields: List of field names that changed
        - previous_values: Dict of previous values for changed fields
        - new_values: Dict of new values for changed fields
        """
        updated_fields = []
        updates = {}
        previous_values = {}
        new_values = {}
        
        # Check for user edits to avoid overwriting
        user_edits = await self._get_user_edited_fields(db, existing["id"])
        
        # === GLOBAL FIELDS (update canonical record) ===
        # Use strict comparison - only update if there's a REAL change
        
        # Employer: Only update if new value is meaningful AND different
        if is_meaningful_value(extracted.employer):
            if not values_are_equal(extracted.employer, existing.get("canonicalEmployer")):
                if "canonicalEmployer" not in user_edits:
                    prev_val = existing.get("canonicalEmployer")
                    updates["canonicalEmployer"] = extracted.employer
                    updated_fields.append(format_changed_field("canonicalEmployer"))
                    previous_values["employer"] = prev_val
                    new_values["employer"] = extracted.employer
        
        # Title: Only update if new value is meaningful AND different
        if is_meaningful_value(extracted.title):
            if not values_are_equal(extracted.title, existing.get("canonicalTitle")):
                if "canonicalTitle" not in user_edits:
                    prev_val = existing.get("canonicalTitle")
                    updates["canonicalTitle"] = extracted.title
                    updated_fields.append(format_changed_field("canonicalTitle"))
                    previous_values["title"] = prev_val
                    new_values["title"] = extracted.title
        
        # === CONFLICT STATUS ===
        # Only update if there's a meaningful change
        if is_meaningful_value(extracted.conflictStatus):
            if not values_are_equal(extracted.conflictStatus, existing.get("conflictStatus")):
                if "conflictStatus" not in user_edits:
                    prev_val = existing.get("conflictStatus")
                    updates["conflictStatus"] = extracted.conflictStatus
                    updated_fields.append(format_changed_field("conflictStatus"))
                    previous_values["conflictStatus"] = prev_val
                    new_values["conflictStatus"] = extracted.conflictStatus
        
        if is_meaningful_value(extracted.conflictId):
            if not values_are_equal(extracted.conflictId, existing.get("conflictId")):
                if "conflictId" not in user_edits:
                    prev_val = existing.get("conflictId")
                    updates["conflictId"] = extracted.conflictId
                    updated_fields.append(format_changed_field("conflictId"))
                    previous_values["conflictId"] = prev_val
                    new_values["conflictId"] = extracted.conflictId
        
        # === STATUS CUE ===
        if extracted.statusCue and extracted.statusCue != "unknown":
            status_mapping = {
                "available": "recommended",
                "interested": "recommended",
                "pending": "pending",
                "declined": "declined",
                "conflict": "declined",
                "not_a_fit": "declined",
                "no_longer_available": "declined"
            }
            new_status = status_mapping.get(extracted.statusCue)
            if new_status and "status" not in user_edits:
                current_status = existing.get("status", "recommended")
                if new_status != current_status:
                    updates["status"] = new_status
                    updated_fields.append(format_changed_field("status"))
                    previous_values["status"] = current_status
                    new_values["status"] = new_status
        
        # Apply updates if any
        if updates:
            await experts.update_expert(db, existing["id"], **updates)
        
        # === NETWORK-SPECIFIC DATA (stored per source) ===
        # Get existing sources to compare availability and screener responses
        existing_sources = await experts.get_expert_sources(db, existing["id"])
        
        # Find the most recent source for this network (if any)
        latest_source = None
        for source in existing_sources:
            if source.get("network") == network:
                if latest_source is None or source.get("createdAt", "") > latest_source.get("createdAt", ""):
                    latest_source = source
        
        # Check if availability actually changed
        existing_availability = latest_source.get("extractedAvailability") if latest_source else None
        if availability_changed(existing_availability, extracted.availabilityWindows):
            # Only report as update if new availability is meaningful
            if extracted.availabilityWindows and any(is_meaningful_value(a) for a in extracted.availabilityWindows):
                updated_fields.append(format_changed_field("availability", network))
        
        # Check if screener responses actually changed
        existing_screener = latest_source.get("extractedScreener") if latest_source else None
        if screener_responses_changed(existing_screener, extracted.screenerResponses):
            # Only report as update if new responses are meaningful
            if extracted.screenerResponses and len(extracted.screenerResponses) > 0:
                updated_fields.append(format_changed_field("screenerResponses", network))
        
        # Always add new source to preserve provenance (but don't count as update)
        await self._create_expert_source(
            db, existing["id"], email_id, extracted, network, raw_response, prompt
        )
        
        return {
            "updated_fields": updated_fields,
            "previous_values": previous_values if previous_values else None,
            "new_values": new_values if new_values else None
        }

    async def _get_user_edited_fields(self, db: databases.Database, expert_id: str) -> set:
        """Get set of field names that user has edited."""
        query = "SELECT DISTINCT fieldName FROM UserEdit WHERE expertId = :expert_id"
        rows = await db.fetch_all(query, {"expert_id": expert_id})
        return {row["fieldName"] for row in rows}

    async def _create_expert_source(
        self,
        db: databases.Database,
        expert_id: str,
        email_id: str,
        extracted: ExtractedExpert,
        network: Optional[str],
        raw_response: str,
        prompt: str
    ):
        """Create expert source record with provenance."""
        import secrets
        
        source_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        
        # Build extracted fields
        relevance_bio = "\n".join(extracted.relevanceBullets) if extracted.relevanceBullets else None
        screener_text = json.dumps([r.model_dump() for r in extracted.screenerResponses]) if extracted.screenerResponses else None
        availability_text = ", ".join(extracted.availabilityWindows) if extracted.availabilityWindows else None
        
        await db.execute(
            """
            INSERT INTO ExpertSource (
                id, expertId, emailId, network, extractedJson,
                extractedName, extractedEmployer, extractedTitle,
                extractedBio, extractedScreener, extractedAvailability, extractedStatusCue,
                openaiResponse, openaiPrompt, createdAt
            )
            VALUES (
                :id, :expert_id, :email_id, :network, :extracted_json,
                :extracted_name, :extracted_employer, :extracted_title,
                :extracted_bio, :extracted_screener, :extracted_availability, :extracted_status_cue,
                :openai_response, :openai_prompt, :created_at
            )
            """,
            {
                "id": source_id,
                "expert_id": expert_id,
                "email_id": email_id,
                "network": network,
                "extracted_json": extracted.model_dump_json(),
                "extracted_name": extracted.fullName,
                "extracted_employer": extracted.employer,
                "extracted_title": extracted.title,
                "extracted_bio": relevance_bio,
                "extracted_screener": screener_text,
                "extracted_availability": availability_text,
                "extracted_status_cue": extracted.statusCue,
                "openai_response": raw_response,
                "openai_prompt": prompt,
                "created_at": now.isoformat()
            }
        )
        
        # Create field provenance records
        await self._create_provenance_records(db, source_id, extracted)

    async def _create_provenance_records(
        self,
        db: databases.Database,
        source_id: str,
        extracted: ExtractedExpert
    ):
        """Create field provenance records for auditing."""
        import secrets
        
        provenance_fields = [
            ("fullName", extracted.fullNameProvenance),
            ("employer", extracted.employerProvenance),
            ("title", extracted.titleProvenance),
            ("relevanceBullets", extracted.relevanceBulletsProvenance),
            ("screenerResponses", extracted.screenerResponsesProvenance),
            ("conflictStatus", extracted.conflictProvenance),
            ("availability", extracted.availabilityProvenance),
            ("statusCue", extracted.statusCueProvenance),
        ]
        
        for field_name, provenance in provenance_fields:
            if provenance:
                await db.execute(
                    """
                    INSERT INTO FieldProvenance (id, expertSourceId, fieldName, excerptText, confidence)
                    VALUES (:id, :source_id, :field_name, :excerpt_text, :confidence)
                    """,
                    {
                        "id": secrets.token_urlsafe(16),
                        "source_id": source_id,
                        "field_name": field_name,
                        "excerpt_text": provenance.excerptText,
                        "confidence": provenance.confidence
                    }
                )

    async def _run_screening(
        self,
        db: databases.Database,
        expert_id: str,
        screener_config: dict | None,
        project_hypothesis: str
    ):
        """Run smart screening for an expert."""
        try:
            # Get expert sources for bio and screener responses
            sources = await experts.get_expert_sources(db, expert_id)
            screener_responses = sources[0].get("extractedScreener") if sources else None
            expert_bio = sources[0].get("extractedBio") if sources else None
            
            # Get expert details
            expert = await experts.get_expert(db, expert_id)
            if not expert:
                return
            
            # Run smart fit assessment
            result, raw_response, prompt = await self.extraction_service.screen_expert(
                expert_name=expert["canonicalName"],
                expert_employer=expert.get("canonicalEmployer"),
                expert_title=expert.get("canonicalTitle"),
                expert_bio=expert_bio,
                screener_responses=screener_responses,
                screener_config=screener_config,
                project_hypothesis=project_hypothesis
            )
            
            # Update expert
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
        except Exception as e:
            # Don't fail the whole ingestion if screening fails
            print(f"Warning: Screening failed for expert {expert_id}: {e}")

    # NOTE: undo_ingestion and redo_ingestion methods REMOVED
    # These were fundamentally broken:
    # - Undo deleted experts but left stale log entries showing "added"
    # - Redo could not recreate deleted experts
    # - Multiple ingestion sources created conflicting logs
    # Users should use explicit delete instead (multi-select delete in UI)
