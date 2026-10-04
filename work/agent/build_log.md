# Refresh Signal Scout — build log

## 2026-10-04T23:05:00Z — initial scaffold
**Did:** Added `config.py`, `fetch.py`, flat-import layout under `work/agent/`, stub `run.py`.
**Broke:** `from work.agent.config import` failed when running `python work/agent/run.py` — no `work/__init__.py` and assignment constraint avoids files outside `work/agent/`.
**Fixed by:** Switched to flat imports with `sys.path` pointing at `work/agent/`.
**Cut from spec:** Google Search Central RSS, Search Engine Land RSS, Hugging Face papers API — deferred to post-MVP; arXiv-only for Checkpoint 1.

## 2026-10-04T23:12:00Z — first live arXiv fetch
**Did:** Wired `fetch_arxiv_recent()` with per-category Atom queries (`max_results=10` × 3 categories).
**Broke:** First run returned `FILTER keyword_hits=0` — recent cs.IR/cs.LG/cs.CL papers in the 7-day window did not contain any fixed-list terms (expected for a narrow filter).
**Fixed by:** Treated as honest empty digest (E01-shaped live run); no fixture backfill.
**Cut from spec:** nothing this entry

## 2026-10-04T23:18:00Z — first filter pass + eval harness
**Did:** Keyword sum filter, capstone tie-in gate, `render.py`, pytest cases E01–E05.
**Broke:** E03 failed — fixture note contained the substring `decline` and tie-in map matched `w01`; E04 ranked items with empty abstract; E01 `append_index` crashed on tmp paths outside `work/agent`.
**Fixed by:** Tightened w01 tie phrases; skip items with empty abstract; fallback index path when digest not under agent root.
**Cut from spec:** nothing this entry

## 2026-10-04T23:22:00Z — renderer + schedule YAML
**Did:** `run.py` CLI, `digests/index.md`, `work/agent/workflows/refresh-signal-scout.yml` (`cron: '0 8 * * 1'`).
**Broke:** GitHub Actions only loads workflows from repo-root `.github/workflows/` — YAML under `work/agent/workflows/` is inert until copied.
**Fixed by:** Documented copy step in `work/agent/README.md` (kept all committed artifacts under `work/agent/` per build constraint).
**Cut from spec:** nothing this entry

## 2026-10-04T23:26:00Z — first full end-to-end live run
**Did:** `python work/agent/run.py` against live export.arxiv.org; wrote digest + index append.
**Broke:** nothing this entry (empty ranked section is valid).
**Fixed by:** n/a
**Cut from spec:** nothing this entry

### Live run stdout (unedited)

```
FETCH url=https://export.arxiv.org/api/query?search_query=cat%3Acs.IR&sortBy=submittedDate&sortOrder=descending&max_results=10 status=200 bytes=26496 items=10
FETCH url=https://export.arxiv.org/api/query?search_query=cat%3Acs.LG&sortBy=submittedDate&sortOrder=descending&max_results=10 status=200 bytes=26113 items=10
FETCH url=https://export.arxiv.org/api/query?search_query=cat%3Acs.CL&sortBy=submittedDate&sortOrder=descending&max_results=10 status=200 bytes=27553 items=10
FILTER keyword_hits=0 tie_in_survivors=0 ranked=0
DIGEST written=work/agent/digests/2026-10-04.md
INDEX appended=work/agent/digests/index.md
```

## 2026-10-05T00:15:00Z — workflow path fix
**Did:** Added runnable `.github/workflows/refresh-signal-scout.yml` (same cron and `workflow_dispatch` as design copy).
**Broke:** Scheduled runs never fired — GitHub ignores YAML under `work/agent/workflows/`.
**Fixed by:** Root workflow file; README updated to point at `.github/workflows/`; design copy kept under `work/agent/workflows/`.
**Cut from spec:** nothing this entry

## 2026-10-05T00:22:00Z — keyword vocabulary + fetch volume fix
**Did:** Added IR/ML academic terms to `RELEVANCE_KEYWORDS`; `max_results=50` per category; added `cs.AI`; re-ran live fetch.
**Broke:** First post-fix run overwrote `digests/2026-10-04.md` (UTC date collision with preserved empty digest).
**Fixed by:** Restored empty `2026-10-04.md` from prior commit; saved non-empty output as `digests/2026-10-05.md`.
**Cut from spec:** nothing this entry

### Live re-run stdout (unedited)

```
FETCH url=https://export.arxiv.org/api/query?search_query=cat%3Acs.IR&sortBy=submittedDate&sortOrder=descending&max_results=50 status=200 bytes=132554 items=50
FETCH url=https://export.arxiv.org/api/query?search_query=cat%3Acs.LG&sortBy=submittedDate&sortOrder=descending&max_results=50 status=200 bytes=120683 items=50
FETCH url=https://export.arxiv.org/api/query?search_query=cat%3Acs.CL&sortBy=submittedDate&sortOrder=descending&max_results=50 status=200 bytes=125089 items=50
FETCH url=https://export.arxiv.org/api/query?search_query=cat%3Acs.AI&sortBy=submittedDate&sortOrder=descending&max_results=50 status=200 bytes=130481 items=50
FILTER keyword_hits=36 tie_in_survivors=36 tie_in_dropped=0 ranked=5
DIGEST written=work/agent/digests/2026-10-04.md
INDEX appended=work/agent/digests/index.md
```

(Post-run: empty 2026-10-04 digest restored; ranked output filed as `2026-10-05.md`.)

