import numpy as np
from sklearn.datasets import make_classification
from sklearn.preprocessing import StandardScaler

from classifiers.hyperparam_tuning import (
    SPACES, space_knn, space_logreg, space_mlp, space_svm, tune_with_cma,
)
from classifiers.models import make_logreg


def test_space_logreg_transform():
    sp = space_logreg()
    params = sp.transform(np.array([0.0]))
    assert "C" in params
    assert 0.99 < params["C"] < 1.01  # 10^0 = 1


def test_space_svm_transform():
    sp = space_svm()
    params = sp.transform(np.array([1.0, -1.0]))
    assert "C" in params and "gamma" in params


def test_space_knn_integer():
    sp = space_knn()
    params = sp.transform(np.array([5.7]))
    assert params["n_neighbors"] == 6
    assert isinstance(params["n_neighbors"], int)


def test_space_mlp_structure():
    sp = space_mlp()
    params = sp.transform(np.array([16.0, -3.0, -2.0]))
    assert isinstance(params["hidden_layer_sizes"], tuple)
    assert all(isinstance(s, int) for s in params["hidden_layer_sizes"])


def test_tune_with_cma_logreg():
    X, y = make_classification(n_samples=200, n_features=5, random_state=0)
    X = StandardScaler().fit_transform(X)
    best_params, best_score, _ = tune_with_cma(
        make_logreg, space_logreg(), X, y,
        cv=3, scoring="f1", method="classic",
        max_iter=8, pop_size=6, random_state=0,
    )
    assert "C" in best_params
    assert 0.0 <= best_score <= 1.0


def test_spaces_registry_has_all_models():
    for name in ("logreg", "svm", "knn", "mlp"):
        assert name in SPACES
