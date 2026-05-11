"""
Research state inspection tool — check/update constraint verification progress.

The agent calls this between web_search rounds to see which constraints
are still unverified and which is the next target.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import Tool, ToolResult
from .research_state import ResearchState, parse_research_state

logger = logging.getLogger(__name__)


class CheckStateTool(Tool):
    """Inspect and update the current research state.

    Call after each web_search or read_webpage to update constraint
    status and find the next target for verification.
    """

    name = "check_state"
    description = (
        "Check the current research state: which constraints are verified, "
        "which are still gaps, and what to search next. "
        "Use after each web_search to update progress and find the next target."
    )
    parameters = {
        "type": "object",
        "properties": {
            "constraint_index": {
                "type": "integer",
                "description": "Constraint number to update (1-based). Omit to just view state.",
            },
            "status": {
                "type": "string",
                "enum": ["verified", "partial", "unverified"],
                "description": "New status for the constraint.",
            },
            "evidence": {
                "type": "string",
                "description": "What evidence was found (1-2 sentences).",
            },
            "positive": {
                "type": "number",
                "description": "Positive confidence (0.0-1.0).",
            },
            "negative": {
                "type": "number",
                "description": "Negative confidence (0.0-1.0).",
            },
            "uncertainty": {
                "type": "number",
                "description": "Uncertainty (0.0-1.0).",
            },
        },
        "required": [],
    }

    def __init__(self, state_holder: Any = None):
        """state_holder: an object with .research_state attribute (e.g. GradioChatHandler)."""
        super().__init__()
        self._holder = state_holder

    @property
    def _state(self) -> ResearchState | None:
        if self._holder and hasattr(self._holder, '_active_research'):
            return self._holder._active_research
        return None

    async def execute(
        self,
        constraint_index: int = 0,
        status: str = "",
        evidence: str = "",
        positive: float = 0.0,
        negative: float = 0.0,
        uncertainty: float = 0.0,
    ) -> ToolResult:
        if self._state is None:
            return ToolResult(
                success=False, output={},
                error="No active research. Call deep_research first to start.",
            )

        state = self._state

        if constraint_index > 0:
            updated = state.update(
                constraint_index - 1,
                status=status or "",
                evidence=evidence,
                positive=positive,
                negative=negative,
                uncertainty=uncertainty,
            )
            if updated is None:
                return ToolResult(False, {}, f"Invalid constraint index {constraint_index}")
            state.iteration += 1

        target = state.next_target()

        return ToolResult(success=True, output={
            "markdown": state.to_markdown(),
            "state": state.to_dict(),
            "next_target": {
                "index": state.constraints.index(target) + 1 if target else 0,
                "description": target.description if target else "",
                "ctype": target.ctype if target else "",
            } if target else None,
            "sufficient": state.is_sufficient(),
            "instruction": (
                "All critical constraints verified. Synthesize final answer now."
                if state.is_sufficient()
                else f"Next: verify constraint #{state.constraints.index(target) + 1} — {target.description}"
                if target
                else "No constraints to verify."
            ),
        })
