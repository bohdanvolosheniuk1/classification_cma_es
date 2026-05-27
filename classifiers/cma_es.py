"""Класичний CMA-ES — обгортка над пакетом ``cma``.

Алгоритм CMA-ES (Covariance Matrix Adaptation Evolution Strategy) —
це стохастичний оптимізатор **без похідних**, описаний у розділі 2
дипломної роботи. Він шукає мінімум функції, ітеративно семплуючи
точки з багатовимірного нормального розподілу :math:`\\mathcal{N}(m, \\sigma^2 C)`
і оновлюючи його параметри за найкращими точками.

Модуль надає тонку обгортку :func:`minimize_cma` навколо
``cma.CMAEvolutionStrategy`` Ніколаса Хансена (той самий пакет
використовує Літвінчук Ю.А. у дисертації). Розширений варіант зі
сумішами реалізовано окремо в :mod:`classifiers.mixture_cma_es`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np


@dataclass
class CMAResult:
    """Результат однієї оптимізації CMA-ES.

    Attributes
    ----------
    best_x : numpy.ndarray of shape (d,)
        Знайдений найкращий розв'язок.
    best_f : float
        Значення цільової функції в ``best_x``.
    n_evaluations : int
        Скільки разів викликано ``objective(x)`` сумарно.
    n_iterations : int
        Скільки зовнішніх ітерацій (поколінь) виконано.
    history : list of float
        ``best_f`` після кожної ітерації — для побудови кривої збіжності.
    """

    best_x: np.ndarray
    best_f: float
    n_evaluations: int
    n_iterations: int
    history: list


def minimize_cma(
    objective: Callable[[np.ndarray], float],
    x0,
    sigma0: float = 0.3,
    pop_size: Optional[int] = None,
    max_iter: int = 100,
    bounds: Optional[tuple] = None,
    random_state: Optional[int] = None,
    verbose: bool = False,
) -> CMAResult:
    """Мінімізувати ``objective`` класичним CMA-ES.

    Parameters
    ----------
    objective : callable
        Цільова функція ``f(x: np.ndarray) -> float``. Має приймати
        1D-вектор і повертати число для мінімізації.
    x0 : array-like
        Початкова точка пошуку. Її довжина визначає розмірність задачі.
    sigma0 : float, default=0.3
        Початковий крок мутації :math:`\\sigma`. Має бути близьким до
        очікуваної відстані між початковою точкою і оптимумом.
    pop_size : int, optional
        Розмір популяції (:math:`\\lambda`). За замовчуванням
        ``4 + floor(3 * ln(d))`` як рекомендує Hansen.
    max_iter : int, default=100
        Ліміт ітерацій (поколінь).
    bounds : tuple of (lo, hi), optional
        Скаляри або вектори межами області пошуку. Якщо задано —
        точки клипуються.
    random_state : int, optional
        Seed. Пакет cma не приймає 0, тому внутрішньо додається +1.
    verbose : bool, default=False
        Чи друкувати прогрес у stdout.

    Returns
    -------
    CMAResult
        Результат із полями ``best_x``, ``best_f`` та історією.

    Examples
    --------
    >>> import numpy as np
    >>> def sphere(x): return float(np.sum(x * x))
    >>> res = minimize_cma(sphere, x0=[1.0, 2.0, 3.0],
    ...                    sigma0=0.5, max_iter=50, random_state=1)
    >>> res.best_f < 1e-3
    True

    Notes
    -----
    Алгоритм безградієнтний — він не вимагає диференційовності
    ``objective``. Підходить для оптимізації hyperparameters,
    тренування малих NN, інженерних задач тощо.
    """
    import cma

    x0 = np.asarray(x0, dtype=float).tolist()
    opts: dict = {
        "maxiter": max_iter,
        "verbose": 1 if verbose else -9,
    }
    if pop_size is not None:
        opts["popsize"] = int(pop_size)
    if random_state is not None:
        # cma не приймає seed=0
        opts["seed"] = int(random_state) + 1
    if bounds is not None:
        lo, hi = bounds
        lo_arr = np.broadcast_to(lo, len(x0)).tolist()
        hi_arr = np.broadcast_to(hi, len(x0)).tolist()
        opts["bounds"] = [lo_arr, hi_arr]

    es = cma.CMAEvolutionStrategy(x0, sigma0, opts)
    history: list = []
    while not es.stop():
        xs = es.ask()
        fs = [float(objective(np.asarray(x))) for x in xs]
        es.tell(xs, fs)
        history.append(float(es.result.fbest))

    res = es.result
    return CMAResult(
        best_x=np.asarray(res.xbest),
        best_f=float(res.fbest),
        n_evaluations=int(res.evaluations),
        n_iterations=int(res.iterations),
        history=history,
    )
