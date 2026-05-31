"""Створює зведений графік порівняння моделей на трьох датасетах."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = REPO_ROOT.parent / "diploma_figures"


# F1-score з реальних прогонів (взято з таблиць у розділах 4.2-4.4)
DATA = {
    "logreg":       {"PhiUSIIL": 0.9985, "Steel Plate": 0.7272, "Loan Approval": 0.3596},
    "svm":          {"PhiUSIIL": 0.9985, "Steel Plate": 0.7514, "Loan Approval": 0.4221},
    "knn":          {"PhiUSIIL": 0.9942, "Steel Plate": 0.7272, "Loan Approval": 0.3512},
    "mlp":          {"PhiUSIIL": 0.9942, "Steel Plate": 0.7225, "Loan Approval": 0.2905},
    "gam":          {"PhiUSIIL": 1.0000, "Steel Plate": 0.7466, "Loan Approval": 0.4271},
    "cma_classic":  {"PhiUSIIL": 0.9913, "Steel Plate": 0.4677, "Loan Approval": 0.2000},
    "cma_mixture":  {"PhiUSIIL": 0.9927, "Steel Plate": 0.3508, "Loan Approval": 0.3333},
    "tuned_logreg": {"PhiUSIIL": 0.9985, "Steel Plate": 0.7357, "Loan Approval": 0.3556},
    "tuned_svm":    {"PhiUSIIL": 0.9956, "Steel Plate": 0.7597, "Loan Approval": 0.4356},
    "tuned_knn":    {"PhiUSIIL": 0.9927, "Steel Plate": 0.7414, "Loan Approval": 0.3280},
    "tuned_mlp":    {"PhiUSIIL": 0.9942, "Steel Plate": 0.7419, "Loan Approval": 0.4360},
    "tuned_gam":    {"PhiUSIIL": 1.0000, "Steel Plate": 0.7576, "Loan Approval": 0.4322},
}


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    models = list(DATA.keys())
    datasets = ["PhiUSIIL", "Steel Plate", "Loan Approval"]

    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(models))
    width = 0.27
    colors = ["#2a9d8f", "#e76f51", "#264653"]

    for i, ds in enumerate(datasets):
        values = [DATA[m][ds] for m in models]
        ax.bar(x + (i - 1) * width, values, width,
               label=ds, color=colors[i], alpha=0.88,
               edgecolor="white", linewidth=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=35, ha="right", fontsize=11)
    ax.set_ylabel("F1-score", fontsize=13)
    ax.set_title("Порівняння F1-score 12 моделей на трьох датасетах",
                 fontsize=14, weight="bold", pad=15)
    ax.legend(loc="upper right", fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", alpha=0.3)
    ax.axhline(y=1.0, color="gray", linewidth=0.5, linestyle=":")

    fig.tight_layout()
    out = FIGURES_DIR / "comparison_f1.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  {out.name} [{out.stat().st_size // 1024} KB]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
