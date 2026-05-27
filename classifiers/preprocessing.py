"""Препроцесинг табличних ознак: імпутація, масштабування, енкодинг.

Модуль будує ``sklearn`` ``ColumnTransformer``, який однаково обробляє
будь-який із трьох датасетів проекту:

* числові ознаки → медіанна імпутація + ``StandardScaler``;
* категоріальні → найчастіше значення + ``OneHotEncoder``.

Цільову змінну окремо кодує :func:`encode_target` в цілі числа
``0..K-1``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def build_preprocessor(X: pd.DataFrame, scale: bool = True) -> ColumnTransformer:
    """Зібрати ``ColumnTransformer`` для табличних ознак.

    Parameters
    ----------
    X : pandas.DataFrame
        Матриця ознак до препроцесингу. Використовується лише для
        визначення типів колонок — самі значення не змінюються.
    scale : bool, default=True
        Чи застосовувати ``StandardScaler`` до числових ознак.
        Корисно вимикати для деревовидних моделей.

    Returns
    -------
    sklearn.compose.ColumnTransformer
        Незбудований препроцесор. Слід викликати ``.fit_transform(X)``
        або вставити у sklearn-пайплайн.

    Examples
    --------
    >>> import pandas as pd
    >>> X = pd.DataFrame({"age": [25, 30, None], "city": ["Kyiv", "Lviv", "Kyiv"]})
    >>> pre = build_preprocessor(X)
    >>> Xt = pre.fit_transform(X)
    >>> Xt.shape
    (3, 3)
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
    """Закодувати цільову змінну в цілі числа 0..K-1.

    На відміну від :class:`sklearn.preprocessing.LabelEncoder`, тут
    класи впорядковуються детермінованим способом (``sorted(y.unique())``)
    — це гарантує стабільне співставлення між запусками.

    Parameters
    ----------
    y : pandas.Series
        Цільова змінна. Може бути числовою або строковою.

    Returns
    -------
    y_enc : numpy.ndarray of shape (n,)
        Цілочисельне кодування, 0..K-1.
    classes : numpy.ndarray of shape (K,)
        Відсортований масив унікальних класів — у тому ж порядку,
        що відповідає кодуванню.

    Examples
    --------
    >>> import pandas as pd
    >>> y = pd.Series(["так", "ні", "так", "ні", "так"])
    >>> y_enc, classes = encode_target(y)
    >>> list(classes)
    ['ні', 'так']
    >>> list(y_enc)
    [1, 0, 1, 0, 1]
    """
    classes = np.array(sorted(y.unique()))
    mapping = {c: i for i, c in enumerate(classes)}
    y_enc = y.map(mapping).to_numpy()
    return y_enc, classes
