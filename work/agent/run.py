"""CLI entry: live fetch, filter, render digest."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

_AGENT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _AGENT_DIR.parents[1]
if str(_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENT_DIR))

from fetch import fetch_arxiv_recent  # noqa: E402
from filter import approved_items, filter_and_rank  # noqa: E402
from render import append_index, digest_path, render_digest, write_digest  # noqa: E402


def main() -> int:
    run_date = datetime.now(timezone.utc).date()
    items, _logs, failures = fetch_arxiv_recent()
    items = approved_items(items)
    fetch_total = len(items)

    ranked, keyword_hits, tie_hits = filter_and_rank(items)
    print(f"FILTER keyword_hits={keyword_hits} tie_in_survivors={tie_hits} ranked={len(ranked)}")

    body = render_digest(
        ranked,
        run_date=run_date,
        source_failures=failures if failures else None,
        fetch_item_total=fetch_total,
    )
    out_path = digest_path(run_date)
    write_digest(body, out_path)
    append_index(out_path, len(ranked), run_date=run_date)
    print(f"DIGEST written={out_path.relative_to(_REPO_ROOT).as_posix()}")
    print(f"INDEX appended=work/agent/digests/index.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
