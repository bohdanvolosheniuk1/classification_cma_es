"""Генерація схематичних діаграм для PDF-гайду."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 10


def _box(ax, x, y, w, h, text, color="#2a9d8f", textcolor="white"):
    box = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02",
        linewidth=1.2, edgecolor=color, facecolor=color, alpha=0.85,
    )
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center", color=textcolor,
            fontsize=10, weight="bold")


def _arrow(ax, x1, y1, x2, y2, color="#444"):
    arr = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=15,
        linewidth=1.2, color=color,
    )
    ax.add_patch(arr)


# ============================================================================

def fig_architecture(out: Path) -> None:
    """Загальна архітектура — як модулі говорять одне з одним."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    _box(ax, 0.5, 6.5, 2.5, 0.8, "data.py\n(3 датасети)", "#e76f51")
    _box(ax, 3.5, 6.5, 2.5, 0.8, "preprocessing.py\n(scale / one-hot)", "#e76f51")
    _box(ax, 6.5, 6.5, 2.8, 0.8, "crossval.py\n(train/test + k-fold)", "#e76f51")

    _box(ax, 0.5, 4.5, 2.0, 0.8, "models.py\n(LogReg, SVM,\nkNN, MLP)", "#2a9d8f", )
    _box(ax, 2.8, 4.5, 1.8, 0.8, "gam.py\n(розд. 1)", "#2a9d8f")
    _box(ax, 4.9, 4.5, 2.0, 0.8, "cma_es.py\n(класичний)", "#2a9d8f")
    _box(ax, 7.2, 4.5, 2.3, 0.8, "mixture_cma_es.py\n(розд. 2 + Літвінчук)", "#2a9d8f")

    _box(ax, 1.5, 2.7, 2.5, 0.8, "cma_nn.py\n(5-й метод)", "#264653")
    _box(ax, 4.5, 2.7, 2.8, 0.8, "hyperparam_tuning.py\n(tuned_*)", "#264653")

    _box(ax, 2.0, 1.0, 2.5, 0.8, "pipeline.py\n(оркестратор)", "#f4a261")
    _box(ax, 5.0, 1.0, 2.0, 0.8, "metrics.py", "#f4a261")
    _box(ax, 7.5, 1.0, 2.0, 0.8, "tracking.py\n(MLflow)", "#f4a261")

    _box(ax, 0.5, -0.5, 4.5, 0.8, "scripts/run_experiment.py (CLI)", "#6a4c93")
    _box(ax, 5.5, -0.5, 4.0, 0.8, "app.py (Streamlit GUI)", "#6a4c93")

    for x in (3.2, 4.0, 5.9, 6.6, 8.2):
        _arrow(ax, x, 4.5, x, 3.7)
    _arrow(ax, 3.2, 2.7, 3.2, 1.85)
    _arrow(ax, 5.9, 2.7, 5.9, 1.85)
    _arrow(ax, 3.2, 1.0, 3.2, 0.35)
    _arrow(ax, 6.0, 1.0, 6.0, 0.35)

    ax.text(5, 7.7, "Архітектура проекту", ha="center", fontsize=14, weight="bold")
    ax.set_ylim(-1.0, 8.2)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================================

