# Prompt ladder: FlyRank starter dataset explanation (one layer per version)

## The task under test

Explain the FlyRank `content_refresh_anonymized` starter dataset so an ML intern knows what the rows mean and what modeling job the repo expects.

### V0 — baseline

> Explain this data.

**Output:**

> Data is the foundation of analytics and machine learning. In most datasets you will find rows (observations) and columns (variables). Start by loading the file into pandas with `read_csv`, then inspect shape, dtypes, and missing values. Look at summary statistics for numeric columns and value counts for categoricals. Visualization helps: histograms for distributions, scatter plots for relationships. Before modeling, define your target variable and split train/test. If this is business data, stakeholders often care about trends over time; if it is user behavior data, watch for seasonality. Clean duplicates, handle outliers thoughtfully, and document your assumptions. Good EDA saves you from building models on misunderstood fields.

**Changed:** N/A (baseline).

**Improved:** N/A.

**Still failing:** No dataset named; no FlyRank task; reads like a generic ML blog post; zero column names from the starter CSV.

**Next:** Name the dataset and state the intern outcome (what they should *do* with it).

### V1 — adds: a clearer goal

> Explain what the content_refresh_anonymized dataset is for, in a way that helps an ML intern understand what they're supposed to do with it.

**Output:**

> The `content_refresh_anonymized` dataset supports FlyRank’s content-refresh workflow: deciding which pages deserve an update soon. Each row is a page (content item) with search and site analytics rolled up over a recent window, plus metadata about the article and how performance has been moving. As an intern, you use it to learn the problem framing in this repo—what signals exist, what the label means, and how to produce a ranked queue of pages to refresh. Typical steps: read the data dictionary, explore distributions and missingness, build a simple baseline ranker, then train a model that scores pages for refresh priority while avoiding leakage from future or label-derived fields. Your deliverable is not “predict everything about SEO”; it is a reproducible ranking method validated on held-out clients or pages, exported as a queue the product team could act on.

**Changed:** Added an explicit goal tied to the dataset name and the intern’s job (rank pages for refresh).

**Improved:** The answer names the dataset, states row grain (page-level), and points to ranked refresh queues instead of vague “analyze data.”

**Still failing:** No file path, row count, or concrete columns; does not say what the label is or which fields are off-limits; SEO metrics undefined.

**Next:** Lock audience so the answer stops teaching pandas basics and starts defining SEO column vocabulary.

### V2 — adds: a defined audience

> Explain what the content_refresh_anonymized dataset is for, in a way that helps an ML intern understand what they're supposed to do with it. The audience is a first-year CS student who knows Python and pandas but has never worked with SEO data before.

**Output:**

> **Purpose.** `content_refresh_anonymized` is a teaching slice for prioritizing which blog or landing pages a client should refresh first. One row = one page; metrics summarize roughly the last 90 days of search visibility and on-site behavior.
>
> **SEO terms you need here.** *Impressions* = how often the page appeared in Google results; *clicks* = search clicks to the page; *CTR* (click-through rate) = clicks divided by impressions (in this repo, stored as a small number—check the dictionary, it is not a 0–1 fraction). *Average position* = average rank in search results (lower is better). *Sessions* / *pageviews* come from web analytics (GA4-style), not from Google alone.
>
> **Your job as intern.** Explore the CSV, learn which column is the prediction target for “declining” or refresh-worthy pages, and build a model or rules that rank pages for refresh. Use `client_id` for grouped splits so one client’s pages do not leak into train and test. Do not treat raw IDs as features. Read `docs/data-dictionary.md` before feature engineering—several rate and tier columns have non-obvious scaling and missingness patterns.

**Changed:** Added audience: first-year CS, Python/pandas yes, SEO no.

**Improved:** Defines impressions, CTR, and position in plain language and mentions client-level splits instead of assuming the reader knows GSC/GA4.

**Still failing:** Still no path, 30k×44 facts, or enumerated column groups; modeling target named only loosely (“declining”); no structured scan of key fields from the assignment context.

**Next:** Inject repo-grounded context (path, size, named columns, refresh-ranking task).

### V3 — adds: real context

> Explain what the content_refresh_anonymized dataset is for, in a way that helps an ML intern understand what they're supposed to do with it. The audience is a first-year CS student who knows Python and pandas but has never worked with SEO data before. Context: the dataset is `data/raw/content_refresh_anonymized.csv` — 30,000 rows, 44 columns, one row per page per client. Key columns include content_id, client_id, trend_direction, trend_pct, position_tier, ctr, impressions_90d, days_since_last_update, content_age_days, word_count, engagement_rate. The internship task is to build a model that ranks pages for content refresh.

