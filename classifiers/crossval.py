"""K-fold перехресна валідація."""

from __future__ import annotations

import time
from typing import Any, Callable

import numpy as np
from sklearn.model_selection import StratifiedKFold, train_test_split

from .metrics import compute_metrics


def split_train_test(X, y, test_size: float = 0.2, random_state: int = 42, stratify: bool = True):
    """Розбиття на train/test зі стратифікацією за умовчанням."""
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
    """Stratified k-fold, повертає метрики по фолдах.

    model_factory — фабрика свіжої необученої моделі (sklearn-сумісної).
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
