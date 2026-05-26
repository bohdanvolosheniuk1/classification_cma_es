"""Метрики класифікації: accuracy, F1, AUC."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score


def compute_metrics(y_true, y_pred, y_proba=None, task: str = "binary") -> dict:
    """Повертає dict з ключами accuracy, f1, auc.

    y_proba: для бінарного — форма (n,) або (n, 2);
             для мультикласу — (n, K).
    """
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
    }

    avg = "binary" if task == "binary" else "weighted"
    metrics["f1"] = float(f1_score(y_true, y_pred, average=avg, zero_division=0))

    auc = float("nan")
    if y_proba is not None:
        try:
            if task == "binary":
                if y_proba.ndim == 2:
                    proba_pos = y_proba[:, 1]
                else:
                    proba_pos = y_proba
                auc = float(roc_auc_score(y_true, proba_pos))
            else:
                auc = float(roc_auc_score(
                    y_true, y_proba, multi_class="ovr", average="weighted",
                ))
        except (ValueError, IndexError):
            pass
    metrics["auc"] = auc
    return metrics


def aggregate_folds(folds: list[dict]) -> dict:
    """Збирає mean/std по фолдах для всіх числових метрик."""
    if not folds:
        return {}
    numeric_keys = [
        k for k, v in folds[0].items()
        if isinstance(v, (int, float)) and k != "fold"
    ]
    summary: dict[str, float] = {}
    for k in numeric_keys:
        vals = np.array(
            [f[k] for f in folds if k in f and not np.isnan(f[k])],
            dtype=float,
        )
        if vals.size == 0:
            summary[f"{k}_mean"] = float("nan")
            summary[f"{k}_std"] = float("nan")
        else:
            summary[f"{k}_mean"] = float(vals.mean())
            summary[f"{k}_std"] = float(vals.std())
    return summary
