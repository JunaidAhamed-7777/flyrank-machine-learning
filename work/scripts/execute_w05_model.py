"""Run w05 modeling pipeline (honest 4-feature frame + leakage demo)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_DIR = ROOT / "work" / "notebooks"
OUT_DIR = ROOT / "work" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DECISION_DATE = "2026-03-31"
RANDOM_STATE = 42

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


def baseline_scores(pages: pd.DataFrame) -> pd.Series:
    tier_median_ctr = pages.groupby("position_tier")["ctr_last30"].transform("median")
    ctr_headroom = (tier_median_ctr - pages["ctr_last30"]).clip(lower=0)
    tier_weight = pages["position_tier"].map(TIER_WEIGHT).fillna(0.0)
    return pages["impressions_90d"] * ctr_headroom * tier_weight


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
    if (
        len(train_idx) > 0
        and len(test_idx) > 0
        and target.iloc[train_idx].nunique() == 2
        and target.iloc[test_idx].nunique() == 2
    ):
        return train_idx, test_idx
    raise RuntimeError("client holdout split failed class balance check")


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
    import truststore

    truststore.inject_into_ssl()
    token_path = NOTEBOOK_DIR.parent / ".hf_token_local"
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


def main() -> None:
    pages = load_pages()
    pages["ctr_last30"] = np.where(
        pages["imp_last30"] > 0,
        pages["clk_last30"] / pages["imp_last30"] * 100.0,
        0.0,
    )
    pages["log_imp_prev30"] = np.log1p(pages["imp_prev30"])
    pages["position_tier"] = pages["avg_pos_last30"].map(position_tier)
    pages["is_declining_label"] = pages["trend_direction"].str.lower().eq("down").astype(int)
    pages["baseline_score"] = baseline_scores(pages)

    global_p50 = precision_at_k(pages["is_declining_label"], pages["baseline_score"], 50)
    y = pages["is_declining_label"]
    train_idx, test_idx = make_client_holdout(pages, y)
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    X_leaky = pages[FEATURES_LEAKY].replace([np.inf, -np.inf], np.nan).fillna(0)
    X_honest = pages[FEATURES_HONEST].replace([np.inf, -np.inf], np.nan).fillna(0)

    rf_leaky = make_rf()
    rf_leaky.fit(X_leaky.iloc[train_idx], y_train)
    leaky_p50 = precision_at_k(y_test, rf_leaky.predict_proba(X_leaky.iloc[test_idx])[:, 1], 50)

    rf_honest_probe = make_rf()
    rf_honest_probe.fit(X_honest.iloc[train_idx], y_train)
    honest_p50_probe = precision_at_k(
        y_test, rf_honest_probe.predict_proba(X_honest.iloc[test_idx])[:, 1], 50
    )

    baseline_holdout = pages.iloc[test_idx]["baseline_score"].to_numpy()
    results = {
        "w04 baseline (CTR headroom)": {
            "50": precision_at_k(y_test, baseline_holdout, 50),
            "100": precision_at_k(y_test, baseline_holdout, 100),
            "200": precision_at_k(y_test, baseline_holdout, 200),
            "20": precision_at_k(y_test, baseline_holdout, 20),
        },
    }

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
    lr.fit(X_honest.iloc[train_idx], y_train)
    rf.fit(X_honest.iloc[train_idx], y_train)
    lr_probs = lr.predict_proba(X_honest.iloc[test_idx])[:, 1]
    rf_probs = rf.predict_proba(X_honest.iloc[test_idx])[:, 1]

    for name, probs in [("Logistic Regression", lr_probs), ("Random Forest", rf_probs)]:
        results[name] = {
            "50": precision_at_k(y_test, probs, 50),
            "100": precision_at_k(y_test, probs, 100),
            "200": precision_at_k(y_test, probs, 200),
            "20": precision_at_k(y_test, probs, 20),
        }

    run_gb = results["Random Forest"]["50"] - results["Logistic Regression"]["50"] >= 0.03
    gb_probs = None
    if run_gb:
        gb = GradientBoostingClassifier(random_state=RANDOM_STATE)
        gb.fit(X_honest.iloc[train_idx], y_train)
        gb_probs = gb.predict_proba(X_honest.iloc[test_idx])[:, 1]
        results["Gradient Boosting"] = {
            "50": precision_at_k(y_test, gb_probs, 50),
            "100": precision_at_k(y_test, gb_probs, 100),
            "200": precision_at_k(y_test, gb_probs, 200),
            "20": precision_at_k(y_test, gb_probs, 20),
        }

    perm = permutation_importance(
        rf, X_honest.iloc[test_idx], y_test, n_repeats=10, random_state=RANDOM_STATE, n_jobs=-1
    )
    imp_df = (
        pd.DataFrame({"feature": FEATURES_HONEST, "importance": perm.importances_mean})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    print(f"global baseline P@50={global_p50:.2f}")
    print(f"leakage demo RF: with log_imp_prev30 P@50={leaky_p50:.2f} | without={honest_p50_probe:.2f}")
    for name, m in results.items():
        print(name, m)
    print(imp_df.to_string(index=False))
    print(f"run_gb={run_gb}")

    out = {
        "feature_frame_honest": FEATURES_HONEST,
        "global_baseline_p50": global_p50,
        "row_count": len(pages),
        "leakage_demo": {
            "rf_with_log_imp_prev30_p50": leaky_p50,
            "rf_honest_four_features_p50": honest_p50_probe,
            "label_definition": "(imp_last30 - imp_prev30) / imp_prev30 < -0.20",
        },
        "results_holdout": results,
        "run_gb": run_gb,
        "importance": imp_df.to_dict(orient="records"),
        "train_decline_rate": float(y.iloc[train_idx].mean()),
        "holdout_decline_rate": float(y.iloc[test_idx].mean()),
        "holdout_rows": int(len(test_idx)),
    }
    (OUT_DIR / "w05_model_metrics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
