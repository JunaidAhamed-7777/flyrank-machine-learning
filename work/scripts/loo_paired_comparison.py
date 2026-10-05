"""Paired leave-one-client-out comparison for the March 2026 refresh slice.

Recomputes per-client Precision@50 for the random forest and the CTR-headroom
baseline using the same split, features, and scoring rule as
work/notebooks/w06_validation_audit.ipynb. Writes aggregate results to
work/outputs/loo_paired_comparison.json.

Does not print page text, queries, or client names.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "work" / "outputs" / "loo_paired_comparison.json"
CACHE_MAR = REPO_ROOT / "work" / "outputs" / "_cache_march_slice.parquet"
CACHE_FEB = REPO_ROOT / "work" / "outputs" / "_cache_feb_slice.parquet"
W06_PATH = REPO_ROOT / "work" / "outputs" / "w06_audit_metrics.json"

DECISION_DATE_MAR = "2026-03-31"
DECISION_DATE_FEB = "2026-02-28"
RANDOM_STATE = 42
N_BOOTSTRAP = 10_000
FEATURES = ["imp_last30", "avg_pos_last30", "ctr_last30", "content_age_days"]
EXPOSURE_FLOOR = 100

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


def precision_at_k(y_true, scores, k: int) -> float:
    frame = pd.DataFrame({"y": list(y_true), "score": list(scores)})
    if frame.empty:
        return 0.0
    top = frame.sort_values("score", ascending=False).head(min(k, len(frame)))
    return float(top["y"].mean()) if len(top) else 0.0


def baseline_score(pages: pd.DataFrame) -> pd.Series:
    tier_median_ctr = pages.groupby("position_tier")["ctr_last30"].transform("median")
    ctr_headroom = (tier_median_ctr - pages["ctr_last30"]).clip(lower=0)
    tier_weight = pages["position_tier"].map(TIER_WEIGHT).fillna(0.0)
    return pages["impressions_90d"] * ctr_headroom * tier_weight


def make_rf() -> RandomForestClassifier:
    return RandomForestClassifier(
        class_weight="balanced_subsample",
        max_depth=10,
        min_samples_leaf=25,
        n_estimators=200,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )


def hf_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if token:
        return token.strip()
    local = REPO_ROOT / "work" / ".hf_token_local"
    if local.is_file():
        return local.read_text(encoding="utf-8").strip()
    raise RuntimeError("HF_TOKEN missing")


def load_pages(decision_date: str, month_globs: list[str]) -> pd.DataFrame:
    import duckdb

    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass

    token = hf_token()
    con = duckdb.connect()
    con.execute("CREATE OR REPLACE SECRET hf (TYPE huggingface, TOKEN ?)", [token])
    rel = "hf://datasets/FlyRank/internship-warehouse"
    dim_content = f"read_parquet('{rel}/dim_content.parquet')"
    paths = ",\n        ".join(
        f"'{rel}/fact_content_daily_performance/{month}/*.parquet'" for month in month_globs
    )
    fact = f"read_parquet([{paths}])"
    sql = f"""
    WITH daily AS (
        SELECT * FROM {fact}
        WHERE report_date <= DATE '{decision_date}'
    ),
    agg AS (
        SELECT
            client_hash_id,
            content_hash_id,
            SUM(CASE WHEN report_date > DATE '{decision_date}' - INTERVAL 90 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS impressions_90d,
            SUM(CASE WHEN report_date > DATE '{decision_date}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_last30,
            SUM(CASE WHEN report_date > DATE '{decision_date}' - INTERVAL 60 DAY
                      AND report_date <= DATE '{decision_date}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_prev30,
            SUM(CASE WHEN report_date > DATE '{decision_date}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_clicks, 0) ELSE 0 END) AS clk_last30,
            AVG(CASE WHEN report_date > DATE '{decision_date}' - INTERVAL 30 DAY
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
        DATE_DIFF('day', d.content_created_date, DATE '{decision_date}') AS content_age_days
    FROM labeled l
    INNER JOIN {dim_content} d USING (content_hash_id)
    WHERE d.content_created_date <= DATE '{decision_date}'
      AND DATE_DIFF('day', d.content_created_date, DATE '{decision_date}') >= 90
    """
    return con.sql(sql).df()


def enrich(pages: pd.DataFrame) -> pd.DataFrame:
    pages = pages.copy()
    pages["ctr_last30"] = np.where(
        pages["imp_last30"] > 0,
        pages["clk_last30"] / pages["imp_last30"] * 100.0,
        0.0,
    )
    pages["position_tier"] = pages["avg_pos_last30"].map(position_tier)
    pages["is_declining_label"] = pages["trend_direction"].str.lower().eq("down").astype(int)
    pages["baseline_score"] = baseline_score(pages)
    return pages


def assign_archetype(frame: pd.DataFrame) -> pd.DataFrame:
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
        code, _action = ARCHETYPE_META[arch]
        if arch == "NEW_OR_UNCLEAR" and tier != "no_data" and trend not in ("new", "flat"):
            code = "INSUFFICIENT_DATA"
        reasons.append(code)
    out = frame.copy()
    out["archetype"] = names
    out["reason_code"] = reasons
    out["action"] = [ARCHETYPE_META[name][1] for name in names]
    return out


def load_or_cache(cache: Path, decision_date: str, months: list[str], label: str) -> pd.DataFrame:
    if cache.is_file():
        print(f"cache hit {label}", flush=True)
        return pd.read_parquet(cache)
    print(f"querying warehouse {label}", flush=True)
    frame = load_pages(decision_date, months)
    frame.to_parquet(cache, index=False)
    print(f"cached {label} rows={len(frame)}", flush=True)
    return frame


def bootstrap_mean_ci(diffs: np.ndarray) -> dict:
    rng = np.random.default_rng(RANDOM_STATE)
    n = len(diffs)
    draws = rng.integers(0, n, size=(N_BOOTSTRAP, n))
    means = diffs[draws].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {
        "n_bootstrap": N_BOOTSTRAP,
        "seed": RANDOM_STATE,
        "method": "percentile bootstrap of the paired mean difference, resampling clients with replacement",
        "mean_difference": float(diffs.mean()),
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "ci_crosses_zero": bool(lo < 0 < hi),
    }


def wilcoxon_and_sign(diffs: np.ndarray) -> dict:
    payload: dict = {"n_clients": int(len(diffs))}
    nonzero = diffs[diffs != 0]
    n_pos = int((diffs > 0).sum())
    n_neg = int((diffs < 0).sum())
    n_tie = int((diffs == 0).sum())
    payload["n_rf_greater"] = n_pos
    payload["n_baseline_greater"] = n_neg
    payload["n_tie"] = n_tie
    try:
        from scipy.stats import binomtest, wilcoxon

        stat, p = wilcoxon(diffs, zero_method="wilcox", alternative="two-sided", method="auto")
        payload["wilcoxon_statistic"] = float(stat)
        payload["wilcoxon_pvalue"] = float(p)
        payload["wilcoxon_zero_method"] = "wilcox"
        payload["wilcoxon_alternative"] = "two-sided"
        if len(nonzero):
            sign = binomtest(n_pos, n_pos + n_neg, p=0.5, alternative="two-sided")
            payload["sign_test_pvalue"] = float(sign.pvalue)
        else:
            payload["sign_test_pvalue"] = None
    except Exception as exc:  # scipy missing or wilcoxon undefined
        payload["scipy_error"] = type(exc).__name__
        if n_pos + n_neg == 0:
            payload["sign_test_pvalue"] = None
        else:
            # two-sided exact binomial via numpy; used only if scipy is absent
            from math import comb

            k = min(n_pos, n_neg)
            n = n_pos + n_neg
            tail = sum(comb(n, i) for i in range(0, k + 1)) / (2**n)
            payload["sign_test_pvalue"] = float(min(1.0, 2 * tail))
    return payload


def worked_example(pages: pd.DataFrame) -> dict:
    scored = assign_archetype(pages)
    X = scored[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = scored["is_declining_label"]
    model = make_rf()
    model.fit(X, y)
    scored = scored.copy()
    scored["score"] = model.predict_proba(X)[:, 1]
    pool = scored[
        (scored["is_declining_label"] == 1) & (scored["archetype"] == "HIGH_LEVERAGE_REFRESH")
    ]
    if pool.empty:
        return {"available": False, "reason": "no declining HIGH_LEVERAGE_REFRESH row"}
    median_score = float(pool["score"].median())
    pick = pool.iloc[(pool["score"] - median_score).abs().argmin()]
    return {
        "available": True,
        "selection": "declining HIGH_LEVERAGE_REFRESH page whose full-slice score is closest to the median score of that group",
        "score_source": "Random forest fit on the full March slice, matching the playbook queue, not a leave-one-client-out score",
        "content_id": str(pick["content_id"]),
        "imp_last30": float(pick["imp_last30"]),
        "avg_pos_last30": float(pick["avg_pos_last30"]),
        "ctr_last30": float(pick["ctr_last30"]),
        "content_age_days": float(pick["content_age_days"]),
        "position_tier": str(pick["position_tier"]),
        "score": float(pick["score"]),
        "archetype": str(pick["archetype"]),
        "reason_code": str(pick["reason_code"]),
        "action": str(pick["action"]),
        "is_declining_label": int(pick["is_declining_label"]),
        "group_median_score": median_score,
        "group_n": int(len(pool)),
    }


def main() -> None:
    raw_mar = load_or_cache(
        CACHE_MAR,
        DECISION_DATE_MAR,
        ["month=2026-01", "month=2026-02", "month=2026-03"],
        "march",
    )
    pages = enrich(raw_mar)
    print(f"march_rows={len(pages)} clients={pages['client_id'].nunique()}", flush=True)

    y = pages["is_declining_label"]
    X = pages[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    rows = []
    skipped = []
    for i, cid in enumerate(sorted(pages["client_id"].unique()), start=1):
        tr = pages["client_id"] != cid
        te = ~tr
        y_tr = y[tr]
        held = pages.loc[te]
        if y_tr.nunique() < 2 or int(te.sum()) == 0:
            skipped.append(str(cid))
            print(f"skip {i}", flush=True)
            continue
        model = make_rf()
        model.fit(X[tr], y_tr)
        p_rf = precision_at_k(y[te], model.predict_proba(X[te])[:, 1], 50)
        p_bl = precision_at_k(y[te], held["baseline_score"], 50)
        rows.append(
            {
                "client_id": str(cid),
                "n_pages": int(te.sum()),
                "n_declines": int(y[te].sum()),
                "median_imp_last30": float(held["imp_last30"].median()),
                "median_impressions_90d": float(held["impressions_90d"].median()),
                "p50_rf": p_rf,
                "p50_baseline": p_bl,
                "k_used": int(min(50, int(te.sum()))),
            }
        )
        print(f"fold {i} p50_rf={p_rf:.4f} p50_bl={p_bl:.4f} n={int(te.sum())}", flush=True)

    client_frame = pd.DataFrame(rows)
    rf = client_frame["p50_rf"].to_numpy(dtype=float)
    bl = client_frame["p50_baseline"].to_numpy(dtype=float)
    diffs = rf - bl
    loo_mean = float(rf.mean())
    loo_std = float(rf.std(ddof=0))
    bl_mean = float(bl.mean())
    stored = json.loads(W06_PATH.read_text(encoding="utf-8"))
    match = abs(loo_mean - float(stored["p50_loo_rf_mean"])) < 1e-9 and abs(
        loo_std - float(stored["p50_loo_rf_std"])
    ) < 1e-9 and abs(bl_mean - float(stored["loo_baseline_mean"])) < 1e-9

    base_rate = float(y.mean())
    boot = bootstrap_mean_ci(diffs)
    tests = wilcoxon_and_sign(diffs)

    print("querying warehouse february overlap", flush=True)
    raw_feb = load_or_cache(
        CACHE_FEB,
        DECISION_DATE_FEB,
        ["month=2026-01", "month=2026-02"],
        "february",
    )
    feb_clients = set(raw_feb["client_id"].astype(str))
    mar_clients = set(pages["client_id"].astype(str))
    feb_pages = set(raw_feb["content_id"].astype(str))
    mar_pages = set(pages["content_id"].astype(str))
    overlap = {
        "feb_rows": int(len(raw_feb)),
        "mar_rows": int(len(pages)),
        "feb_clients": int(len(feb_clients)),
        "mar_clients": int(len(mar_clients)),
        "clients_in_both": int(len(feb_clients & mar_clients)),
        "clients_only_march": int(len(mar_clients - feb_clients)),
        "clients_only_february": int(len(feb_clients - mar_clients)),
        "march_pages_also_in_february": int(len(mar_pages & feb_pages)),
        "march_page_overlap_share": float(len(mar_pages & feb_pages) / len(mar_pages)),
    }
    print(
        f"overlap clients_both={overlap['clients_in_both']} page_share={overlap['march_page_overlap_share']:.4f}",
        flush=True,
    )

    print("fitting playbook example", flush=True)
    example = worked_example(pages)

    zeros = client_frame[client_frame["p50_rf"] == 0.0].sort_values(
        ["n_pages", "n_declines", "client_id"]
    )
    payload = {
        "n_folds": int(len(client_frame)),
        "n_skipped": int(len(skipped)),
        "loo_rf_mean": loo_mean,
        "loo_rf_std_ddof0": loo_std,
        "loo_baseline_mean": bl_mean,
        "n_zero_rf_folds": int((rf == 0).sum()),
        "matches_w06_receipt": bool(match),
        "w06_p50_loo_rf_mean": float(stored["p50_loo_rf_mean"]),
        "w06_p50_loo_rf_std": float(stored["p50_loo_rf_std"]),
        "w06_loo_baseline_mean": float(stored["loo_baseline_mean"]),
        "base_rate": base_rate,
        "expected_declines_per_50_at_base_rate": base_rate * 50,
        "expected_declines_per_50_at_loo_rf_mean": loo_mean * 50,
        "expected_declines_per_50_at_loo_baseline_mean": bl_mean * 50,
        "bootstrap": boot,
        "tests": tests,
        "feb_mar_overlap": overlap,
        "zero_folds": zeros.to_dict(orient="records"),
        "clients": client_frame.sort_values("client_id").to_dict(orient="records"),
        "worked_example": example,
        "row_count": int(len(pages)),
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUT_PATH}", flush=True)
    print(
        f"match={match} mean={loo_mean:.6f} std={loo_std:.6f} diff={boot['mean_difference']:.4f} "
        f"ci=({boot['ci95_low']:.4f},{boot['ci95_high']:.4f}) crosses0={boot['ci_crosses_zero']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
