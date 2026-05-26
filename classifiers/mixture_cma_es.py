"""Розширений CMA-ES зі сумішами нормальних розподілів.

Реалізує підхід дисертації Літвінчук Ю.А. (2024), розділ 2: класичний
унімодальний розподіл замінюється на суміш k нормальних компонент,
параметри якої оцінюються EM-алгоритмом по найкращих хромосомах кожної
ітерації. Опційно — самоадаптивний підбір k (видалення малих піків
за критерієм |X_l| < sqrt(N/2) та додавання нового піку у разі
стагнації цільової функції).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np


# ---- допоміжні ----------------------------------------------------------

def _log_mvn_pdf(X: np.ndarray, mean: np.ndarray, cov: np.ndarray,
                 reg: float = 1e-8) -> np.ndarray:
    """log щільність N(mean, cov) у точках X (форма (n, d))."""
    _, d = X.shape
    try:
        L = np.linalg.cholesky(cov + reg * np.eye(d))
    except np.linalg.LinAlgError:
        L = np.linalg.cholesky(cov + 1e-3 * np.eye(d))
    logdet = 2.0 * float(np.sum(np.log(np.diag(L))))
    diff = X - mean
    z = np.linalg.solve(L, diff.T)
    quad = np.sum(z ** 2, axis=0)
    return -0.5 * (d * np.log(2 * np.pi) + logdet + quad)


def _logsumexp(a: np.ndarray, axis: int, keepdims: bool = False) -> np.ndarray:
    m = np.max(a, axis=axis, keepdims=True)
    out = m + np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True))
    return out if keepdims else np.squeeze(out, axis=axis)


def _sample_mixture(weights, means, covs, n: int, rng: np.random.Generator) -> np.ndarray:
    """Семплування n точок із суміші нормальних."""
    k = len(weights)
    d = means[0].shape[0]
    comps = rng.choice(k, size=n, p=np.asarray(weights))
    X = np.empty((n, d))
    for i in range(n):
        c = int(comps[i])
        try:
            X[i] = rng.multivariate_normal(means[c], covs[c])
        except np.linalg.LinAlgError:
            cov = (covs[c] + covs[c].T) / 2 + 1e-6 * np.eye(d)
            X[i] = rng.multivariate_normal(means[c], cov)
    return X


def _em_step(X, weights, means, covs, reg: float = 1e-6):
    """Один EM-крок для суміші нормальних. means/covs — списки масивів."""
    n, d = X.shape
    k = len(weights)
    log_resp = np.empty((n, k))
    log_w = np.log(np.asarray(weights) + 1e-300)
    for j in range(k):
        log_resp[:, j] = log_w[j] + _log_mvn_pdf(X, means[j], covs[j])
    log_norm = _logsumexp(log_resp, axis=1, keepdims=True)
    gamma = np.exp(log_resp - log_norm)

    Nk = gamma.sum(axis=0)
    new_weights = Nk / n
    # уникаємо нулів у вагах — пік без точок одержує мінімальну вагу
    new_weights = np.where(new_weights < 1e-8, 1e-8, new_weights)
    new_weights = new_weights / new_weights.sum()

    new_means: list = []
    new_covs: list = []
    for j in range(k):
        nk = max(Nk[j], 1e-12)
        mj = (gamma[:, j:j+1] * X).sum(axis=0) / nk
        diff = X - mj
        Cj = (gamma[:, j:j+1] * diff).T @ diff / nk
        new_means.append(mj)
        new_covs.append(Cj + reg * np.eye(d))
    return new_weights, new_means, new_covs


def _em_iterate(X, weights, means, covs, n_steps: int, reg: float = 1e-6):
    for _ in range(n_steps):
        weights, means, covs = _em_step(X, weights, means, covs, reg=reg)
    return weights, means, covs


# ---- основний клас ------------------------------------------------------

@dataclass
class MixtureCMAResult:
    best_x: np.ndarray
    best_f: float
    n_evaluations: int
    n_iterations: int
    history: list
    final_k: int


@dataclass
class MixtureCMAES:
    """Розширений CMA-ES зі сумішами.

    Параметри
    ---------
    n_components : k — кількість піків.
    pop_size : N — хромосом на ітерацію.
    sigma0 : початкове відхилення для ініціалізації піків.
    em_steps : ітерацій EM на кожну зовнішню ітерацію.
    max_iter : ліміт зовнішніх ітерацій.
    tol : відносна точність зупинки.
    adaptive : чи підлаштовувати k під час виконання.
    patience : ітерацій стагнації для додавання нового піку.
    max_k : верхня межа на k у самоадаптивному режимі.
    bounds : (lo, hi) — або None.
    random_state : seed для np.random.
    """

    n_components: int = 3
    pop_size: int = 40
    sigma0: float = 0.5
    em_steps: int = 5
    max_iter: int = 100
    tol: float = 1e-6
    adaptive: bool = False
    patience: int = 10
    max_k: int = 20
    bounds: Optional[tuple] = None
    random_state: Optional[int] = None

    def minimize(self, objective: Callable[[np.ndarray], float], x0) -> MixtureCMAResult:
        rng = np.random.default_rng(self.random_state)
        x0 = np.asarray(x0, dtype=float)
        d = x0.size
        k = self.n_components

        means = [x0 + rng.standard_normal(d) * self.sigma0 for _ in range(k)]
        covs = [np.eye(d) * self.sigma0 ** 2 for _ in range(k)]
        weights = np.full(k, 1.0 / k)

        best_x = x0.copy()
        best_f = float("inf")
        n_evals = 0
        history: list = []
        stagnation = 0
        prev_best = best_f

        last_it = 0
        for it in range(self.max_iter):
            last_it = it
            samples = _sample_mixture(weights, means, covs, self.pop_size, rng)
            if self.bounds is not None:
                lo, hi = self.bounds
                samples = np.clip(samples, lo, hi)

            fitnesses = np.array([float(objective(s)) for s in samples])
            n_evals += self.pop_size

            best_idx = int(np.argmin(fitnesses))
            if fitnesses[best_idx] < best_f:
                best_f = float(fitnesses[best_idx])
                best_x = samples[best_idx].copy()
            history.append(best_f)

            rel = abs(prev_best - best_f) / max(abs(prev_best), 1.0)
            stagnation = stagnation + 1 if rel < self.tol else 0
            prev_best = best_f

            # відбираємо найкращу половину для EM
            n_top = max(self.pop_size // 2, k * 2 + 2)
            top_idx = np.argsort(fitnesses)[:min(n_top, len(fitnesses))]
            X_top = samples[top_idx]

            if X_top.shape[0] >= k:
                weights, means, covs = _em_iterate(
                    X_top, weights, means, covs, n_steps=self.em_steps,
                )

            if self.adaptive:
                weights, means, covs, k, removed = self._maybe_shrink(weights, means, covs, k)
                if removed:
                    stagnation = 0
                if stagnation >= self.patience and k < self.max_k:
                    weights, means, covs, k = self._add_peak(weights, means, covs, k, rng, d)
                    stagnation = 0

            if self._converged(history):
                break

        return MixtureCMAResult(
            best_x=best_x,
            best_f=best_f,
            n_evaluations=n_evals,
            n_iterations=last_it + 1,
            history=history,
            final_k=k,
        )

    def _maybe_shrink(self, weights, means, covs, k):
        """Видаляє піки, чия очікувана кількість представників менша sqrt(N/2)."""
        threshold = np.sqrt(self.pop_size / 2.0)
        expected_count = weights * self.pop_size
        keep = expected_count >= threshold
        if keep.sum() < k and keep.sum() >= 1:
            idx = np.where(keep)[0]
            new_weights = weights[idx]
            new_weights = new_weights / new_weights.sum()
            new_means = [means[i] for i in idx]
            new_covs = [covs[i] for i in idx]
            return new_weights, new_means, new_covs, len(new_weights), True
        return weights, means, covs, k, False

    def _add_peak(self, weights, means, covs, k, rng, d):
        """Додає новий пік шляхом розщеплення найбільшого."""
        biggest = int(np.argmax(weights))
        shift = rng.standard_normal(d) * self.sigma0
        new_mean = means[biggest] + shift
        new_means = list(means) + [new_mean]
        new_covs = list(covs) + [np.eye(d) * self.sigma0 ** 2]
        half = weights[biggest] / 2.0
        new_weights = np.concatenate([weights, [half]])
        new_weights[biggest] = half
        new_weights = new_weights / new_weights.sum()
        return new_weights, new_means, new_covs, k + 1

    def _converged(self, history: list, window: int = 8) -> bool:
        if len(history) < window + 1:
            return False
        recent = history[-window:]
        rel = abs(recent[-1] - recent[0]) / max(abs(recent[0]), 1.0)
        return rel < self.tol
