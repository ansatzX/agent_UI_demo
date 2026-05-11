"""
Deep Research — constraint decomposition + research plan scaffolding.

From LDR: the agent learns HOW to research — decompose, verify, iterate.
The ReAct loop drives the actual research.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from .base import Tool, ToolResult
from .research_state import ResearchState, ConstraintState

logger = logging.getLogger(__name__)


# ── Evidence grading (from LDR evidence/base_evidence.py) ──────────────────

class EvidenceTier(Enum):
    DIRECT_STATEMENT = ("direct_statement", 0.95)
    OFFICIAL_RECORD = ("official_record", 0.90)
    RESEARCH_FINDING = ("research_finding", 0.85)
    STATISTICAL_DATA = ("statistical_data", 0.85)
    NEWS_REPORT = ("news_report", 0.75)
    INFERENCE = ("inference", 0.50)
    CORRELATION = ("correlation", 0.30)
    SPECULATION = ("speculation", 0.10)

    @property
    def confidence(self) -> float:
        return self.value[1]

    @property
    def label(self) -> str:
        return self.value[0]

    @classmethod
    def from_label(cls, label: str) -> EvidenceTier:
        for et in cls:
            if et.label == label:
                return et
        return cls.INFERENCE


class ConstraintType(Enum):
    PROPERTY = "property"
    NAME_PATTERN = "name_pattern"
    EVENT = "event"
    STATISTIC = "statistic"
    TEMPORAL = "temporal"
    LOCATION = "location"
    COMPARISON = "comparison"
    EXISTENCE = "existence"


# ── The tool ───────────────────────────────────────────────────────────────

class DeepResearchTool(Tool):
    """Constraint decomposition + verification plan for complex questions.

    Call ONCE at the start. Returns structured constraints and a
    verification checklist. The agent then drives the loop:
      web_search → cross-validate → mark constraint status → repeat.
    """

    name = "deep_research"
    description = (
        "Decompose a complex question into typed, weighted constraints "
        "and return a verification checklist. Use once at investigation "
        "start. Then verify each constraint via web_search + read_webpage."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Research question."},
        },
        "required": ["query"],
    }

    def __init__(self, llm_service=None, state_holder=None):
        super().__init__()
        self._llm = llm_service
        self._holder = state_holder

    async def execute(self, query: str) -> ToolResult:
        if self._llm is None:
            return ToolResult(False, {}, "LLM service unavailable.")

        try:
            constraints_text = await self._extract(query)
            state = self._parse_state(query, constraints_text)

            if self._holder is not None:
                self._holder._active_research = state

            return ToolResult(True, {
                "query": query,
                "plan": constraints_text,
                "state": state.to_dict(),
                "state_markdown": state.to_markdown(),
                "evidence_guide": self._evidence_guide(),
                "next": (
                    "Research state initialized. Call check_state to see "
                    "which constraint to verify next. Then web_search → "
                    "cross-validate → check_state to update progress. "
                    "Repeat until check_state says 'sufficient: true'."
                ),
            })
        except Exception as exc:
            logger.exception("Constraint extraction failed: %s", exc)
            return ToolResult(False, {}, str(exc))

    async def _extract(self, query: str) -> str:
        prompt = f"""Decompose this question into a verification checklist.

Question: {query}

For each constraint, output:
- Type: property | name_pattern | event | statistic | temporal | location | comparison | existence
- Constraint: what to verify
- Weight: 1.0 (critical) to 0.3 (minor)
- Search query: concrete web search to verify

Return as numbered Markdown with these columns:
| # | Type | Constraint | Weight | Search Query | Status |

Leave Status blank (🟢🟡🔴 to be filled after searching)."""

        resp = await self._llm.generate_response(
            system_prompt="You decompose questions into verification checklists.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
        return resp.get("content", "")

    def _parse_state(self, query: str, text: str) -> ResearchState:
        """Attempt to parse constraint list into a ResearchState."""
        import re
        state = ResearchState(query=query)
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line or not line.startswith("|") or "---" in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) < 4:
                continue
            try:
                ctype = parts[1] if len(parts) > 1 else "property"
                desc = parts[2] if len(parts) > 2 else ""
                weight = float(parts[3]) if len(parts) > 3 and parts[3].replace(".", "").isdigit() else 1.0
                if desc and desc not in ("Constraint", "约束"):
                    state.constraints.append(ConstraintState(
                        description=desc, ctype=ctype, weight=weight,
                    ))
            except (ValueError, IndexError):
                continue
        if not state.constraints:
            state.constraints.append(ConstraintState(
                description=query, ctype="property", weight=1.0,
            ))
        return state

    @staticmethod
    def _evidence_guide() -> str:
        return (
            "Evidence tiers (tag each finding):\n"
            "- `direct_statement`(95%): official document\n"
            "- `official_record`(90%): government/institutional\n"
            "- `research_finding`(85%): peer-reviewed\n"
            "- `statistical_data`(85%): traceable stats\n"
            "- `news_report`(75%): reputable media\n"
            "- `inference`(50%): reasonable deduction\n"
            "- `correlation`(30%): observed correlation\n"
            "- `speculation`(10%): unverified claim\n\n"
            "Final synthesis format:\n"
            "[claim] — tier: `xxx` — sources: [urls]"
        )
