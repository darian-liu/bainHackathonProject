"""
Tests for change detection utilities.

These tests verify that the ingestion pipeline correctly distinguishes:
1. No-op ingests (exact duplicates / repeated thread content)
2. True updates (fields changed or newly filled)
3. Proper normalization of "unknown" values
"""

import pytest
from app.services.change_detection import (
    normalize_value,
    normalize_for_comparison,
    values_are_equal,
    is_meaningful_value,
    availability_changed,
    screener_responses_changed,
    format_changed_field,
)


class TestNormalizeValue:
    """Tests for normalize_value function."""

    def test_none_returns_none(self):
        assert normalize_value(None) is None

    def test_empty_string_returns_none(self):
        assert normalize_value("") is None
        assert normalize_value("   ") is None

    def test_tbd_values_return_none(self):
        """TBD and variants should be treated as unknown."""
        assert normalize_value("TBD") is None
        assert normalize_value("tbd") is None
        assert normalize_value("to be determined") is None
        assert normalize_value("To Be Determined") is None

    def test_unknown_values_return_none(self):
        """Various 'unknown' representations should return None."""
        assert normalize_value("unknown") is None
        assert normalize_value("Unknown") is None
        assert normalize_value("UNKNOWN") is None
        assert normalize_value("n/a") is None
        assert normalize_value("N/A") is None
        assert normalize_value("NA") is None
        assert normalize_value("none") is None
        assert normalize_value("None") is None

    def test_meaningful_value_preserved(self):
        """Meaningful values should be preserved (trimmed)."""
        assert normalize_value("John Smith") == "John Smith"
        assert normalize_value("  John Smith  ") == "John Smith"
        assert normalize_value("Feb 10-14") == "Feb 10-14"

    def test_whitespace_collapsed(self):
        """Multiple spaces should be collapsed to single space."""
        assert normalize_value("John   Smith") == "John Smith"
        assert normalize_value("Feb  10  -  14") == "Feb 10 - 14"


class TestValuesAreEqual:
    """Tests for values_are_equal function."""

    def test_both_none_equal(self):
        assert values_are_equal(None, None) is True

    def test_both_unknown_equal(self):
        """Different 'unknown' representations should be equal."""
        assert values_are_equal(None, "TBD") is True
        assert values_are_equal("TBD", "unknown") is True
        assert values_are_equal("N/A", None) is True
        assert values_are_equal("", "tbd") is True

    def test_same_meaningful_values_equal(self):
        assert values_are_equal("John Smith", "John Smith") is True
        assert values_are_equal("  John Smith  ", "John Smith") is True

    def test_case_insensitive_comparison(self):
        """Comparison should be case-insensitive."""
        assert values_are_equal("cleared", "CLEARED") is True
        assert values_are_equal("Pending", "pending") is True

    def test_different_values_not_equal(self):
        assert values_are_equal("John Smith", "Jane Doe") is False
        assert values_are_equal("pending", "cleared") is False

    def test_unknown_vs_meaningful_not_equal(self):
        """Unknown value vs meaningful value should not be equal."""
        assert values_are_equal(None, "John Smith") is False
        assert values_are_equal("TBD", "cleared") is False

    def test_dash_normalization(self):
        """Different dash types should be normalized."""
        # en-dash vs hyphen
        assert values_are_equal("Feb 10–14", "Feb 10-14") is True
        # em-dash vs hyphen
        assert values_are_equal("Feb 10—14", "Feb 10-14") is True


class TestIsMeaningfulValue:
    """Tests for is_meaningful_value function."""

    def test_none_not_meaningful(self):
        assert is_meaningful_value(None) is False

    def test_empty_not_meaningful(self):
        assert is_meaningful_value("") is False
        assert is_meaningful_value("   ") is False

    def test_unknown_values_not_meaningful(self):
        assert is_meaningful_value("TBD") is False
        assert is_meaningful_value("unknown") is False
        assert is_meaningful_value("N/A") is False

    def test_real_values_meaningful(self):
        assert is_meaningful_value("John Smith") is True
        assert is_meaningful_value("cleared") is True
        assert is_meaningful_value("Feb 10-14") is True


