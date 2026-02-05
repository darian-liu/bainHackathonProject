"""Tests for auto-scan reliability bug fixes."""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.outlook_scanning import OutlookScanningService
from app.db.queries import scan_runs, scanned_emails, ingestion_log


# Test email samples from the user's bug report
EMAIL_1_CONTENT = """Hi Arjun,

Hope you're doing well. Following up on your request, we've identified several experts who may be relevant for Project Atlas, focused on pharma and biologics distribution operations.

Below is an initial slate for your review.

EXPERT 1: Michael O'Connor
Current Role: SVP, Global Supply Chain
Company: Horizon Biologics

Background:
• Led global distribution for injectable biologics across NA and EMEA
• Implemented cold-chain monitoring systems to reduce temperature excursions
• Experience managing outsourced manufacturing and 3PL partnerships

Availability: Feb 18–20
Screener Status: Completed
Conflict Status: CLEARED (ID: CLR-2026-0411)

EXPERT 2: Anika Desai
Current Role: Director of Distribution Operations
Company: VaxCore Pharmaceuticals

Background:
• Oversees regional distribution for specialty vaccines and biologics
• Deep experience in demand planning and inventory optimization
• Worked closely with hospital systems and specialty pharmacies

Availability: Checking
Screener Status: In progress
Conflict Status: Under review

EXPERT 3: Robert Chen
Current Role: Former Head of Global Logistics
Company: MedGen Solutions

Background:
• Led end-to-end logistics strategy for temperature-controlled therapies
• Managed cross-border distribution and regulatory coordination
• Supported rapid scale-up during pandemic response initiatives

Availability: Feb 21 afternoon
Screener Status: Completed
Conflict Status: CLEARED (ID: CLR-2026-0412)

Please let us know which experts you'd like to prioritize, and we'll proceed with scheduling and any additional follow-ups as needed.

Best regards,
John Smith
Senior Associate
AlphaSights"""

EMAIL_2_CONTENT = """Hi Arjun,



Hope you're doing well. Following up on your request, we've identified several experts who may be relevant for Project Atlas, focused on pharma and biologics distribution operations.



Below is an initial slate for your review.



EXPERT 1: Michael O'Connor

Current Role: SVP, Global Supply Chain

Company: Horizon Biologics



Background:

• Led global distribution for injectable biologics across NA and EMEA

• Implemented cold-chain monitoring systems to reduce temperature excursions

• Experience managing outsourced manufacturing and 3PL partnerships



Availability: Feb 18–20

Screener Status: Completed

Conflict Status: CLEARED (ID: CLR-2026-0411)


EXPERT 2: Anika Desai

Current Role: Director of Distribution Operations

Company: VaxCore Pharmaceuticals



Background:

• Oversees regional distribution for specialty vaccines and biologics

• Deep experience in demand planning and inventory optimization

• Worked closely with hospital systems and specialty pharmacies



Availability: Checking

Screener Status: In progress

Conflict Status: Under review


EXPERT 3: Robert Chen

Current Role: Former Head of Global Logistics

Company: MedGen Solutions



Background:

• Led end-to-end logistics strategy for temperature-controlled therapies

• Managed cross-border distribution and regulatory coordination

• Supported rapid scale-up during pandemic response initiatives



Availability: Feb 21 afternoon

Screener Status: Completed

Conflict Status: CLEARED (ID: CLR-2026-0412)


Please let us know which experts you'd like to prioritize, and we'll proceed with scheduling and any additional follow-ups as needed.



Best regards,

John Smith

Senior Associate

AlphaSights"""


