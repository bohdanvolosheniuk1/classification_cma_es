import numpy as np
import pytest
from sklearn.datasets import make_classification
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from classifiers.cma_nn import CMAESNeuralNet


def _split():
    X, y = make_classification(
        n_samples=300, n_features=8, n_informative=5,
        n_classes=2, random_state=0,
    )
    X = StandardScaler().fit_transform(X)
    return train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)


@pytest.mark.parametrize("method", ["classic", "mixture"])
def test_fit_predict_binary(method):
    X_tr, X_te, y_tr, y_te = _split()
    clf = CMAESNeuralNet(
        hidden_layer_sizes=(4,),
        method=method,
        max_iter=20,
        n_components=2,
        random_state=0,
    )
    clf.fit(X_tr, y_tr)
    pred = clf.predict(X_te)
    proba = clf.predict_proba(X_te)
    assert pred.shape == (len(X_te),)
    assert proba.shape == (len(X_te), 2)
    assert np.allclose(proba.sum(axis=1), 1.0)
    acc = float((pred == y_te).mean())
    assert acc > 0.6, f"{method}: very low accuracy {acc}"


def test_pca_reduction():
    X_tr, X_te, y_tr, y_te = _split()
    clf = CMAESNeuralNet(
        hidden_layer_sizes=(4,),
        method="classic",
        max_iter=15,
        max_features=3,
        random_state=0,
    )
    clf.fit(X_tr, y_tr)
    # внутрішня розмірність — 3 ознаки після PCA
    assert clf._params[0][0].shape[0] == 3


def test_max_train_samples_subsamples():
    X_tr, X_te, y_tr, y_te = _split()
    clf = CMAESNeuralNet(
        hidden_layer_sizes=(4,),
        method="classic",
        max_iter=10,
        max_train_samples=50,
        random_state=0,
    )
    # лише перевірка що fit відпрацював без помилок
    clf.fit(X_tr, y_tr)
    assert clf.predict(X_te).shape == (len(X_te),)
