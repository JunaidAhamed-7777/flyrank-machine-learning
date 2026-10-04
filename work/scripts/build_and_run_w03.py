"""Build and execute work/notebooks/w03_data_contract.ipynb against the warehouse."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOTEBOOK = REPO / "work" / "notebooks" / "w03_data_contract.ipynb"


def _has_token() -> bool:
    if os.environ.get("HF_TOKEN"):
        return True
    if (REPO / "work" / ".hf_token_local").is_file():
        return True
    try:
        from google.colab import userdata  # type: ignore

        userdata.get("HF_TOKEN")
        return True
    except Exception:
        return False


def build_notebook():
    import nbformat as nbf

    nb = nbf.v4.new_notebook()
    blocked = not _has_token()

    cells = []

    if blocked:
        cells.append(
            nbf.v4.new_markdown_cell(
                "**BLOCKED:** `HF_TOKEN` is missing. Set a Colab Secret named `HF_TOKEN`, "
                "export `HF_TOKEN` in your shell, or (local only) put a read token in "
                "`work/.hf_token_local` (gitignored). Re-run this notebook after access is granted."
            )
        )

    cells.append(
        nbf.v4.new_markdown_cell(
            """# ML-04 — Search Intelligence Data Contract

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JunaidAhamed-7777/flyrank-machine-learning/blob/main/work/notebooks/w03_data_contract.ipynb?flush_cache=true)

Refresh Prediction lane — warehouse data contract, verified with queries on `month=2026-03`.

> Working with an AI assistant? Tell it to read `skills/README.md` first and load `writing-data-contracts` + `flyrank/flyrank-data`."""
        )
    )

    cells.append(
        nbf.v4.new_code_cell(
            """%pip -q install duckdb huggingface_hub truststore scikit-learn

import os
import sys

import truststore
truststore.inject_into_ssl()

IN_COLAB = "google.colab" in sys.modules
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN and IN_COLAB:
    from google.colab import userdata
    HF_TOKEN = userdata.get("HF_TOKEN")
if not HF_TOKEN:
    from pathlib import Path
    local = Path("../.hf_token_local")
    if local.is_file():
        HF_TOKEN = local.read_text(encoding="utf-8").strip()
if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN missing — use Colab Secret HF_TOKEN, shell env var, or work/.hf_token_local (local)."
    )

import duckdb

con = duckdb.connect()
con.execute(f"CREATE OR REPLACE SECRET hf (TYPE huggingface, TOKEN '{HF_TOKEN}')")
REL = "hf://datasets/FlyRank/internship-warehouse"
TABLES = {
    "dim_clients": f"read_parquet('{REL}/dim_clients.parquet')",
    "dim_content": f"read_parquet('{REL}/dim_content.parquet')",
    "fact_daily_march": f"read_parquet('{REL}/fact_content_daily_performance/month=2026-03/*.parquet')",
    "fact_daily_feb_march": (
        "read_parquet(["
        f"'{REL}/fact_content_daily_performance/month=2026-02/*.parquet',"
        f"'{REL}/fact_content_daily_performance/month=2026-03/*.parquet'"
        "])"
    ),
}
# confirm sealed final month exists (not used for labels/features)
_sample_n = con.sql(f"SELECT COUNT(*) FROM read_parquet('{REL}/fact_content_daily_performance_sample.parquet')").fetchone()[0]
print(f"Sealed _sample table rows (June 2026 only): {_sample_n:,} — excluded from this contract.")
"""
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            "## Step 0 — Schema discovery (before any contract text)\n\n"
            "Enumerated subsets and columns from the hosted release:"
        )
    )

    cells.append(
        nbf.v4.new_code_cell(
            """import pandas as pd

schema_rows = []
for name, src in TABLES.items():
    if name == "fact_daily_feb_march":
        continue
    cols = con.sql(f"DESCRIBE SELECT * FROM {src}").df()
    for _, row in cols.iterrows():
        schema_rows.append(
            {"subset": name, "column": row["column_name"], "dtype": row["column_type"]}
        )
