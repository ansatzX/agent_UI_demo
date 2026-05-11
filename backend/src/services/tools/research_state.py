"""
Research state tracker — constraint-level evidence tracking across turns.

Distilled from LDR EvidenceBasedStrategy:
  candidate.get_unverified_constraints() → pick highest-weight → search → evidence → score

This module provides a lightweight state machine that tracks:
  - Which constraints have been verified (with what confidence)
  - Current knowledge gaps
  - Accumulated evidence
  - Termination conditions
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ConstraintState:
    """State of a single constraint in the research."""

    description: str
    ctype: str
    weight: float
    status: str = "unverified"  # unverified | partial | verified
    evidence_summary: str = ""
    sources: List[str] = field(default_factory=list)
    positive: float = 0.0
    negative: float = 0.0
    uncertainty: float = 0.0


@dataclass
class ResearchState:
    """Tracks research progress across multiple ReAct turns."""

    query: str
    constraints: List[ConstraintState] = field(default_factory=list)
    iteration: int = 0

    @property
    def unverified(self) -> List[ConstraintState]:
        return [c for c in self.constraints if c.status == "unverified"]

    @property
    def critical_unverified(self) -> List[ConstraintState]:
        return [c for c in self.unverified if c.weight >= 0.8]

    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.constraints if c.status == "verified")

    @property
    def total_count(self) -> int:
        return len(self.constraints)

    def is_sufficient(
        self, confidence_threshold: float = 0.85, max_iterations: int = 20,
    ) -> bool:
        """LDR's _has_sufficient_answer: all critical constraints verified."""
        if self.iteration >= max_iterations:
            return True
        critical = [c for c in self.constraints if c.weight >= 0.8]
        if not critical:
            return self.verified_count >= self.total_count * 0.8
        return all(c.status == "verified" for c in critical)

    def update(
        self,
        constraint_index: int,
        status: str,
        evidence: str = "",
        sources: List[str] | None = None,
        positive: float = 0.0,
        negative: float = 0.0,
        uncertainty: float = 0.0,
    ) -> ConstraintState | None:
        """Update a constraint's state after evidence search."""
        if 0 <= constraint_index < len(self.constraints):
            c = self.constraints[constraint_index]
            if status:
                c.status = status
            if evidence:
                c.evidence_summary = evidence
            if sources:
                c.sources.extend(sources)
            c.positive = max(c.positive, positive)
            c.negative = max(c.negative, negative)
            c.uncertainty = max(c.uncertainty, uncertainty)
            return c
        return None

    def next_target(self) -> ConstraintState | None:
        """LDR's get_unverified_constraints → pick highest weight."""
        unverified = self.unverified
        if not unverified:
            return None
        return max(unverified, key=lambda c: c.weight)

    def to_markdown(self) -> str:
        """Render current state as a verification checklist."""
        lines = [f"## 研究状态: {self.query}", f"迭代: {self.iteration}", ""]
        lines.append("| # | 约束 | 类型 | 权重 | 状态 | 正面 | 反面 |")
        lines.append("|---|------|------|------|------|------|------|")
        for i, c in enumerate(self.constraints, 1):
            icon = {"verified": "🟢", "partial": "🟡", "unverified": "🔴"}.get(c.status, "⚪")
            pos_str = f"{c.positive:.0%}" if c.positive else "-"
            neg_str = f"{c.negative:.0%}" if c.negative else "-"
            lines.append(
                f"| {i} | {c.description[:40]} | `{c.ctype}` | {c.weight:.1f} | "
                f"{icon} {c.status} | {pos_str} | {neg_str} |"
            )
        lines.append("")
        lines.append(f"已验证: {self.verified_count}/{self.total_count}")

        target = self.next_target()
        if target:
            idx = self.constraints.index(target) + 1
            lines.append(f"**下一步**: 验证约束 #{idx} — `{target.description[:60]}`")
        elif self.is_sufficient():
            lines.append("**状态**: ✅ 所有关键约束已验证，可以综合输出。")
        else:
            lines.append("**状态**: 已达到最大迭代次数。")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "iteration": self.iteration,
            "verified": self.verified_count,
            "total": self.total_count,
            "sufficient": self.is_sufficient(),
            "constraints": [
                {
                    "id": i + 1,
                    "description": c.description,
                    "type": c.ctype,
                    "weight": c.weight,
                    "status": c.status,
                    "sources": c.sources,
                    "positive": c.positive,
                    "negative": c.negative,
                    "uncertainty": c.uncertainty,
                }
                for i, c in enumerate(self.constraints)
            ],
        }


def parse_research_state(data: dict) -> ResearchState:
    """Parse a research state from a dictionary (e.g., from deep_research output)."""
    state = ResearchState(query=data.get("query", ""))
    for c in data.get("constraints", []):
        state.constraints.append(ConstraintState(
            description=c.get("description", ""),
            ctype=c.get("type", "property"),
            weight=c.get("weight", 1.0),
            status=c.get("status", "unverified"),
            evidence_summary=c.get("evidence_summary", ""),
            sources=c.get("sources", []),
            positive=c.get("positive", 0.0),
            negative=c.get("negative", 0.0),
            uncertainty=c.get("uncertainty", 0.0),
        ))
    state.iteration = data.get("iteration", 0)
    return state
