from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CreatorProfile:
    name: str
    goal: str
    focus_domains: List[str]
    analysis_lens: List[str]
    avoid: List[str]


@dataclass
class SourceItem:
    source: str
    title: str
    url: str = ""
    summary: str = ""
    heat: float = 0.0
    published_at: str = ""
    evidence_tier: str = "inference"  # from EvidenceTier taxonomy
    raw: dict = field(default_factory=dict)


@dataclass
class TopicScore:
    heat: float
    relevance: float
    controversy: float
    explainability: float
    evidence_score: float = 0.5  # avg evidence tier across sources

    @property
    def total(self) -> float:
        return round(
            self.heat * 0.20
            + self.relevance * 0.30
            + self.controversy * 0.15
            + self.explainability * 0.15
            + self.evidence_score * 0.20,
            3,
        )


@dataclass
class TopicCard:
    title: str
    summary: str
    score: TopicScore
    sources: List[SourceItem]
    creator_fit: str
    angles: List[str]
    title_suggestions: List[str]
    mindmap_mermaid: str
    risk_notes: List[str]
    evidence_summary: Dict[str, int] = field(default_factory=dict)
