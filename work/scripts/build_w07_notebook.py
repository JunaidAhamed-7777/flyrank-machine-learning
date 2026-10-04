"""Assemble w07_action_playbook.ipynb (full content). Run from repo root."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NB = ROOT / "work" / "notebooks" / "w07_action_playbook.ipynb"

SECTION1_MD = r"""## 1. Ranked actions + reason codes

*The queue: what to do first, and why, in words a human trusts.*

### Part A — Archetype table

| Archetype | Signature | Action |
|---|---|---|
| `HIGH_LEVERAGE_REFRESH` | `page_1` or `striking`, `ctr_last30` below tier median, `impressions_90d` ≥ p75 (high exposure) | Refresh content |
| `SNIPPET_OPTIMIZATION` | `top_3`, CTR below tier median, high exposure (≥ p75) | CTR/snippet fix, not a rewrite |
| `UNDEREXPOSED_DECLINE` | `deep` or `page_3_5`, `trend_direction` = down, `impressions_90d` below slice median | Deprioritise — no refresh this cycle |
| `STABLE_HIGH_PERFORMER` | `top_3`, or `page_1`/`striking` with CTR at/above tier median | Protect — do not touch |
| `CONTENT_AGING` | High exposure (≥ p75), `content_age_days` > 365, CTR within 0.05 pp of tier median | Refresh on next cycle |
| `NEW_OR_UNCLEAR` | `position_tier` = `no_data`, or `trend_direction` in (`new`, `flat`) | Manual triage — no model action |
| `LOW_SIGNAL` | `impressions_90d` < 100 (exposure floor) | No action |

**Why this set.** Editors need SERP-band language (tier + CTR regime + exposure), not raw features. Seven archetypes cover the w04 CTR-headroom story (`SNIPPET_*`, `HIGH_LEVERAGE_*`), the decline proxy (`UNDEREXPOSED_DECLINE`), protect/skip paths (`STABLE_*`, `LOW_SIGNAL`), and honest gaps (`NEW_OR_UNCLEAR`, `CONTENT_AGING`). Fewer buckets would collapse “snippet fix” vs “full refresh”; more would fragment review without distinct actions.

**Decay / refresh insight.** The model ranks by **decline probability** (30-day impression drop >20% vs prior 30 days) — a decay *signal*, not estimated traffic recovery. Archetypes add *how* to act if an editor accepts the rank; they do not claim causal lift from refresh.

### Part B — Reason codes (fixed vocabulary)

One string per row in the queue CSV — no free text:

- `HIGH_LEVERAGE_REFRESH`
- `SNIPPET_CTR_HEADROOM`
- `UNDEREXPOSED_DECLINE`
- `STABLE_PERFORMER_PROTECT`
- `CONTENT_AGING_CYCLE`
- `MANUAL_TRIAGE_UNCLEAR`
- `BELOW_EXPOSURE_FLOOR`
- `INSUFFICIENT_DATA` (fallback when no other signature matches)

### Part C — Ranked queue

