"""HTTP fetch layer for arXiv Atom API."""

from __future__ import annotations

import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlencode

from config import ARXIV_API_BASE, ARXIV_CATEGORIES, LOOKBACK_DAYS, MAX_FETCH_PER_CATEGORY

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}


@dataclass
class FetchLog:
    url: str
    status_code: int
    response_bytes: int
    item_count: int
    error: str | None = None


@dataclass
class ArxivItem:
    title: str
    abstract: str
    url: str
    published: datetime
    categories: tuple[str, ...]
    source_id: str = "arxiv"


def _build_query_url(category: str) -> str:
    params = {
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(MAX_FETCH_PER_CATEGORY),
    }
    return f"{ARXIV_API_BASE}?{urlencode(params)}"


def _parse_published(published_text: str) -> datetime:
    # arXiv uses ISO-like timestamps, e.g. 2026-03-30T12:00:00Z
    text = published_text.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def _parse_feed(xml_bytes: bytes, category: str) -> list[ArxivItem]:
    root = ET.fromstring(xml_bytes)
    items: list[ArxivItem] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        title_el = entry.find("atom:title", ATOM_NS)
        summary_el = entry.find("atom:summary", ATOM_NS)
        published_el = entry.find("atom:published", ATOM_NS)
        id_el = entry.find("atom:id", ATOM_NS)
        if title_el is None or summary_el is None or published_el is None or id_el is None:
            continue
        title = " ".join(title_el.text.split()) if title_el.text else ""
        abstract = " ".join(summary_el.text.split()) if summary_el.text else ""
        published = _parse_published(published_el.text or "")
        raw_id = (id_el.text or "").strip()
        # Prefer abs link
        url = raw_id
        for link in entry.findall("atom:link", ATOM_NS):
            if link.get("title") == "pdf":
                continue
            href = link.get("href")
            if href and "abs" in href:
                url = href
                break
        cats = tuple(
            c.get("term", "")
            for c in entry.findall("atom:category", ATOM_NS)
            if c.get("term")
        )
        items.append(
            ArxivItem(
                title=title,
                abstract=abstract,
                url=url,
                published=published,
                categories=cats or (category,),
            )
        )
    return items


def fetch_category(
    category: str,
    *,
    opener: Callable[..., object] | None = None,
    timeout: float = 60.0,
) -> tuple[list[ArxivItem], FetchLog]:
    url = _build_query_url(category)
    log = FetchLog(url=url, status_code=0, response_bytes=0, item_count=0)
    open_fn = opener or urllib.request.urlopen
    try:
        with open_fn(url, timeout=timeout) as resp:  # type: ignore[call-arg]
            status = getattr(resp, "status", None) or getattr(resp, "code", 200)
            body = resp.read()
            log.status_code = int(status)
            log.response_bytes = len(body)
            items = _parse_feed(body, category)
            log.item_count = len(items)
            return items, log
    except urllib.error.HTTPError as exc:
        log.status_code = exc.code
        try:
            log.response_bytes = len(exc.read())
        except Exception:
            log.response_bytes = 0
        log.error = str(exc)
        return [], log
    except Exception as exc:
        log.error = str(exc)
        return [], log


def fetch_arxiv_recent(
    *,
    opener: Callable[..., object] | None = None,
    log_fn: Callable[[str], None] | None = None,
) -> tuple[list[ArxivItem], list[FetchLog], list[str]]:
    """Fetch recent items from each configured category; log every request."""
    emit = log_fn or print
    all_items: list[ArxivItem] = []
    logs: list[FetchLog] = []
    failures: list[str] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    for category in ARXIV_CATEGORIES:
        items, flog = fetch_category(category, opener=opener)
        emit(
            f"FETCH url={flog.url} status={flog.status_code} "
            f"bytes={flog.response_bytes} items={flog.item_count}"
        )
        logs.append(flog)
        if flog.error or flog.status_code >= 400:
            failures.append(f"arxiv/{category}: {flog.error or flog.status_code}")
            continue
        for item in items:
            if item.published >= cutoff:
                all_items.append(item)

    return all_items, logs, failures


def items_from_atom_xml(xml_bytes: bytes, category: str = "cs.IR") -> list[ArxivItem]:
    """Parse Atom XML (for tests/fixtures)."""
    return _parse_feed(xml_bytes, category)