class TestAvailabilityChanged:
    """Tests for availability_changed function."""

    def test_both_empty_no_change(self):
        assert availability_changed(None, None) is False
        assert availability_changed(None, []) is False
        assert availability_changed("", None) is False

    def test_same_availability_no_change(self):
        """Same availability in different formats should not count as change."""
        assert availability_changed(
            "Feb 10-14, Feb 15-18",
            ["Feb 10-14", "Feb 15-18"]
        ) is False

    def test_new_availability_is_change(self):
        """Adding availability where none existed is a change."""
        assert availability_changed(None, ["Feb 10-14"]) is True
        assert availability_changed("", ["Feb 10-14"]) is True

    def test_different_availability_is_change(self):
        """Different availability values should be a change."""
        assert availability_changed(
            "Feb 10-14",
            ["Feb 20-24"]
        ) is True

    def test_additional_availability_is_change(self):
        """Adding more availability windows is a change."""
        assert availability_changed(
            "Feb 10-14",
            ["Feb 10-14", "Feb 15-18"]
        ) is True


class TestScreenerResponsesChanged:
    """Tests for screener_responses_changed function."""

    def test_both_empty_no_change(self):
        assert screener_responses_changed(None, None) is False
        assert screener_responses_changed(None, []) is False
        assert screener_responses_changed("[]", None) is False

    def test_same_responses_no_change(self):
        """Same screener responses should not count as change."""
        existing = '[{"question": "Q1", "answer": "My answer"}]'
        new = [{"question": "Q1", "answer": "My answer"}]
        assert screener_responses_changed(existing, new) is False

    def test_new_responses_is_change(self):
        """Adding responses where none existed is a change."""
        assert screener_responses_changed(
            None,
            [{"question": "Q1", "answer": "My answer"}]
        ) is True

    def test_additional_responses_is_change(self):
        """Adding more responses is a change."""
        existing = '[{"question": "Q1", "answer": "Answer 1"}]'
        new = [
            {"question": "Q1", "answer": "Answer 1"},
            {"question": "Q2", "answer": "Answer 2"}
        ]
        assert screener_responses_changed(existing, new) is True


class TestFormatChangedField:
    """Tests for format_changed_field function."""

    def test_basic_field_names(self):
        assert format_changed_field("canonicalEmployer") == "employer"
        assert format_changed_field("canonicalTitle") == "title"
        assert format_changed_field("conflictStatus") == "conflict status"

    def test_network_included_when_meaningful(self):
        assert format_changed_field("availability", "alphasights") == "availability (alphasights)"

    def test_network_excluded_when_unknown(self):
        """Network should not be included if it's unknown/empty."""
        assert format_changed_field("availability", None) == "availability"
        assert format_changed_field("availability", "") == "availability"
        assert format_changed_field("availability", "unknown") == "availability"


class TestNoOpScenario:
    """
    Integration test for the no-op scenario described in the bug report.
    
    Scenario: Ingesting a thread email with quoted content and no new info
    should result in NO changes being reported.
    """

    def test_repeated_content_no_change(self):
        """
        Simulates the scenario where an email thread repeats expert info.
        All comparisons should show no change.
        """
        # Existing expert data (from first email)
        existing = {
            "canonicalName": "Adam Brooks",
            "canonicalEmployer": "Acme Corp",
            "canonicalTitle": "VP Operations",
            "conflictStatus": "pending",
        }
        
        # Extracted data from repeated/quoted thread content
        # (same values, maybe with slight formatting differences)
        extracted = {
            "fullName": "Adam Brooks",
            "employer": "Acme Corp",
            "title": "VP Operations",
            "conflictStatus": "pending",
        }
        
        # All fields should be equal
        assert values_are_equal(
            existing["canonicalEmployer"],
            extracted["employer"]
        ) is True
        
        assert values_are_equal(
            existing["canonicalTitle"],
            extracted["title"]
        ) is True
        
        assert values_are_equal(
            existing["conflictStatus"],
            extracted["conflictStatus"]
        ) is True

    def test_tbd_to_tbd_no_change(self):
        """
        If availability was TBD and is still TBD in quoted content,
        it should NOT be reported as an update.
        """
        # Both are "unknown" - no change
        assert availability_changed("TBD", None) is False
        assert availability_changed(None, []) is False
        assert values_are_equal("TBD", None) is True


class TestRealUpdateScenario:
    """
    Integration test for a real update scenario.
    
    Scenario: Conflict status changes from "pending" to "cleared".
    This SHOULD be reported as an update.
    """

    def test_conflict_status_change_detected(self):
        """Conflict status changing is a real update."""
        assert values_are_equal("pending", "cleared") is False
        assert is_meaningful_value("cleared") is True

    def test_availability_added(self):
        """Adding availability where none existed is a real update."""
        assert availability_changed(None, ["Feb 10-14, 2pm-4pm EST"]) is True
        assert is_meaningful_value("Feb 10-14, 2pm-4pm EST") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
