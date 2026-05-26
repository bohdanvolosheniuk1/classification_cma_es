"""Препроцесинг ознак — масштабування, енкодинг, імпутація."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_preprocessor(X: pd.DataFrame, scale: bool = True) -> ColumnTransformer:
    """Збирає ColumnTransformer для табличних ознак.

    Числові: median imputation + (StandardScaler за замовчуванням).
    Категоріальні: most_frequent + OneHotEncoder.
    """
    num_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = X.select_dtypes(include=["object", "category", "bool"]).columns.tolist()

    num_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scaler", StandardScaler()))
    num_pipe = Pipeline(num_steps)

    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    transformers = []
    if num_cols:
        transformers.append(("num", num_pipe, num_cols))
    if cat_cols:
        transformers.append(("cat", cat_pipe, cat_cols))

    return ColumnTransformer(transformers=transformers, remainder="drop")


def encode_target(y: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Кодує цільову змінну в цілі числа 0..K-1. Повертає (y_enc, classes)."""
    classes = np.array(sorted(y.unique()))
    mapping = {c: i for i, c in enumerate(classes)}
    y_enc = y.map(mapping).to_numpy()
    return y_enc, classes
