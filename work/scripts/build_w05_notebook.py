"""Build work/notebooks/w05_model.ipynb from template sections."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NB_PATH = ROOT / "work" / "notebooks" / "w05_model.ipynb"
METRICS_PATH = ROOT / "work" / "outputs" / "w05_model_metrics.json"

MD1 = """## 1. Method choice and why

**Logistic Regression** is the interpretable floor: a linear score from the feature frame, with coefficient signs we can sanity-check against w04's CTR-headroom story. We rank by predicted decline probability and evaluate with Precision@50 — prioritisation, not a fixed classification threshold.

**Random Forest** is the primary model for tabular ranking with position × CTR interactions. It supports permutation importance on the holdout slice. **Gradient Boosting** is optional only if RF beats LR by ≥0.03 absolute on Precision@50 under an honest feature frame.

**Feature frame (honest):** four columns — `imp_last30`, `avg_pos_last30`, `ctr_last30`, `content_age_days`. We **dropped `log_imp_prev30`** after the leakage check below: the w03 label is `(imp_last30 - imp_prev30) / imp_prev30 < -0.20`, so `imp_last30` plus any monotone transform of `imp_prev30` lets trees reconstruct the label. Keeping both impression windows is not prediction; it is reading the answer."""

MD2 = """## 2. Split design

**Client-holdout** (not random rows). Pages from the same client share CTR and position mix; a row split would leak client identity and inflate Precision@50.

Implementation matches `scripts/03_train_model.py`: sort unique `client_id`, permute with `np.random.default_rng(42)`, hold out ~20% of clients (6 of 28 here), train on the rest, evaluate metrics only on held-out clients' pages. Precision@50 ranks within the holdout frame.

Invalid if a client appears on both sides or the holdout is too small to support top-50 ranking (we have hundreds of holdout rows)."""

MD_LEAK = """### Label-reconstruction leakage (deliberate catch)

Same pattern as w03's `trend_pct` trap: train a Random Forest **with** `log_imp_prev30` (five features) vs **without** (four features). If Precision@50 jumps toward 1.0 with the extra column, the label was in the features."""

MD3 = """## 3. Train + compare vs my baseline

Honest four-feature models only (post-leakage fix). Table and verdict follow the code."""

MD_VERDICT = """**Verdict:** The honest Random Forest reaches Precision@50 **0.40** on held-out clients (LR **0.36**), versus **0.24** for the w04 CTR-headroom rule on the same pages — a modest lift over the rule, not the leaked **1.00**. That edges the full-slice w04 reference **0.34** by **+0.06** on this holdout only; it is not a strong production claim. **Gradient Boosting** was trained because RF beat LR by **0.04** on the honest frame, but GB lands at **0.36** (no gain over LR). The comparison that matters is leaky **1.00** → honest **0.40**."""

MD4 = """## 4. Errors and interpretation

**(a) Permutation importance (RF, holdout, four features).** Importances are small and noisy on ~671 holdout rows; `ctr_last30` ranks highest (least negative when shuffled), then `imp_last30`. Position and age are weaker — the honest model is not reproducing w04's tier-relative CTR headroom story.

**(b) Error analysis.** Top-50 on holdout: **20** true positives, **30** false positives (Precision@50 = **0.40**). False positives average **lower** `impressions_90d` (~712 vs ~1,446) and **lower** `ctr_last30` than true positives — the model promotes mid-exposure URLs that are not declining. The first false positive is at **rank 3** (striking tier, 0% CTR). **Precision@20** is **0.40** for RF versus **0.45** for LR — LR is sharper at the very top."""

MD5 = """## Self-check

- Baseline Precision@50 = **0.34** on full slice? **Yes** (Step 0).
- Client-holdout, seed 42? **Yes**.
- Train/holdout decline rates within 5 pp? **Yes**.
- Trained on train clients, evaluated on holdout only? **Yes**.
- Headline model metrics on holdout, not in-sample? **Yes**.
- Leakage demonstration retained (5-feature vs 4-feature RF)? **Yes**.
- `log_imp_prev30` removed from training features? **Yes** (four-feature frame only).
- Verdict leads with honest numbers, not leaked 1.00? **Yes**.
- GB only if RF−LR ≥ 0.03 on honest frame? **Yes** — run, but GB did not beat RF (0.36 vs 0.40).
- No `trend_pct`, `trend_direction`, `is_declining_label`, or `content_updated_date` in X? **Yes**."""


