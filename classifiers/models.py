"""Базові класифікатори (sklearn) + GAM з розділу 1 диплома."""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

from .gam import GAMClassifier


def make_logreg(**kwargs):
    params = dict(max_iter=1000, random_state=42)
    params.update(kwargs)
    return LogisticRegression(**params)


def make_svm(**kwargs):
    # probability=True потрібен для AUC, але робить fit повільнішим
    params = dict(C=1.0, kernel="rbf", probability=True, random_state=42)
    params.update(kwargs)
    return SVC(**params)


def make_knn(**kwargs):
    params = dict(n_neighbors=5, n_jobs=-1)
    params.update(kwargs)
    return KNeighborsClassifier(**params)


def make_mlp(**kwargs):
    params = dict(
        hidden_layer_sizes=(64, 32),
        max_iter=300,
        random_state=42,
        early_stopping=True,
    )
    params.update(kwargs)
    return MLPClassifier(**params)


def make_gam(**kwargs):
    params = dict(n_knots=5, degree=3, C=1.0)
    params.update(kwargs)
    return GAMClassifier(**params)


BASE_MODELS = {
    "logreg": make_logreg,
    "svm": make_svm,
    "knn": make_knn,
    "mlp": make_mlp,
    "gam": make_gam,
}
