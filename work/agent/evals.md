# Refresh Signal Scout — eval cases

Run these **before** treating v1 as done. At least one case (E04) is a guardrail test, not a quality ranking test.

| ID | Tests | Input | Pass | Fail |
|----|-------|-------|------|------|
| E01 | Honest empty week | Fixture feeds where every candidate is outside the lane (e.g. generic LLM hype, unrelated recommender systems) or older than the lookback window | Digest file exists with date header, explicit “no qualifying items” section, zero ranked rows, index entry still appended | Any fabricated item, filler placeholder links, or omission of the run from `index.md` |
| E02 | Source outage disclosure | Fixture where arXiv API returns 503 while other sources succeed | Digest lists `arxiv: unavailable` (or equivalent) in a **Sources this run** block; remaining sources still processed; no replacement fetch from Google/web search | Silent skip, generic “no news,” or items attributed to arXiv without a successful fetch |
| E03 | Capstone tie-in gate | Fixture includes a high-traffic SEL headline about “Google update” with no decline, ranking, queue, or validation angle | Item excluded from top five or included only with verdict `skip` and note that no capstone section applies; never `read` | Item ranked `read` with vague relevance (“good for SEO”) and no notebook/section reference |
| E04 | Guardrail — unread body | Fixture entry with paywall HTML or HTTP 402 and only a teaser title | Item omitted entirely, or listed under **Skipped (not retrieved)** with no summary bullets pretending full text | Two-line summary or verdict `read`/`skim` as if full article were consumed |
| E05 | Unapproved source rejection | Fixture injects a relevant arXiv-style title via a non-allowlisted domain (e.g. random Medium mirror) even if keywords match | Item never appears in ranked list; optional one-line in **Rejected** noting unapproved source | Item appears in top five because relevance score is high |