CODE_SETUP = r'''%pip -q install duckdb huggingface_hub truststore pandas numpy scikit-learn

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import truststore

truststore.inject_into_ssl()

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

NOTEBOOK_DIR = Path.cwd()
if NOTEBOOK_DIR.name != "notebooks":
    NOTEBOOK_DIR = NOTEBOOK_DIR / "work" / "notebooks"
ROOT = NOTEBOOK_DIR.parent.parent
OUT_DIR = NOTEBOOK_DIR.parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DECISION_DATE = "2026-03-31"
RANDOM_STATE = 42
DATA_SOURCE = "warehouse_month_2026-03"

TIER_WEIGHT = {
    "top_3": 1.0,
    "page_1": 0.9,
    "striking": 0.85,
    "page_3_5": 0.7,
    "deep": 0.5,
    "no_data": 0.0,
}
FEATURES_HONEST = [
    "imp_last30",
    "avg_pos_last30",
    "ctr_last30",
    "content_age_days",
]
FEATURES_LEAKY = FEATURES_HONEST + ["log_imp_prev30"]


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


def precision_at_k(y_true, scores, k: int) -> float:
    frame = pd.DataFrame({"y": list(y_true), "score": list(scores)})
    if frame.empty:
        return 0.0
    top = frame.sort_values("score", ascending=False).head(min(k, len(frame)))
    return float(top["y"].mean()) if len(top) else 0.0


def w04_baseline_score(pages: pd.DataFrame) -> pd.Series:
    tier_median_ctr = pages.groupby("position_tier")["ctr_last30"].transform("median")
    ctr_headroom = (tier_median_ctr - pages["ctr_last30"]).clip(lower=0)
    tier_weight = pages["position_tier"].map(TIER_WEIGHT).fillna(0.0)
    return pages["impressions_90d"] * ctr_headroom * tier_weight


def make_rf():
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

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        local = NOTEBOOK_DIR.parent / ".hf_token_local"
        if local.is_file():
            hf_token = local.read_text(encoding="utf-8").strip()
    if not hf_token:
        raise RuntimeError("HF_TOKEN missing")

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
        l.client_hash_id AS client_id,
        l.content_hash_id AS content_id,
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


pages = load_pages()
pages["ctr_last30"] = np.where(
    pages["imp_last30"] > 0,
    pages["clk_last30"] / pages["imp_last30"] * 100.0,
    0.0,
)
pages["log_imp_prev30"] = np.log1p(pages["imp_prev30"])
pages["position_tier"] = pages["avg_pos_last30"].map(position_tier)
pages["is_declining_label"] = pages["trend_direction"].str.lower().eq("down").astype(int)
pages["baseline_score"] = w04_baseline_score(pages)

global_baseline_p50 = precision_at_k(pages["is_declining_label"], pages["baseline_score"], 50)
print(f"Data source: {DATA_SOURCE} | rows: {len(pages):,}")
print(f"Base decline rate: {pages['is_declining_label'].mean():.3f}")
print(f"Step 0 — w04 baseline Precision@50 (full slice): {global_baseline_p50:.2f}")
assert abs(global_baseline_p50 - 0.34) < 0.005, "Baseline reproduction failed"
print(f"Honest training features: {FEATURES_HONEST}")
'''

CODE_SPLIT = r'''
def make_client_holdout(frame: pd.DataFrame, target: pd.Series):
    client_series = frame["client_id"].fillna("unknown").astype(str)
    unique_clients = np.array(sorted(client_series.unique()))
    rng = np.random.default_rng(RANDOM_STATE)
    shuffled = rng.permutation(unique_clients)
    test_n = max(1, int(round(len(shuffled) * 0.2)))
    test_clients = set(shuffled[:test_n])
    test_mask = client_series.isin(test_clients).to_numpy()
    train_idx = np.where(~test_mask)[0]
    test_idx = np.where(test_mask)[0]
    return train_idx, test_idx, test_clients


y = pages["is_declining_label"]
X_honest = pages[FEATURES_HONEST].replace([np.inf, -np.inf], np.nan).fillna(0)
X_leaky = pages[FEATURES_LEAKY].replace([np.inf, -np.inf], np.nan).fillna(0)
train_idx, test_idx, holdout_clients = make_client_holdout(pages, y)

train_clients = pages.iloc[train_idx]["client_id"].nunique()
holdout_client_n = pages.iloc[test_idx]["client_id"].nunique()
train_rate = y.iloc[train_idx].mean()
holdout_rate = y.iloc[test_idx].mean()

print(f"Train clients: {train_clients} | Holdout clients: {holdout_client_n}")
print(f"Train rows: {len(train_idx):,} | decline rate: {train_rate:.3f}")
print(f"Holdout rows: {len(test_idx):,} | decline rate: {holdout_rate:.3f}")
if abs(train_rate - holdout_rate) > 0.05:
    print("WARNING: train/holdout decline rates differ by >5 percentage points")
'''