Code below loads the w03/w05 March slice, trains the w05 Random Forest on **all clients** (four honest features), assigns archetype + reason + action, sorts by `predicted_probability`, previews top 20. Full queue → `work/outputs/refresh_queue.csv` in §5.
"""

SECTION1_CODE = r'''%pip -q install duckdb huggingface_hub truststore pandas numpy scikit-learn matplotlib

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import truststore
from sklearn.ensemble import RandomForestClassifier

truststore.inject_into_ssl()

NOTEBOOK_DIR = Path.cwd()
if NOTEBOOK_DIR.name != "notebooks":
    NOTEBOOK_DIR = NOTEBOOK_DIR / "work" / "notebooks"
WORK = NOTEBOOK_DIR.parent
OUT_DIR = WORK / "outputs"
FIG_DIR = WORK / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

DECISION_DATE = "2026-03-31"
RANDOM_STATE = 42
EXPOSURE_FLOOR = 100
FEATURES_HONEST = ["imp_last30", "avg_pos_last30", "ctr_last30", "content_age_days"]

TIER_WEIGHT = {
    "top_3": 1.0,
    "page_1": 0.9,
    "striking": 0.85,
    "page_3_5": 0.7,
    "deep": 0.5,
    "no_data": 0.0,
}

ARCHETYPE_META = {
    "HIGH_LEVERAGE_REFRESH": ("HIGH_LEVERAGE_REFRESH", "Refresh content"),
    "SNIPPET_OPTIMIZATION": ("SNIPPET_CTR_HEADROOM", "CTR/snippet fix, not a rewrite"),
    "UNDEREXPOSED_DECLINE": ("UNDEREXPOSED_DECLINE", "Deprioritise — no refresh this cycle"),
    "STABLE_HIGH_PERFORMER": ("STABLE_PERFORMER_PROTECT", "Protect — do not touch"),
    "CONTENT_AGING": ("CONTENT_AGING_CYCLE", "Refresh on next cycle"),
    "NEW_OR_UNCLEAR": ("MANUAL_TRIAGE_UNCLEAR", "Manual triage — no model action"),
    "LOW_SIGNAL": ("BELOW_EXPOSURE_FLOOR", "No action"),
}


def position_tier(pos: float) -> str:
    if pd.isna(pos) or pos <= 0:
        return "no_data"
    if pos <= 3:
        return "top_3"
    if pos <= 10:
        return "page_1"
    if pos <= 20:
        return "striking"
    if pos <= 50:
        return "page_3_5"
    return "deep"


def make_rf() -> RandomForestClassifier:
    return RandomForestClassifier(
        class_weight="balanced_subsample",
        max_depth=10,
        min_samples_leaf=25,
        n_estimators=200,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )


def load_pages() -> pd.DataFrame:
    import duckdb
    import truststore

    truststore.inject_into_ssl()
    token_path = WORK / ".hf_token_local"
    hf_token = os.environ.get("HF_TOKEN") or token_path.read_text(encoding="utf-8").strip()
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE SECRET hf (TYPE huggingface, TOKEN '{hf_token}')")
    rel = "hf://datasets/FlyRank/internship-warehouse"
    dim_content = f"read_parquet('{rel}/dim_content.parquet')"
    fact_90d = (
        "read_parquet(["
        f"'{rel}/fact_content_daily_performance/month=2026-01/*.parquet',"
        f"'{rel}/fact_content_daily_performance/month=2026-02/*.parquet',"
        f"'{rel}/fact_content_daily_performance/month=2026-03/*.parquet'"
        "])"
    )
    sql = f"""
    WITH daily AS (
        SELECT * FROM {fact_90d}
        WHERE report_date <= DATE '{DECISION_DATE}'
    ),
    agg AS (
        SELECT
            client_hash_id,
            content_hash_id,
            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 90 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS impressions_90d,
            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_last30,
            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 60 DAY
                      AND report_date <= DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_prev30,
            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_clicks, 0) ELSE 0 END) AS clk_last30,
            AVG(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN gsc_avg_position END) AS avg_pos_last30,
            BOOL_AND(gsc_data_available IS TRUE) AS gsc_ok
        FROM daily
        GROUP BY 1, 2
    ),
    labeled AS (
        SELECT
            a.*,
            CASE
                WHEN a.imp_prev30 = 0 AND a.imp_last30 > 0 THEN 'new'
                WHEN a.imp_prev30 = 0 AND a.imp_last30 = 0 THEN 'flat'
                WHEN a.imp_prev30 > 0 AND (a.imp_last30 - a.imp_prev30) * 100.0 / a.imp_prev30 > 20 THEN 'up'
                WHEN a.imp_prev30 > 0 AND (a.imp_last30 - a.imp_prev30) * 100.0 / a.imp_prev30 < -20 THEN 'down'
                ELSE 'stable'
            END AS trend_direction
        FROM agg a
        WHERE a.imp_last30 > 0 AND a.gsc_ok IS TRUE
    )
    SELECT
        l.client_hash_id,
        l.content_hash_id,
        l.impressions_90d,
        l.imp_last30,
        l.imp_prev30,
        l.clk_last30,
        l.avg_pos_last30,
        l.trend_direction,
        DATE_DIFF('day', d.content_created_date, DATE '{DECISION_DATE}') AS content_age_days
    FROM labeled l
    INNER JOIN {dim_content} d USING (content_hash_id)
    WHERE d.content_created_date <= DATE '{DECISION_DATE}'
      AND DATE_DIFF('day', d.content_created_date, DATE '{DECISION_DATE}') >= 90
    """
    return con.sql(sql).df()


def assign_archetype_and_reason(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    tier_med = frame.groupby("position_tier")["ctr_last30"].transform("median")
    high_exp = frame["impressions_90d"].quantile(0.75)
    med_exp = frame["impressions_90d"].median()
    names = []
    reasons = []
    for idx, row in frame.iterrows():
        imp90 = row["impressions_90d"]
        ctr = row["ctr_last30"]
        tier = row["position_tier"]
        trend = str(row["trend_direction"]).lower()
        age = row["content_age_days"]
        tmed = tier_med.loc[idx]
        if imp90 < EXPOSURE_FLOOR:
            arch = "LOW_SIGNAL"
        elif tier == "no_data" or trend in ("new", "flat"):
            arch = "NEW_OR_UNCLEAR"
        elif tier == "top_3" and ctr >= tmed:
            arch = "STABLE_HIGH_PERFORMER"
        elif tier == "top_3" and ctr < tmed and imp90 >= high_exp:
            arch = "SNIPPET_OPTIMIZATION"
        elif tier in ("page_1", "striking") and ctr < tmed and imp90 >= high_exp:
            arch = "HIGH_LEVERAGE_REFRESH"
        elif tier in ("deep", "page_3_5") and trend == "down" and imp90 < med_exp:
            arch = "UNDEREXPOSED_DECLINE"
        elif imp90 >= high_exp and age > 365 and abs(ctr - tmed) <= 0.05:
            arch = "CONTENT_AGING"
        elif tier in ("page_1", "striking") and ctr >= tmed:
            arch = "STABLE_HIGH_PERFORMER"
        elif tier in ("page_1", "striking") and ctr < tmed:
            arch = "HIGH_LEVERAGE_REFRESH"
        elif tier == "top_3" and ctr < tmed:
            arch = "SNIPPET_OPTIMIZATION"
        elif tier in ("deep", "page_3_5"):
            arch = "UNDEREXPOSED_DECLINE"
        else:
            arch = "NEW_OR_UNCLEAR"
        names.append(arch)
        code, _ = ARCHETYPE_META[arch]
        if arch == "NEW_OR_UNCLEAR" and tier != "no_data" and trend not in ("new", "flat"):
            code = "INSUFFICIENT_DATA"
        reasons.append(code)
    return pd.Series(names, index=frame.index), pd.Series(reasons, index=frame.index)


pages = load_pages()
pages["ctr_last30"] = np.where(
    pages["imp_last30"] > 0,
    pages["clk_last30"] / pages["imp_last30"] * 100.0,
    0.0,
)
pages["position_tier"] = pages["avg_pos_last30"].map(position_tier)
pages["is_declining_label"] = pages["trend_direction"].str.lower().eq("down").astype(int)

X = pages[FEATURES_HONEST].replace([np.inf, -np.inf], np.nan).fillna(0)
y = pages["is_declining_label"]
rf_deploy = make_rf()
rf_deploy.fit(X, y)
pages["predicted_probability"] = rf_deploy.predict_proba(X)[:, 1]

pages["archetype"], pages["reason_code"] = assign_archetype_and_reason(pages)
pages["action"] = pages["archetype"].map(lambda a: ARCHETYPE_META[a][1])

queue = pages.sort_values("predicted_probability", ascending=False).reset_index(drop=True)
SLICE_BASE_RATE = float(pages["is_declining_label"].mean())
print(f"March slice rows: {len(pages):,} | base decline rate: {SLICE_BASE_RATE:.3f}")
print(f"High-exposure threshold (p75 impressions_90d): {pages['impressions_90d'].quantile(0.75):,.0f}")

preview_cols = [
    "content_hash_id",
    "client_hash_id",
    "predicted_probability",
    "archetype",
    "reason_code",
    "action",
]
print(queue[preview_cols].head(20).to_string(index=False))
'''

SECTION2_MD = r"""## 2. Intended use and limits

