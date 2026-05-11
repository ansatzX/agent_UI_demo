"""Tests for research state tracker."""

import pytest
from src.services.tools.research_state import (
    ResearchState, ConstraintState, parse_research_state,
)


class TestConstraintState:
    def test_default_status(self):
        c = ConstraintState(description="test", ctype="property", weight=1.0)
        assert c.status == "unverified"

    def test_with_sources(self):
        c = ConstraintState(description="x", ctype="temporal", weight=0.5,
                            sources=["a.com", "b.com"])
        assert len(c.sources) == 2


class TestResearchState:
    def test_empty(self):
        rs = ResearchState(query="q")
        assert rs.unverified == []
        assert rs.verified_count == 0

    def test_next_target_picks_highest_weight(self):
        rs = ResearchState(query="q", constraints=[
            ConstraintState("a", "property", 0.3),
            ConstraintState("b", "property", 1.0),
            ConstraintState("c", "property", 0.5),
        ])
        target = rs.next_target()
        assert target is not None
        assert target.description == "b"

    def test_next_target_skips_verified(self):
        rs = ResearchState(query="q", constraints=[
            ConstraintState("a", "property", 1.0, status="verified"),
            ConstraintState("b", "property", 0.5),
        ])
        target = rs.next_target()
        assert target is not None
        assert target.description == "b"

    def test_is_sufficient_all_critical_verified(self):
        rs = ResearchState(query="q", constraints=[
            ConstraintState("a", "property", 0.9, status="verified"),
            ConstraintState("b", "temporal", 0.8, status="verified"),
            ConstraintState("c", "location", 0.3, status="unverified"),
        ])
        assert rs.is_sufficient()

    def test_is_sufficient_missing_critical(self):
        rs = ResearchState(query="q", constraints=[
            ConstraintState("a", "property", 0.9, status="unverified"),
        ])
        assert not rs.is_sufficient()

    def test_update(self):
        rs = ResearchState(query="q", constraints=[
            ConstraintState("a", "property", 1.0),
        ])
        rs.update(0, "verified", "Found evidence", ["x.com"],
                  positive=0.8, negative=0.1, uncertainty=0.1)
        assert rs.constraints[0].status == "verified"
        assert rs.constraints[0].sources == ["x.com"]
        assert rs.constraints[0].positive == 0.8

    def test_to_dict(self):
        rs = ResearchState(query="q", constraints=[
            ConstraintState("a", "property", 1.0, status="verified"),
        ])
        rs.iteration = 3
        d = rs.to_dict()
        assert d["query"] == "q"
        assert d["iteration"] == 3
        assert d["verified"] == 1
        assert d["sufficient"]

    def test_parse_from_dict(self):
        d = {
            "query": "test query",
            "iteration": 2,
            "constraints": [
                {"description": "a", "type": "property", "weight": 1.0, "status": "verified"},
                {"description": "b", "type": "temporal", "weight": 0.5, "status": "unverified"},
            ],
        }
        rs = parse_research_state(d)
        assert rs.query == "test query"
        assert rs.iteration == 2
        assert len(rs.constraints) == 2
        assert rs.constraints[0].status == "verified"
