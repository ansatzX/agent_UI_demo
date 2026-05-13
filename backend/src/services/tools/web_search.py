"""
Multi-source web search with two-phase retrieval.

Distilled from LDR:
  parallel_search_engine.py → multiple sources in parallel
  search_engine_base.py     → preview → filter → full content
  url_classifier.py         → source type → evidence tier

Phase 1: search all sources in parallel → snippets + source classification
Phase 2: LLM filters snippets for relevance → fetch full content for kept results
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List
from urllib.parse import unquote

import httpx
from bs4 import BeautifulSoup

from .base import Tool, ToolResult
from .url_classifier import URLClassifier, URLInfo

logger = logging.getLogger(__name__)

# ── Bing API ───────────────────────────────────────────────────────────────

_BING_API_KEY = os.getenv("BING_API_KEY")
_BING_API_URL = "https://api.bing.microsoft.com/v7.0/search"


async def _bing_api_search(query: str, count: int = 10) -> List[SearchSnippet]:
    """Search using the official Bing Web Search API."""
    if not _BING_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await c.get(
                _BING_API_URL,
                params={"q": query, "count": count, "mkt": "zh-CN"},
                headers={
                    "Ocp-Apim-Subscription-Key": _BING_API_KEY,
                    "User-Agent": "ResearchBot/1.0",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.debug("Bing API search failed: %s", exc)
        return []

    results = []
    for item in data.get("webPages", {}).get("value", []):
        url = item.get("url", "")
        if not url:
            continue
        info = URLClassifier.classify(url)
        results.append(SearchSnippet(
            title=item.get("name", ""),
            url=url,
            snippet=item.get("snippet", ""),
            source_name=f"Bing/{info.source_name}",
            url_info=info,
        ))
    return results


# ── Per-source search functions ────────────────────────────────────────────

_SEARCH_SOURCES = [
    {
        "name": "Bing",
        "url": "https://cn.bing.com/search",
        "params": lambda q: {"q": q},
        "parse": "bing",
    },
    {
        "name": "Sogou",
        "url": "https://www.sogou.com/web",
        "params": lambda q: {"query": q},
        "parse": "sogou",
    },
    {
        "name": "SearXNG",
        "url": "http://localhost:8080/search",
        "params": lambda q: {"q": q, "format": "json", "categories": "general"},
        "parse": "searxng",
    },
    {
        "name": "DuckDuckGo",
        "url": "https://html.duckduckgo.com/html/",
        "params": lambda q: {"q": q},
        "parse": "ddg",
    },
    {
        "name": "Wikipedia",
        "url": "https://en.wikipedia.org/w/index.php",
        "params": lambda q: {"search": q},
        "parse": "wiki",
    },
]


@dataclass
class SearchSnippet:
    """A single search result snippet with source classification."""

    title: str
    url: str
    snippet: str
    source_name: str = "Web"
    url_info: URLInfo | None = None


@dataclass
class SearchBatch:
    """Aggregated search results across all sources."""

    query: str
    snippets: List[SearchSnippet] = field(default_factory=list)
    source_summary: Dict[str, int] = field(default_factory=dict)


# ── HTML parsers ───────────────────────────────────────────────────────────

def _parse_searxng(data: dict) -> List[SearchSnippet]:
    """Parse SearXNG JSON results."""
    results = []
    for r in data.get("results", []):
        url = r.get("url", "")
        if not url:
            continue
        info = URLClassifier.classify(url)
        results.append(SearchSnippet(
            title=r.get("title", ""),
            url=url,
            snippet=r.get("content", "") or r.get("snippet", ""),
            source_name=f"SearXNG/{r.get('engine', 'web')}",
            url_info=info,
        ))
    return results


def _parse_ddg(html: str) -> List[SearchSnippet]:
    """Parse DuckDuckGo HTML results."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for r in soup.select(".result"):
        a_tag = r.select_one(".result__a")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        url = _extract_ddg_url(a_tag.get("href", ""))
        if not url:
            continue
        snippet_el = r.select_one(".result__snippet")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        info = URLClassifier.classify(url)
        results.append(SearchSnippet(
            title=title, url=url, snippet=snippet,
            source_name=info.source_name, url_info=info,
        ))
    return results