def fig_cmaes_cycle(out: Path) -> None:
    """Цикл CMA-ES — Sample → Eval → Select → Update."""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis("off")

    steps = [
        (5.0, 6.5, "1. Семплування\nN точок ~ N(m, σ²C)"),
        (8.0, 4.0, "2. Оцінка\nf(x) для кожної"),
        (5.0, 1.5, "3. Відбір\nкращої половини μ"),
        (2.0, 4.0, "4. Оновлення\nm, σ, C"),
    ]
    for x, y, text in steps:
        _box(ax, x - 1.3, y - 0.6, 2.6, 1.2, text, "#2a9d8f")

    centers = [(5.0, 6.5), (8.0, 4.0), (5.0, 1.5), (2.0, 4.0)]
    for i in range(4):
        x1, y1 = centers[i]
        x2, y2 = centers[(i + 1) % 4]
        _arrow(ax, x1 + 1.0 * np.sign(x2 - x1) * 0.6 if x1 != x2 else x1,
               y1 + 1.0 * np.sign(y2 - y1) * 0.5 if y1 != y2 else y1,
               x2 - 1.0 * np.sign(x2 - x1) * 0.6 if x1 != x2 else x2,
               y2 - 1.0 * np.sign(y2 - y1) * 0.5 if y1 != y2 else y2,
               color="#264653")

    ax.text(5, 4.0, "повторювати\nдоки збігається", ha="center", va="center",
            fontsize=10, style="italic", color="#666")
    ax.text(5, 7.6, "Один цикл CMA-ES", ha="center", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================================

def fig_kfold(out: Path) -> None:
    """K-fold cross-validation візуалізація."""
    fig, ax = plt.subplots(figsize=(8, 4))
    n_folds = 5
    n_total = 25
    fold_size = n_total // n_folds

    for fold in range(n_folds):
        for i in range(n_total):
            is_val = (i // fold_size) == fold
            color = "#e76f51" if is_val else "#2a9d8f"
            ax.barh(
                fold, 1, left=i, color=color,
                edgecolor="white", linewidth=0.5, height=0.7,
            )
        ax.text(-1.5, fold, f"Fold {fold + 1}", ha="right", va="center",
                fontsize=11, weight="bold")

    ax.set_xlim(-3.5, n_total + 1)
    ax.set_ylim(-0.6, n_folds - 0.4)
    ax.invert_yaxis()
    ax.axis("off")

    ax.scatter([], [], s=80, c="#2a9d8f", label="train")
    ax.scatter([], [], s=80, c="#e76f51", label="validation")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.15), ncol=2,
              frameon=False, fontsize=11)

    ax.text(n_total / 2, -1.5, "Stratified K-Fold (k=5)",
            ha="center", fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================================

def fig_gam_decomposition(out: Path) -> None:
    """GAM як сума функцій від ознак."""
    fig, axes = plt.subplots(1, 4, figsize=(10, 3))

    x = np.linspace(-3, 3, 100)
    funcs = [
        ("f₁(x₁) ≈ sin", np.sin(x)),
        ("f₂(x₂) ≈ x²", 0.3 * x ** 2 - 1.5),
        ("f₃(x₃) ≈ logistic",
         1 / (1 + np.exp(-x)) - 0.5),
    ]
    for ax, (name, y) in zip(axes[:3], funcs):
        ax.plot(x, y, color="#2a9d8f", linewidth=2.5)
        ax.set_title(name, fontsize=11)
        ax.axhline(0, color="#aaa", linewidth=0.5)
        ax.axvline(0, color="#aaa", linewidth=0.5)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    ax = axes[3]
    ax.axis("off")
    ax.text(0.05, 0.5,
            "g(E[y]) =\nβ₀\n+ f₁(x₁)\n+ f₂(x₂)\n+ f₃(x₃)\n+ ...",
            fontsize=14, family="monospace",
            verticalalignment="center")
    ax.text(0.5, 0.95, "GAM = сума", ha="center", fontsize=12, weight="bold",
            transform=ax.transAxes)

    fig.suptitle(
        "GAM: кожна ознака має свою гладку функцію, потім всі додаються",
        fontsize=12, weight="bold", y=1.02,
    )
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================================

def fig_mixture_sampling(out: Path) -> None:
    """Розширений CMA-ES — суміш з 3-х нормальних розподілів."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    rng = np.random.default_rng(1)

    # left: 3 components in 2D
    ax = axes[0]
    means = [(2, 2), (-1.5, 3), (0, -2)]
    covs = [
        [[0.6, 0.2], [0.2, 0.4]],
        [[0.4, -0.1], [-0.1, 0.5]],
        [[0.5, 0.0], [0.0, 0.6]],
    ]
    colors = ["#e76f51", "#2a9d8f", "#264653"]
    for m, c, col in zip(means, covs, colors):
        pts = rng.multivariate_normal(m, c, size=40)
        ax.scatter(pts[:, 0], pts[:, 1], c=col, s=20, alpha=0.7,
                   edgecolors="white", linewidths=0.3)
        ax.scatter(m[0], m[1], c=col, s=200, marker="X",
                   edgecolors="black", linewidths=1.0)

    ax.set_xlim(-4, 4)
    ax.set_ylim(-4, 5)
    ax.set_title("Суміш 3-х нормальних\n(k=3)", fontsize=11, weight="bold")
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)

    # right: EM cycle
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    _box(ax, 1.0, 4.5, 3.5, 1.0,
         "E-крок\nкому належить точка?",
         "#2a9d8f")
    _box(ax, 5.5, 4.5, 3.5, 1.0,
         "M-крок\nоновити m, C, w",
         "#264653")
    _box(ax, 1.0, 1.5, 3.5, 1.0,
         "Семпл нових точок\nз оновленої суміші",
         "#e76f51")
    _box(ax, 5.5, 1.5, 3.5, 1.0,
         "Адаптація k\n(додати / видалити пік)",
         "#f4a261")

    _arrow(ax, 4.5, 5.0, 5.5, 5.0)
    _arrow(ax, 7.3, 4.5, 7.3, 2.5)
    _arrow(ax, 5.5, 2.0, 4.5, 2.0)
    _arrow(ax, 2.7, 2.5, 2.7, 4.5)

    ax.set_title("EM-цикл (всередині однієї ітерації CMA-ES)",
                 fontsize=11, weight="bold")

    fig.suptitle("Розширений CMA-ES зі сумішами (за Літвінчук Ю.А.)",
                 fontsize=13, weight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================================

def fig_cma_nn(out: Path) -> None:
    """CMA-NN: ваги мережі — це один вектор для CMA-ES."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    # left: small NN
    ax = axes[0]
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 5)
    ax.axis("off")
    # input layer
    for i, y in enumerate([1, 2, 3, 4]):
        ax.add_patch(plt.Circle((1, y), 0.25, color="#2a9d8f"))
    # hidden
    for i, y in enumerate([1.5, 2.5, 3.5]):
        ax.add_patch(plt.Circle((3, y), 0.25, color="#e76f51"))
    # output
    for y in (2, 3):
        ax.add_patch(plt.Circle((5, y), 0.25, color="#264653"))
    # edges
    for y1 in [1, 2, 3, 4]:
        for y2 in [1.5, 2.5, 3.5]:
            ax.plot([1.25, 2.75], [y1, y2], color="#bbb", linewidth=0.5)
    for y1 in [1.5, 2.5, 3.5]:
        for y2 in (2, 3):
            ax.plot([3.25, 4.75], [y1, y2], color="#bbb", linewidth=0.5)
    ax.text(1, 4.7, "вхід", ha="center", fontsize=10)
    ax.text(3, 4.2, "прихований", ha="center", fontsize=10)
    ax.text(5, 3.6, "вихід", ha="center", fontsize=10)
    ax.set_title("Невелика NN", fontsize=11, weight="bold")

    # right: flat weight vector
    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    n_w = 18
    for i in range(n_w):
        x = 0.5 + i * 0.5
        color = "#2a9d8f" if i % 2 == 0 else "#e76f51"
        ax.add_patch(plt.Rectangle((x, 2.5), 0.4, 0.6,
                                    facecolor=color, edgecolor="white"))
    ax.text(5, 1.8, "плоский вектор ваг w ∈ ℝⁿ", ha="center", fontsize=11)
    ax.text(5, 0.8, "CMA-ES шукає w, який мінімізує\ncross-entropy на train",
            ha="center", fontsize=11, style="italic", color="#444")
    ax.set_title("Те саме як вектор для оптимізатора",
                 fontsize=11, weight="bold")

    fig.suptitle("CMA-NN: нейромережа очима CMA-ES",
                 fontsize=13, weight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================================

def fig_pipeline_flow(out: Path) -> None:
    """Pipeline: від датасета до метрик."""
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 4)
    ax.axis("off")

    steps = [
        (0.5, "Датасет\n(.csv)", "#e76f51"),
        (3.0, "Препроцесинг\n(scale, OHE)", "#f4a261"),
        (5.5, "Train / Test\nsplit 80/20", "#e9c46a"),
        (8.0, "K-fold CV\nна train", "#2a9d8f"),
        (10.5, "Навчання\nкожної моделі", "#264653"),
        (13.0, "Метрики:\nacc, F1, AUC", "#6a4c93"),
    ]
    for x, text, color in steps:
        _box(ax, x, 1.5, 2.3, 1.0, text, color)
    for i in range(len(steps) - 1):
        _arrow(ax, steps[i][0] + 2.4, 2.0, steps[i + 1][0] - 0.05, 2.0)

    ax.text(15.5, 2.0, "→ MLflow", ha="left", va="center",
            fontsize=11, style="italic")
    ax.text(8, 3.3, "Pipeline: один прогон експерименту",
            ha="center", fontsize=13, weight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================================================================

def generate_all(out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "architecture":   out_dir / "01_architecture.png",
        "pipeline":       out_dir / "02_pipeline.png",
        "kfold":          out_dir / "03_kfold.png",
        "gam":            out_dir / "04_gam.png",
        "cmaes_cycle":    out_dir / "05_cmaes_cycle.png",
        "mixture":        out_dir / "06_mixture.png",
        "cma_nn":         out_dir / "07_cma_nn.png",
    }
    fig_architecture(files["architecture"])
    fig_pipeline_flow(files["pipeline"])
    fig_kfold(files["kfold"])
    fig_gam_decomposition(files["gam"])
    fig_cmaes_cycle(files["cmaes_cycle"])
    fig_mixture_sampling(files["mixture"])
    fig_cma_nn(files["cma_nn"])
    return files


if __name__ == "__main__":
    files = generate_all(Path("docs/figures"))
    for name, p in files.items():
        print(f"  {name}: {p}")
