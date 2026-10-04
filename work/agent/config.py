"""Refresh Signal Scout — MVP configuration (arXiv-only)."""

from __future__ import annotations

LOOKBACK_DAYS = 7
MAX_FETCH_PER_CATEGORY = 10
MAX_RANKED_ITEMS = 5

ARXIV_CATEGORIES = ("cs.IR", "cs.LG", "cs.CL")
ARXIV_API_BASE = "https://export.arxiv.org/api/query"

APPROVED_SOURCE_PREFIXES = (
    "https://arxiv.org/",
    "http://arxiv.org/",
    "https://export.arxiv.org/",
)

RELEVANCE_KEYWORDS: tuple[str, ...] = (
    "content refresh",
    "content decline",
    "content decay",
    "learning to rank",
    "search ranking",
    "ctr prediction",
    "seo",
    "click-through",
    "position bias",
    "serp",
    "query performance",
)

# Honest capstone tie-in: section -> phrases that justify linking an item to that notebook lane.
CAPSTONE_TIE_PHRASES: dict[str, tuple[str, ...]] = {
    "w01": (
        "ranked queue",
        "prioritisation",
        "prioritization",
        "content refresh",
        "content decline",
        "refresh budget",
        "traffic recovery",
    ),
    "w02": (
        "target",
        "proxy",
        "ctr",
        "click-through",
        "position",
        "serp",
        "impression",
    ),
    "w03": (
        "leakage",
        "feature",
        "contract",
        "label",
        "temporal",
        "data quality",
    ),
    "w04": (
        "baseline",
        "rule",
        "heuristic",
        "queue",
        "ranking",
    ),
    "w05": (
        "learning to rank",
        "ltr",
        "model",
        "train",
        "validation",
        "prediction",
        "ranker",
    ),
}

DIGESTS_DIR_NAME = "digests"
