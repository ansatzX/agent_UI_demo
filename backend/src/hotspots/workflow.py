from __future__ import annotations

import asyncio
from typing import Iterable, List, Sequence

from .models import CreatorProfile, SourceItem, TopicCard, TopicScore
from .profile import default_creator_profile


class HotspotWorkflow:
    def __init__(self, profile: CreatorProfile | None = None, collectors: Sequence | None = None, analyzer=None):
        self.profile = profile or default_creator_profile()
        self.collectors = list(collectors or [])
        self.analyzer = analyzer

    async def scan(self, keywords: str, limit: int = 10, days: int = 1) -> List[TopicCard]:
        if not self.collectors:
            return []
        results = await asyncio.gather(
            *[collector.collect(keywords=keywords, limit=limit, days=days) for collector in self.collectors],
            return_exceptions=True,
        )
        items: list[SourceItem] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            items.extend(result)
        return await self.build_topic_cards(items, top_k=limit)

    async def build_topic_cards(self, items: Iterable[SourceItem], top_k: int = 10) -> List[TopicCard]:
        unique = self._dedupe(items)
        cards = [await self._make_card(item) for item in unique]
        return sorted(cards, key=lambda card: card.score.total, reverse=True)[:top_k]

    def _dedupe(self, items: Iterable[SourceItem]) -> List[SourceItem]:
        seen = set()
        unique = []
        for item in items:
            key = _normalize_title(item.title)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    async def _make_card(self, item: SourceItem) -> TopicCard:
        text = f"{item.title} {item.summary}"
        score = _score_item(item, text, self.profile)
        analysis = {}
        if self.analyzer:
            try:
                analysis = await self.analyzer.analyze(item, self.profile)
            except Exception:
                analysis = {}
        angles = analysis.get("angles") or _angles_for(item, self.profile)
        return TopicCard(
            title=item.title,
            summary=analysis.get("summary") or item.summary or item.title,
            score=score,
            sources=[item],
            creator_fit=analysis.get("creator_fit") or f"为什么适合热点选题：该选题与{_matched_domains(text, self.profile)}相关，具备热点讨论、观点拆解和视频化讲述空间。",
            angles=angles,
            title_suggestions=analysis.get("title_suggestions") or [
                f"{item.title}，真正值得关注的不是表面热闹",
                f"从普通人视角看：{item.title}",
                f"{item.title}背后的利益结构与舆论分裂",
            ],
            mindmap_mermaid=analysis.get("mindmap_mermaid") or _mindmap_for(item, angles),
            risk_notes=analysis.get("risk_notes") or ["需人工核实关键事实和原始来源", "避免使用未证实传言作为核心论据"],
        )


def _normalize_title(title: str) -> str:
    return "".join(ch for ch in title.lower().strip() if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")[:80]


def _score_item(item: SourceItem, text: str, profile: CreatorProfile) -> TopicScore:
    relevance_hits = sum(1 for token in profile.focus_domains if token[:2] in text or token in text)
    lens_hits = sum(1 for token in ["争议", "舆论", "影响", "政策", "公司", "中美", "普通人", "利益"] if token in text)
    relevance = min(1.0, 0.25 + relevance_hits * 0.18 + lens_hits * 0.08)
    controversy = min(1.0, 0.25 + sum(1 for token in ["争议", "热议", "分裂", "冲突", "质疑"] if token in text) * 0.2)
    explainability = min(1.0, 0.45 + lens_hits * 0.07)
    return TopicScore(
        heat=max(0.0, min(1.0, item.heat or 0.4)),
        relevance=relevance,
        controversy=controversy,
        explainability=explainability,
    )


def _matched_domains(text: str, profile: CreatorProfile) -> str:
    matched = [d for d in profile.focus_domains if d[:2] in text or d in text]
    return "、".join(matched[:3]) if matched else "公共议题和舆论争议"


def _angles_for(item: SourceItem, profile: CreatorProfile) -> List[str]:
    return [
        f"普通人视角：这件事会如何影响日常生活、就业、消费或安全感？",
        f"利益结构：谁受益、谁受损、谁在塑造叙事？",
        f"舆论分裂：支持者和反对者分别抓住了哪些事实与情绪？",
        f"长期趋势：它是否是{profile.focus_domains[0]}或{profile.focus_domains[2]}变化的信号？",
    ]


def _mindmap_for(item: SourceItem, angles: List[str]) -> str:
    lines = ["mindmap", f"  root(({item.title[:28]}))", "    事件背景", "    关键事实", "    争议焦点"]
    for angle in angles[:3]:
        lines.append(f"    {angle.split('：', 1)[0]}")
    lines.extend(["    视频表达", "      开头钩子", "      反转点", "      结论与提醒"])
    return "\n".join(lines)


def render_topic_cards_markdown(cards: Sequence[TopicCard]) -> str:
    if not cards:
        return "暂无候选选题。请调整关键词、时间范围或检查数据源配置。"
    sections = []
    for idx, card in enumerate(cards, 1):
        source_lines = "\n".join(f"- [{s.source}] {s.title} {s.url}" for s in card.sources)
        angles = "\n".join(f"{i}. {angle}" for i, angle in enumerate(card.angles, 1))
        titles = "\n".join(f"- {title}" for title in card.title_suggestions)
        risks = "\n".join(f"- {risk}" for risk in card.risk_notes)
        sections.append(f"""## {idx}. {card.title}

**综合分：{card.score.total:.3f}**  
热度 {card.score.heat:.2f} / 匹配度 {card.score.relevance:.2f} / 争议度 {card.score.controversy:.2f} / 可讲述性 {card.score.explainability:.2f}

### 事件摘要
{card.summary}

### 热点选题匹配理由
{card.creator_fit}

### 可切入角度
{angles}

### 推荐标题
{titles}

### 思维导图
```mermaid
{card.mindmap_mermaid}
```

### 风险提示
{risks}

### 来源
{source_lines}
""")
    return "\n---\n".join(sections)
