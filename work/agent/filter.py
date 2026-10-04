"""Keyword relevance filter and capstone tie-in gate."""

from __future__ import annotations

from dataclasses import dataclass

from config import (
    CAPSTONE_TIE_PHRASES,
    MAX_RANKED_ITEMS,
    RELEVANCE_KEYWORDS,
    APPROVED_SOURCE_PREFIXES,
)
from fetch import ArxivItem


@dataclass
class RankedItem:
    item: ArxivItem
    score: int
    capstone_section: str
    tie_in_line1: str
    tie_in_line2: str
    verdict: str


def _combined_text(item: ArxivItem) -> str:
    return f"{item.title}\n{item.abstract}".lower()


def keyword_score(text: str) -> int:
    score = 0
    for term in RELEVANCE_KEYWORDS:
        if term in text:
            score += 1
    return score


def capstone_tie_in(text: str) -> tuple[str | None, str, str]:
    """Return (section_id, line1, line2) or (None, '', '') if no honest link."""
    lower = text.lower()
    for section, phrases in CAPSTONE_TIE_PHRASES.items():
        hits = [p for p in phrases if p in lower]
        if hits:
            line1 = f"Capstone tie-in: `{section}` — matches themes in title/abstract ({hits[0]})."
            line2 = f"Use in `work/notebooks/{section}_*.ipynb` lane when stress-testing claims or features."
            return section, line1, line2
    return None, "", ""


def verdict_for(score: int, section: str) -> str:
    if score >= 3 and section in ("w03", "w05"):
        return "read"
    if score >= 2:
        return "skim"
    if score >= 1:
        return "skim"
    return "skip"


def filter_and_rank(items: list[ArxivItem]) -> tuple[list[RankedItem], int, int]:
    """
    Score items, apply tie-in gate, cap at MAX_RANKED_ITEMS.
    Returns (ranked, passed_keyword_count, passed_tie_in_count).
    """
    scored: list[tuple[ArxivItem, int]] = []
    for item in items:
        if not (item.abstract or "").strip():
            continue
        text = _combined_text(item)
        score = keyword_score(text)
        if score > 0:
            scored.append((item, score))

    scored.sort(key=lambda x: (-x[1], -x[0].published.timestamp()))

    ranked: list[RankedItem] = []
    passed_tie = 0
    for item, score in scored:
        text = _combined_text(item)
        section, line1, line2 = capstone_tie_in(text)
        if section is None:
            continue
        passed_tie += 1
        ranked.append(
            RankedItem(
                item=item,
                score=score,
                capstone_section=section,
                tie_in_line1=line1,
                tie_in_line2=line2,
                verdict=verdict_for(score, section),
            )
        )
        if len(ranked) >= MAX_RANKED_ITEMS:
            break

    return ranked, len(scored), passed_tie


def is_approved_url(url: str) -> bool:
    return any(url.startswith(prefix) for prefix in APPROVED_SOURCE_PREFIXES)


def approved_items(items: list[ArxivItem]) -> list[ArxivItem]:
    return [i for i in items if is_approved_url(i.url)]
