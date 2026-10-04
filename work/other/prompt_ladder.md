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
