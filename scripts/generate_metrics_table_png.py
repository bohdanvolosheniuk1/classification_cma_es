"""Рендерить чисту PNG-таблицю метрик для слайду презентації.

Дані – результати на датасеті PhiUSIIL (відповідають таблиці у дипломі).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT.parent / "diploma_figures"


HEADERS = ["Модель", "Accuracy", "F1", "AUC", "Час, с"]


# Дані всіх трьох таблиць – точно з диплома (розділ 4)
DATASETS = {
    "phiusiil": [
        ("logreg",       "0.9983", "0.9985", "1.0000", "0.01"),
        ("svm",          "0.9983", "0.9985", "1.0000", "0.16"),
        ("knn",          "0.9933", "0.9942", "0.9999", "0.00"),
        ("mlp",          "0.9933", "0.9942", "0.9999", "0.26"),
        ("gam",          "1.0000", "1.0000", "1.0000", "0.05"),
        ("cma_classic",  "0.9900", "0.9913", "0.9996", "0.23"),
        ("cma_mixture",  "0.9917", "0.9927", "0.9993", "21.59"),
        ("tuned_logreg", "0.9983", "0.9985", "1.0000", "0.01"),
        ("tuned_svm",    "0.9950", "0.9956", "1.0000", "0.44"),
        ("tuned_knn",    "0.9917", "0.9927", "0.9998", "0.00"),
        ("tuned_mlp",    "0.9933", "0.9942", "0.9999", "0.11"),
        ("tuned_gam",    "1.0000", "1.0000", "1.0000", "0.05"),
    ],
    "steel_plate": [
        ("logreg",       "0.7275", "0.7272", "0.9064", "0.08"),
        ("svm",          "0.7506", "0.7514", "0.9209", "0.39"),
        ("knn",          "0.7301", "0.7272", "0.8956", "0.00"),
        ("mlp",          "0.7198", "0.7225", "0.9091", "0.26"),
        ("gam",          "0.7455", "0.7466", "0.9131", "0.25"),
        ("cma_classic",  "0.5116", "0.4677", "0.7749", "0.20"),
        ("cma_mixture",  "0.4216", "0.3508", "0.7363", "11.74"),
        ("tuned_logreg", "0.7352", "0.7357", "0.9079", "0.17"),
        ("tuned_svm",    "0.7584", "0.7597", "0.9281", "0.40"),
        ("tuned_knn",    "0.7455", "0.7414", "0.8851", "0.00"),
        ("tuned_mlp",    "0.7404", "0.7419", "0.9251", "0.27"),
        ("tuned_gam",    "0.7558", "0.7576", "0.9191", "0.95"),
    ],
    "credit_default": [
        ("logreg",       "0.8100", "0.3596", "0.7013", "0.01"),
        ("svm",          "0.8083", "0.4221", "0.7008", "0.79"),
        ("knn",          "0.7783", "0.3512", "0.6731", "0.00"),
        ("mlp",          "0.7883", "0.2905", "0.6442", "0.13"),
        ("gam",          "0.8167", "0.4271", "0.7311", "0.04"),
        ("cma_classic",  "0.7867", "0.2000", "0.6920", "0.21"),
        ("cma_mixture",  "0.8067", "0.3333", "0.6447", "6.53"),
        ("tuned_logreg", "0.8067", "0.3556", "0.7002", "0.01"),
        ("tuned_svm",    "0.8100", "0.4356", "0.6967", "0.77"),
        ("tuned_knn",    "0.7883", "0.3280", "0.6861", "0.00"),
        ("tuned_mlp",    "0.8017", "0.4360", "0.7213", "0.18"),
        ("tuned_gam",    "0.8117", "0.4322", "0.7111", "0.11"),
    ],
}


def render_table(rows, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.axis("off")

    table = ax.table(
        cellText=[HEADERS] + [list(r) for r in rows],
        cellLoc="left",
        loc="center",
        colWidths=[0.22, 0.18, 0.18, 0.18, 0.14],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(13)
    table.scale(1.0, 1.55)

    # Шапка – білий фон, жирний чорний текст
    for col in range(len(HEADERS)):
        cell = table[(0, col)]
        cell.set_facecolor("#FFFFFF")
        cell.get_text().set_color("#000000")
        cell.get_text().set_weight("bold")
        cell.set_edgecolor("#000000")
        cell.set_linewidth(1.2)

    # Чергуємо світло-сірі смуги
    for row_idx in range(1, len(rows) + 1):
        for col in range(len(HEADERS)):
            cell = table[(row_idx, col)]
            cell.set_edgecolor("#000000")
            cell.set_linewidth(0.6)
            cell.set_facecolor("#E8E8E8" if row_idx % 2 == 1 else "#FFFFFF")

    plt.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for key, rows in DATASETS.items():
        out_path = OUT_DIR / f"metrics_table_{key}.png"
        render_table(rows, out_path)
        print(f"OK: {out_path.name} ({out_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
