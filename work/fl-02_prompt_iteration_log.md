# FL-02 — Prompt iteration log: capstone Results and Limitations

**Task (FL-01 Target B):** Draft the **Results and Limitations** section of the capstone report for the content-refresh prioritisation project.

## Fixed input bundle

```
Research framing question: Given a limited weekly content-refresh budget, which pages should a FlyRank client refresh first to recover the most traffic?

Dataset: data/raw/content_refresh_anonymized.csv — 30,000 rows, 44 columns. Unit of analysis: one page (one content_id) per pseudonymized client (client_id).

Decline prevalence: 54.2% of pages have trend_direction == 'down' (declining-label rate 0.542 in the executed pipeline report).

Validation: client_holdout — hold out ~20% of clients so no client_id appears in both train and test (fallback: stratified_row_holdout if too few clients).

Primary metric: Precision@50 on held-out test pages (of the top 50 ranked for refresh review, share that are decline-labelled).

Precision@50 on client_holdout (executed pipeline):
- Hand-written rule baseline: 0.240 (~12 of 50)
- Random forest (best model): 0.740 (~37 of 50)

CTR by position_tier (notebook 01, Discovery B; pages with impressions_90d >= 100 only; ctr stored as percent):
- page_1: 0.3548
- top_3: 0.3341
- striking: 0.2558
- page_3_5: 0.1424
- deep: 0.0554
```

---

## V0 — naive baseline

**Prompt:**

> Write the results and limitations for my capstone ML report.

**Output:**

> ## Results
>
> The machine learning model significantly outperformed the baseline and demonstrates that AI can effectively prioritize content refreshes for SEO. Accuracy and precision were both strong on the test set, showing that the approach is production-ready. Random forests are well suited to this type of tabular marketing data because they capture nonlinear relationships between ranking factors and user behavior.
>
> Click-through rate generally decreases for lower search positions, which supports using position as an important feature. With more than half of pages showing decline signals, the model has plenty of signal to learn from.
>
> ## Limitations
>
> The dataset is anonymized and may not reflect every real-world client. Future work could add more features and deep learning. Results might vary on other industries.

**Technique:** none (naive baseline).

**Why this layer:** N/A — starting point.

**Observed difference:** N/A — baseline.

---

## V1 — role assignment

**Prompt:**

> You are a technical writer drafting portfolio-facing capstone report sections for a hiring manager who will skim in under two minutes.
>
> Write the **Results** and **Limitations** sections for the content-refresh prioritisation capstone.
>
> Fixed input bundle (only facts you may use):
>
> ```
> Research framing question: Given a limited weekly content-refresh budget, which pages should a FlyRank client refresh first to recover the most traffic?
>
> Dataset: data/raw/content_refresh_anonymized.csv — 30,000 rows, 44 columns. Unit of analysis: one page (one content_id) per pseudonymized client (client_id).
>
> Decline prevalence: 54.2% of pages have trend_direction == 'down' (declining-label rate 0.542 in the executed pipeline report).
>
> Validation: client_holdout — hold out ~20% of clients so no client_id appears in both train and test (fallback: stratified_row_holdout if too few clients).
>
> Primary metric: Precision@50 on held-out test pages (of the top 50 ranked for refresh review, share that are decline-labelled).
>
> Precision@50 on client_holdout (executed pipeline):
> - Hand-written rule baseline: 0.240 (~12 of 50)
> - Random forest (best model): 0.740 (~37 of 50)
>
> CTR by position_tier (notebook 01, Discovery B; pages with impressions_90d >= 100 only; ctr stored as percent):
> - page_1: 0.3548
> - top_3: 0.3341
> - striking: 0.2558
> - page_3_5: 0.1424
> - deep: 0.0554
> ```

**Output:**

