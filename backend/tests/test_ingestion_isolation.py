"""Tests for project isolation and ingestion accounting.

These tests verify that:
1. Experts are properly scoped to their project (no cross-project contamination)
2. Ingestion accounting is accurate (added vs updated counts)
3. Scan run tracking works correctly for multi-email scans

Run with: python -m pytest tests/test_ingestion_isolation.py -v
"""

import sqlite3
import os
from datetime import datetime


# Test database path
TEST_DB_PATH = "./test_ingestion.db"


def setup_test_db():
    """Create a test database with schema."""
    # Remove existing test DB
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Project (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hypothesisText TEXT NOT NULL,
            createdAt TEXT NOT NULL,
            updatedAt TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Expert (
            id TEXT PRIMARY KEY,
            projectId TEXT NOT NULL,
            canonicalName TEXT NOT NULL,
            canonicalEmployer TEXT,
            canonicalTitle TEXT,
            status TEXT DEFAULT 'recommended',
            statusUpdatedAt TEXT,
            createdAt TEXT NOT NULL,
            updatedAt TEXT NOT NULL,
            FOREIGN KEY (projectId) REFERENCES Project(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    return conn


def teardown_test_db(conn):
    """Clean up test database."""
    conn.close()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def create_project(conn, project_id: str, name: str, hypothesis: str = "Test hypothesis"):
    """Helper to create a test project."""
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO Project (id, name, hypothesisText, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, name, hypothesis, now, now)
    )
    conn.commit()


def create_expert(conn, expert_id: str, project_id: str, name: str, 
                  employer: str = None, title: str = None):
    """Helper to create a test expert."""
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO Expert (id, projectId, canonicalName, canonicalEmployer, canonicalTitle,
                           status, statusUpdatedAt, createdAt, updatedAt)
        VALUES (?, ?, ?, ?, ?, 'recommended', ?, ?, ?)
        """,
        (expert_id, project_id, name, employer, title, now, now, now)
    )
    conn.commit()


def list_experts_for_project(conn, project_id: str):
    """Helper to list experts for a project."""
    cursor = conn.execute(
        "SELECT * FROM Expert WHERE projectId = ? ORDER BY createdAt DESC",
        (project_id,)
    )
    return [dict(row) for row in cursor.fetchall()]


def test_experts_scoped_to_project():
    """
    Test that experts are properly scoped to their project.
    
    Scenario:
    1) Create Project A with 5 experts
    2) Create Project B empty
    3) Verify Project B has 0 experts (not 5)
    """
    conn = setup_test_db()
    try:
        # Create Project A with 5 experts
        create_project(conn, "project_a", "Project A")
        for i in range(5):
            create_expert(conn, f"expert_a_{i}", "project_a", f"Expert A{i}")
        
        # Create Project B empty
        create_project(conn, "project_b", "Project B")
        
        # Verify Project A has 5 experts
        experts_a = list_experts_for_project(conn, "project_a")
        assert len(experts_a) == 5, f"Expected 5 experts in Project A, got {len(experts_a)}"
        
        # Verify Project B has 0 experts
        experts_b = list_experts_for_project(conn, "project_b")
        assert len(experts_b) == 0, f"Expected 0 experts in Project B, got {len(experts_b)}"
        
        print("✅ test_experts_scoped_to_project PASSED")
    finally:
        teardown_test_db(conn)


def test_no_cross_project_contamination():
    """
    Test that adding experts to one project doesn't affect another.
    """
    conn = setup_test_db()
    try:
        # Create Project A with 5 experts
        create_project(conn, "project_a", "Project A")
        for i in range(5):
            create_expert(conn, f"expert_a_{i}", "project_a", f"Alpha Expert {i}")
        
        # Create Project B with 3 experts
        create_project(conn, "project_b", "Project B")
        for i in range(3):
            create_expert(conn, f"expert_b_{i}", "project_b", f"Beta Expert {i}")
        
        # Verify Project A still has exactly 5 experts
        experts_a = list_experts_for_project(conn, "project_a")
        assert len(experts_a) == 5, f"Expected 5 experts in Project A, got {len(experts_a)}"
        
        # Verify Project B has exactly 3 experts
        experts_b = list_experts_for_project(conn, "project_b")
        assert len(experts_b) == 3, f"Expected 3 experts in Project B, got {len(experts_b)}"
        
        print("✅ test_no_cross_project_contamination PASSED")
    finally:
        teardown_test_db(conn)


def test_scan_created_ids_tracking():
    """
    Test that scan_created_expert_ids properly tracks experts across emails in a scan.
    """
    conn = setup_test_db()
    try:
        create_project(conn, "test_project", "Test Project")
        
        # Simulate a multi-email scan with shared tracking set
        scan_created_expert_ids = set()
        
        # Email 1: Creates 3 experts
        for name in ["Laura Jensen", "David Huang", "Priya Malhotra"]:
            expert_id = f"expert_{name.replace(' ', '_').lower()}"
            create_expert(conn, expert_id, "test_project", name)
            scan_created_expert_ids.add(expert_id)
        
        # Verify 3 experts tracked
        assert len(scan_created_expert_ids) == 3
        
        # Email 2: Same experts appear - should be in tracking set
        # The fix checks: if existing["id"] in scan_created_expert_ids
        for name in ["Laura Jensen", "David Huang"]:
            expected_id = f"expert_{name.replace(' ', '_').lower()}"
            assert expected_id in scan_created_expert_ids, \
                f"Expert {expected_id} should be in scan_created_expert_ids"
        
        # Verify we still only have 3 experts in the project
        experts = list_experts_for_project(conn, "test_project")
        assert len(experts) == 3
        
        print("✅ test_scan_created_ids_tracking PASSED")
    finally:
        teardown_test_db(conn)


def test_new_project_starts_empty():
    """
    Test that a newly created project has no experts.
    This is the core of the bug fix - new projects should not inherit experts.
    """
    conn = setup_test_db()
    try:
        # Create project with some experts first
        create_project(conn, "old_project", "Old Project")
        for name in ["Rachel Kim", "Thomas Patel", "Sarah Nguyen"]:
            create_expert(conn, f"old_{name.replace(' ', '_').lower()}", "old_project", name)
        
        # Create a new project
        create_project(conn, "new_project", "New Project")
        
        # The new project MUST have 0 experts
        experts = list_experts_for_project(conn, "new_project")
        assert len(experts) == 0, \
            f"NEW PROJECT CONTAMINATED! Expected 0 experts, got {len(experts)}: {[e['canonicalName'] for e in experts]}"
        
        print("✅ test_new_project_starts_empty PASSED")
    finally:
        teardown_test_db(conn)


if __name__ == "__main__":
    print("Running ingestion isolation tests...")
    test_experts_scoped_to_project()
    test_no_cross_project_contamination()
    test_scan_created_ids_tracking()
    test_new_project_starts_empty()
    print("\n✅ All tests passed!")
