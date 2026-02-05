"""Expert deduplication service."""

import re
import json
from dataclasses import dataclass
from typing import List, Optional
import databases


def normalize_name(name: str) -> str:
    """Normalize a name for comparison (lowercase, trim, remove extra spaces and punctuation)."""
    normalized = name.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)  # Remove extra spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
    return normalized


def normalize_employer(employer: str) -> str:
    """Normalize an employer name for comparison."""
    normalized = employer.lower().strip()
    normalized = re.sub(r'\s+', ' ', normalized)  # Remove extra spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
    # Remove common suffixes
    normalized = re.sub(r'\b(inc|llc|ltd|corp|corporation|company|co)\b', '', normalized)
    return normalized.strip()


def levenshtein_distance(a: str, b: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(a) < len(b):
        return levenshtein_distance(b, a)

    if len(b) == 0:
        return len(a)

    previous_row = range(len(b) + 1)
    for i, c1 in enumerate(a):
        current_row = [i + 1]
        for j, c2 in enumerate(b):
            # j+1 instead of j since previous_row and current_row are one character longer than b
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def string_similarity(a: str, b: str) -> float:
    """Calculate similarity score between two strings (0-1)."""
    if a == b:
        return 1.0
    if len(a) == 0 or len(b) == 0:
        return 0.0

    distance = levenshtein_distance(a, b)
    max_length = max(len(a), len(b))
    return 1.0 - (distance / max_length)


@dataclass
class DedupeMatch:
    """Potential duplicate match between two experts."""
    expert_id_a: str
    expert_id_b: str
    score: float
    match_type: str  # strong_name_employer, medium_name_roles, fuzzy_name_employer


class ExpertDedupeService:
    """Service for finding and managing duplicate experts."""

    async def find_duplicate_candidates(
        self,
        new_expert: dict,
        existing_experts: List[dict]
    ) -> List[DedupeMatch]:
        """
        Find potential duplicates using deterministic rules.

        Rules:
        1. Strong match: exact name + employer (score: 0.95)
        2. Medium match: exact name + overlapping roles (score: 0.75)
        3. Fuzzy match: similar name (>85%) + similar employer (>80%)
        """
        matches = []

        normalized_name_new = normalize_name(new_expert["canonicalName"])
        employer_new = new_expert.get("canonicalEmployer")
        normalized_employer_new = normalize_employer(employer_new) if employer_new else None

        for existing in existing_experts:
            # Skip self
            if existing["id"] == new_expert["id"]:
                continue

            match = self._compare_experts(
                new_expert,
                existing,
                normalized_name_new,
                normalized_employer_new
            )

            if match:
                matches.append(match)

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def _compare_experts(
        self,
        expert_a: dict,
        expert_b: dict,
        normalized_name_a: str,
        normalized_employer_a: Optional[str]
    ) -> Optional[DedupeMatch]:
        """Compare two experts and return match if they're similar enough."""
        # Normalize expert B
        normalized_name_b = normalize_name(expert_b["canonicalName"])
        employer_b = expert_b.get("canonicalEmployer")
        normalized_employer_b = normalize_employer(employer_b) if employer_b else None

        # Check name similarity
        exact_name_match = normalized_name_a == normalized_name_b
        name_similarity = string_similarity(normalized_name_a, normalized_name_b)
        fuzzy_name_match = name_similarity > 0.85

        if not exact_name_match and not fuzzy_name_match:
            return None

        # Check employer similarity
        exact_employer_match = False
        employer_similarity = 0.0
        fuzzy_employer_match = False

        if normalized_employer_a and normalized_employer_b:
            exact_employer_match = normalized_employer_a == normalized_employer_b
            employer_similarity = string_similarity(normalized_employer_a, normalized_employer_b)
            fuzzy_employer_match = employer_similarity > 0.8

        # Rule 1: Strong match - exact name + exact employer
        if exact_name_match and exact_employer_match:
            return DedupeMatch(
                expert_id_a=expert_a["id"],
                expert_id_b=expert_b["id"],
                score=0.95,
                match_type="strong_name_employer"
            )

        # Rule 2: Medium match - exact name (with or without employer)
        if exact_name_match:
            # Check title similarity if employer missing
            if not normalized_employer_a or not normalized_employer_b:
                title_a = expert_a.get("canonicalTitle", "").lower()
                title_b = expert_b.get("canonicalTitle", "").lower()
                title_similarity = string_similarity(title_a, title_b)

                if title_similarity > 0.7 or (not title_a and not title_b):
                    return DedupeMatch(
                        expert_id_a=expert_a["id"],
                        expert_id_b=expert_b["id"],
                        score=0.65,
                        match_type="medium_name_roles"
                    )
            else:
                # Have employers but they don't match - check for role overlap
                return DedupeMatch(
                    expert_id_a=expert_a["id"],
                    expert_id_b=expert_b["id"],
                    score=0.75,
                    match_type="medium_name_roles"
                )

        # Rule 3: Fuzzy match - fuzzy name + fuzzy employer
        if fuzzy_name_match and fuzzy_employer_match:
            combined_score = 0.6 * name_similarity * employer_similarity
            return DedupeMatch(
                expert_id_a=expert_a["id"],
                expert_id_b=expert_b["id"],
                score=combined_score,
                match_type="fuzzy_name_employer"
            )

        return None

    async def merge_experts(
        self,
        db: databases.Database,
        expert_id_a: str,
        expert_id_b: str
    ) -> dict:
        """
        Merge two experts by moving all sources from one to the other.

        Returns the canonical expert that was kept.
        """
        # Get both experts
        expert_a = await db.fetch_one(
            "SELECT * FROM Expert WHERE id = :id",
            {"id": expert_id_a}
        )
        expert_b = await db.fetch_one(
            "SELECT * FROM Expert WHERE id = :id",
            {"id": expert_id_b}
        )

        if not expert_a or not expert_b:
            raise ValueError("One or both experts not found")

        # Decide which one to keep (more complete data wins)
        score_a = self._calculate_completeness_score(dict(expert_a))
        score_b = self._calculate_completeness_score(dict(expert_b))

        if score_a >= score_b:
            canonical_id = expert_id_a
            merged_id = expert_id_b
        else:
            canonical_id = expert_id_b
            merged_id = expert_id_a

        # Move all sources from merged expert to canonical expert
        await db.execute(
            "UPDATE ExpertSource SET expertId = :canonical_id WHERE expertId = :merged_id",
            {"canonical_id": canonical_id, "merged_id": merged_id}
        )

        # Delete the merged expert (cascade will handle related records)
        await db.execute(
            "DELETE FROM Expert WHERE id = :merged_id",
            {"merged_id": merged_id}
        )

        # Return the canonical expert
        canonical = await db.fetch_one(
            "SELECT * FROM Expert WHERE id = :id",
            {"id": canonical_id}
        )

        return dict(canonical)

    def _calculate_completeness_score(self, expert: dict) -> float:
        """Calculate completeness score for an expert."""
        score = 0.0
        if expert.get("canonicalName"):
            score += 1.0
        if expert.get("canonicalEmployer"):
            score += 1.0
        if expert.get("canonicalTitle"):
            score += 1.0
        # Note: We can't count sources here without a separate query
        return score