def _parse_wiki(html: str) -> List[SearchSnippet]:
    """Parse Wikipedia search results."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.select(".mw-search-results li"):
        a_tag = li.select_one("a")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True) or a_tag.get("title", "")
        href = a_tag.get("href", "")
        url = f"https://en.wikipedia.org{href}" if href.startswith("/") else href
        desc_div = li.select_one(".searchresult")
        snippet = desc_div.get_text(strip=True) if desc_div else ""
        info = URLClassifier.classify(url)
        results.append(SearchSnippet(
            title=title, url=url, snippet=snippet,
            source_name="Wikipedia", url_info=info,
        ))
    return results


def _extract_ddg_url(href: str) -> str:
    """Extract real URL from DuckDuckGo redirect."""
    m = re.search(r"uddg=(https?://[^&]+)", href)
    if m:
        return unquote(m.group(1))
    if href.startswith("http"):
        return href
    return ""


# ── Full content fetcher ───────────────────────────────────────────────────

async def _fetch_full(url: str, max_chars: int = 5000) -> str:
    """Fetch full text content from a URL (Phase 2)."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as c:
            resp = await c.get(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)",
            })
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(strip=True, separator="\n")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return "\n".join(lines)[:max_chars]
    except Exception as exc:
        logger.debug("Full fetch failed for %s: %s", url, exc)
        return ""


# ── The tool ───────────────────────────────────────────────────────────────

