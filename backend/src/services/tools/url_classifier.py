"""
URL classifier with reputation scoring.

Distilled from LDR content_fetcher/url_classifier.py +
journal_reputation_filter.py scoring tiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse


class URLType(Enum):
    ARXIV = ("arxiv", "research_finding", 0.85)
    PUBMED = ("pubmed", "research_finding", 0.85)
    PMC = ("pmc", "research_finding", 0.85)
    SEMANTIC_SCHOLAR = ("semantic_scholar", "research_finding", 0.85)
    BIORXIV = ("biorxiv", "research_finding", 0.70)
    WIKIPEDIA = ("wikipedia", "news_report", 0.65)
    GOV = ("government", "official_record", 0.90)
    EDU = ("education", "news_report", 0.60)
    NEWS_TOP = ("news_top", "news_report", 0.80)
    NEWS = ("news", "news_report", 0.70)
    PDF = ("pdf", "inference", 0.40)
    BLOG = ("blog", "inference", 0.30)
    SOCIAL = ("social", "speculation", 0.15)
    SUSPICIOUS = ("suspicious", "speculation", 0.05)
    HTML = ("webpage", "inference", 0.35)
    INVALID = ("invalid", "speculation", 0.0)

    @property
    def evidence_tier(self) -> str:
        return self.value[1]

    @property
    def reputation(self) -> float:
        return self.value[2]


DANGEROUS_SCHEMES = {"javascript", "data", "file", "vbscript", "about"}

# Top-tier news (high editorial standards)
TOP_NEWS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "wsj.com", "washingtonpost.com", "economist.com",
    "nature.com", "science.org", "bloomberg.com", "ft.com",
    "npr.org", "theguardian.com",
}

# Mid-tier news
NEWS_DOMAINS = {
    "cnn.com", "politico.com", "axios.com", "techcrunch.com",
    "arstechnica.com", "wired.com", "theverge.com",
    "36kr.com", "jiemian.com", "caixin.com", "thepaper.cn", "yicai.com",
    "sciencenews.org", "newscientist.com", "smithsonianmag.com",
    "newyorker.com", "theatlantic.com", "vox.com", "propublica.org",
}

# Blog/self-publishing platforms (lower reputation)
BLOG_DOMAINS = {
    "medium.com", "substack.com", "blogspot.com", "wordpress.com",
    "tumblr.com", "dev.to", "hashnode.dev",
    "zhuanlan.zhihu.com", "jianshu.com", "douban.com",
    "mp.weixin.qq.com",
}

# Social media / user-generated
SOCIAL_DOMAINS = {
    "twitter.com", "x.com", "facebook.com", "reddit.com",
    "instagram.com", "tiktok.com", "weibo.com", "zhihu.com",
    "bilibili.com", "youtube.com", "tieba.baidu.com",
}

# Suspicious / known low-quality
SUSPICIOUS = {
    "t.me", "vk.com", "rutracker.org",
}


@dataclass
class URLInfo:
    url: str
    type: URLType
    source_name: str
    evidence_tier: str
    reputation: float
    extracted_id: str | None = None


class URLClassifier:
    """Classify URLs with reputation scoring."""

    ARXIV_PATTERNS = [
        r"arxiv\.org/abs/", r"arxiv\.org/pdf/", r"arxiv\.org/html/", r"ar5iv\.org/",
    ]
    PUBMED_PATTERNS = [
        r"pubmed\.ncbi\.nlm\.nih\.gov/\d+", r"ncbi\.nlm\.nih\.gov/pubmed/\d+",
    ]
    PMC_PATTERNS = [
        r"ncbi\.nlm\.nih\.gov/pmc/articles/pmc", r"europepmc\.org/article/pmc",
    ]
    SEMANTIC_SCHOLAR = [r"semanticscholar\.org/paper/"]
    BIORXIV = [r"biorxiv\.org/content/", r"medrxiv\.org/content/"]
    DOI = [r"doi\.org/10\.", r"dx\.doi\.org/10\."]
    WIKIPEDIA = [r"wikipedia\.org/wiki/"]
    GOV = [r"\.gov\.", r"\.gov/"]
    EDU = [r"\.edu/"]

    @classmethod
    def classify(cls, url: str) -> URLInfo:
        url_lower = url.lower().strip()

        try:
            parsed = urlparse(url_lower)
            if parsed.scheme in DANGEROUS_SCHEMES:
                return cls._make(URLType.INVALID, url)
            if parsed.scheme and parsed.scheme not in ("http", "https", ""):
                return cls._make(URLType.INVALID, url)
        except Exception:
            return cls._make(URLType.INVALID, url)

        # ── Academic sources ──────────────────────────────────────
        for pats, ut in [
            (cls.ARXIV_PATTERNS, URLType.ARXIV),
            (cls.PMC_PATTERNS, URLType.PMC),
            (cls.PUBMED_PATTERNS, URLType.PUBMED),
            (cls.SEMANTIC_SCHOLAR, URLType.SEMANTIC_SCHOLAR),
            (cls.BIORXIV, URLType.BIORXIV),
            (cls.DOI, URLType.PDF),
            (cls.WIKIPEDIA, URLType.WIKIPEDIA),
            (cls.GOV, URLType.GOV),
            (cls.EDU, URLType.EDU),
        ]:
            for pat in pats:
                if re.search(pat, url_lower):
                    return cls._make(ut, url)

        # ── Domain-based classification ───────────────────────────
        hostname = parsed.hostname or ""

        # Check top-tier news first
        if any(d in hostname for d in TOP_NEWS):
            return cls._make(URLType.NEWS_TOP, url)
        if any(d in hostname for d in NEWS_DOMAINS):
            return cls._make(URLType.NEWS, url)
        if any(d in hostname for d in SOCIAL_DOMAINS):
            return cls._make(URLType.SOCIAL, url)
        if any(d in hostname for d in BLOG_DOMAINS):
            return cls._make(URLType.BLOG, url)
        if any(d in hostname for d in SUSPICIOUS):
            return cls._make(URLType.SUSPICIOUS, url)

        # PDF
        if url_lower.endswith(".pdf") or "/pdf/" in parsed.path:
            return cls._make(URLType.PDF, url)

        return cls._make(URLType.HTML, url)

    @classmethod
    def _make(cls, ut: URLType, url: str) -> URLInfo:
        return URLInfo(
            url=url,
            type=ut,
            source_name=cls._name(ut),
            evidence_tier=ut.evidence_tier,
            reputation=ut.reputation,
            extracted_id=cls._extract_id(url, ut),
        )

    @classmethod
    def _name(cls, ut: URLType) -> str:
        return {
            URLType.ARXIV: "arXiv", URLType.PUBMED: "PubMed",
            URLType.PMC: "PubMed Central", URLType.SEMANTIC_SCHOLAR: "Semantic Scholar",
            URLType.BIORXIV: "bioRxiv/medRxiv", URLType.WIKIPEDIA: "Wikipedia",
            URLType.GOV: "Government", URLType.EDU: "Education",
            URLType.NEWS_TOP: "Top News", URLType.NEWS: "News",
            URLType.BLOG: "Blog", URLType.SOCIAL: "Social Media",
            URLType.SUSPICIOUS: "Suspicious", URLType.PDF: "PDF",
            URLType.HTML: "Webpage", URLType.INVALID: "Invalid",
        }.get(ut, "Unknown")

    @classmethod
    def _extract_id(cls, url: str, ut: URLType) -> str | None:
        if ut == URLType.ARXIV:
            m = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?)", url)
            return m.group(1) if m else None
        if ut == URLType.PUBMED:
            m = re.search(r"/(\d+)/?", url)
            return m.group(1) if m else None
        if ut == URLType.SEMANTIC_SCHOLAR:
            m = re.search(r"/paper/(?:[^/]+/)?([a-f0-9]{40})", url, re.I)
            return m.group(1) if m else None
        return None

    @classmethod
    def classify_batch(cls, urls: list[str]) -> list[URLInfo]:
        return [cls.classify(u) for u in urls]

    @classmethod
    def score(cls, url: str) -> float:
        """Quick reputation score for a single URL."""
        return cls.classify(url).reputation
