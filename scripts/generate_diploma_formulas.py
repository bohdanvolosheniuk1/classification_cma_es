"""Рендерить математичні формули як PNG для вставки в диплом.

Кожна формула — окремий файл у ``../../diploma_figures/``. Використовує
matplotlib з вбудованим mathtext (LaTeX-нотація).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = REPO_ROOT.parent / "diploma_figures"


def _render(formula: str, out: Path, *, height_inch: float = 1.2,
            fontsize: int = 22) -> None:
    fig, ax = plt.subplots(figsize=(10, height_inch))
    ax.text(0.5, 0.5, formula, fontsize=fontsize,
            ha="center", va="center")
    ax.axis("off")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    formulas = [
        # GAM з логіт-функцією зв'язку
        ("formula_gam.png",
         r"$g(\mathbb{E}[y \mid X]) = \beta_0 + \sum_{i=1}^{p} f_i(x_i),"
         r"\quad f_i(x_i) = \sum_{j=1}^{k} \beta_{ij} \, b_j(x_i)$",
         1.3),

        # CMA-ES семплування
        ("formula_cmaes_sample.png",
         r"$x_i \sim m + \sigma \cdot \mathcal{N}(0, C),"
         r"\quad i = 1, \ldots, \lambda$",
         1.0),

        # Розширений CMA-ES — суміш нормальних
        ("formula_mixture_pdf.png",
         r"$p(x; \theta) = \sum_{s=1}^{k} w_s \cdot \mathcal{N}(x; m_s, C_s),"
         r"\quad \sum_{s=1}^{k} w_s = 1$",
         1.0),

        # EM E-крок
        ("formula_em_estep.png",
         r"$\gamma_{ij} = \frac{w_j \, \mathcal{N}(x_i; m_j, C_j)}"
         r"{\sum_{s=1}^{k} w_s \, \mathcal{N}(x_i; m_s, C_s)}$",
         1.4),

        # EM M-крок
        ("formula_em_mstep.png",
         r"$w_j = \frac{N_j}{N}, \quad"
         r"m_j = \frac{\sum_i \gamma_{ij} \, x_i}{N_j}, \quad"
         r"C_j = \frac{\sum_i \gamma_{ij} (x_i - m_j)(x_i - m_j)^\top}{N_j}$",
         1.3),

        # Cross-entropy loss для CMA-NN
        ("formula_crossentropy.png",
         r"$\mathcal{L}(w) = -\frac{1}{N} \sum_{i=1}^{N} "
         r"\log p_w(y_i \mid x_i)$",
         1.0),

        # F1-score
        ("formula_f1.png",
         r"$\mathrm{F1} = 2 \cdot \frac{\mathrm{precision} \cdot "
         r"\mathrm{recall}}{\mathrm{precision} + \mathrm{recall}}$",
         1.0),

        # ROC-AUC через інтеграл
        ("formula_auc.png",
         r"$\mathrm{AUC} = \int_0^1 \mathrm{TPR}(t) \, d\,\mathrm{FPR}(t)$",
         0.9),

        # Cov-momentum update (наша поправка)
        ("formula_cov_lr.png",
         r"$C^{(t+1)} = (1 - \mathrm{cov\_lr}) \cdot C^{(t)} + "
         r"\mathrm{cov\_lr} \cdot C^{(t)}_{\mathrm{EM}}$",
         1.0),
    ]

    for filename, text, h in formulas:
        out = FIGURES_DIR / filename
        _render(text, out, height_inch=h)
        kb = out.stat().st_size // 1024
        print(f"  {filename} [{kb} KB]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
