"""Нейронна мережа, ваги якої навчає CMA-ES.

Це і є **"5-й метод"** із завдання куратора — підхід, що походить із
дисертації Літвінчук Ю.А. (2024). Ідея проста: всі ваги невеликої
повнозв'язної нейромережі укладаються в один плоский вектор
:math:`w \\in \\mathbb{R}^n` і CMA-ES шукає такий :math:`w`, який
мінімізує кросентропію на тренувальних даних.

Це принципово відрізняється від класичного backpropagation:

* немає обчислення градієнтів — лише прямий прохід (forward) і
  значення лосу;
* підходить для недиференційовних архитектур (хоча наша звичайна);
* повільніше, але універсальніше — оптимізатор той самий, що і
  для tuning гіперпараметрів чи інших задач.

Доступні два режими через параметр ``method``:

* ``"classic"`` — :func:`classifiers.cma_es.minimize_cma` (пакет ``cma``);
* ``"mixture"`` — :class:`classifiers.mixture_cma_es.MixtureCMAES`
  (власна реалізація зі сумішами за Літвінчук).

Для роботи на широких ознаках і великих вибірках передбачено
автоматичний PCA (``max_features``) і субсемплування train
(``max_train_samples``).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.decomposition import PCA

from .cma_es import minimize_cma
from .mixture_cma_es import MixtureCMAES


# ---- активації та утиліти ----------------------------------------------

def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


_ACTIVATIONS = {
    "relu": lambda z: np.maximum(0.0, z),
    "tanh": np.tanh,
}


def _count_params(layer_sizes) -> int:
    n = 0
    for n_in, n_out in zip(layer_sizes[:-1], layer_sizes[1:]):
        n += n_in * n_out + n_out
    return n


def _unpack(weights: np.ndarray, layer_sizes) -> list:
    out: list = []
    offset = 0
    for n_in, n_out in zip(layer_sizes[:-1], layer_sizes[1:]):
        size = n_in * n_out
        W = weights[offset:offset + size].reshape(n_in, n_out)
        offset += size
        b = weights[offset:offset + n_out]
        offset += n_out
        out.append((W, b))
    return out


def _forward(X: np.ndarray, params: list, activation) -> np.ndarray:
    h = X
    last = len(params) - 1
    for i, (W, b) in enumerate(params):
        z = h @ W + b
        h = _softmax(z) if i == last else activation(z)
    return h


def _cross_entropy(probs: np.ndarray, y_int: np.ndarray, eps: float = 1e-12) -> float:
    n = probs.shape[0]
    p = probs[np.arange(n), y_int]
    return -float(np.log(np.clip(p, eps, 1.0)).mean())


# ---- класифікатор -------------------------------------------------------

class CMAESNeuralNet(BaseEstimator, ClassifierMixin):
    """Невелика повнозв'язна NN, навчена CMA-ES (sklearn-сумісний API).

    Parameters
    ----------
    hidden_layer_sizes : tuple of int, default=(8,)
        Розміри прихованих шарів. Один шар (за замовчуванням) — це
        компроміс: достатньо параметрів для нелінійності, але CMA-ES
        ще може ефективно шукати у такому просторі.
    activation : {"tanh", "relu"}, default="tanh"
        Функція активації прихованих шарів. На виході — завжди softmax.
    method : {"classic", "mixture"}, default="classic"
        Оптимізатор: ``classic`` — пакет ``cma``; ``mixture`` —
        :class:`~classifiers.mixture_cma_es.MixtureCMAES` зі сумішами
        нормальних розподілів (за Літвінчук).
    max_iter : int, default=80
        Ліміт ітерацій CMA-ES.
    pop_size : int, optional
        Розмір популяції. ``None`` — за замовчуванням cma (для
        ``classic``) або ``max(40, 4 + 3·ln(n_params))`` для ``mixture``.
    sigma0 : float, default=0.3
        Початковий крок мутації.
    n_components : int, default=3
        Кількість піків у суміші (тільки для ``method="mixture"``).
    adaptive : bool, default=True
        Самоадаптивний підбір ``k`` (тільки для ``method="mixture"``).
    max_features : int, optional
        Якщо задано і кількість вхідних ознак більша — попередній PCA
        до цього розміру. Прискорює CMA-ES (менше ваг = менша
        розмірність пошуку).
    max_train_samples : int, optional
        Якщо задано і кількість тренувальних прикладів більша —
        випадково субсемплити train для пришвидшення обчислення лосу.
        Не впливає на test-метрики.
    l2 : float, default=0.0
        Коефіцієнт L2-регуляризації на ваги (додається до лосу).
    random_state : int, optional
        Seed для відтворюваності.

    Attributes
    ----------
    classes_ : numpy.ndarray
        Унікальні мітки класів.
    best_w_ : numpy.ndarray
        Найкращий знайдений вектор ваг.
    history_ : list of float
        Крива збіжності (для побудови графіку у дашборді).
    n_evaluations_, n_iterations_ : int
        Статистика CMA-ES.
    final_k_ : int
        Фінальна кількість піків (1 для ``classic``, може бути різна
        для ``mixture``).

    Examples
    --------
    >>> from sklearn.datasets import make_classification
    >>> X, y = make_classification(n_samples=200, n_features=8, random_state=0)
    >>> clf = CMAESNeuralNet(hidden_layer_sizes=(4,), method="classic",
    ...                       max_iter=30, random_state=0).fit(X, y)
    >>> proba = clf.predict_proba(X[:3])
    >>> proba.shape
    (3, 2)
    """

    def __init__(
        self,
        hidden_layer_sizes: tuple = (8,),
        activation: str = "tanh",
        method: str = "classic",
        max_iter: int = 80,
        pop_size: Optional[int] = None,
        sigma0: float = 0.3,
        n_components: int = 3,
        adaptive: bool = True,
        max_features: Optional[int] = None,
        max_train_samples: Optional[int] = None,
        l2: float = 0.0,
        random_state: Optional[int] = 42,
    ):
        self.hidden_layer_sizes = hidden_layer_sizes
        self.activation = activation
        self.method = method
        self.max_iter = max_iter
        self.pop_size = pop_size
        self.sigma0 = sigma0
        self.n_components = n_components
        self.adaptive = adaptive
        self.max_features = max_features
        self.max_train_samples = max_train_samples
        self.l2 = l2
        self.random_state = random_state

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y)
        self.classes_ = np.unique(y)
        y_int_full = np.searchsorted(self.classes_, y)

        # опційний PCA для зменшення розмірності
        if self.max_features is not None and X.shape[1] > self.max_features:
            self._pca: Optional[PCA] = PCA(
                n_components=self.max_features,
                random_state=self.random_state,
            )
            X = self._pca.fit_transform(X)
        else:
            self._pca = None

        # опційне субсемплування тренувальних прикладів
        rng = np.random.default_rng(self.random_state)
        if self.max_train_samples is not None and X.shape[0] > self.max_train_samples:
            idx = rng.choice(X.shape[0], size=self.max_train_samples, replace=False)
            X_use = X[idx]
            y_use = y_int_full[idx]
        else:
            X_use = X
            y_use = y_int_full

        n_features = X_use.shape[1]
        n_classes = len(self.classes_)
        layer_sizes = (n_features,) + tuple(self.hidden_layer_sizes) + (n_classes,)
        n_params = _count_params(layer_sizes)
        activation_fn = _ACTIVATIONS[self.activation]
        l2 = self.l2

        def loss(w: np.ndarray) -> float:
            params = _unpack(w, layer_sizes)
            probs = _forward(X_use, params, activation_fn)
            ce = _cross_entropy(probs, y_use)
            if l2 > 0:
                ce += l2 * float(np.sum(w * w))
            return ce

        x0 = rng.standard_normal(n_params) * 0.1

        if self.method == "classic":
            res = minimize_cma(
                loss, x0,
                sigma0=self.sigma0,
                pop_size=self.pop_size,
                max_iter=self.max_iter,
                random_state=self.random_state,
            )
            self.final_k_ = 1
        elif self.method == "mixture":
            pop = self.pop_size or max(40, 4 + int(3 * np.log(n_params + 1)))
            opt = MixtureCMAES(
                n_components=self.n_components,
                pop_size=pop,
                sigma0=self.sigma0,
                max_iter=self.max_iter,
                adaptive=self.adaptive,
                random_state=self.random_state,
            )
            res = opt.minimize(loss, x0)
            self.final_k_ = res.final_k
        else:
            raise ValueError(f"невідомий метод: {self.method!r}")

        self.best_w_ = res.best_x
        self.history_ = res.history
        self.n_evaluations_ = res.n_evaluations
        self.n_iterations_ = res.n_iterations
        self._params = _unpack(self.best_w_, layer_sizes)
        self._activation_fn = activation_fn
        self._layer_sizes = layer_sizes
        return self

    def predict_proba(self, X):
        X = np.asarray(X, dtype=float)
        if self._pca is not None:
            X = self._pca.transform(X)
        return _forward(X, self._params, self._activation_fn)

    def predict(self, X):
        proba = self.predict_proba(X)
        return self.classes_[proba.argmax(axis=1)]
