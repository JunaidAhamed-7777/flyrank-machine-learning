"""Theme-aware figures for docs/index.html.

Bars in Figure 1 use the saved audit receipt (work/outputs/w06_audit_metrics.json).
The client strip uses the refit in work/outputs/loo_paired_comparison.json.
Archetype counts come from work/outputs/w07_playbook_metrics.json.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs" / "assets"
FIGS = ROOT / "work" / "figures"

STYLE = """
<style>
  .chart { color: var(--text, #1a1a1a); }
  .chart text { fill: currentColor; font-family: "Source Serif 4", Georgia, serif; }
  .axis, .grid { stroke: var(--rule, #e2e0d8); }
  .axis { fill: none; }
  .rf { fill: var(--accent, #3b4cca); }
  .bl { fill: var(--bar-baseline, #b7b4ac); }
  .zero { fill: var(--muted, #5c5a55); }
  @media (prefers-color-scheme: dark) {
    .chart {
      color: var(--text, #e8e6e1);
      --accent: #9aa6ff;
      --rule: #3a3934;
      --bar-baseline: #8d8a82;
      --muted: #b1aea6;
    }
  }
</style>
"""


def load(name: str) -> dict:
    return json.loads((ROOT / "work" / "outputs" / name).read_text(encoding="utf-8"))


def svg_open(width: int, height: int, label: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="chart" role="img" '
        f'aria-label="{label}" viewBox="0 0 {width} {height}" width="100%">'
        f"{STYLE}"
    )


def figure1() -> str:
    audit = load("w06_audit_metrics.json")
    w07 = load("w07_playbook_metrics.json")
    groups = [
        ("Leave-one-client-out", audit["p50_loo_rf_mean"], audit["loo_baseline_mean"]),
        ("Single holdout", audit["p50_w05_holdout_rf"], audit["p50_w05_holdout_baseline"]),
        ("February to March", audit["p50_time_aware_rf"], audit["time_aware_baseline_p50"]),
    ]
    base = w07["slice_base_decline_rate"]
    width, height = 640, 380
    left, right, top, bottom = 52, 616, 28, 268
    ymax = 0.55
    plot_h = bottom - top

    def y(value: float) -> float:
        return bottom - (value / ymax) * plot_h

    parts = [
        svg_open(width, height, "Random forest and baseline Precision at 50 across three checks, with the base rate marked"),
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>',
    ]
    for tick in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
        yy = y(tick)
        parts.append(f'<line class="grid" x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke-dasharray="2 4"/>')
        parts.append(
            f'<text x="{left - 8}" y="{yy + 4:.1f}" text-anchor="end" font-size="12">{tick:.1f}</text>'
        )
    base_y = y(base)
    parts.append(
        f'<line x1="{left}" y1="{base_y:.1f}" x2="{right}" y2="{base_y:.1f}" '
        f'stroke="currentColor" stroke-dasharray="5 4" stroke-width="1.25"/>'
    )
    centers = (150, 330, 510)
    bar_w = 26
    for (label, rf, bl), cx in zip(groups, centers):
        for value, klass, dx in ((rf, "rf", -16), (bl, "bl", 16)):
            yy = y(value)
            hh = bottom - yy
            parts.append(
                f'<rect class="{klass}" x="{cx + dx - bar_w / 2:.1f}" y="{yy:.1f}" '
                f'width="{bar_w}" height="{hh:.1f}"/>'
            )
        parts.append(
            f'<text x="{cx}" y="{bottom + 22}" text-anchor="middle" font-size="13">{label}</text>'
        )
    parts.append(f'<text x="18" y="150" font-size="12" transform="rotate(-90 18 150)">Precision at 50</text>')
    parts.append(f'<rect class="rf" x="52" y="318" width="14" height="14"/>')
    parts.append('<text x="72" y="330" font-size="13">Random forest</text>')
    parts.append(f'<rect class="bl" x="190" y="318" width="14" height="14"/>')
    parts.append('<text x="210" y="330" font-size="13">CTR-headroom baseline</text>')
    parts.append(
        f'<line x1="400" y1="325" x2="428" y2="325" stroke="currentColor" stroke-dasharray="5 4"/>'
    )
    parts.append('<text x="436" y="330" font-size="13">Base rate 0.21</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def figure_archetypes() -> str:
    w07 = load("w07_playbook_metrics.json")
    actions = {
        "NEW_OR_UNCLEAR": "Manual triage",
        "LOW_SIGNAL": "No action",
        "CONTENT_AGING": "Refresh next cycle",
        "SNIPPET_OPTIMIZATION": "Snippet fix",
        "UNDEREXPOSED_DECLINE": "Deprioritise",
        "HIGH_LEVERAGE_REFRESH": "Refresh content",
        "STABLE_HIGH_PERFORMER": "Protect",
    }
    pairs = sorted(w07["archetype_counts"].items(), key=lambda kv: kv[1])
    width, height = 640, 420
    left, right = 250, 600
    top = 24
    row_h = 48
    max_value = max(count for _, count in pairs)
    parts = [
        svg_open(width, height, "Page counts by archetype, each of which maps to one editorial action"),
    ]
    for i, (name, count) in enumerate(pairs):
        y = top + i * row_h
        bar_w = (count / max_value) * (right - left)
        parts.append(f'<text x="{left - 12}" y="{y + 18}" text-anchor="end" font-size="12">{name}</text>')
        parts.append(
            f'<text x="{left - 12}" y="{y + 34}" text-anchor="end" font-size="11">{actions[name]}</text>'
        )
        parts.append(f'<rect class="rf" x="{left}" y="{y + 8}" width="{bar_w:.1f}" height="22"/>')
        parts.append(
            f'<text x="{left + bar_w + 8:.1f}" y="{y + 24}" font-size="12">{count:,}</text>'
        )
    parts.append('<text x="250" y="400" font-size="12">Pages in the March 2026 slice</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def figure_strip() -> str:
    paired = load("loo_paired_comparison.json")
    scores = sorted(float(row["p50_rf"]) for row in paired["clients"])
    width, height = 640, 300
    left, right, top, bottom = 52, 616, 24, 230
    ymax = 1.0
    plot_h = bottom - top

    def y(value: float) -> float:
        return bottom - (value / ymax) * plot_h

    parts = [
        svg_open(width, height, "Precision at 50 for each of 28 client folds on the refit"),
        f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{bottom}"/>',
        f'<line class="axis" x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}"/>',
    ]
    for tick in (0, 0.25, 0.5, 0.75, 1):
        yy = y(tick)
        parts.append(f'<line class="grid" x1="{left}" y1="{yy:.1f}" x2="{right}" y2="{yy:.1f}" stroke-dasharray="2 4"/>')
        parts.append(f'<text x="{left - 8}" y="{yy + 4:.1f}" text-anchor="end" font-size="12">{tick:.2f}</text>')
    receipt = paired["w06_p50_loo_rf_mean"]
    parts.append(
        f'<line x1="{left}" y1="{y(receipt):.1f}" x2="{right}" y2="{y(receipt):.1f}" '
        f'stroke="currentColor" stroke-dasharray="5 4"/>'
    )
    span = right - left
    for i, score in enumerate(scores):
        cx = left + (i + 0.5) * span / len(scores)
        klass = "zero" if score == 0 else "rf"
        parts.append(f'<circle class="{klass}" cx="{cx:.1f}" cy="{y(score):.1f}" r="5"/>')
    parts.append(f'<text x="16" y="130" font-size="12" transform="rotate(-90 16 130)">Precision at 50</text>')
    parts.append('<text x="334" y="258" text-anchor="middle" font-size="13">Client folds, low score to high</text>')
    parts.append('<text x="52" y="286" font-size="12">Dashed line: saved audit mean 0.26. Grey dots: folds at 0.</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def write(name: str, body: str) -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    for folder in (DOCS, FIGS):
        (folder / name).write_text(body, encoding="utf-8")


def og_card() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    font = ROOT / "docs" / "assets" / "fonts" / "source-serif-4-latin-400-normal.ttf"
    font_manager.fontManager.addfont(str(font))
    fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor="#faf9f6")
    ax = fig.add_axes((0.07, 0.14, 0.86, 0.48))
    labels = ["Leave-one-client-out", "Single holdout", "February to March"]
    audit = load("w06_audit_metrics.json")
    base = load("w07_playbook_metrics.json")["slice_base_decline_rate"]
    rf = [audit["p50_loo_rf_mean"], audit["p50_w05_holdout_rf"], audit["p50_time_aware_rf"]]
    bl = [audit["loo_baseline_mean"], audit["p50_w05_holdout_baseline"], audit["time_aware_baseline_p50"]]
    import numpy as np

    x = np.arange(len(labels))
    ax.bar(x - 0.18, rf, 0.36, color="#3b4cca", label="Random forest")
    ax.bar(x + 0.18, bl, 0.36, color="#b7b4ac", label="Baseline")
    ax.axhline(base, color="#1a1a1a", linestyle="--", linewidth=1)
    ax.set_ylim(0, 0.55)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontname="Source Serif 4", fontsize=12, color="#1a1a1a")
    ax.tick_params(colors="#1a1a1a")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#1a1a1a")
    ax.spines["bottom"].set_color("#1a1a1a")
    ax.set_ylabel("Precision at 50", fontname="Source Serif 4", color="#1a1a1a")
    ax.legend(frameon=False, prop={"family": "Source Serif 4", "size": 11})
    fig.text(0.07, 0.90, "Ranking Pages for Content Refresh", fontsize=26, fontname="Source Serif 4", color="#1a1a1a")
    fig.text(0.07, 0.82, "Leakage audit and grouped validation", fontsize=16, fontname="Source Serif 4", color="#5c5a55")
    fig.text(0.07, 0.04, "Junaid Ahamed  ·  2026", fontsize=12, fontname="Source Serif 4", color="#5c5a55")
    out = DOCS / "og-card.png"
    fig.savefig(out, dpi=100)
    plt.close(fig)
    print(f"wrote {out}")


def main() -> None:
    write("model_vs_baseline.svg", figure1())
    write("archetype_mix.svg", figure_archetypes())
    write("loo_client_strip.svg", figure_strip())
    og_card()
    print("wrote figures")


if __name__ == "__main__":
    main()
