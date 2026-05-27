"""Розбиття даних і перехресна валідація.

Модуль інкапсулює дві стандартні процедури оцінки моделі:

* :func:`split_train_test` — поділ 80/20 (стратифікований) для
  фінальної оцінки на test.
* :func:`kfold_evaluate` — Stratified K-Fold (k=5 за замовчуванням)
  для оцінки стабільності моделі на тренувальній частині.

Стратифікація зберігає пропорції класів у кожному фолді — критично
для незбалансованих задач (наприклад, Loan Approval ~78% / 22%).
"""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np
from sklearn.model_selection import StratifiedKFold, train_test_split

from .metrics import compute_metrics


def split_train_test(
    X,
    y,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
):
    """Розбити дані на train/test зі стратифікацією за умовчанням.

    Parameters
    ----------
    X : array-like of shape (n, p)
        Матриця ознак.
    y : array-like of shape (n,)
        Цільова змінна.
    test_size : float, default=0.2
        Частка прикладів для тесту.
    random_state : int, default=42
        Seed.
    stratify : bool, default=True
        Чи зберігати пропорції класів у фолдах.

    Returns
    -------
    X_train, X_test, y_train, y_test : tuple of arrays
        Як у :func:`sklearn.model_selection.train_test_split`.
    """
    return train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_state,
        stratify=y if stratify else None,
    )


def kfold_evaluate(
    model_factory: Callable[[], Any],
    X: np.ndarray,
    y: np.ndarray,
    n_splits: int = 5,
    task: str = "binary",
    random_state: int = 42,
) -> list[dict]:
    """Stratified K-Fold з метриками на кожному фолді.

    На кожному фолді створюється **свіжа** модель (через ``model_factory``),
    навчається на ``(k-1)`` фолдах і оцінюється на 1 валідаційному.

    Parameters
    ----------
    model_factory : callable
        Функція без аргументів, що повертає необучену sklearn-сумісну
        модель. Використання фабрики (а не вже створеного об'єкта)
        гарантує, що між фолдами немає протікання станів.
    X : numpy.ndarray of shape (n, p)
        Матриця ознак (після препроцесингу).
    y : numpy.ndarray of shape (n,)
        Цільова змінна (закодована цілими через
        :func:`classifiers.preprocessing.encode_target`).
    n_splits : int, default=5
        Кількість фолдів.
    task : {"binary", "multiclass"}, default="binary"
        Тип задачі. Впливає на спосіб обчислення F1 і AUC.
    random_state : int, default=42
        Seed для розбиття.

    Returns
    -------
    list of dict
        Один словник на фолд із полями: ``accuracy``, ``f1``, ``auc``
        (з :func:`classifiers.metrics.compute_metrics`), а також
        ``fold`` (номер фолду 1..k) і ``train_time`` (секунд на ``fit``).

    Examples
    --------
    >>> from classifiers.models import make_logreg
    >>> from sklearn.datasets import make_classification
    >>> X, y = make_classification(n_samples=200, random_state=0)
    >>> folds = kfold_evaluate(make_logreg, X, y, n_splits=3)
    >>> len(folds)
    3
    >>> "accuracy" in folds[0]
    True
    """
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    folds: list[dict] = []
    for i, (tr_idx, val_idx) in enumerate(skf.split(X, y), start=1):
        X_tr, X_val = X[tr_idx], X[val_idx]
        y_tr, y_val = y[tr_idx], y[val_idx]

        model = model_factory()
        t0 = time.time()
        model.fit(X_tr, y_tr)
        elapsed = time.time() - t0

        y_pred = model.predict(X_val)
        y_proba = None
        if hasattr(model, "predict_proba"):
            try:
                y_proba = np.asarray(model.predict_proba(X_val))
            except Exception:
                y_proba = None

        m = compute_metrics(y_val, y_pred, y_proba=y_proba, task=task)
        m["fold"] = i
        m["train_time"] = elapsed
        folds.append(m)
    return folds
