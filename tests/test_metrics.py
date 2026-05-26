import numpy as np

from classifiers.metrics import aggregate_folds, compute_metrics


def test_binary_metrics():
    y_true = np.array([0, 0, 1, 1, 1, 0])
    y_pred = np.array([0, 0, 1, 1, 0, 0])
    y_proba = np.array([0.1, 0.2, 0.8, 0.7, 0.4, 0.3])
    m = compute_metrics(y_true, y_pred, y_proba=y_proba, task="binary")
    assert 0.0 <= m["accuracy"] <= 1.0
    assert m["accuracy"] == 5 / 6
    assert 0.0 <= m["f1"] <= 1.0
    assert 0.0 <= m["auc"] <= 1.0


def test_multiclass_metrics():
    y_true = np.array([0, 1, 2, 0, 1, 2])
    y_pred = np.array([0, 1, 2, 0, 1, 2])
    proba = np.eye(3)[y_true]
    m = compute_metrics(y_true, y_pred, y_proba=proba, task="multiclass")
    assert m["accuracy"] == 1.0
    assert m["f1"] == 1.0


def test_missing_proba_gives_nan_auc():
    y_true = np.array([0, 1, 1])
    y_pred = np.array([0, 1, 0])
    m = compute_metrics(y_true, y_pred, y_proba=None, task="binary")
    assert np.isnan(m["auc"])


def test_aggregate_folds():
    folds = [
        {"fold": 1, "accuracy": 0.8, "f1": 0.75, "auc": 0.9},
        {"fold": 2, "accuracy": 0.9, "f1": 0.85, "auc": 0.95},
        {"fold": 3, "accuracy": 0.85, "f1": 0.80, "auc": 0.92},
    ]
    out = aggregate_folds(folds)
    assert abs(out["accuracy_mean"] - 0.85) < 1e-9
    assert out["accuracy_std"] > 0
    assert "f1_mean" in out