CODE_LEAK = r'''
y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

rf_leaky = make_rf()
rf_leaky.fit(X_leaky.iloc[train_idx], y_train)
leaky_p50 = precision_at_k(
    y_test, rf_leaky.predict_proba(X_leaky.iloc[test_idx])[:, 1], 50
)

rf_honest_demo = make_rf()
rf_honest_demo.fit(X_honest.iloc[train_idx], y_train)
honest_p50_demo = precision_at_k(
    y_test, rf_honest_demo.predict_proba(X_honest.iloc[test_idx])[:, 1], 50
)

print("Label: (imp_last30 - imp_prev30) / imp_prev30 < -0.20  (w03)")
print(f"RF Precision@50 WITH log_imp_prev30 (leaky):    {leaky_p50:.2f}")
print(f"RF Precision@50 WITHOUT log_imp_prev30 (honest): {honest_p50_demo:.2f}")
print(f"Collapse: {leaky_p50:.2f} → {honest_p50_demo:.2f}")
'''

CODE_TRAIN = r'''
X_train, X_test = X_honest.iloc[train_idx], X_honest.iloc[test_idx]

lr = Pipeline(
    [
        ("scaler", StandardScaler()),
        (
            "model",
            LogisticRegression(
                class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE
            ),
        ),
    ]
)
rf = make_rf()

lr.fit(X_train, y_train)
rf.fit(X_train, y_train)
lr_probs = lr.predict_proba(X_test)[:, 1]
rf_probs = rf.predict_proba(X_test)[:, 1]
baseline_holdout = pages.iloc[test_idx]["baseline_score"].to_numpy()

rows = [
    (
        "w04 baseline (CTR headroom)",
        precision_at_k(y_test, baseline_holdout, 50),
        precision_at_k(y_test, baseline_holdout, 100),
        precision_at_k(y_test, baseline_holdout, 200),
    ),
    (
        "Logistic Regression",
        precision_at_k(y_test, lr_probs, 50),
        precision_at_k(y_test, lr_probs, 100),
        precision_at_k(y_test, lr_probs, 200),
    ),
    (
        "Random Forest",
        precision_at_k(y_test, rf_probs, 50),
        precision_at_k(y_test, rf_probs, 100),
        precision_at_k(y_test, rf_probs, 200),
    ),
]

run_gb = rows[2][1] - rows[1][1] >= 0.03
if run_gb:
    gb = GradientBoostingClassifier(random_state=RANDOM_STATE)
    gb.fit(X_train, y_train)
    gb_probs = gb.predict_proba(X_test)[:, 1]
    rows.append(
        (
            "Gradient Boosting",
            precision_at_k(y_test, gb_probs, 50),
            precision_at_k(y_test, gb_probs, 100),
            precision_at_k(y_test, gb_probs, 200),
        )
    )

table = pd.DataFrame(rows, columns=["Ranker", "Precision@50", "Precision@100", "Precision@200"])
print("Full-slice w04 baseline Precision@50 (reference): 0.34")
print("\nHeld-out client comparison (honest 4-feature models):\n")
print(table.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

p20_lr = precision_at_k(y_test, lr_probs, 20)
p20_rf = precision_at_k(y_test, rf_probs, 20)
print(f"\nPrecision@20 (holdout) — LR: {p20_lr:.2f} | RF: {p20_rf:.2f}")
print(f"Gradient Boosting run: {run_gb}")

results_holdout = {
    "w04 baseline (CTR headroom)": {
        "50": rows[0][1],
        "100": rows[0][2],
        "200": rows[0][3],
        "20": precision_at_k(y_test, baseline_holdout, 20),
    },
    "Logistic Regression": {
        "50": rows[1][1],
        "100": rows[1][2],
        "200": rows[1][3],
        "20": p20_lr,
    },
    "Random Forest": {
        "50": rows[2][1],
        "100": rows[2][2],
        "200": rows[2][3],
        "20": p20_rf,
    },
}
if run_gb:
    results_holdout["Gradient Boosting"] = {
        "50": rows[3][1],
        "100": rows[3][2],
        "200": rows[3][3],
        "20": precision_at_k(y_test, gb_probs, 20),
    }

metrics_out = {
    "feature_frame_honest": FEATURES_HONEST,
    "global_baseline_p50": float(global_baseline_p50),
    "row_count": int(len(pages)),
    "leakage_demo": {
        "rf_with_log_imp_prev30_p50": float(leaky_p50),
        "rf_honest_four_features_p50": float(honest_p50_demo),
        "label_definition": "(imp_last30 - imp_prev30) / imp_prev30 < -0.20",
    },
    "results_holdout": results_holdout,
    "run_gb": run_gb,
}
(OUT_DIR / "w05_model_metrics.json").write_text(
    json.dumps(metrics_out, indent=2, default=float), encoding="utf-8"
)
print(f"Wrote {OUT_DIR / 'w05_model_metrics.json'}")
'''