class TestAutoScanReliability:
    """Test suite for auto-scan reliability fixes."""

    @pytest.fixture
    def mock_db(self):
        """Mock database connection."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def mock_outlook_messages(self):
        """Mock Outlook messages for testing."""
        return [
            {
                "id": "msg_001",
                "subject": "Expert recommendations for Project Atlas",
                "from": {"emailAddress": {"address": "john.smith@alphasights.com"}},
                "receivedDateTime": "2026-02-05T10:00:00Z",
                "internetMessageId": "<msg001@alphasights.com>",
                "bodyPreview": "Hope you're doing well. Following up on your request..."
            },
            {
                "id": "msg_002", 
                "subject": "Re: Expert recommendations for Project Atlas",
                "from": {"emailAddress": {"address": "john.smith@alphasights.com"}},
                "receivedDateTime": "2026-02-05T11:00:00Z",
                "internetMessageId": "<msg002@alphasights.com>",
                "bodyPreview": "Hope you're doing well. Following up on your request..."
            }
        ]

    @pytest.fixture
    def outlook_service(self):
        """Mock outlook scanning service."""
        service = OutlookScanningService()
        return service

    @pytest.mark.asyncio
    async def test_scan_creates_scan_run_record(self, mock_db, outlook_service):
        """Test that scan creates a ScanRun record for tracking."""
        project_id = "test_project_123"
        max_emails = 10

        # Mock dependencies
        with patch('app.db.queries.projects.get_project') as mock_get_project, \
             patch('app.db.queries.outlook.get_active_connection') as mock_get_connection, \
             patch('app.services.outlook_service.outlook_service') as mock_outlook, \
             patch('app.db.queries.scan_runs.create_scan_run') as mock_create_scan_run, \
             patch('app.db.queries.scanned_emails.get_scanned_message_ids') as mock_get_scanned:

            # Setup mocks
            mock_get_project.return_value = {"id": project_id, "hypothesisText": "Test hypothesis"}
            mock_get_connection.return_value = {
                "id": "conn_123",
                "accessToken": "token_123",
                "refreshToken": "refresh_123",
                "tokenExpiresAt": "2026-02-06T10:00:00Z"
            }
            mock_create_scan_run.return_value = {"id": "scan_run_123", "projectId": project_id}
            mock_get_scanned.return_value = set()
            mock_outlook.list_messages.return_value = []
            mock_outlook.is_token_expired.return_value = False

            # Execute scan
            result = await outlook_service.scan_inbox(mock_db, project_id, max_emails)

            # Verify scan run was created
            mock_create_scan_run.assert_called_once_with(mock_db, project_id, max_emails)
            assert "scanRunId" in result
            assert result["scanRunId"] == "scan_run_123"

    @pytest.mark.asyncio
    async def test_scan_processes_new_messages_correctly(self, mock_db, mock_outlook_messages, outlook_service):
        """Test that scan correctly processes new messages and tracks metrics."""
        project_id = "test_project_123"
        
        # Mock the auto-ingestion to return realistic results
        mock_ingestion_result = {
            "changes": {
                "added": [
                    {"expertId": "expert_1", "expertName": "Michael O'Connor"},
                    {"expertId": "expert_2", "expertName": "Anika Desai"},
                    {"expertId": "expert_3", "expertName": "Robert Chen"}
                ],
                "updated": [],
                "merged": [],
                "needsReview": []
            },
            "emailId": "email_123"
        }

        with patch('app.db.queries.projects.get_project') as mock_get_project, \
             patch('app.db.queries.outlook.get_active_connection') as mock_get_connection, \
             patch('app.services.outlook_service.outlook_service') as mock_outlook, \
             patch('app.db.queries.scan_runs.create_scan_run') as mock_create_scan_run, \
             patch('app.db.queries.scan_runs.update_scan_run_progress') as mock_update_progress, \
             patch('app.db.queries.scan_runs.complete_scan_run') as mock_complete_scan_run, \
             patch('app.db.queries.scanned_emails.get_scanned_message_ids') as mock_get_scanned, \
             patch('app.db.queries.scanned_emails.record_scanned_email') as mock_record_scanned, \
             patch('app.services.auto_ingestion.AutoIngestionService.auto_ingest') as mock_auto_ingest:

            # Setup mocks
            mock_get_project.return_value = {"id": project_id, "hypothesisText": "Test hypothesis"}
            mock_get_connection.return_value = {
                "id": "conn_123",
                "accessToken": "token_123", 
                "refreshToken": "refresh_123",
                "tokenExpiresAt": "2026-02-06T10:00:00Z"
            }
            mock_create_scan_run.return_value = {"id": "scan_run_123", "projectId": project_id}
            mock_get_scanned.return_value = set()  # No previously scanned messages
            mock_outlook.list_messages.return_value = mock_outlook_messages
            mock_outlook.is_token_expired.return_value = False
            mock_outlook.filter_messages_by_sender_domain.return_value = mock_outlook_messages
            mock_outlook.filter_messages_by_keywords.return_value = mock_outlook_messages
            mock_outlook.allowed_sender_domains = ["alphasights.com"]
            mock_outlook.get_message_body.return_value = {"body": {"content": EMAIL_1_CONTENT}}
            mock_outlook.extract_plain_text_from_body.return_value = EMAIL_1_CONTENT
            mock_outlook.detect_network_from_email.return_value = "AlphaSights"
            mock_auto_ingest.return_value = mock_ingestion_result

            # Execute scan
            result = await outlook_service.scan_inbox(mock_db, project_id, 10)

            # Verify scan run tracking
            mock_create_scan_run.assert_called_once()
            mock_update_progress.assert_called()
            mock_complete_scan_run.assert_called_once()

            # Verify correct metrics in result
            assert result["status"] == "complete"
            assert result["results"]["summary"]["emailsProcessed"] == 2
            assert result["results"]["summary"]["addedCount"] == 6  # 3 experts per email
            assert result["results"]["summary"]["updatedCount"] == 0
            assert result["results"]["summary"]["emailsSkipped"] == 0

            # Verify messages were recorded as scanned
            assert mock_record_scanned.call_count == 2

    @pytest.mark.asyncio
    async def test_scan_handles_duplicate_messages_correctly(self, mock_db, mock_outlook_messages, outlook_service):
        """Test that scan correctly handles already-scanned messages."""
        project_id = "test_project_123"
        
        with patch('app.db.queries.projects.get_project') as mock_get_project, \
             patch('app.db.queries.outlook.get_active_connection') as mock_get_connection, \
             patch('app.services.outlook_service.outlook_service') as mock_outlook, \
             patch('app.db.queries.scan_runs.create_scan_run') as mock_create_scan_run, \
             patch('app.db.queries.scan_runs.update_scan_run_progress') as mock_update_progress, \
             patch('app.db.queries.scan_runs.complete_scan_run') as mock_complete_scan_run, \
             patch('app.db.queries.scanned_emails.get_scanned_message_ids') as mock_get_scanned:

            # Setup mocks - all messages already scanned
            mock_get_project.return_value = {"id": project_id, "hypothesisText": "Test hypothesis"}
            mock_get_connection.return_value = {
                "id": "conn_123",
                "accessToken": "token_123",
                "refreshToken": "refresh_123", 
                "tokenExpiresAt": "2026-02-06T10:00:00Z"
            }
            mock_create_scan_run.return_value = {"id": "scan_run_123", "projectId": project_id}
            mock_get_scanned.return_value = {"msg_001", "msg_002"}  # Both messages already scanned
            mock_outlook.list_messages.return_value = mock_outlook_messages
            mock_outlook.is_token_expired.return_value = False
            mock_outlook.filter_messages_by_sender_domain.return_value = mock_outlook_messages
            mock_outlook.filter_messages_by_keywords.return_value = mock_outlook_messages
            mock_outlook.allowed_sender_domains = ["alphasights.com"]

            # Execute scan
            result = await outlook_service.scan_inbox(mock_db, project_id, 10)

            # Verify correct handling of duplicates
            assert result["status"] == "complete"
            assert result["results"]["summary"]["emailsProcessed"] == 0
            assert result["results"]["summary"]["emailsSkipped"] == 2
            assert result["results"]["summary"]["addedCount"] == 0
            assert "No new expert network emails found" in result["message"]

            # Verify scan run was still completed properly
            mock_complete_scan_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_scan_handles_parsing_failures_gracefully(self, mock_db, mock_outlook_messages, outlook_service):
        """Test that scan handles email parsing failures without breaking."""
        project_id = "test_project_123"
        
        with patch('app.db.queries.projects.get_project') as mock_get_project, \
             patch('app.db.queries.outlook.get_active_connection') as mock_get_connection, \
             patch('app.services.outlook_service.outlook_service') as mock_outlook, \
             patch('app.db.queries.scan_runs.create_scan_run') as mock_create_scan_run, \
             patch('app.db.queries.scan_runs.update_scan_run_progress') as mock_update_progress, \
             patch('app.db.queries.scan_runs.complete_scan_run') as mock_complete_scan_run, \
             patch('app.db.queries.scanned_emails.get_scanned_message_ids') as mock_get_scanned, \
             patch('app.db.queries.scanned_emails.record_scanned_email') as mock_record_scanned, \
             patch('app.services.auto_ingestion.AutoIngestionService.auto_ingest') as mock_auto_ingest:

            # Setup mocks
            mock_get_project.return_value = {"id": project_id, "hypothesisText": "Test hypothesis"}
            mock_get_connection.return_value = {
                "id": "conn_123",
                "accessToken": "token_123",
                "refreshToken": "refresh_123",
                "tokenExpiresAt": "2026-02-06T10:00:00Z"
            }
            mock_create_scan_run.return_value = {"id": "scan_run_123", "projectId": project_id}
            mock_get_scanned.return_value = set()
            mock_outlook.list_messages.return_value = mock_outlook_messages
            mock_outlook.is_token_expired.return_value = False
            mock_outlook.filter_messages_by_sender_domain.return_value = mock_outlook_messages
            mock_outlook.filter_messages_by_keywords.return_value = mock_outlook_messages
            mock_outlook.allowed_sender_domains = ["alphasights.com"]
            mock_outlook.get_message_body.return_value = {"body": {"content": EMAIL_1_CONTENT}}
            mock_outlook.extract_plain_text_from_body.return_value = EMAIL_1_CONTENT
            mock_outlook.detect_network_from_email.return_value = "AlphaSights"
            
            # Make auto_ingest fail for first email, succeed for second
            mock_auto_ingest.side_effect = [
                Exception("Parsing failed for first email"),
                {
                    "changes": {
                        "added": [{"expertId": "expert_1", "expertName": "Test Expert"}],
                        "updated": [],
                        "merged": [],
                        "needsReview": []
                    },
                    "emailId": "email_123"
                }
            ]

            # Execute scan
            result = await outlook_service.scan_inbox(mock_db, project_id, 10)

            # Verify scan completed despite one failure
            assert result["status"] == "complete"
            assert result["results"]["summary"]["emailsProcessed"] == 1  # Only one succeeded
            assert result["results"]["summary"]["addedCount"] == 1
            
            # Verify both messages were recorded (including the failed one)
            assert mock_record_scanned.call_count == 2
            
            # Verify scan run was completed with error tracking
            mock_complete_scan_run.assert_called_once()
            complete_call_args = mock_complete_scan_run.call_args[1]
            assert complete_call_args["status"] == "completed"
            assert complete_call_args["experts_added"] == 1

    def test_email_content_parsing_differences(self):
        """Test that the system can handle different email formatting."""
        # This test validates that EMAIL_1_CONTENT and EMAIL_2_CONTENT
        # would be parsed differently despite containing the same experts
        
        # EMAIL_1 has normal formatting
        assert "EXPERT 1: Michael O'Connor" in EMAIL_1_CONTENT
        assert "EXPERT 2: Anika Desai" in EMAIL_1_CONTENT
        assert "EXPERT 3: Robert Chen" in EMAIL_1_CONTENT
        
        # EMAIL_2 has extra whitespace and line breaks
        assert "EXPERT 1: Michael O'Connor" in EMAIL_2_CONTENT
        assert "EXPERT 2: Anika Desai" in EMAIL_2_CONTENT  
        assert "EXPERT 3: Robert Chen" in EMAIL_2_CONTENT
        
        # Verify they're different in formatting
        assert EMAIL_1_CONTENT != EMAIL_2_CONTENT
        assert len(EMAIL_2_CONTENT) > len(EMAIL_1_CONTENT)  # EMAIL_2 has more whitespace


if __name__ == "__main__":
    pytest.main([__file__])
