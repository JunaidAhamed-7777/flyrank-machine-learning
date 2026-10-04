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

## V3 — few-shot examples

**Prompt:**

> You are a technical writer drafting portfolio-facing capstone report sections for a hiring manager who will skim in under two minutes.
>
> **Context and motivation:** The capstone frames refresh work as **weekly budget allocation**, not decline classification. Editors can only refresh *N* pages; the deliverable is a **ranked queue** aligned to the framing question in the bundle. Claims must stay observational — no causation, no guarantees about Google rankings or revenue.
>
> **Style examples (match this register; do not copy topics or numbers from the examples):**
>
> - Good results sentence: *On held-out clients, Precision@50 rose from 0.24 to 0.74 — about 25 more decline-labelled pages in the top 50 shortlist.*
> - Bad results sentence: *The model proves ML can fix SEO and is ready for production.*
> - Good limitation sentence: *We rank pages using a proxy decline label in one anonymized snapshot; we did not measure post-refresh traffic.*
> - Bad limitation sentence: *Limitations include lack of deep learning and more data.*
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
> On held-out clients (`client_holdout`), Precision@50 for the hand-written rule baseline was **0.240** (~12 of 50) versus **0.740** (~37 of 50) for the random forest — about 25 more decline-labelled pages in the top weekly shortlist in this evaluation.
>
> In the same 30,000-page sample, **54.2%** of pages show `trend_direction == down`, so the capstone problem is **ordering** under a refresh budget, not hunting a rare class. Among pages with `impressions_90d >= 100`, mean `ctr` in Discovery B falls from **0.3341%** (`top_3`) to **0.1424%** (`page_3_5`), supporting position-aware scoring alongside decline signals when editors ask which URLs to refresh first.
>
> ## Limitations
>
> We rank pages using a proxy decline label in one anonymized CSV; we did not measure post-refresh traffic or revenue. Precision@50 on client holdout describes **this sample and split** — not a guarantee for live clients or future ranking environments.

**Technique:** few-shot examples.

**Why this layer:** V2 was complete but still used bold mini-headers and phrasing (“Decision supported”) that a skim reader might treat as marketing labels.

**Observed difference:** Prose tightened to example-like sentences; banned-pattern fluff (“production,” “proves”) disappeared; the CTR paragraph kept the Discovery B filter explicit.

---

## V4 — output structure

**Prompt:**

> You are a technical writer drafting portfolio-facing capstone report sections for a hiring manager who will skim in under two minutes.
>
> **Context and motivation:** The capstone frames refresh work as **weekly budget allocation**, not decline classification. Editors can only refresh *N* pages; the deliverable is a **ranked queue** aligned to the framing question in the bundle. Claims must stay observational — no causation, no guarantees about Google rankings or revenue.
>
> **Style examples (match this register; do not copy topics or numbers from the examples):**
>
> - Good results sentence: *On held-out clients, Precision@50 rose from 0.24 to 0.74 — about 25 more decline-labelled pages in the top 50 shortlist.*
> - Bad results sentence: *The model proves ML can fix SEO and is ready for production.*
> - Good limitation sentence: *We rank pages using a proxy decline label in one anonymized snapshot; we did not measure post-refresh traffic.*
> - Bad limitation sentence: *Limitations include lack of deep learning and more data.*
>
> Write the **Results** and **Limitations** sections for the content-refresh prioritisation capstone.
>
> **Required structure:**
> 1. `## Results` with exactly three subsections: `### Headline metric`, `### Why ranking beats classification here`, `### Position context (Discovery B)`.
> 2. `## Limitations` with exactly two bullet points: one on **label/proxy**, one on **validation scope**.
> 3. No other sections. No tables. Under 220 words total.
> 4. Every number must come from the fixed input bundle.
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
> ### Headline metric
> Under `client_holdout`, Precision@50 was **0.240** for the hand-written rule baseline (~12 of 50) and **0.740** for the random forest (~37 of 50) on the 30,000-page anonymized sample.
>
> ### Why ranking beats classification here
> **54.2%** of pages show `trend_direction == down`, so editors need a **top-N queue** for a weekly refresh budget — not a yes/no decline flag on every row.
>
> ### Position context (Discovery B)
> For pages with `impressions_90d >= 100`, mean `ctr` was **0.3341%** in `top_3` versus **0.1424%** in `page_3_5`, so position tier carries different click upside in this dataset when prioritising refreshes.
>
> ## Limitations
>
> - **Label/proxy:** Rankings use a trailing-window decline proxy on one CSV; post-refresh recovery was not observed.
> - **Validation scope:** `client_holdout` tests held-out clients in this file only — not live traffic or future periods.

