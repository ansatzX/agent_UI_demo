"""Tests for web_search parsing and relevance filtering."""

import pytest
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from src.services.tools.web_search import (
        _parse_searxng,
        _parse_ddg,
        _parse_wiki,
        _extract_ddg_url,
        SearchSnippet,
    )
    _has_web_search = True
except ImportError:
    _has_web_search = False

pytestmark = pytest.mark.skipif(not _has_web_search, reason="bs4/httpx not available")



class TestSearXNGParser:
    def test_empty(self):
        assert _parse_searxng({"results": []}) == []

    def test_single_result(self):
        data = {
            "results": [
                {
                    "title": "Test Title",
                    "url": "https://example.com",
                    "content": "Test snippet",
                    "engine": "google",
                }
            ]
        }
        results = _parse_searxng(data)
        assert len(results) == 1
        assert results[0].title == "Test Title"
        assert results[0].url == "https://example.com"
        assert results[0].snippet == "Test snippet"
        assert "SearXNG" in results[0].source_name

    def test_multiple_results(self):
        data = {
            "results": [
                {"title": "A", "url": "https://a.com", "content": "sa", "engine": "google"},
                {"title": "B", "url": "https://b.com", "content": "sb", "engine": "bing"},
            ]
        }
        results = _parse_searxng(data)
        assert len(results) == 2

    def test_missing_url(self):
        data = {"results": [{"title": "No URL", "content": "x"}]}
        assert _parse_searxng(data) == []


class TestDDGParser:
    def test_empty_html(self):
        results = _parse_ddg("<html></html>")
        assert results == []

    def test_parse_single_result(self):
        html = """
        <div class="result">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https://example.com">Example</a>
            <div class="result__snippet">This is an example snippet.</div>
        </div>
        """
        results = _parse_ddg(html)
        assert len(results) == 1
        assert results[0].title == "Example"
        assert "example.com" in results[0].url
        assert "example snippet" in results[0].snippet

    def test_parse_multiple_results(self):
        html = """
        <div class="result">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https://a.com">A</a>
            <div class="result__snippet">Snippet A</div>
        </div>
        <div class="result">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https://b.com">B</a>
            <div class="result__snippet">Snippet B</div>
        </div>
        """
        results = _parse_ddg(html)
        assert len(results) == 2

    def test_missing_link(self):
        html = '<div class="result"><div class="result__snippet">No link</div></div>'
        results = _parse_ddg(html)
        assert results == []


class TestWikiParser:
    def test_empty(self):
        assert _parse_wiki("<html></html>") == []

    def test_parse_results(self):
        html = """
        <ul class="mw-search-results">
            <li>
                <a href="/wiki/Quantum" title="Quantum">Quantum Computing</a>
                <div class="searchresult">Quantum computing is a type of computation...</div>
            </li>
        </ul>
        """
        results = _parse_wiki(html)
        assert len(results) == 1
        assert results[0].title == "Quantum Computing"
        assert "wikipedia.org/wiki/Quantum" in results[0].url
        assert results[0].source_name == "Wikipedia"


class TestDDGURLExtract:
    def test_extract_uddg(self):
        url = _extract_ddg_url("//duckduckgo.com/l/?uddg=https://example.com/page")
        assert url == "https://example.com/page"

    def test_extract_direct_http(self):
        assert _extract_ddg_url("https://example.com") == "https://example.com"

    def test_extract_empty(self):
        assert _extract_ddg_url("") == ""


class TestSearchSnippet:
    def test_basic(self):
        s = SearchSnippet(
            title="Test", url="https://x.com", snippet="hello",
            source_name="DuckDuckGo",
        )
        assert s.title == "Test"
        assert s.snippet == "hello"
