"""Метрики класифікації — accuracy, F1, ROC-AUC.

Куратор затвердив 3 метрики. Функції цього модуля підтримують одночасно
бінарні і мультикласові задачі, автоматично перемикаючи усереднення.

* Accuracy — частка правильних прогнозів. Обманює на незбалансованих
  класах (тривіальна модель ``predict=0`` на Loan Approval = 78%).
* F1-score — для бінарного беремо стандартний (positive class), для
  мультикласу — weighted average по класах.
* ROC-AUC — для бінарного звичайний, для мультикласу OvR weighted.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score


def compute_metrics(y_true, y_pred, y_proba=None, task: str = "binary") -> dict:
    """Обчислити accuracy, F1 і AUC для одного фолду або тесту.

    Parameters
    ----------
    y_true : array-like of shape (n,)
        Справжні мітки класів.
    y_pred : array-like of shape (n,)
        Прогнозовані мітки.
    y_proba : array-like, optional
        Ймовірності класів. Потрібно для AUC:

        * для бінарної задачі — форма ``(n,)`` (ймовірність позитивного
          класу) або ``(n, 2)``;
        * для мультикласу — ``(n, K)``.
    task : {"binary", "multiclass"}, default="binary"
        Тип задачі. Впливає на ``average`` для F1 і ``multi_class``
        для AUC.

    Returns
    -------
    dict
        Словник з ключами:

        * ``accuracy`` — частка правильних;
        * ``f1`` — F1-score;
        * ``auc`` — ROC-AUC (NaN, якщо ``y_proba`` не передано чи
          обчислення впало).

    Examples
    --------
    >>> import numpy as np
    >>> y_true = np.array([0, 0, 1, 1])
    >>> y_pred = np.array([0, 1, 1, 1])
    >>> proba = np.array([0.2, 0.6, 0.7, 0.9])
    >>> m = compute_metrics(y_true, y_pred, y_proba=proba, task="binary")
    >>> m["accuracy"]
    0.75
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
    """Усереднити метрики по фолдах k-fold CV.

    Для кожної числової метрики обчислюються mean і std — за критерієм
    стабільності моделі.

    Parameters
    ----------
    folds : list of dict
        Список словників, повернутих :func:`classifiers.crossval.kfold_evaluate`.

    Returns
    -------
    dict
        Для кожного числового ключа ``k`` (наприклад ``"f1"``) додається
        ``f"{k}_mean"`` і ``f"{k}_std"``. Поле ``"fold"`` (номер фолду)
        ігнорується.

    Notes
    -----
    NaN-значення (наприклад ``auc`` коли AUC не вдалось обчислити)
    виключаються з усереднення. Якщо всі значення метрики NaN —
    результат також NaN.
    """
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
