"""Outlook inbox scanning service for automatic email ingestion.

Orchestrates scanning Outlook inbox, filtering relevant emails,
and feeding them into the existing auto-ingestion pipeline.

Processes emails sequentially to ensure proper tracking of created experts.
"""

import asyncio
import hashlib
import secrets
import logging
from typing import Optional, List, Set
from datetime import datetime
import databases

# Configure logging for scan debugging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from app.services.outlook_service import outlook_service
from app.services.auto_ingestion import AutoIngestionService
from app.db.queries import outlook as outlook_queries
from app.db.queries import scanned_emails
from app.db.queries import projects
from app.db.queries import ingestion_log
from app.db.queries import scan_runs

# Sequential processing to prevent race conditions between emails in same scan
# This ensures experts created by email 1 are properly tracked before email 2 runs


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
        # Create scan run record for authoritative tracking
        scan_run = await scan_runs.create_scan_run(db, project_id, max_emails)
        scan_run_id = scan_run["id"]
        
        logger.info(f"[SCAN {scan_run_id}] ===== STARTING INBOX SCAN =====")
        logger.info(f"[SCAN {scan_run_id}] Project ID: {project_id}")
        logger.info(f"[SCAN {scan_run_id}] Max emails: {max_emails}")
        
        progress = ScanProgress()
        
        # Track ALL expert IDs created during this entire scan run
        # This prevents experts created by email 1 from being marked as "updated" by email 2
        scan_created_expert_ids: Set[str] = set()
        
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
        logger.info(f"[SCAN {scan_run_id}] Already scanned message IDs: {len(scanned_ids)} messages")
        
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
        logger.info(f"[SCAN {scan_run_id}] Fetched {len(messages)} messages from Outlook")
        
        # Update scan run with messages considered
        await scan_runs.update_scan_run_progress(
            db, scan_run_id, messages_considered=len(messages)
        )
        
        # Log message details for debugging
        for i, msg in enumerate(messages[:5]):  # Log first 5 messages
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "unknown")
            subject = msg.get("subject", "")[:50]
            received = msg.get("receivedDateTime", "")
            logger.info(f"[SCAN {scan_run_id}] Message {i+1}: id={msg['id'][:20]}..., from={sender}, subject='{subject}', received={received}")
        
        # Filter by sender domain (if configured)
        domain_filtered = outlook_service.filter_messages_by_sender_domain(messages)
        logger.info(f"[SCAN {scan_run_id}] Domain filtered: {len(domain_filtered)} messages")
        
        # If no domain filter, filter by keywords instead
        if not outlook_service.allowed_sender_domains:
            filtered_messages = outlook_service.filter_messages_by_keywords(messages)
            logger.info(f"[SCAN {scan_run_id}] Keyword filtered (no domain filter): {len(filtered_messages)} messages")
        else:
            # If domain filter is set, use domain-filtered results
            # Also include keyword matches from non-domain emails
            keyword_filtered = outlook_service.filter_messages_by_keywords(messages)
            logger.info(f"[SCAN {scan_run_id}] Keyword filtered: {len(keyword_filtered)} messages")
            # Combine: domain matches OR keyword matches
            filtered_ids = {m["id"] for m in domain_filtered}
            filtered_messages = domain_filtered.copy()
            for msg in keyword_filtered:
                if msg["id"] not in filtered_ids:
                    filtered_messages.append(msg)
            logger.info(f"[SCAN {scan_run_id}] Combined filtered: {len(filtered_messages)} messages")
        
        progress.filtered_emails = len(filtered_messages)
        
        # Filter out already scanned emails
        new_messages = [m for m in filtered_messages if m["id"] not in scanned_ids]
        progress.skipped_count = len(filtered_messages) - len(new_messages)
        logger.info(f"[SCAN {scan_run_id}] After dedup: {len(new_messages)} new messages, {progress.skipped_count} already scanned")
        
        if not new_messages:
            logger.info(f"[SCAN {scan_run_id}] No new messages to process - returning early")
            
            # Update scan run with final counts
            await scan_runs.update_scan_run_progress(
                db, scan_run_id, 
                messages_processed=0,
                messages_skipped=progress.skipped_count
            )
            await scan_runs.complete_scan_run(
                db, scan_run_id, 
                status="completed",
                experts_added=0,
                experts_updated=0,
                experts_merged=0
            )
            
            return {
                "status": "complete",
                "progress": progress.to_dict(),
                "scanRunId": scan_run_id,
                "results": {
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
        
        # Process emails SEQUENTIALLY to ensure proper tracking of created experts
        # This prevents race conditions where email 2 sees experts from email 1 as "existing"
        progress.stage = "extracting"
        logger.info(f"[SCAN {scan_run_id}] Processing {len(new_messages)} emails sequentially")
        
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
        results = []
        
        # Process emails one by one (sequential)
        for msg in new_messages:
            progress.stage = f"processing_email_{len(results)+1}_of_{len(new_messages)}"
            
            try:
                # Log email being processed
                sender_email = msg.get("from", {}).get("emailAddress", {}).get("address", "")
                subject = msg.get("subject", "")
                received_dt = msg.get("receivedDateTime", "")
                logger.info(f"[SCAN {scan_run_id}] Processing email: id={msg['id'][:20]}..., subject='{subject[:50]}', from={sender_email}, received={received_dt}")
                
                # Fetch full message body
                full_message = await outlook_service.get_message_body(
                    access_token=access_token,
                    message_id=msg["id"],
                )
                
                # Extract email content
                body = full_message.get("body", {})
                email_text = outlook_service.extract_plain_text_from_body(body)
                
                # Log body hash for debugging
                body_hash = hashlib.sha256(email_text.encode()).hexdigest()[:16] if email_text else "empty"
                logger.info(f"[SCAN {scan_run_id}] Email body hash: {body_hash}, length: {len(email_text) if email_text else 0}")
                
                if not email_text or len(email_text.strip()) < 50:
                    logger.info(f"[SCAN {scan_run_id}] Skipping email - body too short")
                    results.append({"status": "skipped", "msg": msg})
                    continue
                
                # Detect network
                preview = msg.get("bodyPreview", "")
                network = outlook_service.detect_network_from_email(sender_email, subject, preview)
                
                # Run auto-ingestion with skip_log=True and pass scan_created_expert_ids
                # This allows tracking experts created across all emails in this scan
                result = await self.auto_ingestion.auto_ingest(
                    db=db,
                    project_id=project_id,
                    email_text=email_text,
                    network=network,
                    project_hypothesis=project["hypothesisText"],
                    screener_config=project.get("screenerConfig"),
                    skip_log=True,
                    scan_created_expert_ids=scan_created_expert_ids,  # Pass shared set
                )
                
                # Log extraction results
                changes = result.get("changes", {})
                added_count = len(changes.get("added", []))
                updated_count = len(changes.get("updated", []))
                merged_count = len(changes.get("merged", []))
                logger.info(f"[SCAN {scan_run_id}] Email ingestion result: {added_count} added, {updated_count} updated, {merged_count} merged")
                
                # Log individual expert names for debugging
                for added in changes.get("added", []):
                    logger.info(f"[SCAN {scan_run_id}] ADDED: {added.get('expertName', 'Unknown')} (ID: {added.get('expertId', 'Unknown')})")
                for updated in changes.get("updated", []):
                    logger.info(f"[SCAN {scan_run_id}] UPDATED: {updated.get('expertName', 'Unknown')} (ID: {updated.get('expertId', 'Unknown')})")
                for merged in changes.get("merged", []):
                    logger.info(f"[SCAN {scan_run_id}] MERGED: {merged.get('keptExpertId', 'Unknown')} <- {merged.get('mergedExpertId', 'Unknown')}")
                
                # Track created expert IDs from this email
                for added in changes.get("added", []):
                    scan_created_expert_ids.add(added["expertId"])
                    logger.info(f"[SCAN {scan_run_id}] Created expert: id={added['expertId']}, name={added['expertName']}")
                
                # Record that we scanned this email successfully
                await scanned_emails.record_scanned_email(
                    db=db,
                    project_id=project_id,
                    outlook_message_id=msg["id"],
                    email_subject=subject,
                    sender=sender_email,
                    received_at=msg.get("receivedDateTime"),
                    internet_message_id=msg.get("internetMessageId"),
                    subject_hash=hashlib.sha256(subject.encode()).hexdigest()[:16] if subject else None,
                    status="processed",
                )
                
                results.append({"status": "success", "result": result, "msg": msg})
                
            except Exception as e:
                logger.error(f"[SCAN {scan_run_id}] Error processing email: {str(e)}")
                # Still record that we attempted this email to avoid retrying
                try:
                    await scanned_emails.record_scanned_email(
                        db=db,
                        project_id=project_id,
                        outlook_message_id=msg["id"],
                        email_subject=msg.get("subject"),
                        sender=msg.get("from", {}).get("emailAddress", {}).get("address"),
                        received_at=msg.get("receivedDateTime"),
                        internet_message_id=msg.get("internetMessageId"),
                        subject_hash=hashlib.sha256(msg.get("subject", "").encode()).hexdigest()[:16] if msg.get("subject") else None,
                        status="failed",
                    )
                except Exception as record_error:
                    logger.error(f"[SCAN {scan_run_id}] Failed to record failed email: {record_error}")
                results.append({"status": "error", "error": str(e), "msg": msg})
        
        # Aggregate results
        emails_processed = 0
        emails_failed = 0
        for r in results:
            progress.processed_emails += 1
            
            if r["status"] == "skipped":
                progress.skipped_count += 1
            elif r["status"] == "error":
                progress.error_count += 1
                emails_failed += 1
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
        
        # Update scan run with final progress
        await scan_runs.update_scan_run_progress(
            db, scan_run_id,
            messages_processed=emails_processed,
            messages_skipped=progress.skipped_count,
            messages_failed=emails_failed
        )
        
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
        
        logger.info(f"[SCAN {scan_run_id}] ===== SCAN COMPLETE =====")
        logger.info(f"[SCAN {scan_run_id}] Final summary: {unified_summary}")
        logger.info(f"[SCAN {scan_run_id}] Total experts added: {len(all_changes['added'])}")
        logger.info(f"[SCAN {scan_run_id}] Total experts updated: {len(all_changes['updated'])}")
        logger.info(f"[SCAN {scan_run_id}] Total experts merged: {len(all_changes['merged'])}")
        logger.info(f"[SCAN {scan_run_id}] Emails processed: {emails_processed}")
        logger.info(f"[SCAN {scan_run_id}] Emails failed: {emails_failed}")
        logger.info(f"[SCAN {scan_run_id}] Emails skipped: {progress.skipped_count}")
        logger.info(f"[SCAN {scan_run_id}] =================================")
        
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
        
        # Complete the scan run with final results
        try:
            await scan_runs.complete_scan_run(
                db, scan_run_id,
                status="completed",
                experts_added=len(all_changes["added"]),
                experts_updated=len(all_changes["updated"]),
                experts_merged=len(all_changes["merged"]),
                ingestion_log_id=unified_log["id"] if unified_log else None,
                error_details=progress.errors if progress.errors else None
            )
        except Exception as e:
            logger.error(f"[SCAN {scan_run_id}] Failed to complete scan run: {e}")
        
        progress.stage = "complete"
        
        return {
            "status": "complete",
            "progress": progress.to_dict(),
            "scanRunId": scan_run_id,
            "ingestionLogId": unified_log["id"] if unified_log else None,
            "results": {
                "summary": unified_summary,
                "changes": all_changes,
            },
            "message": f"Processed {emails_processed} emails. {unified_summary['addedCount']} experts added, {unified_summary['updatedCount']} updated."
        }


# Singleton instance
outlook_scanning_service = OutlookScanningService()