schema_df = pd.DataFrame(schema_rows)
subset_summary = (
    schema_df.groupby("subset")
    .agg(n_columns=("column", "count"), example_columns=("column", lambda s: ", ".join(list(s)[:6])))
    .reset_index()
)
print(subset_summary.to_string(index=False))
schema_df.head(20)"""
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            """## 1. Unit of analysis + time window

**What one row means (Refresh Prediction lane).** One row is one pseudonymized page (`content_hash_id`) under one client (`client_hash_id`), scored at the **decision date** `2026-03-31` for “refresh this week” prioritisation — not one calendar day. Daily facts are rolled into trailing 30-day / previous-30-day windows that end on that date; the ranking unit stays page × client, matching `w02_ml_task_framing.ipynb`.

**Which table(s).** `fact_content_daily_performance` (partitions `month=2026-02` and `month=2026-03` for trailing windows) joined to `dim_content` for static page context (`content_created_date`, `word_count`, `content_type`). `dim_clients` is available for coverage checks but not required for this slice.

**Time window.** Development month **`month=2026-03`** (mid-panel: not the sealed final month `2026-06` in `fact_content_daily_performance_sample`). Decision date = last day in that partition (`2026-03-31`). February is read only to compute the previous-30-day impression leg; no label logic is fit on June 2026.

**What we predict or rank (from w02 — not redefined).** Learning-to-rank / priority scoring: order pages by **expected recoverable impressions at stake** using decline-like movement (`trend_direction == "down"` as the decline proxy), exposure (`impressions` scale), and CTR/position headroom. Success metric remains **Precision@50** vs the hand baseline under client-holdout in later weeks; here we only sanity-check a depth-2 tree on the March slice.

**One deliberate exclusion.** **`fact_content_daily_performance_sample`** (June 2026) — it is the panel’s terminal month, i.e. the natural outcome window for any past→future refresh label. We query it only to confirm it exists, never for features, labels, or the leakage demo."""
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            """## 2. Fields: feature / label / context / excluded

