"""Класичний CMA-ES — обгортка над пакетом `cma`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np


@dataclass
class CMAResult:
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
    """Запускає cma.CMAEvolutionStrategy на мінімізацію objective(x)."""
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
