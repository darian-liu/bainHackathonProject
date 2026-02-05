"""Outlook inbox scanning service for automatic email ingestion.

Orchestrates scanning Outlook inbox, filtering relevant emails,
and feeding them into the existing auto-ingestion pipeline.

Uses parallel processing for 3-5x faster email extraction.
"""

import asyncio
from typing import Optional, List
from datetime import datetime
import databases

from app.services.outlook_service import outlook_service
from app.services.auto_ingestion import AutoIngestionService
from app.db.queries import outlook as outlook_queries
from app.db.queries import scanned_emails
from app.db.queries import projects
from app.db.queries import ingestion_log

# Limit concurrent API calls to avoid rate limits
MAX_CONCURRENT_EXTRACTIONS = 5


class ScanProgress:
    """Progress tracking for inbox scanning."""
    
    def __init__(self):
        self.stage = "initializing"
        self.total_emails = 0
        self.processed_emails = 0
        self.filtered_emails = 0
        self.ingested_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.errors: List[str] = []
    
    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "totalEmails": self.total_emails,
            "processedEmails": self.processed_emails,
            "filteredEmails": self.filtered_emails,
            "ingestedCount": self.ingested_count,
            "skippedCount": self.skipped_count,
            "errorCount": self.error_count,
            "errors": self.errors[:5],  # Limit errors in response
        }


