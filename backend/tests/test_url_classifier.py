"""Tests for URL classifier with reputation scoring."""

import pytest
from src.services.tools.url_classifier import URLClassifier, URLType


class TestURLClassify:
    def test_arxiv(self):
        info = URLClassifier.classify("https://arxiv.org/abs/2301.12345")
        assert info.type == URLType.ARXIV
        assert info.reputation == 0.85

    def test_pubmed(self):
        info = URLClassifier.classify("https://pubmed.ncbi.nlm.nih.gov/12345678/")
        assert info.type == URLType.PUBMED
        assert info.reputation == 0.85

    def test_wikipedia(self):
        info = URLClassifier.classify("https://en.wikipedia.org/wiki/Quantum")
        assert info.type == URLType.WIKIPEDIA
        assert info.reputation == 0.65

    def test_gov(self):
        info = URLClassifier.classify("https://www.nasa.gov/mission")
        assert info.type == URLType.GOV
        assert info.reputation == 0.90

    def test_edu(self):
        info = URLClassifier.classify("https://csail.mit.edu/research")
        assert info.type == URLType.EDU
        assert info.reputation == 0.60

    def test_top_news_reuters(self):
        info = URLClassifier.classify("https://www.reuters.com/article/xyz")
        assert info.type == URLType.NEWS_TOP
        assert info.reputation == 0.80

    def test_top_news_bbc(self):
        info = URLClassifier.classify("https://www.bbc.com/news/science-123")
        assert info.type == URLType.NEWS_TOP

    def test_mid_news(self):
        info = URLClassifier.classify("https://techcrunch.com/article")
        assert info.type == URLType.NEWS
        assert info.reputation == 0.70

    def test_blog_medium(self):
        info = URLClassifier.classify("https://medium.com/@user/post")
        assert info.type == URLType.BLOG
        assert info.reputation == 0.30

    def test_social_twitter(self):
        info = URLClassifier.classify("https://twitter.com/user/status/123")
        assert info.type == URLType.SOCIAL
        assert info.reputation == 0.15

    def test_social_reddit(self):
        info = URLClassifier.classify("https://reddit.com/r/programming")
        assert info.type == URLType.SOCIAL

    def test_suspicious(self):
        info = URLClassifier.classify("https://t.me/somechannel")
        assert info.type == URLType.SUSPICIOUS
        assert info.reputation == 0.05

    def test_generic_html(self):
        info = URLClassifier.classify("https://someblog.com/post")
        assert info.type == URLType.HTML
        assert info.reputation == 0.35

    def test_invalid_javascript(self):
        info = URLClassifier.classify("javascript:alert(1)")
        assert info.type == URLType.INVALID
        assert info.reputation == 0.0

    def test_pdf(self):
        info = URLClassifier.classify("https://example.com/report.pdf")
        assert info.type == URLType.PDF

    def test_classify_batch(self):
        infos = URLClassifier.classify_batch([
            "https://arxiv.org/abs/1",
            "https://en.wikipedia.org/wiki/X",
            "https://example.com/blog",
        ])
        assert infos[0].type == URLType.ARXIV
        assert infos[1].type == URLType.WIKIPEDIA
        assert infos[2].type == URLType.HTML

    def test_score(self):
        assert URLClassifier.score("https://arxiv.org/abs/1") == 0.85
        assert URLClassifier.score("https://t.me/x") == 0.05
        assert URLClassifier.score("https://example.com") == 0.35

    def test_reputation_ordering(self):
        """Higher reputation sources should score higher."""
        assert URLType.GOV.reputation > URLType.NEWS_TOP.reputation
        assert URLType.NEWS_TOP.reputation > URLType.NEWS.reputation
        assert URLType.NEWS.reputation > URLType.BLOG.reputation
        assert URLType.BLOG.reputation > URLType.SOCIAL.reputation
        assert URLType.SOCIAL.reputation > URLType.SUSPICIOUS.reputation
