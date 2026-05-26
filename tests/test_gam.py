import numpy as np
import pytest
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from classifiers.gam import GAMClassifier
from classifiers.hyperparam_tuning import SPACES, space_gam, tune_with_cma
from classifiers.models import make_gam


def _split(n_classes=2):
    X, y = make_classification(
        n_samples=300, n_features=8, n_informative=5,
        n_redundant=2,
        n_classes=n_classes,
        n_clusters_per_class=1 if n_classes > 2 else 2,
        random_state=0,
    )
    X = StandardScaler().fit_transform(X)
    return train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)


def test_gam_binary():
    X_tr, X_te, y_tr, y_te = _split()
    gam = GAMClassifier(n_knots=5, degree=3, C=1.0)
    gam.fit(X_tr, y_tr)
    pred = gam.predict(X_te)
    proba = gam.predict_proba(X_te)
    assert pred.shape == (len(X_te),)
    assert proba.shape == (len(X_te), 2)
    assert np.allclose(proba.sum(axis=1), 1.0)
    assert (pred == y_te).mean() > 0.7


def test_gam_multiclass():
    X_tr, X_te, y_tr, y_te = _split(n_classes=3)
    gam = GAMClassifier(n_knots=5)
    gam.fit(X_tr, y_tr)
    proba = gam.predict_proba(X_te)
    assert proba.shape == (len(X_te), 3)


@pytest.mark.parametrize("kn", [3, 5, 8])
def test_gam_different_knot_counts(kn):
    X_tr, X_te, y_tr, y_te = _split()
    gam = GAMClassifier(n_knots=kn).fit(X_tr, y_tr)
    assert gam.predict(X_te).shape == (len(X_te),)


def test_make_gam_factory():
    gam = make_gam()
    assert isinstance(gam, GAMClassifier)


def test_space_gam_transform():
    sp = space_gam()
    params = sp.transform(np.array([5.0, 3.0, 0.0]))
    assert params["n_knots"] == 5
    assert params["degree"] == 3
    assert 0.99 < params["C"] < 1.01


def test_gam_in_spaces_registry():
    assert "gam" in SPACES


def test_tune_gam():
    X_tr, X_te, y_tr, y_te = _split()
    best_params, best_score, _ = tune_with_cma(
        make_gam, space_gam(), X_tr, y_tr,
        cv=3, scoring="f1", method="classic",
        max_iter=8, pop_size=6, random_state=0,
    )
    assert "n_knots" in best_params
    assert "C" in best_params
    assert 0.0 <= best_score <= 1.0
