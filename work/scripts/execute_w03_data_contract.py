"""Execute w03_data_contract.ipynb logic against the hosted warehouse.

Requires HF_TOKEN in the environment (Colab Secret or shell). Never commit the token.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOTEBOOK = REPO / "work" / "notebooks" / "w03_data_contract.ipynb"
MID_MONTH = "2026-03"
DECISION_DATE = "2026-03-31"


def _require_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if not token:
        try:
            from google.colab import userdata  # type: ignore

            token = userdata.get("HF_TOKEN")
        except Exception:
            token = None
    if not token:
        local = REPO / "work" / ".hf_token_local"
        if local.is_file():
            token = local.read_text(encoding="utf-8").strip()
    if not token:
        print(
            "BLOCKED: HF_TOKEN is not set (env var, Colab Secret, or work/.hf_token_local).",
            file=sys.stderr,
        )
        sys.exit(2)
    return token


def main() -> None:
    import truststore

    truststore.inject_into_ssl()

    import duckdb
    import numpy as np
    import pandas as pd
    from sklearn.tree import DecisionTreeClassifier

    token = _require_token()
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE SECRET hf (TYPE huggingface, TOKEN '{token}')")

    rel = "hf://datasets/FlyRank/internship-warehouse"
    tables = {
        "dim_clients": f"read_parquet('{rel}/dim_clients.parquet')",
        "dim_content": f"read_parquet('{rel}/dim_content.parquet')",
        "fact_daily_march": (
            f"read_parquet('{rel}/fact_content_daily_performance/month={MID_MONTH}/*.parquet')"
        ),
        "fact_daily_feb_march": (
            "read_parquet(["
            f"'{rel}/fact_content_daily_performance/month=2026-02/*.parquet',"
            f"'{rel}/fact_content_daily_performance/month={MID_MONTH}/*.parquet'"
            "])"
        ),
        "fact_daily_sample": f"read_parquet('{rel}/fact_content_daily_performance_sample.parquet')",
        "fact_query_90d": f"read_parquet('{rel}/fact_query_90d.parquet')",
    }

    schema_rows = []
    for name, src in tables.items():
        if name == "fact_daily_feb_march":
            continue
        cols = con.sql(f"DESCRIBE SELECT * FROM {src}").df()
        for _, row in cols.iterrows():
            schema_rows.append(
                {"subset": name, "column": row["column_name"], "type": row["column_type"]}
            )

    schema_df = pd.DataFrame(schema_rows)

    # --- Query 1: daily fact grain in March partition ---
    q1 = con.sql(
        f"""
        SELECT report_date, client_hash_id, content_hash_id, COUNT(*) AS n
        FROM {tables['fact_daily_march']}
        GROUP BY 1, 2, 3
        HAVING COUNT(*) > 1
        LIMIT 5
        """
    ).df()

    # --- Query 2: slice row count + date span (March daily fact) ---
    q2 = con.sql(
        f"""
        SELECT
            COUNT(*) AS row_count,
            MIN(report_date) AS min_report_date,
            MAX(report_date) AS max_report_date
        FROM {tables['fact_daily_march']}
        """
    ).df()

    # --- Query 3: availability with IS TRUE ---
    q3 = con.sql(
        f"""
        SELECT
            COUNT(*) AS rows_before,
            COUNT(*) FILTER (WHERE gsc_data_available IS TRUE) AS rows_after_gsc_true
        FROM {tables['fact_daily_march']}
        """
    ).df()

    # Page-level decision frame: trailing windows ending 2026-03-31
    page_sql = f"""
    WITH daily AS (
        SELECT *
        FROM {tables['fact_daily_feb_march']}
        WHERE report_date <= DATE '{DECISION_DATE}'
    ),
    agg AS (
        SELECT
            client_hash_id,
            content_hash_id,
            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_last30,
            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 60 DAY
                      AND report_date <= DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_prev30,
            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN COALESCE(gsc_clicks, 0) ELSE 0 END) AS clk_last30,
            AVG(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY
                     THEN gsc_avg_position END) AS avg_pos_last30,
            BOOL_AND(gsc_data_available IS TRUE) AS gsc_ok_all_days
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
            END AS trend_direction,
            CASE
                WHEN a.imp_prev30 = 0 THEN NULL
                ELSE (a.imp_last30 - a.imp_prev30) * 100.0 / a.imp_prev30
            END AS trend_pct
        FROM agg a
        WHERE a.imp_last30 > 0
    )
    SELECT
        l.client_hash_id,
        l.content_hash_id,
        l.imp_prev30,
        l.imp_last30,
        l.clk_last30,
        l.avg_pos_last30,
        l.trend_direction,
        l.trend_pct,
        DATE_DIFF('day', d.content_created_date, DATE '{DECISION_DATE}') AS content_age_days,
        d.word_count
    FROM labeled l
    LEFT JOIN {tables['dim_content']} d USING (content_hash_id)
    WHERE l.gsc_ok_all_days IS TRUE
      AND DATE_DIFF('day', d.content_created_date, DATE '{DECISION_DATE}') >= 90
    """

    pages = con.sql(page_sql).df()
    pages["is_declining_label"] = pages["trend_direction"].eq("down").astype(int)
    pages["ctr_last30"] = np.where(
        pages["imp_last30"] > 0, pages["clk_last30"] / pages["imp_last30"] * 100.0, 0.0
    )
    pages["log_imp_prev30"] = np.log1p(pages["imp_prev30"])

    feature_cols = [
        "log_imp_prev30",
        "imp_last30",
        "avg_pos_last30",
        "ctr_last30",
        "content_age_days",
    ]
    feat = pages[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0)
    y = pages["is_declining_label"].values

    def precision_at_k(scores, labels, k=50):
        order = np.argsort(-np.asarray(scores))
        topk = np.asarray(labels)[order[:k]]
        return float(topk.mean())

    tree_honest = DecisionTreeClassifier(max_depth=2, class_weight="balanced", random_state=42)
    tree_honest.fit(feat, y)
    honest_p50 = precision_at_k(tree_honest.predict_proba(feat)[:, 1], y, 50)

    X_leaky = feat.copy()
    X_leaky["trend_pct"] = pages["trend_pct"].fillna(0)
    tree_leaky = DecisionTreeClassifier(max_depth=2, class_weight="balanced", random_state=42)
    tree_leaky.fit(X_leaky, y)
    leaky_p50 = precision_at_k(tree_leaky.predict_proba(X_leaky)[:, 1], y, 50)

    # Page-level grain check on the modeling frame
    q1_page = (
        pages.groupby(["client_hash_id", "content_hash_id"]).size().reset_index(name="n")
    )
    q1_page_dupes = q1_page[q1_page["n"] > 1].head(5)

    out = {
        "schema_row_count": len(schema_df),
        "schema_subsets": sorted(schema_df["subset"].unique().tolist()),
        "q1_daily_dupes": q1.to_dict(orient="records"),
        "q2": q2.to_dict(orient="records")[0],
        "q3": q3.to_dict(orient="records")[0],
        "page_rows": len(pages),
        "q1_page_dupes": q1_page_dupes.to_dict(orient="records"),
        "honest_p50": honest_p50,
        "leaky_p50": leaky_p50,
        "decline_rate": float(pages["is_declining_label"].mean()),
        "feature_cols": feature_cols,
    }
    cache = REPO / "work" / "outputs" / "w03_execution_cache.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
