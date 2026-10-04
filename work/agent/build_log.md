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
