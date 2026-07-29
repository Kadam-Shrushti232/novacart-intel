"""Tests for retrieval and search (Phase 4)."""

import pytest
from app.retrieval.search import _build_metadata_filter


class TestMetadataFilter:
    """Test metadata filter building for Chroma queries."""

    def test_filter_by_single_source_type(self):
        """Build filter for a single source type."""
        filter_dict = _build_metadata_filter(source_types=["order"])
        assert filter_dict == {"source_type": "order"}

    def test_filter_by_multiple_source_types(self):
        """Build filter for multiple source types."""
        filter_dict = _build_metadata_filter(source_types=["order", "refund"])
        assert "$or" in filter_dict
        assert len(filter_dict["$or"]) == 2

    def test_filter_by_date_range(self):
        """Build filter for date range."""
        filter_dict = _build_metadata_filter(date_range=("2024-01-01", "2024-01-31"))
        assert "$and" in filter_dict
        conditions = filter_dict["$and"]
        assert any("$gte" in str(c) for c in conditions)
        assert any("$lte" in str(c) for c in conditions)

    def test_filter_by_date_converts_to_int(self):
        """Verify date strings convert to YYYYMMDD integers."""
        filter_dict = _build_metadata_filter(date_range=("2024-01-15", "2024-01-20"))
        and_conditions = filter_dict["$and"]
        # Find the date_int conditions
        date_conditions = [c for c in and_conditions if "date_int" in str(c)]
        assert len(date_conditions) > 0

    def test_filter_combined_source_and_date(self):
        """Build filter combining source_type and date range."""
        filter_dict = _build_metadata_filter(
            source_types=["refund"],
            date_range=("2024-01-01", "2024-01-31")
        )
        assert "$and" in filter_dict
        # Should have both source_type and date_int conditions
        assert len(filter_dict["$and"]) >= 2

    def test_filter_no_conditions_returns_none(self):
        """Return None when no filters are specified."""
        filter_dict = _build_metadata_filter()
        assert filter_dict is None

    def test_filter_invalid_date_format_ignored(self):
        """Invalid date format is silently ignored."""
        filter_dict = _build_metadata_filter(date_range=("invalid-date", "also-invalid"))
        # Should not crash, and should ignore the invalid dates
        assert filter_dict is None

    def test_filter_partial_date_range(self):
        """Only start_date and end_date are used."""
        filter_dict = _build_metadata_filter(date_range=("2024-01-15", "2024-01-20"))
        assert filter_dict is not None
        # Should contain date_int range conditions
        assert "date_int" in str(filter_dict)
