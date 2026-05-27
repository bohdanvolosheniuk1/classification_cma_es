"""Підбір гіперпараметрів базових класифікаторів через CMA-ES.

Модуль реалізує модель ``tuned_*`` — обгортку, де CMA-ES виступає
тюнером гіперпараметрів. Для кожної базової моделі визначено простір
гіперпараметрів (:class:`HyperSpace`) з межами і функцією перетворення
вектора CMA-ES у словник параметрів sklearn-моделі.

Найцікавіший випадок — ``tuned_gam``: CMA-ES (розділ 2 диплома)
підбирає ``n_knots`` і ``λ = 1/C`` для GAM (розділ 1 диплома). Це
**пряме об'єднання обох теоретичних розділів** у одній моделі.

Для 1-вимірних просторів (наприклад, kNN з одним ``n_neighbors``)
використовується ``random search`` fallback — пакет ``cma`` коректно
не працює з ``dim == 1``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from sklearn.model_selection import cross_val_score

from .cma_es import minimize_cma
from .mixture_cma_es import MixtureCMAES


@dataclass
class HyperSpace:
    """Опис простору гіперпараметрів для CMA-ES.

    CMA-ES шукає у звичайному ``R^d`` (з опційними межами), а реальні
    параметри моделі можуть бути цілими (n_neighbors), логарифмічними
    (C, gamma) або структурованими (hidden_layer_sizes). ``transform``
    конвертує вектор CMA-ES у словник параметрів sklearn-моделі.

    Attributes
    ----------
    lows : numpy.ndarray of shape (d,)
        Нижні межі координат у просторі пошуку.
    highs : numpy.ndarray of shape (d,)
        Верхні межі.
    transform : callable
        Функція ``np.ndarray -> dict``, що мапить вектор CMA-ES у
        kwargs для відповідної ``make_*`` фабрики.
    """

    lows: np.ndarray
    highs: np.ndarray
    transform: Callable[[np.ndarray], dict]

    @property
    def dim(self) -> int:
        """Розмірність простору пошуку."""
        return len(self.lows)


def space_logreg() -> HyperSpace:
    """Простір для LogisticRegression: log10(C) ∈ [-3, 3]."""
    return HyperSpace(
        lows=np.array([-3.0]),
        highs=np.array([3.0]),
        transform=lambda x: {"C": float(10 ** np.clip(x[0], -3, 3))},
    )


def space_svm() -> HyperSpace:
    """Простір для SVM: log10(C) ∈ [-3, 3], log10(gamma) ∈ [-4, 1]."""
    return HyperSpace(
        lows=np.array([-3.0, -4.0]),
        highs=np.array([3.0, 1.0]),
        transform=lambda x: {
            "C": float(10 ** np.clip(x[0], -3, 3)),
            "gamma": float(10 ** np.clip(x[1], -4, 1)),
        },
    )


def space_knn() -> HyperSpace:
    """Простір для kNN: n_neighbors ∈ [1, 30] (цілочисельне)."""
    return HyperSpace(
        lows=np.array([1.0]),
        highs=np.array([30.0]),
        transform=lambda x: {"n_neighbors": int(np.clip(round(x[0]), 1, 30))},
    )


def space_mlp() -> HyperSpace:
    """Простір для MLP: hidden_size ∈ [4, 128], log10(alpha), log10(lr)."""
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
    """Простір для GAM (міст між розд. 1 і розд. 2 диплома).

    Шукаємо параметри з розділу 1.5 диплома:

    * ``n_knots`` ∈ [3, 15] — кількість базисних функцій (:math:`k`);
    * ``degree`` ∈ [2, 4] — степінь сплайну;
    * ``log10(C)`` ∈ [-3, 3] — параметр згладжування :math:`\\lambda = 1/C`.

    Оптимізація — алгоритмом з розділу 2 (CMA-ES).
    """
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
"""Реєстр функцій-фабрик для просторів гіперпараметрів.

Використовується pipeline'ом для моделей з префіксом ``tuned_*``.
Ключі мають збігатися з ключами :data:`classifiers.models.BASE_MODELS`.
"""


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
    """Підібрати гіперпараметри ``factory(**params)`` через CMA-ES.

    Цільова функція — від'ємне середнє ``cross_val_score`` (бо CMA-ES
    мінімізує). Для 1-вимірного простору використовується random search
    fallback.

    Parameters
    ----------
    factory : callable
        Фабрика моделі, наприклад :func:`classifiers.models.make_logreg`.
        Приймає ``**kwargs`` із простору параметрів і повертає
        sklearn-сумісний естіматор.
    space : HyperSpace
        Простір пошуку для CMA-ES і функція трансформації.
    X, y : array-like
        Тренувальні дані.
    cv : int, default=3
        Кількість фолдів у внутрішньому ``cross_val_score``.
    scoring : str, default="f1_weighted"
        sklearn-метрика для оптимізації.
    method : {"classic", "mixture"}, default="classic"
        Тип CMA-ES.
    max_iter : int, default=20
        Ліміт ітерацій оптимізатора.
    pop_size : int, default=10
        Розмір популяції на ітерацію.
    random_state : int, default=42
        Seed.

    Returns
    -------
    best_params : dict
        Найкращі знайдені параметри (готові для ``factory(**best_params)``).
    best_score : float
        Найкраще значення ``scoring`` (вже з правильним знаком, не negated).
    raw_result : CMAResult or MixtureCMAResult or dict
        Внутрішній об'єкт оптимізатора (історія, evals тощо).
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
