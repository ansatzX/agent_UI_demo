from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List, Sequence

from .models import CreatorProfile, SourceItem, TopicCard, TopicScore
from .profile import default_creator_profile

logger = logging.getLogger(__name__)


class HotspotWorkflow:
    def __init__(
        self,
        profile: CreatorProfile | None = None,
        collectors: Sequence | None = None,
        analyzer=None,
        llm_service=None,
        web_search=None,
    ):
        self.profile = profile or default_creator_profile()
        self.collectors = list(collectors or [])
        self.analyzer = analyzer
        self._llm = llm_service
        self._search = web_search

    async def scan(self, keywords: str, limit: int = 10, days: int = 1) -> List[TopicCard]:
        if not self.collectors:
            return []
        results = await asyncio.gather(
            *[c.collect(keywords=keywords, limit=limit, days=days) for c in self.collectors],
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

    # ── Research-driven card builder ───────────────────────────────────────

    async def _make_card(self, item: SourceItem) -> TopicCard:
        text = f"{item.title} {item.summary}"

        # ── Phase 1: decompose into constraints ───────────────────────
        constraints = []
        evidence_summary: dict = {"total": 0, "verified": 0, "partial": 0, "unverified": 0, "iterations": 0}
        risk_notes: list[str] = []
        enriched_summary = item.summary or item.title
        creator_fit = ""
        angles: list[str] = []
        title_suggestions: list[str] = []
        mindmap = ""

        if self._llm:
            try:
                constraints = await self._extract_constraints(item)
                evidence_summary["total"] = len(constraints)
            except Exception:
                constraints = []

        # ── Phase 2: verify critical constraints ──────────────────────
        verified_sources: list[SourceItem] = [item]
        research_text = f"{item.title}\n{item.summary}"

        for i, c in enumerate(constraints):
            if not c.get("is_critical") and c.get("weight", 0) < 0.8:
                continue

            query = c.get("search_query", c.get("description", ""))
            try:
                sr = None
                if self._search:
                    sr = await self._search.execute(query, max_results=3, fetch_full=False)
            except Exception as exc:
                logger.debug("web_search failed for constraint #%d: %s", i + 1, exc)
                sr = None

            if sr and sr.success and sr.output.get("results"):
                results = sr.output["results"]
                # Grade evidence from search results
                evidence_tiers = [r.get("evidence_tier", "inference") for r in results]
                pos_count = sum(1 for t in evidence_tiers if t in ("research_finding", "official_record", "news_report", "direct_statement"))
                total_results = len(results)

                if total_results > 0 and pos_count / total_results >= 0.5:
                    c["status"] = "verified"
                    evidence_summary["verified"] += 1
                elif total_results > 0:
                    c["status"] = "partial"
                    evidence_summary["partial"] += 1
                    risk_notes.append(
                        f"约束#{i + 1}（{c.get('description', query)[:30]}）: "
                        f"{total_results}个源中仅{pos_count}个有可靠证据"
                    )
                else:
                    c["status"] = "unverified"
                    evidence_summary["unverified"] += 1
                    risk_notes.append(f"约束#{i + 1}（{c.get('description', query)[:30]}）: 未找到相关信息")

                # Capture evidence snippets
                snippets = [r.get("content", "")[:200] for r in results[:2]]
                research_text += "\n\n## 验证: " + query + "\n" + "\n".join(snippets)

                # Track sources
                for r in results[:3]:
                    url = r.get("url", "")
                    if url:
                        verified_sources.append(SourceItem(
                            source="web_search", title=r.get("title", url)[:50],
                            url=url, summary=snippets[0] if snippets else "",
                            evidence_tier=r.get("evidence_tier", "inference"),
                        ))
            else:
                c["status"] = "unverified"
                evidence_summary["unverified"] += 1
                risk_notes.append(
                    f"约束#{i + 1}（{c.get('description', query)[:30]}）: "
                    "搜索无结果，仅有推测级证据"
                )

            evidence_summary["iterations"] += 1

        # ── Phase 3: synthesize with LLM ──────────────────────────────
        if self.analyzer and self._llm:
            try:
                # Enrich item with research findings
                enriched_item = SourceItem(
                    source=item.source, title=item.title, url=item.url,
                    summary=research_text[:3000],
                    heat=item.heat, evidence_tier=item.evidence_tier,
                )
                analysis = await self.analyzer.analyze(enriched_item, self.profile)
                enriched_summary = analysis.get("summary", enriched_summary)
                creator_fit = analysis.get("creator_fit", "")
                angles = analysis.get("angles", [])
                title_suggestions = analysis.get("title_suggestions", [])
                mindmap = analysis.get("mindmap_mermaid", "")
                # Merge analyzer risk notes with evidence-based ones
                analysis_risks = analysis.get("risk_notes", [])
                risk_notes = risk_notes + analysis_risks
            except Exception as exc:
                logger.warning("LLM synthesis failed: %s", exc)

        # ── Phase 4: score with evidence ──────────────────────────────
        evidence_score = 0.5
        total = evidence_summary["total"]
        if total > 0:
            evidence_score = (
                evidence_summary["verified"] * 1.0
                + evidence_summary["partial"] * 0.5
            ) / total
        elif not constraints and self.analyzer:
            # Old path: no research, but we have the old analyzer output
            pass

        score = _score_item(item, text, self.profile)
        score.evidence_score = evidence_score

        # ── Defaults ───────────────────────────────────────────────────
        if not angles:
            angles = _angles_for(item, self.profile)
        if not title_suggestions:
            title_suggestions = [
                f"{item.title}，真正值得关注的不是表面热闹",
                f"从普通人视角看：{item.title}",
            ]
        if not mindmap:
            mindmap = _mindmap_for(item, angles)

        return TopicCard(
            title=item.title,
            summary=enriched_summary,
            score=score,
            sources=verified_sources,
            creator_fit=creator_fit or f"该选题与{_matched_domains(text, self.profile)}相关，具备讨论和讲述空间。",
            angles=angles,
            title_suggestions=title_suggestions,
            mindmap_mermaid=mindmap,
            risk_notes=risk_notes or ["需人工核实关键事实和原始来源"],
            evidence_summary=evidence_summary,
        )

    async def _extract_constraints(self, item: SourceItem) -> list[dict]:
        """Decompose a source item into typed constraints."""
        text = f"{item.title}\n{item.summary}"
        prompt = f"""将此热点事件分解为可验证的子约束，用于事实核查和选题分析。

事件：{text[:2000]}

输出 JSON 列表，每项包含：
- "type": property|event|statistic|temporal|comparison|existence
- "description": 需要验证的具体事实
- "weight": 0.3-1.0（核心事实=1.0，次要细节=0.3）
- "search_query": 用于 web search 的具体查询词
- "is_critical": true（weight>=0.8时）或 false

聚焦于：核心事实是否成立、是否有官方回应、不同方观点和论据、争议焦点。

返回纯 JSON 列表，最多 8 项。"""

        resp = await self._llm.generate_response(
            system_prompt="你是事实核查约束分析器。只输出 JSON。",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )
        content = resp.get("content", "[]")
        import json as _json
        from json_repair import repair_json
        try:
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                return _json.loads(repair_json(content[start:end]))
        except Exception:
            pass
        return []


# ── Helpers ────────────────────────────────────────────────────────────────

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
        "普通人视角：这件事会如何影响日常生活、就业、消费或安全感？",
        "利益结构：谁受益、谁受损、谁在塑造叙事？",
        "舆论分裂：支持者和反对者分别抓住了哪些事实与情绪？",
        f"长期趋势：它是否是{profile.focus_domains[0] if profile.focus_domains else '社会'}变化的信号？",
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
        evidence = ""
        if card.evidence_summary and card.evidence_summary.get("total", 0) > 0:
            ev = card.evidence_summary
            evidence = f"\n**证据链**: 已验证 {ev.get('verified',0)}/{ev.get('total',0)} 约束 (迭代 {ev.get('iterations',0)} 轮)"
        sections.append(f"""## {idx}. {card.title}

**综合分：{card.score.total:.3f}**  
热度 {card.score.heat:.2f} / 匹配度 {card.score.relevance:.2f} / 争议度 {card.score.controversy:.2f} / 可讲述性 {card.score.explainability:.2f}{evidence}

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