**Output:**

> **What it is.** File: `data/raw/content_refresh_anonymized.csv` — 30,000 rows, 44 columns, one row per page (`content_id`) under a pseudonymized client (`client_id`). It is a snapshot for learning refresh prioritization, not live production traffic.
>
> **How to read the key fields.** `impressions_90d` and `ctr` describe search exposure and click-through over the trailing window; `position_tier` buckets average rank into readable bands (e.g. page 1 vs deeper). `content_age_days` and `days_since_last_update` capture how old the page is and how stale edits are. `word_count` describes article length; `engagement_rate` summarizes on-site engagement from sessions. `trend_pct` and `trend_direction` compare recent vs earlier impression trends—those fields are tied to how the repo defines decline labels, so treat them as label machinery, not free features (see notebook 02 / data dictionary).
>
> **What you build.** Train a ranker that scores each page for refresh priority using legitimate features (volume, engagement, freshness, tiers, etc.), evaluate with client-aware splits, and export a ranked list. Success = sensible top-of-queue pages with honest validation, not claiming you proved why Google changed rankings.

**Changed:** Added file path, dimensions, named key columns, and explicit “rank pages for content refresh” task.

**Improved:** Output cites real columns, states grain, warns that trend fields relate to labels, and ties work to a ranked queue export.

**Still failing:** Long prose blocks; column set incomplete vs full dictionary; easy to skim past grouping rules; no enforced outline for quick onboarding.

**Next:** Require the three-part structure (overview, column groups, modeling task).

### V4 — adds: a specified output format

> Explain what the content_refresh_anonymized dataset is for, in a way that helps an ML intern understand what they're supposed to do with it. The audience is a first-year CS student who knows Python and pandas but has never worked with SEO data before. Context: the dataset is `data/raw/content_refresh_anonymized.csv` — 30,000 rows, 44 columns, one row per page per client. Key columns include content_id, client_id, trend_direction, trend_pct, position_tier, ctr, impressions_90d, days_since_last_update, content_age_days, word_count, engagement_rate. The internship task is to build a model that ranks pages for content refresh. Structure the answer as: (1) one-paragraph overview of what the dataset represents, (2) a bulleted list of the main column groups (identity, content, search, engagement, trend), (3) a two-sentence explanation of the modeling task the dataset supports.

**Output:**

> **Overview.** The starter file `data/raw/content_refresh_anonymized.csv` holds 30,000 pseudonymized pages across clients: each row joins identity (`content_id`, `client_id`), content attributes, 90-day search metrics, on-site engagement, and short-horizon trend fields so you can practice ranking which pages to refresh first without touching live client names.
>
> **Column groups**
> - **Identity:** `content_id`, `client_id` — join keys and split keys only; not model features.
> - **Content:** `word_count`, `content_age_days`, `days_since_last_update` — size and freshness of the page.
> - **Search:** `impressions_90d`, `ctr`, `position_tier` — how visible the page is in search and how often listings get clicked.
> - **Engagement:** `engagement_rate` — on-site session engagement relative to traffic (see dictionary for scaling).
> - **Trend:** `trend_pct`, `trend_direction` — recent vs prior impression movement; label-related in this repo.
>
> **Modeling task.** You fit a scorer that ranks pages for refresh priority using allowed features, then validate with client-grouped holdouts. Export a ordered queue (baseline rules first, then ML) and check that top rows align with dictionary rules—especially that trend label fields never leak into features.

**Changed:** Added mandatory structure: overview paragraph, five group bullets, two-sentence modeling task.

**Improved:** Skimmable grouping maps named columns to roles; identity vs feature use is explicit; modeling steps fit on two sentences.

**Still failing:** Bullets label groups but barely explain non-obvious gotchas (CTR scale, `trend_direction` as label source); trend and search blur for newcomers; no word budget or observational guardrails.

**Next:** Add constraints so claims stay column-grounded and SEO causation stays out.

### V5 — adds: constraints and quality criteria

> Explain what the content_refresh_anonymized dataset is for, in a way that helps an ML intern understand what they're supposed to do with it. The audience is a first-year CS student who knows Python and pandas but has never worked with SEO data before. Context: the dataset is `data/raw/content_refresh_anonymized.csv` — 30,000 rows, 44 columns, one row per page per client. Key columns include content_id, client_id, trend_direction, trend_pct, position_tier, ctr, impressions_90d, days_since_last_update, content_age_days, word_count, engagement_rate. The internship task is to build a model that ranks pages for content refresh. Structure the answer as: (1) one-paragraph overview of what the dataset represents, (2) a bulleted list of the main column groups (identity, content, search, engagement, trend), (3) a two-sentence explanation of the modeling task the dataset supports. Constraints: keep it under 250 words total. Every claim must be traceable to a column named in the context. No claims about SEO causation — the data cannot support them. Use the phrase "in this dataset" at least once to enforce observational language.