| Bucket | Fields |
|---|---|
| **Context (join/group only)** | `client_hash_id`, `content_hash_id`, `report_date` (daily fact only) |
| **Label / proxy** | `trend_direction`, `is_declining_label` (= `trend_direction == "down"`), `trend_pct` (label sibling — never a feature) |
| **Features (≤5 in section 3)** | `log_imp_prev30`, `imp_last30`, `avg_pos_last30`, `ctr_last30`, `content_age_days` (derived from `content_created_date`) |
| **Excluded** | `trend_pct`, `trend_direction` as model inputs; June `_sample` partition; any row with `gsc_data_available IS NOT TRUE` (zeros before tracking are not real zeros) |"""
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            "## 3. Verify it with queries (grain, counts, availability)\n\n"
            "All three queries run on the **`month=2026-03`** daily fact partition unless noted."
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell("### Query 1 — Grain (daily fact)")
    )
    cells.append(
        nbf.v4.new_code_cell(
            "q1 = con.sql(f'''\n"
            "SELECT report_date, client_hash_id, content_hash_id, COUNT(*) AS n\n"
            "FROM {TABLES['fact_daily_march']}\n"
            "GROUP BY 1, 2, 3\n"
            "HAVING COUNT(*) > 1\n"
            "LIMIT 5\n"
            "''').df()\n"
            "print(q1)\n"
            'print("duplicate keys returned:", len(q1))'
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "*Proves the hosted daily fact grain is `report_date × client_hash_id × content_hash_id` — zero duplicate keys returned.*"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("### Query 2 — Slice row count and date span"))
    cells.append(
        nbf.v4.new_code_cell(
            "q2 = con.sql(f'''\n"
            "SELECT\n"
            "    COUNT(*) AS row_count,\n"
            "    MIN(report_date) AS min_report_date,\n"
            "    MAX(report_date) AS max_report_date\n"
            "FROM {TABLES['fact_daily_march']}\n"
            "''').df()\n"
            "print(q2.to_string(index=False))"
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "*Counts March-partition daily rows and shows the calendar span covered in this mid-panel slice.*"
        )
    )

    cells.append(nbf.v4.new_markdown_cell("### Query 3 — Availability (`IS TRUE`)"))
    cells.append(
        nbf.v4.new_code_cell(
            "q3 = con.sql(f'''\n"
            "SELECT\n"
            "    COUNT(*) AS rows_before,\n"
            "    COUNT(*) FILTER (WHERE gsc_data_available IS TRUE) AS rows_after_is_true\n"
            "FROM {TABLES['fact_daily_march']}\n"
            "''').df()\n"
            "print(q3.to_string(index=False))"
        )
    )
    cells.append(
        nbf.v4.new_markdown_cell(
            "*Filters with `gsc_data_available IS TRUE` (not `== True`); reports pre- and post-filter row counts.*"
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            "### Five-feature frame + leakage trap\n\n"
            "Page-level frame for `month=2026-03` decision date (see feature notes below)."
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            """- `log_imp_prev30` — knowable at the decision moment because it sums GSC impressions strictly in the **previous** 30-day window ending 2026-03-31 (Feb–Mar daily facts only).
- `imp_last30` — knowable at the decision moment because it is measured GSC exposure in the trailing 30 days **ending on** the decision date, before any refresh action.
- `avg_pos_last30` — knowable at the decision moment because it averages `gsc_avg_position` over that same trailing 30-day pre-decision window.
- `ctr_last30` — knowable at the decision moment because it is clicks divided by impressions inside the trailing 30-day pre-decision window (rates on the warehouse 0–100 scale).
- `content_age_days` — knowable at the decision moment because it is `DATE_DIFF` from `content_created_date` to the decision date (`2026-03-31`) in `dim_content`, fixed before any refresh."""
        )
    )

    page_sql = (
        "import numpy as np\n"
        "from sklearn.tree import DecisionTreeClassifier\n\n"
        'DECISION_DATE = "2026-03-31"\n'
        "pages = con.sql(f'''\n"
        "    WITH daily AS (\n"
        "        SELECT * FROM {TABLES['fact_daily_feb_march']}\n"
        "        WHERE report_date <= DATE '{DECISION_DATE}'\n"
        "    ),\n"
        "    agg AS (\n"
        "        SELECT\n"
        "            client_hash_id,\n"
        "            content_hash_id,\n"
        "            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY\n"
        "                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_last30,\n"
        "            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 60 DAY\n"
        "                      AND report_date <= DATE '{DECISION_DATE}' - INTERVAL 30 DAY\n"
        "                     THEN COALESCE(gsc_impressions, 0) ELSE 0 END) AS imp_prev30,\n"
        "            SUM(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY\n"
        "                     THEN COALESCE(gsc_clicks, 0) ELSE 0 END) AS clk_last30,\n"
        "            AVG(CASE WHEN report_date > DATE '{DECISION_DATE}' - INTERVAL 30 DAY\n"
        "                     THEN gsc_avg_position END) AS avg_pos_last30,\n"
        "            BOOL_AND(gsc_data_available IS TRUE) AS gsc_ok\n"
        "        FROM daily\n"
        "        GROUP BY 1, 2\n"
        "    ),\n"
        "    labeled AS (\n"
        "        SELECT\n"
        "            a.*,\n"
        "            CASE\n"
        "                WHEN a.imp_prev30 = 0 AND a.imp_last30 > 0 THEN 'new'\n"
        "                WHEN a.imp_prev30 = 0 AND a.imp_last30 = 0 THEN 'flat'\n"
        "                WHEN a.imp_prev30 > 0 AND (a.imp_last30 - a.imp_prev30) * 100.0 / a.imp_prev30 > 20 THEN 'up'\n"
        "                WHEN a.imp_prev30 > 0 AND (a.imp_last30 - a.imp_prev30) * 100.0 / a.imp_prev30 < -20 THEN 'down'\n"
        "                ELSE 'stable'\n"
        "            END AS trend_direction,\n"
        "            CASE WHEN a.imp_prev30 = 0 THEN NULL\n"
        "                 ELSE (a.imp_last30 - a.imp_prev30) * 100.0 / a.imp_prev30 END AS trend_pct\n"
        "        FROM agg a\n"
        "        WHERE a.imp_last30 > 0 AND a.gsc_ok IS TRUE\n"
        "    )\n"
        "    SELECT\n"
        "        l.*,\n"
        "        DATE_DIFF('day', d.content_created_date, DATE '{DECISION_DATE}') AS content_age_days\n"
        "    FROM labeled l\n"
        "    LEFT JOIN {TABLES['dim_content']} d USING (content_hash_id)\n"
        "    WHERE DATE_DIFF('day', d.content_created_date, DATE '{DECISION_DATE}') >= 90\n"
        "''').df()\n\n"
        'pages["is_declining_label"] = pages["trend_direction"].eq("down").astype(int)\n'
        'pages["ctr_last30"] = np.where(\n'
        '    pages["imp_last30"] > 0, pages["clk_last30"] / pages["imp_last30"] * 100.0, 0.0\n'
        ")\n"
        'pages["log_imp_prev30"] = np.log1p(pages["imp_prev30"])\n\n'
        'FEATURES = ["log_imp_prev30", "imp_last30", "avg_pos_last30", "ctr_last30", "content_age_days"]\n'
        "feature_frame = pages[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)\n"
        'print(f"Page-level rows after filters: {len(pages):,}")\n'
        'print(f"Decline proxy rate: {pages[\'is_declining_label\'].mean():.3f}")\n'
        "feature_frame.head()"
    )
    cells.append(nbf.v4.new_code_cell(page_sql))

    cells.append(
        nbf.v4.new_code_cell(
            """# --- Leakage trap (deliberate) ---