### Intended use

The ranked queue is **decision-support** for a human content editor choosing which URLs to review first when they have capacity for *N* refreshes this week. It is not an automated publishing system, not a causal claim that refresh will recover traffic, and not a client-facing recommendation without human review. Honest grouped performance from w06 is **LOO-client Precision@50 = 0.258 ± 0.237** — at the top of the queue (top 50 within a client), roughly **one quarter** of pages are truly declining, versus a slice base rate near **0.21**; that is a **directional** lift for prioritisation, not a strong classifier.

**What changed since w05 (historic only).** w05’s single six-client holdout reported **0.38–0.40** P@50; w06 re-measured holdout **0.38** and LOO mean **≈0.26**. This playbook anchors expectations to LOO, not the holdout draw.

### Limits

- Trained and evaluated on one mid-panel month (`month=2026-03`, decision **2026-03-31**); forward performance beyond the Feb→Mar time-aware check in w06 is untested.
- The evaluation cohort requires continuous GSC in the 90-day window (`gsc_ok`); clients with patchy coverage are under-represented or excluded.
- False positives concentrate in `page_1` and `striking` tiers where high `impressions_90d` makes the RF over-rank visible URLs that are not declining (w05 error analysis).
- `content_updated_date` is excluded from features because the dim snapshot includes post-decision updates — refresh timing cannot be modelled honestly from it (w03/w04 audit).
- LOO-client standard deviation **0.237** with **seven folds at P@50 = 0.0** — some clients get no value from the queue at the top-50 cut.
- The queue ranks **decline probability**, not traffic recovered; archetype actions describe editorial intent, not measured uplift.
- w06 LOO RF mean (**0.258**) sits **below** the global w04 baseline reference P@50 (**0.34**) on the full slice — do not claim a stable beat over the rule baseline under grouped validation.
"""

SECTION2_CODE = r'''audit = json.loads((OUT_DIR / "w06_audit_metrics.json").read_text(encoding="utf-8"))
LOO_P50 = audit["p50_loo_rf_mean"]
LOO_STD = audit["p50_loo_rf_std"]
print(f"Playbook headline metric (from w06): LOO P@50 = {LOO_P50:.3f} ± {LOO_STD:.3f}")
print(f"Slice base decline rate (this run): {SLICE_BASE_RATE:.3f}")
print(f"w05 holdout P@50 (historic, not headline): {audit['p50_w05_holdout_rf']:.2f}")
'''

SECTION3_MD = r"""## 3. Human review + the no-go list

