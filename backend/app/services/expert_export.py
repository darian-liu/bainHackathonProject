"""Service for exporting experts to CSV."""

import csv
from io import StringIO
from typing import List
import databases


async def export_experts_to_csv(
    db: databases.Database,
    project_id: str
) -> str:
    """
    Export all experts for a project to CSV format.

    Returns CSV string with headers and expert data.
    """
    # Fetch all experts with their sources
    experts_rows = await db.fetch_all(
        """
        SELECT e.*,
               COUNT(es.id) as sourceCount
        FROM Expert e
        LEFT JOIN ExpertSource es ON es.expertId = e.id
        WHERE e.projectId = :project_id
        GROUP BY e.id
        ORDER BY e.createdAt DESC
        """,
        {"project_id": project_id}
    )

    # CSV headers
    headers = [
        "Name",
        "Employer",
        "Title",
        "Status",
        "Conflict Status",
        "Conflict ID",
        "Interview Date",
        "Lead Interviewer",
        "Interview Length (hrs)",
        "Hypothesis Match",
        "Hypothesis Notes",
        "AI Recommendation",
        "AI Rationale",
        "Source Count",
        "Created At",
        "Updated At"
    ]

    # Write CSV
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()

    for row in experts_rows:
        expert = dict(row)
        writer.writerow({
            "Name": expert.get("canonicalName", ""),
            "Employer": expert.get("canonicalEmployer", ""),
            "Title": expert.get("canonicalTitle", ""),
            "Status": expert.get("status", ""),
            "Conflict Status": expert.get("conflictStatus", ""),
            "Conflict ID": expert.get("conflictId", ""),
            "Interview Date": expert.get("interviewDate", ""),
            "Lead Interviewer": expert.get("leadInterviewer", ""),
            "Interview Length (hrs)": expert.get("interviewLength", ""),
            "Hypothesis Match": expert.get("hypothesisMatch", ""),
            "Hypothesis Notes": expert.get("hypothesisNotes", ""),
            "AI Recommendation": expert.get("aiRecommendation", ""),
            "AI Rationale": expert.get("aiRecommendationRationale", ""),
            "Source Count": expert.get("sourceCount", 0),
            "Created At": expert.get("createdAt", ""),
            "Updated At": expert.get("updatedAt", "")
        })

    return output.getvalue()
