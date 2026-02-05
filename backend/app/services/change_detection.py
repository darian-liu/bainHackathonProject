"""
Change detection utilities for ingestion pipeline.

This module provides strict, conservative change detection to ensure
the ingestion summary is truthful and user-trust oriented.

Key principles:
1. Only count as "Updated" if a field MATERIALLY changed
2. Treat null/empty/"TBD"/"unknown"/"N/A" as equivalent (unknown)
3. Normalize whitespace, casing, and formatting before comparison
4. Never report "availability (unknown)" as an update
"""

import re
from typing import Optional, List, Tuple, Any


# Values treated as "unknown" (no meaningful data)
UNKNOWN_VALUES = {
    None,
    "",
    "tbd",
    "TBD", 
    "unknown",
    "Unknown",
    "UNKNOWN",
    "n/a",
    "N/A",
    "na",
    "NA",
    "none",
    "None",
    "NONE",
    "pending",  # For availability, "pending" often means unknown
    "to be determined",
    "to be confirmed",
}


def normalize_value(value: Any) -> Optional[str]:
    """
    Normalize a value for comparison.
    
    - Returns None for unknown/empty values
    - Trims whitespace
    - Collapses repeated spaces
    - Normalizes casing for comparison
    - Normalizes dash types for dates/availability
    
    Args:
        value: The value to normalize
        
    Returns:
        Normalized string or None if value represents "unknown"
    """
    if value is None:
        return None
    
    # Convert to string
    if not isinstance(value, str):
        value = str(value)
    
    # Trim and collapse whitespace
    value = value.strip()
    value = re.sub(r'\s+', ' ', value)
    
    # Check if it's an "unknown" value
    if value.lower() in {v.lower() if isinstance(v, str) else v for v in UNKNOWN_VALUES if v is not None}:
        return None
    
    if value == "":
        return None
    
    return value


def normalize_for_comparison(value: Any) -> Optional[str]:
    """
    Normalize a value for strict equality comparison.
    
    Same as normalize_value but also:
    - Lowercases for case-insensitive comparison
    - Normalizes dashes (en-dash, em-dash -> hyphen)
    - Removes punctuation variations
    """
    normalized = normalize_value(value)
    if normalized is None:
        return None
    
    # Lowercase for comparison
    normalized = normalized.lower()
    
    # Normalize dash types (en-dash, em-dash -> hyphen)
    normalized = normalized.replace('–', '-').replace('—', '-')
    
    # Normalize common punctuation
    normalized = re.sub(r'[,;:]+\s*', ', ', normalized)
    
    return normalized


def values_are_equal(old_value: Any, new_value: Any) -> bool:
    """
    Check if two values are semantically equal.
    
    Returns True if:
    - Both normalize to the same value
    - Both are "unknown" (null/empty/TBD/etc)
    """
    old_normalized = normalize_for_comparison(old_value)
    new_normalized = normalize_for_comparison(new_value)
    
    # Both unknown = equal
    if old_normalized is None and new_normalized is None:
        return True
    
    # One unknown, one not = not equal
    if old_normalized is None or new_normalized is None:
        return False
    
    return old_normalized == new_normalized


def is_meaningful_value(value: Any) -> bool:
    """Check if a value contains meaningful data (not unknown/empty)."""
    return normalize_value(value) is not None


def compute_field_changes(
    existing_data: dict,
    new_data: dict,
    field_mappings: List[Tuple[str, str]]
) -> List[Tuple[str, Any, Any]]:
    """
    Compute which fields have actually changed.
    
    Args:
        existing_data: Current expert data from database
        new_data: Newly extracted data
        field_mappings: List of (existing_field_name, new_field_name) tuples
        
    Returns:
        List of (field_name, old_value, new_value) for fields that actually changed
    """
    changes = []
    
    for existing_field, new_field in field_mappings:
        old_value = existing_data.get(existing_field)
        new_value = new_data.get(new_field)
        
        # Skip if values are semantically equal
        if values_are_equal(old_value, new_value):
            continue
        
        # Skip if new value is not meaningful (don't update with unknown)
        if not is_meaningful_value(new_value):
            continue
        
        # This is a real change
        changes.append((existing_field, old_value, new_value))
    
    return changes


def normalize_availability_list(availability: Optional[List[str]]) -> Optional[str]:
    """
    Normalize an availability list for comparison.
    
    Sorts, normalizes each entry, and joins for comparison.
    """
    if not availability:
        return None
    
    normalized = []
    for item in availability:
        norm = normalize_for_comparison(item)
        if norm:
            normalized.append(norm)
    
    if not normalized:
        return None
    
    # Sort for consistent comparison
    normalized.sort()
    return "|".join(normalized)


def availability_changed(
    existing_availability: Optional[str],
    new_availability: Optional[List[str]]
) -> bool:
    """
    Check if availability has meaningfully changed.
    
    Args:
        existing_availability: Comma-separated availability string from DB
        new_availability: List of availability windows from extraction
        
    Returns:
        True if availability has actually changed
    """
    # Normalize existing (convert from comma-separated string)
    if existing_availability:
        existing_list = [s.strip() for s in existing_availability.split(',')]
    else:
        existing_list = []
    
    existing_normalized = normalize_availability_list(existing_list)
    new_normalized = normalize_availability_list(new_availability)
    
    # Both empty = no change
    if existing_normalized is None and new_normalized is None:
        return False
    
    # One empty, one not = change
    if existing_normalized is None or new_normalized is None:
        return existing_normalized != new_normalized
    
    return existing_normalized != new_normalized


def screener_responses_changed(
    existing_screener: Optional[str],
    new_screener: Optional[List[dict]]
) -> bool:
    """
    Check if screener responses have meaningfully changed.
    
    Args:
        existing_screener: JSON string of existing screener responses
        new_screener: List of new screener response dicts
        
    Returns:
        True if screener responses have actually changed
    """
    import json
    
    # Parse existing
    if existing_screener:
        try:
            existing_list = json.loads(existing_screener)
        except:
            existing_list = []
    else:
        existing_list = []
    
    new_list = new_screener or []
    
    # Both empty = no change
    if not existing_list and not new_list:
        return False
    
    # Normalize and compare
    def normalize_screener_list(items):
        normalized = []
        for item in items:
            if isinstance(item, dict):
                answer = normalize_for_comparison(item.get('answer', ''))
                if answer:
                    normalized.append(answer)
        normalized.sort()
        return normalized
    
    existing_normalized = normalize_screener_list(existing_list)
    new_normalized = normalize_screener_list(new_list)
    
    # Check if new has additional content
    if len(new_normalized) > len(existing_normalized):
        return True
    
    # Check if content differs
    return existing_normalized != new_normalized


def format_changed_field(field_name: str, network: Optional[str] = None) -> str:
    """
    Format a field name for display in the UI.
    
    Never includes "(unknown)" - only includes network if it's meaningful.
    """
    # Map internal field names to display names
    display_names = {
        "canonicalEmployer": "employer",
        "canonicalTitle": "title",
        "conflictStatus": "conflict status",
        "conflictId": "conflict ID",
        "status": "status",
        "availability": "availability",
        "screenerResponses": "screener responses",
    }
    
    display_name = display_names.get(field_name, field_name)
    
    # Only add network if it's a meaningful value
    if network and is_meaningful_value(network):
        return f"{display_name} ({network})"
    
    return display_name
