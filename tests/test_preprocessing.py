import numpy as np
import pandas as pd

from classifiers.preprocessing import build_preprocessor, encode_target


def test_build_preprocessor_mixed():
    X = pd.DataFrame({
        "num1": [1.0, 2.0, 3.0, np.nan],
        "num2": [10, 20, 30, 40],
        "cat": ["a", "b", "a", "c"],
    })
    pre = build_preprocessor(X)
    Z = pre.fit_transform(X)
    assert Z.shape[0] == 4
    # 2 числові (масштабовані) + 3 категорії (a, b, c) у one-hot = 5
    assert Z.shape[1] == 5


def test_encode_target_binary():
    y = pd.Series(["yes", "no", "yes", "yes", "no"])
    y_enc, classes = encode_target(y)
    assert list(classes) == ["no", "yes"]
    assert list(y_enc) == [1, 0, 1, 1, 0]


def test_encode_target_multiclass():
    y = pd.Series([2, 0, 1, 2, 0])
    y_enc, classes = encode_target(y)
    assert list(classes) == [0, 1, 2]
    assert list(y_enc) == [2, 0, 1, 2, 0]