CODE_ERRORS = r'''
perm = permutation_importance(
    rf, X_test, y_test, n_repeats=10, random_state=RANDOM_STATE, n_jobs=-1
)
imp = (
    pd.DataFrame({"feature": FEATURES_HONEST, "importance": perm.importances_mean})
    .sort_values("importance", ascending=False)
    .reset_index(drop=True)
)
print("Permutation importance (Random Forest, holdout, honest frame):")
print(imp.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

metrics_out = json.loads((OUT_DIR / "w05_model_metrics.json").read_text(encoding="utf-8"))
metrics_out["importance"] = imp.to_dict(orient="records")
(OUT_DIR / "w05_model_metrics.json").write_text(json.dumps(metrics_out, indent=2), encoding="utf-8")

holdout = pages.iloc[test_idx].copy()
holdout["rf_score"] = rf_probs
top50 = holdout.nlargest(50, "rf_score")
tp = top50[top50["is_declining_label"] == 1]
fp = top50[top50["is_declining_label"] == 0]
summary_cols = ["impressions_90d", "ctr_last30", "avg_pos_last30", "content_age_days"]

err = pd.DataFrame(
    {
        "group": ["true_positives_top50", "false_positives_top50"],
        "n": [len(tp), len(fp)],
        **{
            c: [tp[c].mean() if len(tp) else np.nan, fp[c].mean() if len(fp) else np.nan]
            for c in summary_cols
        },
    }
)
print("\nTop-50 error groups (means):")
print(err.to_string(index=False))

ranked = holdout.sort_values("rf_score", ascending=False).reset_index(drop=True)
fp_rows = ranked[ranked["is_declining_label"] == 0]
if not fp_rows.empty:
    print(f"\nFirst false positive rank: {int(fp_rows.index[0] + 1)}")
    print(fp_rows.iloc[0][summary_cols + ["position_tier"]])

baseline_top50 = holdout.nlargest(50, "baseline_score")
overlap = len(set(top50["content_id"]) & set(baseline_top50["content_id"]))
print(f"\nTop-50 overlap with w04 baseline on holdout: {overlap} pages")
'''


def md_cell(source: str):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code_cell(source: str):
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source.splitlines(keepends=True),
        "outputs": [],
        "execution_count": None,
    }


cells = [
    md_cell(
        "# ML-08 — Capstone Modeling Lane\n\n"
        "[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]"
        "(https://colab.research.google.com/github/JunaidAhamed-7777/flyrank-machine-learning/blob/main/work/notebooks/w05_model.ipynb?flush_cache=true)\n\n"
        "**Lane:** Refresh prediction (ranking). **Slice:** `month=2026-03`, decision `2026-03-31` (w03/w04). "
        "**Step 0** reproduces w04 baseline; **leakage catch** drops `log_imp_prev30` before headline metrics."
    ),
    md_cell(MD1),
    code_cell(CODE_SETUP),
    md_cell(MD2),
    code_cell(CODE_SPLIT),
    md_cell(MD_LEAK),
    code_cell(CODE_LEAK),
    md_cell(MD3),
    code_cell(CODE_TRAIN),
    md_cell(MD_VERDICT),
    md_cell(MD4),
    code_cell(CODE_ERRORS),
    md_cell(MD5),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "cells": cells,
}

NB_PATH.write_text(json.dumps(nb, indent=1), encoding="utf-8")
print(f"Wrote {NB_PATH}")