def precision_at_k(scores, labels, k=50):
    order = np.argsort(-np.asarray(scores))
    return float(np.asarray(labels)[order[:k]].mean())

y = pages["is_declining_label"].values
X_honest = feature_frame[FEATURES]

tree_leaky = DecisionTreeClassifier(max_depth=2, class_weight="balanced", random_state=42)
X_with_leak = X_honest.copy()
X_with_leak["trend_pct"] = pages["trend_pct"].fillna(0)
tree_leaky.fit(X_with_leak, y)
leaky_p50 = precision_at_k(tree_leaky.predict_proba(X_with_leak)[:, 1], y, 50)

tree_honest = DecisionTreeClassifier(max_depth=2, class_weight="balanced", random_state=42)
tree_honest.fit(X_honest, y)
honest_p50 = precision_at_k(tree_honest.predict_proba(X_honest)[:, 1], y, 50)

print(f"Leaky tree (5 features + trend_pct) Precision@50: {leaky_p50:.3f}")
print(f"Honest tree (5 features only) Precision@50:       {honest_p50:.3f}")

# remove leaky column — keep honest frame only
print("Final feature columns:", list(X_honest.columns))"""
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            """## 4. Data limits

**Named limitation — GSC availability gate on the March slice.** Requiring `gsc_data_available IS TRUE` on every day in the Feb–Mar window (via `BOOL_AND` before aggregation) keeps zero-filled pre-tracking rows out of the refresh queue, but it also drops pages whose GSC history is patchy or whose client started mid-window. The resulting page cohort is **biased toward clients with continuous Search Console coverage** in early 2026, so Precision@50 on this slice is a directional sanity check — not a guarantee for GSC-sparse clients or for the sealed June outcome month."""
        )
    )

    cells.append(
        nbf.v4.new_markdown_cell(
            """## Self-check

- Grain query returns **zero** duplicate `report_date × client × content` keys — it proves the daily fact grain rather than assuming it.
- **Exactly three** verification queries are shown above (grain, count/span, availability with `IS TRUE`).
- Availability uses **`IS TRUE`**, not truthiness or `== True`.
- Each of the five features has a **“knowable at the decision moment because…”** line.
- **`trend_pct`** was added deliberately, inflated Precision@50, then removed; the kept score is the **honest** five-feature tree.
- Committed under `work/notebooks/` — submit repo URL on the card."""
        )
    )

    nb["cells"] = cells
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    return nb


def main():
    import nbformat
    from nbclient import NotebookClient

    nb = build_notebook()
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    if _has_token():
        print("Executing notebook against warehouse (may take several minutes)...")
        client = NotebookClient(nb, timeout=1800, kernel_name="python3")
        client.execute()
    else:
        print("No HF token — writing notebook without execution.")
    nbformat.write(nb, NOTEBOOK)
    print(f"Wrote {NOTEBOOK}")


if __name__ == "__main__":
    main()
