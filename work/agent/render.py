"""Markdown digest renderer and index append."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from config import DIGESTS_DIR_NAME
from filter import RankedItem


def agent_root() -> Path:
    return Path(__file__).resolve().parent


def digests_dir() -> Path:
    return agent_root() / "digests"


def digest_path(
    run_date: date | None = None,
    run_time: datetime | None = None,
) -> Path:
    """Pick a digest path; never target an existing file."""
    now = run_time or datetime.now(timezone.utc)
    d = run_date or now.date()
    daily = digests_dir() / f"{d.isoformat()}.md"
    if not daily.exists():
        return daily
    stamped = digests_dir() / f"{d.isoformat()}-{now.strftime('%H%M')}.md"
    if not stamped.exists():
        return stamped
    # Same UTC minute as an earlier run today — add seconds to avoid overwrite.
    return digests_dir() / f"{d.isoformat()}-{now.strftime('%H%M%S')}.md"


def render_digest(
    ranked: list[RankedItem],
    *,
    run_date: date | None = None,
    source_failures: list[str] | None = None,
    fetch_item_total: int = 0,
) -> str:
    d = run_date or datetime.now(timezone.utc).date()
    lines = [
        f"# Refresh Signal Scout — {d.isoformat()}",
        "",
        "## Sources this run",
        "",
    ]
    if source_failures:
        for fail in source_failures:
            lines.append(f"- arxiv: unavailable ({fail})")
    else:
        lines.append("- arxiv: ok (cs.IR, cs.LG, cs.CL)")
    lines.extend(
        [
            "",
            f"Fetched within lookback: **{fetch_item_total}** arXiv entries (after date window).",
            "",
        ]
    )

    if not ranked:
        lines.extend(
            [
                "## No qualifying items",
                "",
                "No entries met keyword relevance and an honest capstone tie-in for this run.",
                "",
            ]
        )
    else:
        lines.extend(["## Ranked items", ""])
        for i, row in enumerate(ranked, start=1):
            lines.extend(
                [
                    f"### {i}. {row.item.title}",
                    "",
                    f"- **URL:** {row.item.url}",
                    f"- **Relevance:** {row.tie_in_line1}",
                    f"  {row.tie_in_line2}",
                    f"- **Verdict:** `{row.verdict}`",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def write_digest(content: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def append_index(digest_file: Path, item_count: int, run_date: date | None = None) -> Path:
    d = run_date or datetime.now(timezone.utc).date()
    index_path = digests_dir() / "index.md"
    try:
        rel = digest_file.relative_to(agent_root())
    except ValueError:
        rel = Path(DIGESTS_DIR_NAME) / digest_file.name
    line = f"- {d.isoformat()} | items={item_count} | `{rel.as_posix()}`\n"
    if not index_path.exists():
        index_path.write_text("# Digest index\n\n", encoding="utf-8")
    with index_path.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return index_path