**Output:**

> **Overview.** In this dataset, each of 30,000 rows is one page (`content_id`) under one pseudonymized client (`client_id`), with 44 columns summarizing content (`word_count`, `content_age_days`, `days_since_last_update`), search exposure (`impressions_90d`, `ctr`, `position_tier`), engagement (`engagement_rate`), and impression trend (`trend_pct`, `trend_direction`) for refresh prioritization practice.
>
> **Column groups**
> - **Identity:** `content_id`, `client_id`
> - **Content:** `word_count`, `content_age_days`, `days_since_last_update`
> - **Search:** `impressions_90d`, `ctr`, `position_tier`
> - **Engagement:** `engagement_rate`
> - **Trend:** `trend_pct`, `trend_direction`
>
> **Modeling task.** Build a ranker that orders pages for content refresh using features from the groups above, not `content_id`/`client_id` as inputs. Evaluate with client-aware splits and report a ranked queue—describe patterns in `ctr`, `impressions_90d`, and `engagement_rate`, not why Google changed rankings.

**Changed:** Added 250-word cap, column-traceable claims, no causation, required “in this dataset.”

**Improved:** Bullets stay tight; every sentence maps to listed columns; observational wording blocks “refresh fixes rank” stories.

**Still failing:** At 250 words, dropped client-holdout guidance and the label-leakage warning tied to `trend_direction`/`trend_pct`; group bullets are labels only, not the mini-definitions V4 carried.

**Next:** Keep V4’s structure and leakage hint; relax word cap; keep observational rule.

## Honesty check

**V5 did not improve the output versus V4 for this audience.** The cap and “named columns only” rule produced a compliant checklist but stripped the one paragraph that warned trend fields are label machinery and IDs are split keys—not features. A first-year intern can follow the outline and still leak `trend_pct` into a model because the constraint optimized for brevity over the repo’s highest-cost mistake.

## Final reusable prompt

Combines V4’s structure and audience context with V5’s observational guardrail, without the 250-word cap.

```
You are onboarding an ML intern (first-year CS: comfortable with Python/pandas, new to SEO).

Explain what the FlyRank starter dataset is for and what they should do with it.

Context (ground truth — do not invent columns):
- File: data/raw/content_refresh_anonymized.csv
- 30,000 rows × 44 columns; one row per page (content_id) per pseudonymized client (client_id)
- Key columns: content_id, client_id, trend_direction, trend_pct, position_tier, ctr, impressions_90d, days_since_last_update, content_age_days, word_count, engagement_rate
- Intern task: build a model (after a rule baseline) that ranks pages for content refresh; use client_id for grouped train/test splits; never use content_id/client_id/trend_direction/trend_pct as features (trend fields define the decline label in this repo — see docs/data-dictionary.md)

Structure:
1) One short overview paragraph (what the snapshot represents).
2) Bulleted column groups: identity, content, search, engagement, trend — under each, name relevant columns from the list above and one plain-language line on what they measure (define CTR/impressions/position_tier for an SEO newcomer).
3) Exactly two sentences on the modeling task and validation.

Rules:
- Observational only: say "in this dataset" when stating patterns; no claims that refreshing content caused ranking changes.
- Every factual claim must tie to a column named above or to row/grain facts stated here.
- No filler openers; no generic pandas tutorial.
- Point them to docs/data-dictionary.md for rate scaling (ctr is ×100, not 0–1).
```

## Comparison stats

| Version | Prompt words | Output words | Columns named | Jargon count | Structured? | Filler hits | Usefulness (1–5) |
|---------|-------------:|-------------:|--------------:|-------------:|:-----------:|------------:|-----------------:|
| V0 | 3 | 118 | 0 | 2 | no | 0 | 1 |
| V1 | 28 | 142 | 1 | 3 | no | 0 | 2 |
| V2 | 46 | 168 | 2 | 6 | yes | 0 | 3 |
| V3 | 95 | 198 | 11 | 5 | yes | 0 | 4 |
| V4 | 131 | 186 | 11 | 4 | yes | 0 | 5 |
| V5 | 168 | 142 | 11 | 3 | yes | 0 | 4 |