### Human review rules

- **Top 5 pages per `client_hash_id`** must be opened by a human editor before any refresh or snippet change — the model’s highest ranks are where LOO precision is thin (~0.26 mean).
- Rows with archetype `NEW_OR_UNCLEAR` or `LOW_SIGNAL` require **manual triage**; do not auto-skip or auto-approve from the queue alone.
- Any page with **`impressions_90d` ≥ 50,000** must be reviewed even if ranked below top 50 — high-exposure URLs dominate client risk.
- **`reason_code` is mandatory UI**: if a row has no code, no editorial action may be taken from the queue.
- **Editor decision overrides the queue**; the RF score is an input ordering, not approval.

### Cost / value (honest)

With LOO P@50 ≈ **0.26**, expect ~**13** true declines in a client-level top-50 batch (~**37** false positives). Editorial time is justified only when the **cost of missing a large-exposure decline** exceeds the cost of reviewing ~3 false positives per true positive — tune *N* per client capacity, not model confidence alone.

### No-go list (never automate)

- **Never auto-publish or auto-edit live content** — the label is observational GSC momentum, not a safe CMS action trigger.
- **Never send client-facing recommendations without human sign-off** — grouped precision does not support client-ready guarantees.
- **Never act on pages where GSC/GA coverage is incomplete for the decision window** — zeros and flags in the warehouse are not neutral missingness.
- **Never treat a high `predicted_probability` as causal recovery** — it ranks decline association, not counterfactual traffic.
- **Never route the raw queue to a client** without an editor reviewing that client’s top items.
- **Never suppress a URL from review solely because the model ranked it low** — low exposure and stable tiers still need spot checks for brand-critical URLs.
"""

SECTION3_CODE = r'''HIGH_REVIEW_IMP = 50_000
n_high = int((pages["impressions_90d"] >= HIGH_REVIEW_IMP).sum())
print(f"Pages above human-review exposure floor ({HIGH_REVIEW_IMP:,} imp_90d): {n_high:,}")
'''

SECTION4_MD = r"""## 4. Monitoring / retrain triggers

| Trigger | Threshold / Action |
|---|---|
| LOO P@50 on a new sealed month | Falls **below 0.20** (near LOO baseline band) → retrain with the new month included and re-audit grouped splits |
| Feature drift (`ctr_last30` slice mean) | Shifts **>20%** month-over-month → pause queue export; investigate data pipeline before retrain |
| Client mix shift | **>30%** of pages from clients absent in the training month window → flag for retrain / recalibrate archetype exposure cutoffs |
| Sealed month opened | **June 2026** evaluation available → re-run LOO-client and compare to **0.258** benchmark |
| Reason-code concentration | Any single code **>70%** of rows → re-tune archetype signatures (rule layer collapsed) |
| Unstable LOO folds | **>40%** of client folds with P@50 **= 0.0** → review split protocol and minimum exposure floors before trusting the queue |
| Holdout vs LOO gap | Single holdout P@50 exceeds LOO mean by **>0.15** without new data → treat holdout as optimistic; do not promote holdout to headline metric |
"""

SECTION4_CODE = r'''# Monitoring table is markdown-only; no numeric gate runs here.
print("Monitoring triggers are operational thresholds — see table above.")
'''

SECTION5_MD = r"""## 5. Exports for the paper

Artifacts written by the next cell:

- `work/outputs/refresh_queue.csv` — full ranked queue (gitignored; regenerates on run)
- `work/figures/archetype_mix.svg` — bar chart of archetype counts (commit)
- `work/figures/action_distribution.svg` — bar chart of action labels (commit)
- `work/outputs/w07_playbook_metrics.json` — committed receipt (counts + w06 LOO headline)
"""

SECTION5_CODE = r'''import matplotlib.pyplot as plt
from datetime import datetime, timezone

QUEUE_PATH = OUT_DIR / "refresh_queue.csv"
export_cols = [
    "content_hash_id",
    "client_hash_id",
    "predicted_probability",
    "archetype",
    "reason_code",
    "action",
    *FEATURES_HONEST,
]
queue[export_cols].to_csv(QUEUE_PATH, index=False)
print(f"Wrote {QUEUE_PATH} ({len(queue):,} rows)")

arch_counts = queue["archetype"].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 4))
arch_counts.plot(kind="bar", ax=ax, color="#2c5282")
ax.set_title("Archetype mix (March 2026 slice)")
ax.set_ylabel("Pages")
ax.tick_params(axis="x", rotation=45, labelsize=8)
fig.tight_layout()
arch_path = FIG_DIR / "archetype_mix.svg"
fig.savefig(arch_path)
plt.close(fig)

act_counts = queue["action"].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 4))
act_counts.plot(kind="bar", ax=ax, color="#276749")
ax.set_title("Action distribution")
ax.set_ylabel("Pages")
ax.tick_params(axis="x", rotation=45, labelsize=8)
fig.tight_layout()
act_path = FIG_DIR / "action_distribution.svg"
fig.savefig(act_path)
plt.close(fig)

metrics = {
    "run_timestamp_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "data_source": "warehouse_month_2026-03",
    "decision_date": DECISION_DATE,
    "row_count": int(len(queue)),
    "slice_base_decline_rate": SLICE_BASE_RATE,
    "p50_loo_rf_mean": LOO_P50,
    "p50_loo_rf_std": LOO_STD,
    "archetype_counts": arch_counts.astype(int).to_dict(),
    "action_counts": act_counts.astype(int).to_dict(),
    "reason_code_counts": queue["reason_code"].value_counts().astype(int).to_dict(),
    "headline_limitation": (
        "LOO-client P@50 std is 0.237 with seven client folds at 0.0 — queue value is uneven across clients."
    ),
}
metrics_path = OUT_DIR / "w07_playbook_metrics.json"
metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
print(f"Wrote {arch_path}")
print(f"Wrote {act_path}")
print(f"Wrote {metrics_path}")
'''

SECTION6_MD = r"""## Self-check

- Headline performance is **LOO P@50 = 0.258 ± 0.237** (w06), not **0.40** / **0.38** as the playbook headline? **Yes**
- **Seven** archetypes, each with a signature and one action? **Yes**
- Reason codes are a **fixed string vocabulary**? **Yes**
- Exported CSV includes **`reason_code` per row**? **Yes**
- Human-review rules are **concrete** (top-5 per client, 50k imp floor, codes required)? **Yes**
- No-go list has **≥5 hard rules**? **Yes** (six)
- Monitoring triggers are **numeric**? **Yes**
- Two SVGs under **`work/figures/`**? **Yes** (after §5 runs)
- Metrics JSON **committed**, CSV **gitignored**? **Yes** (repo policy)
- Any claim **stronger than w06** supports? **No** — expectations anchored to LOO ~0.26, not holdout 0.38
"""

TITLE = r"""# ML-10 — Content Action Playbook

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JunaidAhamed-7777/flyrank-machine-learning/blob/main/work/notebooks/w07_action_playbook.ipynb?flush_cache=true)

Turns the validated refresh-ranking model into a **human-reviewed action playbook**: archetypes, reason codes, ranked queue, limits, and paper exports. Headline precision: **LOO-client P@50 = 0.258 ± 0.237** (w06 audit).

> Lane: Refresh Prediction · ranking · decision-support only (not production automation).
"""


def md_cell(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in text.split("\n")]}


def code_cell(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in text.split("\n")],
    }


cells = [
    md_cell(TITLE),
    md_cell(SECTION1_MD),
    code_cell(SECTION1_CODE),
    md_cell(SECTION2_MD),
    code_cell(SECTION2_CODE),
    md_cell(SECTION3_MD),
    code_cell(SECTION3_CODE),
    md_cell(SECTION4_MD),
    code_cell(SECTION4_CODE),
    md_cell(SECTION5_MD),
    code_cell(SECTION5_CODE),
    md_cell(SECTION6_MD),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "cells": cells,
}

NB.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"Wrote {NB}")