> ## Results
>
> This capstone builds a ranked refresh queue for editors working under a weekly budget. On the anonymized starter portfolio (30,000 pages × 44 features), a random forest markedly improved top-of-queue quality versus a hand-written rule baseline when measured by Precision@50 under client holdout validation.
>
> The baseline achieved Precision@50 of 0.24, while the random forest reached 0.74 — roughly three times as many of the top 50 recommendations were decline-labelled on held-out clients. Because 54.2% of pages already show declining trend direction, the operational problem is ordering scarce refresh capacity, not surfacing a rare event.
>
> Discovery analysis in the same dataset shows mean CTR falling through the SERP (for example, 0.3341% in `top_3` versus 0.1424% in `page_3_5` among pages with at least 100 impressions), which motivates combining decline signals with visibility and position context in the score.
>
> ## Limitations
>
> The evaluation is on a single anonymized snapshot with a proxy decline label, not measured post-refresh traffic recovery. Client holdout tests generalization to unseen clients in this file, not guaranteed performance on live production traffic.

**Technique:** role assignment.

**Why this layer:** V0 read like a generic ML blog post and invented “production-ready” claims without metrics.

**Observed difference:** The output adopted report-style headings and cited Precision@50 numbers from the bundle, but still slipped into comparative language (“markedly improved”) without naming client_holdout in the first results paragraph.

---

## V2 — context and motivation

**Prompt:**

> You are a technical writer drafting portfolio-facing capstone report sections for a hiring manager who will skim in under two minutes.
>
> **Context and motivation:** The capstone frames refresh work as **weekly budget allocation**, not decline classification. Editors can only refresh *N* pages; the deliverable is a **ranked queue** aligned to the framing question in the bundle. Claims must stay observational — no causation, no guarantees about Google rankings or revenue.
>
> Write the **Results** and **Limitations** sections for the content-refresh prioritisation capstone.
>
> Fixed input bundle (only facts you may use):
>
> ```
> Research framing question: Given a limited weekly content-refresh budget, which pages should a FlyRank client refresh first to recover the most traffic?
>
> Dataset: data/raw/content_refresh_anonymized.csv — 30,000 rows, 44 columns. Unit of analysis: one page (one content_id) per pseudonymized client (client_id).
>
> Decline prevalence: 54.2% of pages have trend_direction == 'down' (declining-label rate 0.542 in the executed pipeline report).
>
> Validation: client_holdout — hold out ~20% of clients so no client_id appears in both train and test (fallback: stratified_row_holdout if too few clients).
>
> Primary metric: Precision@50 on held-out test pages (of the top 50 ranked for refresh review, share that are decline-labelled).
>
> Precision@50 on client_holdout (executed pipeline):
> - Hand-written rule baseline: 0.240 (~12 of 50)
> - Random forest (best model): 0.740 (~37 of 50)
>
> CTR by position_tier (notebook 01, Discovery B; pages with impressions_90d >= 100 only; ctr stored as percent):
> - page_1: 0.3548
> - top_3: 0.3341
> - striking: 0.2558
> - page_3_5: 0.1424
> - deep: 0.0554
> ```

**Output:**

> ## Results
>
> **Decision supported.** In this dataset, the capstone answers: *given a limited weekly refresh budget, which pages should a client review first?* The output is a ranked queue at page grain (`content_id` within `client_id`), not a binary “decline detector.”
>
> **Top-50 hit rate on held-out clients.** Under `client_holdout` validation, the hand-written rule baseline scored Precision@50 **0.240** (~12 of 50), while the random forest scored **0.740** (~37 of 50). That gap is the main empirical result: learned ranking concentrates decline-labelled pages at the top of a realistic weekly shortlist.
>
> **Why ordering matters here.** 54.2% of rows are already `trend_direction == down`, so editors face abundance of candidates, not scarcity. Mean CTR in Discovery B drops from **0.3341%** (`top_3`) to **0.1424%** (`page_3_5`) among pages with `impressions_90d >= 100`, so two pages with the same decline flag can imply different click upside depending on tier — consistent with scoring visibility and position alongside movement.
>
> ## Limitations
>
> Labels are a trailing-window proxy (`is_declining_label` / trend fields), not observed traffic after a refresh. This report describes **associations and ranking quality on held-out clients in one 30,000-row sample**; it does not show that refreshing caused recovery.

**Technique:** context and motivation.

**Why this layer:** V1 reported metrics but still read like “model beats baseline” without tying results to the budget-allocation question.

**Observed difference:** The opening anchored on the framing question and named client_holdout explicitly; limitations dropped “production-ready” tone in favor of proxy-label and no-causation wording.

---
