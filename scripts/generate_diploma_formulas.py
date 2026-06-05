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

        # ----- Формули розділу 1 -----

        # (1.1) Адитивна модель
        ("formula_1_1_additive.png",
         r"$y = \beta_0 + \sum_{i=1}^{n} f_i(x_i) + \varepsilon$",
         1.0),

        # (1.2) Лінійна регресія
        ("formula_1_2_linear.png",
         r"$y = \beta_0 + \beta_1 x_1 + \beta_2 x_2 + \ldots + "
         r"\beta_n x_n + \varepsilon$",
         1.0),

        # (1.3) GAM із функцією зв'язку
        ("formula_1_3_gam_link.png",
         r"$g(\mathbb{E}[y]) = \beta_0 + \sum_{i=1}^{n} f_i(x_i)$",
         1.0),

        # (1.4) Базисне представлення
        ("formula_1_4_basis.png",
         r"$f(x) = \sum_{j=1}^{k} \beta_j \, B_j(x)$",
         1.0),

        # (1.5) Поліноміальне базисне представлення
        ("formula_1_5_poly.png",
         r"$f(x) = \beta_0 + \beta_1 x + \beta_2 x^2 + \ldots + "
         r"\beta_n x^n$",
         1.0),

        # (1.6) Функція оптимізації GAM
        ("formula_1_6_loss.png",
         r"$\mathcal{L} = \mathrm{RSS} + \lambda \int "
         r"\left(f''(x)\right)^2 \, dx$",
         1.0),

        # (1.7) Тотожна функція зв'язку
        ("formula_1_7_identity.png",
         r"$g(y) = y$",
         0.9),

        # (1.8) Логарифмічна функція зв'язку
        ("formula_1_8_log.png",
         r"$g(y) = \log y$",
         0.9),

        # (1.9) Логіт-функція
        ("formula_1_9_logit.png",
         r"$g(y) = \log \frac{y}{1 - y}$",
         1.2),

        # ----- Формули розділу 2 -----

        # (2.1) CMA-ES sample (розподіл)
        ("formula_2_1_sample.png",
         r"$x_k^{(g+1)} \sim m^{(g)} + \sigma^{(g)} \, "
         r"\mathcal{N}(0, C^{(g)})$",
         1.0),

        # (2.2) CMA-ES sample (через випадковий вектор)
        ("formula_2_2_sample2.png",
         r"$x_k^{(g+1)} = m^{(g)} + \sigma^{(g)} \, z_k^{(g+1)}$",
         1.0),

        # (2.3) Оновлення середнього
        ("formula_2_3_mean.png",
         r"$m^{(g+1)} = \sum_{i=1}^{\mu} w_i \, x_{i:\lambda}^{(g+1)}$",
         1.0),

        # (2.4) Оновлення коваріаційної матриці
        ("formula_2_4_cov.png",
         r"$C^{(g+1)} = (1 - c_1 - c_\mu) C^{(g)} + "
         r"c_1 \, p_c p_c^{\mathrm{T}} + "
         r"c_\mu \sum_{i=1}^{\mu} w_i \, y_i y_i^{\mathrm{T}}$",
         1.0),

        # (2.5) Оновлення масштабу пошуку
        ("formula_2_5_sigma.png",
         r"$\sigma^{(g+1)} = \sigma^{(g)} \, "
         r"\exp\!\left(\frac{c_\sigma}{d_\sigma} \left("
         r"\frac{\|p_\sigma\|}{\mathbb{E}\|\mathcal{N}(0,I)\|} - 1"
         r"\right)\right)$",
         1.2),
    ]

    for filename, text, h in formulas:
        out = FIGURES_DIR / filename
        _render(text, out, height_inch=h)
        kb = out.stat().st_size // 1024
        print(f"  {filename} [{kb} KB]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
