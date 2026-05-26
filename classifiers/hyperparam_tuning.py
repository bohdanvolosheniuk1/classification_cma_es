"""Підбір гіперпараметрів базових класифікаторів за допомогою CMA-ES."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from sklearn.model_selection import cross_val_score

from .cma_es import minimize_cma
from .mixture_cma_es import MixtureCMAES


@dataclass
class HyperSpace:
    """Простір гіперпараметрів: межі для CMA-ES + transform у sklearn-params."""

    lows: np.ndarray
    highs: np.ndarray
    transform: Callable[[np.ndarray], dict]

    @property
    def dim(self) -> int:
        return len(self.lows)


def space_logreg() -> HyperSpace:
    # log10(C) у [-3, 3]
    return HyperSpace(
        lows=np.array([-3.0]),
        highs=np.array([3.0]),
        transform=lambda x: {"C": float(10 ** np.clip(x[0], -3, 3))},
    )


def space_svm() -> HyperSpace:
    return HyperSpace(
        lows=np.array([-3.0, -4.0]),
        highs=np.array([3.0, 1.0]),
        transform=lambda x: {
            "C": float(10 ** np.clip(x[0], -3, 3)),
            "gamma": float(10 ** np.clip(x[1], -4, 1)),
        },
    )


def space_knn() -> HyperSpace:
    return HyperSpace(
        lows=np.array([1.0]),
        highs=np.array([30.0]),
        transform=lambda x: {"n_neighbors": int(np.clip(round(x[0]), 1, 30))},
    )


def space_mlp() -> HyperSpace:
    return HyperSpace(
        lows=np.array([4.0, -6.0, -4.0]),
        highs=np.array([128.0, -1.0, -1.0]),
        transform=lambda x: {
            "hidden_layer_sizes": (int(np.clip(round(x[0]), 4, 128)),),
            "alpha": float(10 ** np.clip(x[1], -6, -1)),
            "learning_rate_init": float(10 ** np.clip(x[2], -4, -1)),
        },
    )


def space_gam() -> HyperSpace:
    # n_knots, degree, log10(C) — параметри з розділу 1 диплома:
    # k — кількість базисних функцій, степінь сплайна, λ = 1/C
    return HyperSpace(
        lows=np.array([3.0, 2.0, -3.0]),
        highs=np.array([15.0, 4.0, 3.0]),
        transform=lambda x: {
            "n_knots": int(np.clip(round(x[0]), 3, 15)),
            "degree": int(np.clip(round(x[1]), 2, 4)),
            "C": float(10 ** np.clip(x[2], -3, 3)),
        },
    )


SPACES = {
    "logreg": space_logreg,
    "svm": space_svm,
    "knn": space_knn,
    "mlp": space_mlp,
    "gam": space_gam,
}


def _random_search_1d(neg_score, space, n_evals: int, rng: np.random.Generator):
    """Простий fallback для 1-вимірних просторів — пакет cma не любить dim=1."""
    samples = rng.uniform(space.lows[0], space.highs[0], size=n_evals)
    best_x = None
    best_f = float("inf")
    for v in samples:
        f = neg_score(np.array([v]))
        if f < best_f:
            best_f = f
            best_x = np.array([v])
    return best_x, best_f


def tune_with_cma(
    factory: Callable,
    space: HyperSpace,
    X,
    y,
    cv: int = 3,
    scoring: str = "f1_weighted",
    method: str = "classic",
    max_iter: int = 20,
    pop_size: int = 10,
    random_state: int = 42,
):
    """Шукає оптимальні гіперпараметри factory(**params).

    Повертає (best_params_dict, best_score, raw_result).
    """

    def neg_score(x: np.ndarray) -> float:
        params = space.transform(np.asarray(x))
        model = factory(**params)
        scores = cross_val_score(model, X, y, cv=cv, scoring=scoring, n_jobs=1)
        return -float(scores.mean())

    # для 1-вимірних просторів cma іноді ламається — використовуємо random search
    if space.dim == 1:
        rng = np.random.default_rng(random_state)
        best_x, best_f = _random_search_1d(neg_score, space, pop_size * max_iter, rng)
        return space.transform(best_x), -best_f, {"best_x": best_x, "best_f": best_f}

    x0 = (space.lows + space.highs) / 2.0
    bounds_t = (space.lows.tolist(), space.highs.tolist())

    if method == "classic":
        res = minimize_cma(
            neg_score, x0,
            sigma0=0.5,
            pop_size=pop_size,
            max_iter=max_iter,
            bounds=bounds_t,
            random_state=random_state,
        )
    elif method == "mixture":
        opt = MixtureCMAES(
            n_components=2,
            pop_size=pop_size,
            sigma0=0.5,
            max_iter=max_iter,
            bounds=(space.lows, space.highs),
            adaptive=True,
            random_state=random_state,
        )
        res = opt.minimize(neg_score, x0)
    else:
        raise ValueError(f"невідомий method={method!r}")

    return space.transform(res.best_x), -res.best_f, res