class OutlookScanningService:
    """Service for scanning Outlook inbox and ingesting expert network emails."""
    
    def __init__(self):
        self.auto_ingestion = AutoIngestionService()
    
    async def scan_inbox(
        self,
        db: databases.Database,
        project_id: str,
        max_emails: int = 3,
    ) -> dict:
        """
        Scan Outlook inbox for expert network emails and ingest them.
        
        Args:
            db: Database connection
            project_id: Project to ingest emails into
            max_emails: Maximum number of emails to scan
            
        Returns:
            Aggregated ingestion results
        """
        progress = ScanProgress()
        
        # Get project details
        project = await projects.get_project(db, project_id)
        if not project:
            raise Exception("Project not found")
        
        # Get Outlook connection
        progress.stage = "connecting"
        connection = await outlook_queries.get_active_connection(db)
        if not connection:
            raise Exception("No active Outlook connection. Please connect Outlook in Settings first.")
        
        # Get access token (refresh if needed)
        access_token = connection["accessToken"]
        refresh_token = connection["refreshToken"]
        token_expires_at = datetime.fromisoformat(connection["tokenExpiresAt"])
        
        if outlook_service.is_token_expired(token_expires_at):
            try:
                token_result = await outlook_service.refresh_access_token(refresh_token)
                access_token = token_result["access_token"]
                new_refresh_token = token_result.get("refresh_token", refresh_token)
                expires_in = token_result.get("expires_in", 3600)
                new_expires_at = outlook_service.calculate_token_expiry(expires_in)
                
                await outlook_queries.update_tokens(
                    db=db,
                    connection_id=connection["id"],
                    access_token=access_token,
                    refresh_token=new_refresh_token,
                    token_expires_at=new_expires_at,
                )
            except Exception as e:
                raise Exception(f"Failed to refresh Outlook token: {str(e)}. Please reconnect Outlook.")
        
        # Get already scanned message IDs for this project
        scanned_ids = await scanned_emails.get_scanned_message_ids(db, project_id)
        
        # Fetch recent messages
        progress.stage = "scanning"
        try:
            messages = await outlook_service.list_messages(
                access_token=access_token,
                top=max_emails,
            )
        except Exception as e:
            raise Exception(f"Failed to fetch emails from Outlook: {str(e)}")
        
        progress.total_emails = len(messages)
        
        # Filter by sender domain (if configured)
        domain_filtered = outlook_service.filter_messages_by_sender_domain(messages)
        
        # If no domain filter, filter by keywords instead
        if not outlook_service.allowed_sender_domains:
            filtered_messages = outlook_service.filter_messages_by_keywords(messages)
        else:
            # If domain filter is set, use domain-filtered results
            # Also include keyword matches from non-domain emails
            keyword_filtered = outlook_service.filter_messages_by_keywords(messages)
            # Combine: domain matches OR keyword matches
            filtered_ids = {m["id"] for m in domain_filtered}
            filtered_messages = domain_filtered.copy()
            for msg in keyword_filtered:
                if msg["id"] not in filtered_ids:
                    filtered_messages.append(msg)
        
        progress.filtered_emails = len(filtered_messages)
        
        # Filter out already scanned emails
        new_messages = [m for m in filtered_messages if m["id"] not in scanned_ids]
        progress.skipped_count = len(filtered_messages) - len(new_messages)
        
        if not new_messages:
            return {
                "status": "complete",
                "progress": progress.to_dict(),
                "results": {
                    "ingestionLogIds": [],
                    "summary": {
                        "addedCount": 0,
                        "updatedCount": 0,
                        "mergedCount": 0,
                        "needsReviewCount": 0,
                        "extractedCount": 0,
                        "emailsProcessed": 0,
                        "emailsSkipped": progress.skipped_count,
                    },
                    "changes": {
                        "added": [],
                        "updated": [],
                        "merged": [],
                        "needsReview": [],
                    },
                },
                "message": f"No new expert network emails found. {progress.skipped_count} emails already processed."
            }
        
        # Process emails in PARALLEL for 3-5x faster extraction
        progress.stage = "extracting"
        
        # Aggregated data for unified transaction
        all_changes = {
            "added": [],
            "updated": [],
            "merged": [],
            "needsReview": [],
        }
        all_snapshots = {
            "createdExpertIds": [],
            "mergedPairs": [],
            "updatedExperts": [],
        }
        email_ids = []
        
        # Semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXTRACTIONS)
        
        async def process_single_email(msg: dict) -> dict:
            """Process a single email with rate limiting."""
            async with semaphore:
                try:
                    # Fetch full message body
                    full_message = await outlook_service.get_message_body(
                        access_token=access_token,
                        message_id=msg["id"],
                    )
                    
                    # Extract email content
                    body = full_message.get("body", {})
                    email_text = outlook_service.extract_plain_text_from_body(body)
                    
                    if not email_text or len(email_text.strip()) < 50:
                        return {"status": "skipped", "msg": msg}
                    
                    # Detect network
                    sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "")
                    subject = msg.get("subject", "")
                    preview = msg.get("bodyPreview", "")
                    network = outlook_service.detect_network_from_email(sender_email, subject, preview)
                    
                    # Run auto-ingestion with skip_log=True (we create unified log at end)
                    result = await self.auto_ingestion.auto_ingest(
                        db=db,
                        project_id=project_id,
                        email_text=email_text,
                        network=network,
                        project_hypothesis=project["hypothesisText"],
                        screener_config=project.get("screenerConfig"),
                        skip_log=True,
                    )
                    
                    # Record that we scanned this email
                    await scanned_emails.record_scanned_email(
                        db=db,
                        project_id=project_id,
                        outlook_message_id=msg["id"],
                        email_subject=subject,
                        sender=sender_email,
                        received_at=msg.get("receivedDateTime"),
                    )
                    
                    return {"status": "success", "result": result, "msg": msg}
                    
                except Exception as e:
                    # Still record that we attempted this email to avoid retrying
                    try:
                        await scanned_emails.record_scanned_email(
                            db=db,
                            project_id=project_id,
                            outlook_message_id=msg["id"],
                            email_subject=msg.get("subject"),
                            sender=msg.get("from", {}).get("emailAddress", {}).get("address"),
                            received_at=msg.get("receivedDateTime"),
                        )
                    except Exception as record_error:
                        print(f"Warning: Failed to record scanned email: {record_error}")
                    return {"status": "error", "error": str(e), "msg": msg}
        
        # Process all emails in parallel
        progress.stage = f"processing_{len(new_messages)}_emails_parallel"
        results = await asyncio.gather(*[process_single_email(msg) for msg in new_messages])
        
        # Aggregate results
        emails_processed = 0
        for r in results:
            progress.processed_emails += 1
            
            if r["status"] == "skipped":
                progress.skipped_count += 1
            elif r["status"] == "error":
                progress.error_count += 1
                progress.errors.append(f"Failed to process email '{r['msg'].get('subject', 'Unknown')}': {r['error']}")
            elif r["status"] == "success":
                result = r["result"]
                email_ids.append(result.get("emailId"))
                emails_processed += 1
                
                changes = result.get("changes", {})
                all_changes["added"].extend(changes.get("added", []))
                all_changes["updated"].extend(changes.get("updated", []))
                all_changes["merged"].extend(changes.get("merged", []))
                all_changes["needsReview"].extend(changes.get("needsReview", []))
                
                # Aggregate snapshots (kept for now, will be removed with undo/redo)
                snapshot = result.get("snapshot", {})
                all_snapshots["createdExpertIds"].extend(snapshot.get("createdExpertIds", []))
                all_snapshots["mergedPairs"].extend(snapshot.get("mergedPairs", []))
                all_snapshots["updatedExperts"].extend(snapshot.get("updatedExperts", []))
                
                progress.ingested_count += 1
        
        # Update sync timestamp
        await outlook_queries.update_sync_timestamp(db, connection["id"])
        
        # Build unified summary
        unified_summary = {
            "addedCount": len(all_changes["added"]),
            "updatedCount": len(all_changes["updated"]),
            "mergedCount": len(all_changes["merged"]),
            "needsReviewCount": len(all_changes["needsReview"]),
            "extractedCount": len(all_changes["added"]) + len(all_changes["updated"]),
            "emailsProcessed": emails_processed,
            "emailsSkipped": progress.skipped_count,
            "source": "outlook_scan",
            "isNoOp": len(all_changes["added"]) == 0 and len(all_changes["updated"]) == 0,
        }
        
        # Create ONE unified ingestion log for the entire scan
        unified_log = None
        if emails_processed > 0:
            unified_log = await ingestion_log.create_ingestion_log(
                db,
                project_id=project_id,
                email_id=email_ids[0] if email_ids else None,  # First email as reference
                summary=unified_summary,
                snapshot=all_snapshots,
            )
            
            # Create log entries for all changes
            for added in all_changes["added"]:
                await ingestion_log.create_ingestion_log_entry(
                    db,
                    ingestion_log_id=unified_log["id"],
                    action="added",
                    expert_id=added["expertId"],
                    expert_name=added["expertName"],
                )
            
            for updated in all_changes["updated"]:
                await ingestion_log.create_ingestion_log_entry(
                    db,
                    ingestion_log_id=unified_log["id"],
                    action="updated",
                    expert_id=updated["expertId"],
                    expert_name=updated["expertName"],
                    fields_changed=updated.get("fieldsUpdated"),
                    previous_values=updated.get("previousValues"),
                    new_values=updated.get("newValues"),
                )
            
            for merged in all_changes["merged"]:
                await ingestion_log.create_ingestion_log_entry(
                    db,
                    ingestion_log_id=unified_log["id"],
                    action="merged",
                    expert_id=merged["keptExpertId"],
                    merged_from_expert_id=merged["mergedExpertId"],
                )
        
        progress.stage = "complete"
        
        return {
            "status": "complete",
            "progress": progress.to_dict(),
            "ingestionLogId": unified_log["id"] if unified_log else None,
            "results": {
                "summary": unified_summary,
                "changes": all_changes,
            },
            "message": f"Processed {emails_processed} emails. {unified_summary['addedCount']} experts added, {unified_summary['updatedCount']} updated."
        }


# Singleton instance
outlook_scanning_service = OutlookScanningService()
