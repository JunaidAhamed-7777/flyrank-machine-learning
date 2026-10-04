"""Eval cases E01–E05 from work/agent/evals.md."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path

import pytest

from fetch import ArxivItem, fetch_category, items_from_atom_xml
from filter import approved_items, capstone_tie_in, filter_and_rank, is_approved_url, keyword_score
from render import append_index, digests_dir, render_digest, write_digest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class _FakeHTTPError(Exception):
    def __init__(self, code: int):
        self.code = code


def _fake_503_opener(url, timeout=60.0):
    raise _FakeHTTPError(503)


def test_e01_honest_empty_week(tmp_path, monkeypatch):
    """E01: no qualifying items — explicit empty section, index still appended."""
    old_items = [
        ArxivItem(
            title="Unrelated recommender systems",
            abstract="Collaborative filtering for e-commerce.",
            url="https://arxiv.org/abs/1",
            published=datetime.now(timezone.utc),
            categories=("cs.LG",),
        )
    ]
    ranked, _, _ = filter_and_rank(old_items)
    assert ranked == []

    body = render_digest(ranked, run_date=datetime(2026, 3, 30).date())
    assert "No qualifying items" in body
    assert "## Ranked items" not in body

    dig_root = tmp_path / "digests"
    monkeypatch.setattr("render.digests_dir", lambda: dig_root)
    dig = dig_root / "2026-03-30.md"
    write_digest(body, dig)
    idx = append_index(dig, 0, run_date=datetime(2026, 3, 30).date())
    text = idx.read_text(encoding="utf-8")
    assert "2026-03-30" in text
    assert "items=0" in text


def test_e02_source_outage_disclosure():
    """E02: arXiv failure surfaces in digest sources block (MVP: arXiv-only)."""
    import urllib.error

    def opener(url, timeout=60.0):
        raise urllib.error.HTTPError(url, 503, "Service Unavailable", None, io.BytesIO(b""))

    from fetch import fetch_category as fc

    _, flog = fc("cs.IR", opener=opener)
    assert flog.status_code == 503
    failures = [f"arxiv/cs.IR: {flog.error or flog.status_code}"]
    body = render_digest([], source_failures=failures)
    assert "arxiv: unavailable" in body
    assert "503" in body or "arxiv/cs.IR" in body


def test_e03_capstone_tie_in_gate():
    """E03: trendy SEO headline without capstone angle — no read verdict via filter path."""
    item = ArxivItem(
        title=(FIXTURES / "sel_google_update.txt").read_text(encoding="utf-8").splitlines()[0],
        abstract="Industry reacts to search changes with generic SEO tips.",
        url="https://arxiv.org/abs/99",
        published=datetime.now(timezone.utc),
        categories=("cs.IR",),
    )
    ranked, _, _ = filter_and_rank([item])
    assert all(r.verdict != "read" for r in ranked)
    assert len(ranked) == 0


def test_e04_unread_body_not_summarized():
    """E04: paywall / not-retrieved items must not appear as ranked summaries."""
    item = ArxivItem(
        title="CTR prediction behind paywall",
        abstract="",
        url="https://arxiv.org/abs/paywalled",
        published=datetime.now(timezone.utc),
        categories=("cs.IR",),
    )
    ranked, _, _ = filter_and_rank([item])
    assert item not in [r.item for r in ranked]


def test_e05_unapproved_source_rejection():
    """E05: relevant title on non-allowlisted domain is rejected."""
    assert is_approved_url("https://medium.com/mirror/ltr-paper") is False
    mirror = ArxivItem(
        title="Learning to rank for search ranking",
        abstract="CTR prediction and SERP query performance.",
        url="https://evil.example/ltr",
        published=datetime.now(timezone.utc),
        categories=(),
    )
    scored_text = f"{mirror.title}\n{mirror.abstract}".lower()
    assert keyword_score(scored_text) >= 2
    assert approved_items([mirror]) == []
    ranked, _, _ = filter_and_rank(approved_items([mirror]))
    assert ranked == []


def test_fixture_arxiv_parses_and_filters():
    xml = (FIXTURES / "arxiv_sample.xml").read_bytes()
    items = items_from_atom_xml(xml)
    assert len(items) == 2
    ranked, kw, tie = filter_and_rank(items)
    assert kw >= 1
    assert len(ranked) >= 1
    assert ranked[0].verdict in ("read", "skim", "skip")