class WebSearchTool(Tool):
    """Multi-source parallel search with two-phase retrieval.

    Phase 1: search DuckDuckGo + Wikipedia in parallel → get snippets
    Phase 2: LLM filters snippets for relevance → fetch full content
             for kept results only.

    The agent should use this instead of guessing URLs for read_webpage.
    """

    name = "web_search"
    description = (
        "Search the web across multiple sources in parallel. "
        "Returns snippets with source classification and evidence tiers. "
        "Use for any question that needs real web information. "
        "For deeper content on specific results, use read_webpage."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query.",
            },
            "max_results": {
                "type": "integer",
                "description": "Max results to return (default 10).",
                "default": 10,
            },
            "fetch_full": {
                "type": "boolean",
                "description": "Fetch full text for top results. Default true.",
                "default": True,
            },
        },
        "required": ["query"],
    }

    def __init__(self, llm_service=None):
        super().__init__()
        self._llm = llm_service

    async def execute(
        self,
        query: str,
        max_results: int = 10,
        fetch_full: bool = True,
    ) -> ToolResult:
        try:
            # ── Phase 1: Parallel search across sources ────────────────
            all_snippets: List[SearchSnippet] = []
            source_counts: Dict[str, int] = {}

            async def _search_source(source: dict) -> List[SearchSnippet]:
                try:
                    async with httpx.AsyncClient(
                        timeout=15.0, follow_redirects=True
                    ) as c:
                        resp = await c.get(
                            source["url"],
                            params=source["params"](query),
                            headers={
                                "User-Agent": (
                                    "Mozilla/5.0 (compatible; ResearchBot/1.0)"
                                ),
                            },
                        )
                        resp.raise_for_status()
                    parser_name = source["parse"]
                    if parser_name == "searxng":
                        try:
                            return _parse_searxng(resp.json())
                        except Exception:
                            pass
                    parser = {"ddg": _parse_ddg, "wiki": _parse_wiki, "bing": _parse_bing, "sogou": _parse_sogou}.get(parser_name)
                    if parser:
                        return parser(resp.text)
                except Exception as exc:
                    logger.debug(
                        "Search source %s failed: %s", source["name"], exc
                    )
                return []

            # ── Bing API (priority) ──────────────────────────────────
            tasks = []
            if _BING_API_KEY:
                tasks.append(_bing_api_search(query, max_results))
            tasks.extend([_search_source(s) for s in _SEARCH_SOURCES])
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for snippets in results:
                if isinstance(snippets, list):
                    for s in snippets:
                        all_snippets.append(s)
                        src = s.source_name
                        source_counts[src] = source_counts.get(src, 0) + 1

            # Deduplicate by URL
            seen: set[str] = set()
            unique: List[SearchSnippet] = []
            for s in all_snippets:
                if s.url and s.url not in seen:
                    seen.add(s.url)
                    unique.append(s)
            all_snippets = unique

            # ── Phase 1.5: LLM fallback when external sources fail ───
            if not all_snippets and self._llm:
                all_snippets = await self._llm_search_fallback(query, max_results)
                for s in all_snippets:
                    source_counts[s.source_name] = source_counts.get(s.source_name, 0) + 1

            # ── Phase 2: LLM relevance filter on snippets ─────────────
            kept = all_snippets
            if self._llm and len(all_snippets) > 3:
                kept = await self._filter_relevance(query, all_snippets, max_results)

            # Cap
            kept = kept[:max_results]

            # ── Phase 3: Fetch full content for kept results ───────────
            if fetch_full and kept:
                full_tasks = [_fetch_full(s.url) for s in kept]
                full_texts = await asyncio.gather(*full_tasks, return_exceptions=True)
                for snippet, text in zip(kept, full_texts):
                    if isinstance(text, str) and text:
                        snippet.snippet = text  # replace snippet with full text

            # ── Build output ───────────────────────────────────────────
            results_out = []
            for i, s in enumerate(kept, 1):
                tier = s.url_info.evidence_tier if s.url_info else "inference"
                results_out.append({
                    "index": i,
                    "title": s.title,
                    "url": s.url,
                    "content": s.snippet,
                    "source_type": s.source_name,
                    "evidence_tier": tier,
                })

            return ToolResult(success=True, output={
                "query": query,
                "results": results_out,
                "total_found": len(all_snippets),
                "kept": len(kept),
                "source_summary": source_counts,
                "instruction": (
                    "Sources tagged with evidence_tier. "
                    "Cross-validate key facts across sources. "
                    "For deeper reading on a specific URL, use read_webpage."
                ),
            })

        except Exception as exc:
            logger.exception("web_search failed: %s", exc)
            return ToolResult(success=False, output={}, error=str(exc))

    async def _filter_relevance(
        self,
        query: str,
        snippets: List[SearchSnippet],
        max_keep: int,
    ) -> List[SearchSnippet]:
        """Phase 2: LLM judges snippet relevance. Keeps only relevant."""
        if not self._llm:
            return snippets[:max_keep]

        preview_text = "\n\n".join(
            f"[{i}] {s.title}\n    {s.snippet[:300]}"
            for i, s in enumerate(snippets)
        )

        prompt = f"""Filter these search results for relevance.

Query: "{query}"

{preview_text}

Return ONLY the 0-based indices of relevant results as comma-separated list.
Example: 0, 2, 5"""

        try:
            response = await self._llm.generate_response(
                system_prompt="You filter search results. Return indices only.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )
            content = response.get("content", "")
            indices = [int(m) for m in re.findall(r"\d+", content)]
            valid = [i for i in indices if 0 <= i < len(snippets)]
            if valid:
                return [snippets[i] for i in valid[:max_keep]]
        except Exception as exc:
            logger.warning("Relevance filter failed: %s", exc)

        return snippets[:max_keep]

    async def _llm_search_fallback(self, query: str, max_results: int) -> List[SearchSnippet]:
        """Use LLM knowledge as search fallback when external sources are unreachable."""
        if not self._llm:
            return []
        prompt = f"""Based on your training data, provide up to {max_results} search results for: "{query}"

Return a JSON array. Each item:
- "title": result title
- "url": a plausible source URL (e.g. news site, official docs)
- "snippet": 2-3 sentence summary of the content

Only output JSON array, no other text. Max {max_results} items."""
        try:
            resp = await self._llm.generate_response(
                system_prompt="You are a web search engine. Return realistic search results as JSON.",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
            )
            content = resp.get("content", "[]")
            import json as _json
            from json_repair import repair_json
            start = content.find("[")
            end = content.rfind("]") + 1
            if start < 0 or end <= start:
                return []
            data = _json.loads(repair_json(content[start:end]))
            snippets = []
            for item in data[:max_results]:
                url = item.get("url", "")
                info = URLClassifier.classify(url) if url else None
                snippets.append(SearchSnippet(
                    title=item.get("title", ""),
                    url=url,
                    snippet=item.get("snippet", ""),
                    source_name="LLM",
                    url_info=info,
                ))
            return snippets
        except Exception as exc:
            logger.warning("LLM search fallback failed: %s", exc)
            return []
def _parse_bing(html: str) -> List[SearchSnippet]:
    """Parse Bing search results."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.select("li.b_algo"):
        a_tag = li.select_one("h2 a")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        url = a_tag.get("href", "")
        if not url or not url.startswith("http"):
            continue
        snippet_el = li.select_one(".b_caption p") or li.select_one("p")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        info = URLClassifier.classify(url)
        results.append(SearchSnippet(
            title=title, url=url, snippet=snippet,
            source_name=info.source_name, url_info=info,
        ))
    return results


def _parse_sogou(html: str) -> List[SearchSnippet]:
    """Parse Sogou search results."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for div in soup.select(".vrwrap"):
        a_tag = div.select_one("h3 a")
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        href = a_tag.get("href", "")
        url = href if href.startswith("http") else f"https://www.sogou.com{href}"
        snippet_el = div.select_one(".str_info") or div.select_one("p")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        info = URLClassifier.classify(url)
        results.append(SearchSnippet(
            title=title, url=url, snippet=snippet,
            source_name="Sogou", url_info=info,
        ))
    return results
