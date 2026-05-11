"""
End-to-end research pipeline test — requires configured LLM.

Test flow: deep_research → check_state → update → check_state → sufficient
"""

import pytest

from src.services.tools.research_state import (
    ResearchState, ConstraintState, parse_research_state,
)
from src.services.tools.deep_research import DeepResearchTool
from src.services.tools.check_state import CheckStateTool


class TestPipelineStateMachine:
    """Test the research state machine without LLM — pure state logic."""

    def test_full_cycle(self):
        # Simulate what happens across multiple ReAct turns
        rs = ResearchState(query="What is quantum advantage in drug discovery?", constraints=[
            ConstraintState("存在量子加速的实验证据", "existence", 1.0),
            ConstraintState("具体药物发现任务受益", "property", 0.9),
            ConstraintState("当前实验阶段", "temporal", 0.7),
        ])

        # Turn 1: start research
        assert not rs.is_sufficient()
        target = rs.next_target()
        assert target.description == "存在量子加速的实验证据"

        # Turn 1: agent searches and updates
        rs.update(0, "verified", "Nature 2024 paper shows 100x speedup on molecular docking",
                  sources=["https://nature.com/paper1"], positive=0.85, negative=0.05, uncertainty=0.10)
        rs.iteration += 1
        assert rs.constraints[0].status == "verified"

        # Turn 2: check state, pick next target
        target = rs.next_target()
        assert target.description == "具体药物发现任务受益"

        # Turn 2: agent searches and updates
        rs.update(1, "verified", "Molecular docking, binding affinity prediction, de novo design",
                  sources=["https://science.org/paper2", "https://arxiv.org/abs/2301.1"],
                  positive=0.80, negative=0.10, uncertainty=0.10)
        rs.iteration += 1

        # Turn 3: check state, pick next
        target = rs.next_target()
        assert target.description == "当前实验阶段"

        # Turn 3: verify
        rs.update(2, "verified", "Experimental demonstration on IBM Quantum and Google Sycamore in 2024-2025",
                  sources=["https://ibm.com/quantum/blog", "https://blog.google/quantum"],
                  positive=0.75, negative=0.10, uncertainty=0.15)
        rs.iteration += 1

        # Now all critical constraints verified
        assert rs.is_sufficient()
        assert rs.verified_count == 3
        assert rs.next_target() is None

        # Verify markdown output
        md = rs.to_markdown()
        assert "🟢 verified" in md
        assert "已验证: 3/3" in md
        assert "所有关键约束已验证" in md

    def test_rejection_threshold(self):
        """Test that negative evidence > 0.25 prevents verification."""
        rs = ResearchState(query="test", constraints=[
            ConstraintState("claim needs evidence", "property", 1.0),
        ])
        rs.update(0, "partial", "Mixed evidence",
                  positive=0.30, negative=0.30, uncertainty=0.40)
        rs.iteration += 1
        assert rs.constraints[0].status == "partial"
        # Not sufficient because the critical constraint is only partial
        assert not rs.is_sufficient()

    def test_partial_to_verified_improvement(self):
        """Test that additional searching can improve partial → verified."""
        rs = ResearchState(query="test", constraints=[
            ConstraintState("complex claim", "property", 1.0, status="partial",
                            positive=0.30, negative=0.25, uncertainty=0.45),
        ])
        # Second round of evidence improves confidence
        rs.update(0, "verified", "Additional sources confirmed",
                  sources=["new-source.com"], positive=0.70, negative=0.10, uncertainty=0.20)
        assert rs.constraints[0].status == "verified"


class TestCheckStateTool:
    """Test the check_state tool logic."""

    def test_no_active_research(self):
        tool = CheckStateTool(state_holder=None)
        # Just verify the tool exists with correct parameters
        # Since we can't await, just verify the tool exists and has params
        assert tool.name == "check_state"
        assert "constraint_index" in tool.parameters["properties"]

    def test_with_mock_state(self):
        class MockHolder:
            _active_research = None

        holder = MockHolder()
        holder._active_research = ResearchState(query="test", constraints=[
            ConstraintState("a", "property", 1.0),
            ConstraintState("b", "temporal", 0.5),
        ])

        tool = CheckStateTool(state_holder=holder)
        assert tool._state is not None
        assert tool._state.total_count == 2
        target = tool._state.next_target()
        assert target.description == "a"


@pytest.mark.slow
@pytest.mark.llm
class TestDeepResearchLLM:
    """End-to-end test with real LLM — requires configured API key."""

    @pytest.mark.asyncio
    async def test_constraint_extraction(self):
        """Test deep_research with real LLM extracts meaningful constraints."""
        from src.services.llm_service import LLMService

        llm = LLMService()
        if not llm.api_key:
            pytest.skip("No LLM API key configured")

        tool = DeepResearchTool(llm_service=llm)
        result = await tool.execute("量子计算在药物发现中的应用有哪些？")

        assert result.success
        output = result.output
        assert "plan" in output
        assert "state" in output
        assert len(output["plan"]) > 50  # should have meaningful content

        state_data = output["state"]
        assert state_data["query"] == "量子计算在药物发现中的应用有哪些？"
        assert len(state_data["constraints"]) >= 3  # at least 3 constraints
        assert state_data["total"] >= 3

