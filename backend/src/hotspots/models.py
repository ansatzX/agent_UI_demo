from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


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
    raw: dict = field(default_factory=dict)


@dataclass
class TopicScore:
    heat: float
    relevance: float
    controversy: float
    explainability: float

    @property
    def total(self) -> float:
        return round(
            self.heat * 0.25
            + self.relevance * 0.35
            + self.controversy * 0.2
            + self.explainability * 0.2,
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
