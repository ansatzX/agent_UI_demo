"""Tests for deep_research evidence grading and constraint types."""

import pytest
from src.services.tools.deep_research import (
    EvidenceTier,
    ConstraintType,
    DeepResearchTool,
)


class TestEvidenceTier:
    def test_confidence_values(self):
        assert EvidenceTier.DIRECT_STATEMENT.confidence == 0.95
        assert EvidenceTier.OFFICIAL_RECORD.confidence == 0.90
        assert EvidenceTier.RESEARCH_FINDING.confidence == 0.85
        assert EvidenceTier.STATISTICAL_DATA.confidence == 0.85
        assert EvidenceTier.NEWS_REPORT.confidence == 0.75
        assert EvidenceTier.INFERENCE.confidence == 0.50
        assert EvidenceTier.CORRELATION.confidence == 0.30
        assert EvidenceTier.SPECULATION.confidence == 0.10

    def test_order_is_decreasing(self):
        tiers = list(EvidenceTier)
        for i in range(len(tiers) - 1):
            assert tiers[i].confidence >= tiers[i + 1].confidence

    def test_from_label_exact(self):
        assert EvidenceTier.from_label("research_finding") == EvidenceTier.RESEARCH_FINDING
        assert EvidenceTier.from_label("direct_statement") == EvidenceTier.DIRECT_STATEMENT

    def test_from_label_unknown_fallback(self):
        assert EvidenceTier.from_label("nonexistent") == EvidenceTier.INFERENCE

    def test_labels_match(self):
        for tier in EvidenceTier:
            assert EvidenceTier.from_label(tier.label) == tier


class TestConstraintType:
    def test_all_types_exist(self):
        types = {c.value for c in ConstraintType}
        expected = {
            "property", "name_pattern", "event", "statistic",
            "temporal", "location", "comparison", "existence",
        }
        assert types == expected


class TestDeepResearchTool:
    def test_parameters_schema(self):
        tool = DeepResearchTool()
        params = tool.parameters
        assert params["type"] == "object"
        assert "query" in params["required"]
        assert "query" in params["properties"]

    def test_to_definition(self):
        tool = DeepResearchTool()
        d = tool.to_definition()
        assert d["type"] == "function"
        assert d["function"]["name"] == "deep_research"

    def test_execute_without_llm(self):
        tool = DeepResearchTool(llm_service=None)
        assert tool._llm is None
        assert tool._llm is None

    def test_evidence_guide_format(self):
        guide = DeepResearchTool._evidence_guide()
        assert "direct_statement" in guide
        assert "95%" in guide
        assert "speculation" in guide
        assert "10%" in guide
