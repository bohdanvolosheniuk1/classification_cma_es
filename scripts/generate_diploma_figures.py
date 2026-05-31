"""Генерує рисунки для розділу 4 диплома — на основі реальних прогонів.

Виконує тренування моделей на трьох датасетах, обчислює confusion
matrix, ROC-криві, криву збіжності CMA-ES та коваріаційну матрицю.
Зберігає у теку ``../../diploma_figures/`` (поруч із самим
диплом 1.docx).

Виклик::

    python scripts/generate_diploma_figures.py

Час виконання — приблизно 5-10 хвилин на типовому ноутбуці.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import auc, confusion_matrix, roc_curve

from classifiers.cma_nn import CMAESNeuralNet
from classifiers.hyperparam_tuning import space_svm, tune_with_cma
from classifiers.models import make_gam, make_logreg, make_mlp, make_svm
from classifiers.pipeline import prepare_data


REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = REPO_ROOT.parent / "diploma_figures"


plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 11


# ============================================================================
# helpers

def _save_confusion(ax, cm, labels, title):
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Прогноз", fontsize=11)
    ax.set_ylabel("Справжній клас", fontsize=11)
    ax.set_title(title, fontsize=12, weight="bold")
    threshold = cm.max() / 2
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > threshold else "black",
                    fontsize=10)
    return im


def _save_roc(curves, title, out: Path):
    fig, ax = plt.subplots(figsize=(8, 6))
    colors = ["#2a9d8f", "#e76f51", "#264653", "#f4a261", "#6a4c93", "#1976d2"]
    for (name, (fpr, tpr, auc_val)), c in zip(curves.items(), colors):
        ax.plot(fpr, tpr, color=c, linewidth=2,
                label=f"{name} (AUC={auc_val:.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, linewidth=1,
            label="випадково (AUC=0.5)")
    ax.set_xlabel("False Positive Rate", fontsize=12)
    ax.set_ylabel("True Positive Rate", fontsize=12)
    ax.set_title(title, fontsize=13, weight="bold")
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _save_convergence(histories, title, out: Path):
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {"cma_classic": "#264653", "cma_mixture": "#e76f51"}
    for name, hist in histories.items():
        ax.plot(hist, color=colors.get(name, "#2a9d8f"),
                linewidth=2.2, label=name, marker="o", markersize=4)
    ax.set_xlabel("Ітерація CMA-ES", fontsize=12)
    ax.set_ylabel("Cross-entropy на train", fontsize=12)
    ax.set_title(title, fontsize=13, weight="bold")
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)


def _save_covariance(C, title, out: Path):
    fig, ax = plt.subplots(figsize=(7, 6))
    vmax = np.abs(C).max()
    im = ax.imshow(C, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    plt.colorbar(im, ax=ax, label="значення коваріації")
    ax.set_xlabel("Параметр j", fontsize=12)
    ax.set_ylabel("Параметр i", fontsize=12)
    ax.set_title(title, fontsize=13, weight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)


# ============================================================================
# рисунки

def figures_phiusiil():
    print("PhiUSIIL — підготовка...")
    X_tr, X_te, y_tr, y_te, _ = prepare_data("phiusiil", sample=3000, seed=42)

    print("PhiUSIIL — gam + cma_mixture (confusion matrices)...")
    gam = make_gam().fit(X_tr, y_tr)
    cma_mix = CMAESNeuralNet(
        hidden_layer_sizes=(8,), method="mixture", n_components=3,
        adaptive=True, max_iter=15, max_features=20,
        max_train_samples=1500, random_state=42,
    ).fit(X_tr, y_tr)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, (name, model) in zip(axes, [("gam", gam), ("cma_mixture", cma_mix)]):
        cm = confusion_matrix(y_te, model.predict(X_te))
        _save_confusion(ax, cm, ["legit (0)", "phishing (1)"], name)
    fig.suptitle("Матриці плутанини на датасеті PhiUSIIL",
                 fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "phiusiil_confusion.png",
                dpi=120, bbox_inches="tight")
    plt.close(fig)

    print("PhiUSIIL — ROC...")
    curves = {}
    for name, model in [("logreg", make_logreg().fit(X_tr, y_tr)),
                        ("svm",    make_svm().fit(X_tr, y_tr)),
                        ("gam",    gam),
                        ("mlp",    make_mlp().fit(X_tr, y_tr))]:
        proba = model.predict_proba(X_te)[:, 1]
        fpr, tpr, _ = roc_curve(y_te, proba)
        curves[name] = (fpr, tpr, auc(fpr, tpr))
    _save_roc(curves, "ROC-криві на PhiUSIIL",
              FIGURES_DIR / "phiusiil_roc.png")


def figures_steel_plate():
    print("Steel Plate — підготовка...")
    X_tr, X_te, y_tr, y_te, info = prepare_data("steel_plate", seed=42)
    class_names = ["B", "Di", "K_S", "OF", "Pa", "St", "Z_S"]

    print("Steel Plate — tuned_svm (confusion matrix)...")
    best_params, _, _ = tune_with_cma(
        make_svm, space_svm(), X_tr, y_tr,
        cv=3, scoring="f1_weighted", method="classic",
        max_iter=8, pop_size=6, random_state=42,
    )
    tuned_svm = make_svm(**best_params).fit(X_tr, y_tr)
    cm = confusion_matrix(y_te, tuned_svm.predict(X_te))
    fig, ax = plt.subplots(figsize=(8, 7))
    _save_confusion(ax, cm, class_names,
                    "Steel Plate — tuned_svm")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "steel_plate_confusion.png",
                dpi=120, bbox_inches="tight")
    plt.close(fig)

    print("Steel Plate — convergence (cma_classic + cma_mixture)...")
    cma_c = CMAESNeuralNet(
        hidden_layer_sizes=(8,), method="classic",
        max_iter=25, max_features=15, max_train_samples=1500,
        random_state=42,
    ).fit(X_tr, y_tr)
    cma_m = CMAESNeuralNet(
        hidden_layer_sizes=(8,), method="mixture", n_components=3,
        adaptive=True, max_iter=25, max_features=15,
        max_train_samples=1500, random_state=42,
    ).fit(X_tr, y_tr)
    _save_convergence(
        {"cma_classic": cma_c.history_, "cma_mixture": cma_m.history_},
        "Збіжність CMA-ES на Steel Plate",
        FIGURES_DIR / "steel_plate_cma_convergence.png",
    )


def figures_loan_approval():
    print("Loan Approval — підготовка...")
    X_tr, X_te, y_tr, y_te, _ = prepare_data(
        "loan_approval", sample=3000, seed=42,
    )

    print("Loan Approval — tuned_mlp + cma_mixture (confusion)...")
    tuned_mlp = make_mlp(hidden_layer_sizes=(32,), max_iter=200,
                         random_state=42).fit(X_tr, y_tr)
    cma_mix = CMAESNeuralNet(
        hidden_layer_sizes=(8,), method="mixture", n_components=3,
        adaptive=True, max_iter=15, max_features=15,
        max_train_samples=1500, random_state=42,
    ).fit(X_tr, y_tr)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, (name, model) in zip(axes,
                                 [("tuned_mlp", tuned_mlp),
                                  ("cma_mixture", cma_mix)]):
        cm = confusion_matrix(y_te, model.predict(X_te))
        _save_confusion(ax, cm, ["no default (0)", "default (1)"], name)
    fig.suptitle("Матриці плутанини на датасеті Loan Approval",
                 fontsize=14, weight="bold")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "loan_approval_confusion.png",
                dpi=120, bbox_inches="tight")
    plt.close(fig)

    print("Loan Approval — ROC...")
    curves = {}
    for name, model in [("logreg", make_logreg().fit(X_tr, y_tr)),
                        ("svm",    make_svm().fit(X_tr, y_tr)),
                        ("gam",    make_gam().fit(X_tr, y_tr)),
                        ("tuned_mlp", tuned_mlp)]:
        proba = model.predict_proba(X_te)[:, 1]
        fpr, tpr, _ = roc_curve(y_te, proba)
        curves[name] = (fpr, tpr, auc(fpr, tpr))
    _save_roc(curves, "ROC-криві на Loan Approval",
              FIGURES_DIR / "loan_approval_roc.png")

    print("Loan Approval — covariance matrix (CMA-ES напряму)...")
    # Запускаємо cma безпосередньо щоб отримати фінальну C
    import cma
    from sklearn.decomposition import PCA
    # стискаємо ознаки в 8 компонент щоб вектор ваг був керованого розміру
    pca = PCA(n_components=8, random_state=42)
    X_tr_p = pca.fit_transform(X_tr[:1500])
    y_tr_s = y_tr[:1500]

    # маленька NN: 8 -> 4 -> 2  =>  8*4 + 4 + 4*2 + 2 = 46 ваг
    layer_sizes = (8, 4, 2)
    n_params = sum(a * b + b
                   for a, b in zip(layer_sizes[:-1], layer_sizes[1:]))

    def unpack(w):
        out, off = [], 0
        for a, b in zip(layer_sizes[:-1], layer_sizes[1:]):
            W = w[off:off + a * b].reshape(a, b)
            off += a * b
            bb = w[off:off + b]
            off += b
            out.append((W, bb))
        return out

    def forward(X, w):
        h = X
        params = unpack(w)
        for i, (W, bb) in enumerate(params):
            z = h @ W + bb
            if i < len(params) - 1:
                h = np.tanh(z)
            else:
                z = z - z.max(axis=1, keepdims=True)
                e = np.exp(z)
                h = e / e.sum(axis=1, keepdims=True)
        return h

    def loss(w):
        probs = forward(X_tr_p, w)
        n = probs.shape[0]
        p = probs[np.arange(n), y_tr_s]
        return -float(np.log(np.clip(p, 1e-12, 1.0)).mean())

    rng = np.random.default_rng(42)
    x0 = rng.standard_normal(n_params) * 0.1
    es = cma.CMAEvolutionStrategy(
        x0.tolist(), 0.3,
        {"maxiter": 20, "verbose": -9, "seed": 43},
    )
    while not es.stop():
        xs = es.ask()
        fs = [loss(np.asarray(x)) for x in xs]
        es.tell(xs, fs)

    C = np.array(es.C)
    _save_covariance(C,
                     f"Коваріаційна матриця CMA-ES (n_params={n_params})",
                     FIGURES_DIR / "loan_approval_cma_covariance.png")


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    figures_phiusiil()
    figures_steel_plate()
    figures_loan_approval()

    print("\nГотово! Рисунки збережено:")
    for f in sorted(FIGURES_DIR.glob("*.png")):
        kb = f.stat().st_size // 1024
        print(f"  {f.name} [{kb} KB]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