**Technique:** output structure.

**Why this layer:** V3 was accurate but free-form; a capstone reader still had to hunt for the headline metric and the single limitation ask from FL-01 Target B.

**Observed difference:** Skimmable subsection titles appeared; word count dropped; invented metrics hit zero because the structure forced bundle-only numbers.

---

## V5 — step decomposition

**Prompt:**

> You are a technical writer drafting portfolio-facing capstone report sections for a hiring manager who will skim in under two minutes.
>
> **Context and motivation:** The capstone frames refresh work as **weekly budget allocation**, not decline classification. Editors can only refresh *N* pages; the deliverable is a **ranked queue** aligned to the framing question in the bundle. Claims must stay observational — no causation, no guarantees about Google rankings or revenue.
>
> **Style examples (match this register; do not copy topics or numbers from the examples):**
>
> - Good results sentence: *On held-out clients, Precision@50 rose from 0.24 to 0.74 — about 25 more decline-labelled pages in the top 50 shortlist.*
> - Bad results sentence: *The model proves ML can fix SEO and is ready for production.*
> - Good limitation sentence: *We rank pages using a proxy decline label in one anonymized snapshot; we did not measure post-refresh traffic.*
> - Bad limitation sentence: *Limitations include lack of deep learning and more data.*
>
> **Step decomposition — do this internally before writing, then output only the final sections:**
> 1. List the three numeric claims you will make and cite bundle fields for each.
> 2. Check each sentence for banned causation/guarantee language; rewrite if needed.
> 3. Confirm the limitation section includes exactly one sentence that states what the work **cannot** claim.
> 4. Draft using the required structure below.
>
> Write the **Results** and **Limitations** sections for the content-refresh prioritisation capstone.
>
> **Required structure:**
> 1. `## Results` with exactly three subsections: `### Headline metric`, `### Why ranking beats classification here`, `### Position context (Discovery B)`.
> 2. `## Limitations` with exactly two bullet points: one on **label/proxy**, one on **validation scope**.
> 3. No other sections. No tables. Under 220 words total.
> 4. Every number must come from the fixed input bundle.
> 5. Do not use `trend_direction` / `trend_pct` as model features (they define the decline label in this repo); if you mention them, say they are label-related only.
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
> ### Headline metric
> On `client_holdout` test pages, Precision@50 was **0.240** for the hand-written rule baseline (~12 of 50) and **0.740** for the random forest (~37 of 50) in the executed pipeline on `data/raw/content_refresh_anonymized.csv` (30,000 pages).
>
> ### Why ranking beats classification here
> **54.2%** of pages are decline-labelled via trend fields used only as labels — not features — so the weekly refresh question is which **top-N** URLs to review first, not whether decline exists on most rows.
>
> ### Position context (Discovery B)
> With `impressions_90d >= 100`, mean `ctr` was **0.3341%** (`top_3`) versus **0.1424%** (`page_3_5`), a measured SERP gradient in this sample when weighing refresh upside.
>
> ## Limitations
>
> - **Label/proxy:** This work cannot claim that refreshing a page caused traffic to return; only that decline-labelled pages ranked higher under a proxy label.
> - **Validation scope:** Client holdout on this anonymized slice does not establish performance on unseen domains, time periods, or editorial workflows.

**Technique:** step decomposition.

**Why this layer:** V4 met structure but did not surface the repo’s highest-cost mistake (treating trend fields as features) or a single explicit “cannot claim” limitation sentence.

**Observed difference:** Added leakage-aware wording on trend fields and a blunt cannot-claim limitation; subsection bodies changed slightly while layout matched V4 — the step checklist did not change headings or word budget.

---

