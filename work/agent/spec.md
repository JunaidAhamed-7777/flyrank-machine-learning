# Refresh Signal Scout — design spec

## 1. Job to be done

The **Refresh Signal Scout** serves one user — the author of the FlyRank content-refresh prioritisation capstone in `work/notebooks/` — with a **single weekly deliverable**: a short, ranked markdown digest of **three to five** new items (research, technical posts, or industry writing) that bear directly on **content decline prediction, refresh queue prioritisation, or SEO signal ranking**. Each item includes a two-line relevance note anchored to a **specific capstone artifact** (e.g. w01 ranked-queue framing, w03 data contract / leakage, w04 baseline queue, w05 model, w06 validation), plus a one-word verdict: `read`, `skim`, or `skip`. Runs are **filter-first**, not exhaustive coverage. **Out of scope for v1:** interactive chat, deep dives on demand, adding sources without explicit approval, authenticated or paywalled content, posting anywhere external, or modifying files outside `work/agent/`.

## 2. User and usage frequency

**Who:** the capstone author; no other readers assumed. **When:** every **Monday 08:00** local time, before notebook work for the week. **Good week:** three to five items, each clearly tied to a notebook or deliverable, at least one item that would change or stress-test a modeling or validation choice; zero filler from generic SEO listicles. **Wasted run:** more than five items, vague “relevant to SEO” blurbs, silent omission of a down source, or items included from outside the approved source list.

## 3. Tools and data needed, with access plan

| Source | Type | Auth required | Access plan | Fallback if unavailable |
|--------|------|---------------|-------------|-------------------------|
| arXiv (cs.IR, cs.LG, cs.CL) | Atom API + category RSS | No | Query `export.arxiv.org/api/query` with category filters and `submittedDate` window; mirror check via `rss.arxiv.org/rss/cs.IR` (and LG, CL) | Record `arxiv: unavailable` in digest header; continue other sources; do not backfill from the open web |
| Google Search Central blog | RSS | No | Fetch `https://developers.google.com/search/blog/rss.xml` (verify URL live before build) | Same: note failure in digest; no substitute blog |
| Search Engine Land | RSS | No | Fetch site RSS feed URL (verify before build — category feed for SEO/product news) | Note failure; do not scrape HTML without an approved fetch module |
| Hugging Face papers hub | Public HTTP API | No | `GET https://huggingface.co/api/papers` with date filter; optional search terms aligned to ranking / retrieval / web search | Note failure; do not use HF datasets requiring login in v1 |
| FlyRank internal channel | — | — | **Not available:** no internal comms endpoint is defined in this repo; v1 uses the four public sources above only | N/A — do not invent or wire Slack/email without a documented endpoint |

**Tools (v1):** read-only HTTP client in Python; markdown renderer; git commit of digest paths only (post-build). **Schedule:** GitHub Actions `workflow_dispatch` + weekly cron (build phase). **Outputs:** `work/agent/digests/YYYY-MM-DD.md`, append row to `work/agent/digests/index.md`.

## 4. Draft instructions (summary)

The agent pulls only from the approved source list for the lookback window (default seven days), drops anything it cannot retrieve in full text or official abstract, scores items against the capstone lane (decline/trend signals, learning-to-rank / queue output, leakage-safe features, validation honesty), keeps at most five after deduplication, and writes an honest empty digest when nothing qualifies. Uncertainty defaults to **exclude** or `skip`, never invent. Full operating rules live in [`agent_instructions.md`](agent_instructions.md).

## 5. Five eval cases

Summaries below; full inputs and pass/fail in [`evals.md`](evals.md).

| ID | One-line description |
|----|------------------------|
| E01 | Zero qualifying items in the window — digest states empty run, no fabricated entries. |
| E02 | One approved source returns HTTP error — digest names the source and continues without silent substitution. |
| E03 | Trendy SEO post with no tie to a named capstone section — excluded or marked `skip`, not promoted to top five. |
| E04 | **Guardrail:** paywalled or body-not-retrieved item — must not appear as summarised content. |
| E05 | Relevant paper discovered only via an unapproved domain — rejected even if on-topic. |

## 6. Risks and guardrails

**Must confirm:**

- Any write outside `work/agent/digests/` or `work/agent/digests/index.md`.
- Any addition, removal, or reorder of the approved source list.
- Any use of credentials, cookies, or API keys for gated content.
- Any change to max items per run (five) or verdict vocabulary (`read` / `skim` / `skip`).
- Enabling git push from the workflow to a branch other than the user’s intended integration branch.

**Must never do:**

- Post to Slack, email, social, or any external platform.
- Fetch from authenticated or paywalled sources and pretend the body was read.
- Modify any file outside `work/agent/` (including notebooks, data, skills).
- Summarise a source that was not successfully retrieved (metadata-only is allowed only if abstract is present and labeled as abstract-only).
- Emit more than five ranked items in a single run.
- Pull from sources not listed in section 3.
- Store or log private client names, warehouse queries, or raw capstone CSV rows in the digest.

## 7. Platform choice

**Chosen:** scripted agent on the **scripting path** — Python fetch/filter/render modules in this repo, triggered weekly by **GitHub Actions**, with guardrails enforced in code (path allowlists, source allowlists, item cap, structured empty-run template).

**Alternative considered:** **Claude Project with connectors and skills.** Useful for ad hoc research chat and pasted eval review, but it does **not** run autonomously on a Monday cron, cannot reliably commit digests into `work/agent/digests/` without custom tooling anyway, and keeps guardrails in natural-language instructions where they drift. A script gives reproducible runs, version-controlled behavior, and explicit failure modes for evals — within the same ~10 h budget once the spec is fixed.

## 8. Build-hour budget

| Phase | Hours |
|-------|------:|
| Spec + source URL verification (this doc) | 1.5 |
| Fetch layer (HTTP + RSS + arXiv parsing) | 2.5 |
| Filter / relevance scoring (keywords + capstone map) | 2.0 |
| Digest renderer + index append | 1.5 |
| Eval harness (fixture feeds + pass/fail checks) | 1.5 |
| GitHub Actions schedule + dry-run | 0.5 |
| Operator README + runbook | 0.5 |
| **Total** | **10.0** |
