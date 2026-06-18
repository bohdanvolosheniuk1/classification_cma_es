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
OUT = REPO_ROOT.parent / "diploma_figures" / "metrics_table_phiusiil.png"


HEADERS = ["Модель", "Accuracy", "F1", "AUC", "Час, с"]
ROWS = [
    ("logreg",      "0.9983", "0.9985", "1.0000", "0.01"),
    ("svm",         "0.9983", "0.9985", "1.0000", "0.16"),
    ("knn",         "0.9933", "0.9942", "0.9999", "0.00"),
    ("mlp",         "0.9933", "0.9942", "0.9999", "0.26"),
    ("gam",         "1.0000", "1.0000", "1.0000", "0.05"),
    ("cma_classic", "0.9900", "0.9913", "0.9996", "0.23"),
    ("cma_mixture", "0.9917", "0.9927", "0.9993", "21.59"),
    ("tuned_logreg","0.9983", "0.9985", "1.0000", "0.01"),
    ("tuned_svm",   "0.9950", "0.9956", "1.0000", "0.44"),
    ("tuned_knn",   "0.9917", "0.9927", "0.9998", "0.00"),
    ("tuned_mlp",   "0.9933", "0.9942", "0.9999", "0.11"),
    ("tuned_gam",   "1.0000", "1.0000", "1.0000", "0.05"),
]


def main() -> int:
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.axis("off")

    table = ax.table(
        cellText=[HEADERS] + [list(r) for r in ROWS],
        cellLoc="left",
        loc="center",
        colWidths=[0.22, 0.18, 0.18, 0.18, 0.14],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(13)
    table.scale(1.0, 1.55)

    # Стиль шапки – темний фон, біла жирна шрифт
    for col in range(len(HEADERS)):
        cell = table[(0, col)]
        cell.set_facecolor("#FFFFFF")
        cell.get_text().set_color("#000000")
        cell.get_text().set_weight("bold")
        cell.set_edgecolor("#000000")
        cell.set_linewidth(1.2)

    # Чергуємо світло-сірі смуги для непарних рядків (для читабельності)
    for row_idx in range(1, len(ROWS) + 1):
        for col in range(len(HEADERS)):
            cell = table[(row_idx, col)]
            cell.set_edgecolor("#000000")
            cell.set_linewidth(0.6)
            if row_idx % 2 == 1:
                cell.set_facecolor("#E8E8E8")
            else:
                cell.set_facecolor("#FFFFFF")

    # Заголовок над таблицею
    plt.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"OK: {OUT} ({OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
