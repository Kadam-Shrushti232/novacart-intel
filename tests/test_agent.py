"""Tests for agent citation extraction and reasoning (Phase 5-6)."""

import pytest
from app.agent.agent import RetrievalAgent


class TestCitationExtraction:
    """Test citation extraction from agent answers."""

    def test_extract_single_citation(self):
        """Extract single record_id from (source: X) format."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "The order was placed (source: ORD-001) and shipped."
        citations = agent._extract_citations(text)
        assert citations == ["ORD-001"]

    def test_extract_multiple_citations_in_sources(self):
        """Extract multiple record_ids from (sources: X, Y, Z) format."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "Multiple records (sources: ORD-001, ORD-002, REF-001) show the issue."
        citations = agent._extract_citations(text)
        assert set(citations) == {"ORD-001", "ORD-002", "REF-001"}

    def test_extract_mixed_single_and_plural_sources(self):
        """Extract from both (source: X) and (sources: X, Y) in same text."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "First claim (source: REF-001) and second claim (sources: WH-001, TKT-002)."
        citations = agent._extract_citations(text)
        assert set(citations) == {"REF-001", "WH-001", "TKT-002"}

    def test_extract_ignores_incidental_mentions(self):
        """Don't extract record_ids not in explicit (source: ...) markers."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "ORD-001 had a problem, but we examined ORD-002. The real issue is here (source: REF-001)."
        citations = agent._extract_citations(text)
        assert citations == ["REF-001"]

    def test_extract_empty_for_no_sources(self):
        """Return empty list when no (source: ...) markers are found."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "No citations here, just plain text with ORD-001 mentioned."
        citations = agent._extract_citations(text)
        assert citations == []

    def test_extract_deduplicates_citations(self):
        """Remove duplicate citations."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "First (source: ORD-001) and second (source: ORD-001)."
        citations = agent._extract_citations(text)
        assert citations == ["ORD-001"]

    def test_extract_sorts_citations(self):
        """Return sorted citations for consistency."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "(sources: WH-005, ORD-001, TKT-003)"
        citations = agent._extract_citations(text)
        assert citations == ["ORD-001", "TKT-003", "WH-005"]

    def test_extract_handles_various_record_id_formats(self):
        """Match record_ids with 2+ letter prefix and numeric suffix."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "(sources: ORD-001, REF-099, WH-500, TKT-001, SUP-999)"
        citations = agent._extract_citations(text)
        assert len(citations) == 5
        assert all(len(c) > 0 for c in citations)

    def test_extract_does_not_match_malformed_ids(self):
        """Don't extract malformed record_ids."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        text = "(source: INVALID-RECORD) and (source: ORD-001)"
        citations = agent._extract_citations(text)
        # Only ORD-001 matches the pattern (2-5 letter prefix)
        assert "ORD-001" in citations


class TestPlanningPrompt:
    """Test planning prompt generation."""

    def test_planning_prompt_includes_tools(self):
        """Planning prompt lists all 5 tools."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        prompt = agent._build_planning_prompt("What happened?")
        assert "search_orders" in prompt
        assert "search_refunds" in prompt
        assert "search_tickets" in prompt
        assert "search_suppliers" in prompt
        assert "search_warehouse_logs" in prompt

    def test_planning_prompt_includes_question(self):
        """Planning prompt includes the user's question."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        question = "Why did refunds spike?"
        prompt = agent._build_planning_prompt(question)
        assert question in prompt


class TestSynthesisPrompt:
    """Test synthesis prompt generation."""

    def test_synthesis_prompt_cites_properly(self):
        """Synthesis prompt instructs agent to cite with (source: X) format."""
        agent = RetrievalAgent.__new__(RetrievalAgent)
        tool_calls = []
        prompt = agent._build_synthesis_prompt("What happened?", tool_calls)
        assert "(source: RECORD-ID)" in prompt
        assert "Only cite records that directly support your conclusion" in prompt
