"""Outlook inbox scanning service for automatic email ingestion.

Orchestrates scanning Outlook inbox, filtering relevant emails,
and feeding them into the existing auto-ingestion pipeline.

Processes emails sequentially to ensure proper tracking of created experts.
"""

import asyncio
import hashlib
import secrets
import logging
import json
from typing import Optional, List, Set, Dict, Any
from datetime import datetime
import databases

# Configure logging for scan debugging - use DEBUG level for detailed tracing
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Also add a console handler if not already present
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

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
        self.skipped_reasons: List[Dict[str, str]] = []  # Track why emails were skipped
        self.processed_details: List[Dict[str, Any]] = []  # Track what was processed
    
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
            "skippedReasons": self.skipped_reasons[:10],  # Include skip reasons
            "processedDetails": self.processed_details[:10],  # Include processing details
        }


class OutlookScanningService:
    """Service for scanning Outlook inbox and ingesting expert network emails."""
    
    def __init__(self):
        self.auto_ingestion = AutoIngestionService()
    
    async def scan_inbox(
        self,
        db: databases.Database,
        project_id: str,
        max_emails: int = 5,
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
        # Generate unique scan_run_id for tracing
        scan_run_id = secrets.token_urlsafe(8)
        logger.info(f"[SCAN {scan_run_id}] Starting inbox scan for project_id={project_id}, max_emails={max_emails}")
        
        progress = ScanProgress()
        
        # Track ALL expert IDs created during this entire scan run
        # This prevents experts created by email 1 from being marked as "updated" by email 2
        scan_created_expert_ids: Set[str] = set()
        
        # Get project details
        project = await projects.get_project(db, project_id)
        if not project:
            raise Exception("Project not found")
        
        # Create persistent ScanRun record for authoritative tracking
        scan_run_record = None
        try:
            scan_run_record = await scan_runs.create_scan_run(
                db=db,
                project_id=project_id,
                max_emails=max_emails,
                sender_domains=",".join(outlook_service.allowed_sender_domains) if outlook_service.allowed_sender_domains else None,
                keywords=",".join(outlook_service.network_keywords) if outlook_service.network_keywords else None,
            )
            scan_run_id = scan_run_record["id"]  # Use the DB-generated ID
            logger.info(f"[SCAN {scan_run_id}] Created ScanRun record in database")
        except Exception as e:
            # If ScanRun table doesn't exist yet, continue without it
            logger.warning(f"[SCAN {scan_run_id}] Could not create ScanRun record (table may not exist): {e}")
        
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
        logger.debug(f"[SCAN {scan_run_id}] Already scanned message IDs for project: {len(scanned_ids)} messages")
        
        # Fetch recent messages from INBOX ONLY with body included (single API call)
        progress.stage = "scanning"
        
        # Default to last 7 days for faster scans
        from datetime import timedelta
        since_date = datetime.utcnow() - timedelta(days=7)
        
        try:
            messages = await outlook_service.list_messages(
                access_token=access_token,
                top=max_emails,
                since=since_date,
                include_body=True,  # Include body to avoid second API call per email
                inbox_only=True,    # Only read from Inbox folder (not Sent, Drafts, etc.)
            )
            logger.info(f"[SCAN {scan_run_id}] Fetched {len(messages)} messages from Inbox (last 7 days)")
            
            # Log each message for debugging
            for i, msg in enumerate(messages):
                msg_id = msg.get("id", "unknown")[:20]
                subject = msg.get("subject", "")[:50]
                sender = msg.get("from", {}).get("emailAddress", {}).get("address", "unknown")
                received = msg.get("receivedDateTime", "unknown")
                logger.debug(f"[SCAN {scan_run_id}] Message {i+1}: id={msg_id}..., subject='{subject}', from={sender}, received={received}")
        except Exception as e:
            logger.error(f"[SCAN {scan_run_id}] Failed to fetch emails: {str(e)}")
            raise Exception(f"Failed to fetch emails from Outlook: {str(e)}")
        
        progress.total_emails = len(messages)
        
        # Filter by sender domain (if configured)
        domain_filtered = outlook_service.filter_messages_by_sender_domain(messages)
        logger.debug(f"[SCAN {scan_run_id}] After domain filter: {len(domain_filtered)} messages (domains: {outlook_service.allowed_sender_domains})")
        
        # If no domain filter, filter by keywords instead
        if not outlook_service.allowed_sender_domains:
            filtered_messages = outlook_service.filter_messages_by_keywords(messages)
            logger.debug(f"[SCAN {scan_run_id}] After keyword filter: {len(filtered_messages)} messages (keywords: {outlook_service.network_keywords})")
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
            logger.debug(f"[SCAN {scan_run_id}] After combined filter: {len(filtered_messages)} messages")
        
        progress.filtered_emails = len(filtered_messages)
        
        # Filter out already scanned emails and track why each is skipped
        new_messages = []
        already_scanned_count = 0
        for msg in filtered_messages:
            if msg["id"] in scanned_ids:
                already_scanned_count += 1
                progress.skipped_reasons.append({
                    "messageId": msg["id"][:20],
                    "subject": msg.get("subject", "")[:50],
                    "reason": "already_processed"
                })
                logger.debug(f"[SCAN {scan_run_id}] Skipping already-processed: {msg.get('subject', '')[:50]}")
            else:
                new_messages.append(msg)
        
        progress.skipped_count = already_scanned_count
        logger.info(f"[SCAN {scan_run_id}] New messages to process: {len(new_messages)}, already processed: {already_scanned_count}")
        
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
                
                # Use body from initial request (already fetched with include_body=True)
                # Only fetch separately if body is missing (fallback for truncated responses)
                body = msg.get("body")
                if not body:
                    logger.debug(f"[SCAN {scan_run_id}] Body not in initial response, fetching separately")
                    full_message = await outlook_service.get_message_body(
                        access_token=access_token,
                        message_id=msg["id"],
                    )
                    body = full_message.get("body", {})
                
                # Extract email content
                email_text = outlook_service.extract_plain_text_from_body(body)
                
                # Log body hash for debugging
                body_hash = hashlib.sha256(email_text.encode()).hexdigest()[:16] if email_text else "empty"
                logger.info(f"[SCAN {scan_run_id}] Email body hash: {body_hash}, length: {len(email_text) if email_text else 0}")
                
                if not email_text or len(email_text.strip()) < 50:
                    logger.info(f"[SCAN {scan_run_id}] Skipping email - body too short (length={len(email_text.strip()) if email_text else 0})")
                    progress.skipped_reasons.append({
                        "messageId": msg["id"][:20],
                        "subject": subject[:50],
                        "reason": "body_too_short",
                        "bodyLength": len(email_text.strip()) if email_text else 0
                    })
                    results.append({"status": "skipped", "reason": "body_too_short", "msg": msg})
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
                extracted_count = result.get("summary", {}).get("extractedCount", 0)
                
                logger.info(f"[SCAN {scan_run_id}] Email extraction complete: extracted={extracted_count}, added={added_count}, updated={updated_count}, merged={merged_count}")
                
                # Track processing details for transparency
                processing_detail = {
                    "messageId": msg["id"][:20],
                    "subject": subject[:50],
                    "sender": sender_email,
                    "network": network,
                    "extractedCount": extracted_count,
                    "addedCount": added_count,
                    "updatedCount": updated_count,
                    "mergedCount": merged_count,
                    "addedExperts": [e.get("expertName") for e in changes.get("added", [])],
                    "updatedExperts": [e.get("expertName") for e in changes.get("updated", [])],
                }
                progress.processed_details.append(processing_detail)
                
                # Track created expert IDs from this email
                for added in changes.get("added", []):
                    scan_created_expert_ids.add(added["expertId"])
                    logger.info(f"[SCAN {scan_run_id}] Created expert: id={added['expertId']}, name={added['expertName']}")
                
                for updated in changes.get("updated", []):
                    logger.info(f"[SCAN {scan_run_id}] Updated expert: id={updated['expertId']}, name={updated['expertName']}, fields={updated.get('fieldsUpdated', [])}")
                
                # Record that we scanned this email
                await scanned_emails.record_scanned_email(
                    db=db,
                    project_id=project_id,
                    outlook_message_id=msg["id"],
                    email_subject=subject,
                    sender=sender_email,
                    received_at=msg.get("receivedDateTime"),
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
                    )
                except:
                    pass
                results.append({"status": "error", "error": str(e), "msg": msg})
        
        # Aggregate results
        logger.info(f"[SCAN {scan_run_id}] Aggregating results from {len(results)} email processing attempts")
        emails_processed = 0
        emails_with_extraction = 0
        
        for r in results:
            progress.processed_emails += 1
            
            if r["status"] == "skipped":
                progress.skipped_count += 1
                logger.debug(f"[SCAN {scan_run_id}] Result: skipped - {r.get('reason', 'unknown')}")
            elif r["status"] == "error":
                progress.error_count += 1
                error_msg = f"Failed to process email '{r['msg'].get('subject', 'Unknown')}': {r['error']}"
                progress.errors.append(error_msg)
                logger.error(f"[SCAN {scan_run_id}] Result: error - {error_msg}")
            elif r["status"] == "success":
                result = r["result"]
                email_ids.append(result.get("emailId"))
                emails_processed += 1
                
                changes = result.get("changes", {})
                added_in_email = changes.get("added", [])
                updated_in_email = changes.get("updated", [])
                
                all_changes["added"].extend(added_in_email)
                all_changes["updated"].extend(updated_in_email)
                all_changes["merged"].extend(changes.get("merged", []))
                all_changes["needsReview"].extend(changes.get("needsReview", []))
                
                # Track if this email actually extracted anything
                if len(added_in_email) > 0 or len(updated_in_email) > 0:
                    emails_with_extraction += 1
                
                # Aggregate snapshots (kept for now, will be removed with undo/redo)
                snapshot = result.get("snapshot", {})
                all_snapshots["createdExpertIds"].extend(snapshot.get("createdExpertIds", []))
                all_snapshots["mergedPairs"].extend(snapshot.get("mergedPairs", []))
                all_snapshots["updatedExperts"].extend(snapshot.get("updatedExperts", []))
                
                progress.ingested_count += 1
                logger.debug(f"[SCAN {scan_run_id}] Result: success - added={len(added_in_email)}, updated={len(updated_in_email)}")
        
        logger.info(f"[SCAN {scan_run_id}] Aggregation complete: processed={emails_processed}, with_extraction={emails_with_extraction}, skipped={progress.skipped_count}, errors={progress.error_count}")
        
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
        
        # Final summary logging
        logger.info(f"[SCAN {scan_run_id}] === SCAN COMPLETE ===")
        logger.info(f"[SCAN {scan_run_id}] Emails processed: {emails_processed}")
        logger.info(f"[SCAN {scan_run_id}] Experts added: {len(all_changes['added'])}")
        logger.info(f"[SCAN {scan_run_id}] Experts updated: {len(all_changes['updated'])}")
        logger.info(f"[SCAN {scan_run_id}] Experts merged: {len(all_changes['merged'])}")
        logger.info(f"[SCAN {scan_run_id}] Ingestion log ID: {unified_log['id'] if unified_log else 'None'}")
        
        # Log added expert names for verification
        if all_changes['added']:
            added_names = [e.get('expertName', 'Unknown') for e in all_changes['added']]
            logger.info(f"[SCAN {scan_run_id}] Added experts: {added_names}")
        
        # Complete the ScanRun record with final results
        if scan_run_record:
            try:
                await scan_runs.complete_scan_run(
                    db=db,
                    scan_run_id=scan_run_id,
                    messages_processed=emails_processed,
                    messages_skipped=progress.skipped_count,
                    messages_failed=progress.error_count,
                    experts_added=len(all_changes['added']),
                    experts_updated=len(all_changes['updated']),
                    experts_merged=len(all_changes['merged']),
                    added_experts=all_changes['added'],
                    updated_experts=all_changes['updated'],
                    skipped_reasons=progress.skipped_reasons,
                    errors=progress.errors,
                    processed_details=progress.processed_details,
                    ingestion_log_id=unified_log["id"] if unified_log else None,
                )
                logger.info(f"[SCAN {scan_run_id}] Completed ScanRun record in database")
            except Exception as e:
                logger.warning(f"[SCAN {scan_run_id}] Could not complete ScanRun record: {e}")
        
        final_result = {
            "status": "complete",
            "progress": progress.to_dict(),
            "ingestionLogId": unified_log["id"] if unified_log else None,
            "scanRunId": scan_run_id,  # Include scan run ID for frontend tracking
            "results": {
                "summary": unified_summary,
                "changes": all_changes,
            },
            "message": f"Processed {emails_processed} emails. {unified_summary['addedCount']} experts added, {unified_summary['updatedCount']} updated."
        }
        
        logger.debug(f"[SCAN {scan_run_id}] Final result summary: {json.dumps(unified_summary)}")
        
        return final_result


# Singleton instance
outlook_scanning_service = OutlookScanningService()
