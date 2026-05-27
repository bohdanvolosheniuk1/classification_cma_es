"""Узагальнена адитивна модель (GAM) для класифікації.

Модель базується на матеріалі **розділу 1 дипломної роботи**.
Кожна неперервна ознака проходить через сплайнове базисне перетворення
(B-сплайни), потім всі базисні функції лінійно комбінуються
:class:`sklearn.linear_model.LogisticRegression`. Така конструкція
еквівалентна узагальненій адитивній моделі з логіт-зв'язком
(розділ 1.6 диплома).

Математично:

.. math::

    g(\\mathbb{E}[y \\mid X]) = \\beta_0 + \\sum_{i=1}^{p} f_i(x_i),
    \\quad f_i(x_i) = \\sum_{j=1}^{k} \\beta_{ij} \\, b_j(x_i)

де :math:`g` — логіт, :math:`b_j` — базисна B-сплайн-функція,
:math:`\\beta_{ij}` — коефіцієнти, які підбирає логістична регресія.
Штраф L2 у LogisticRegression грає роль параметра згладжування
:math:`\\lambda = 1/C` (розділ 1.5).

Реалізовано лише через sklearn — без зовнішніх залежностей типу
``pygam``. Сумісно зі sklearn API.
"""

from __future__ import annotations

from typing import Optional

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import SplineTransformer


class GAMClassifier(BaseEstimator, ClassifierMixin):
    """Класифікатор GAM = ``SplineTransformer + LogisticRegression``.

    Parameters
    ----------
    n_knots : int, default=5
        Кількість вузлів сплайну (параметр :math:`k` з розділу 1.3
        диплома). Більше — гнучкіша модель, але ризик перенавчання.
    degree : int, default=3
        Степінь B-сплайну. 3 — стандартний кубічний сплайн (розд. 1.4).
    C : float, default=1.0
        Обернений параметр згладжування :math:`C = 1/\\lambda`.
        Менше — більше згладжування / штрафу за складність.
    knots : {"uniform", "quantile"}, default="uniform"
        Стратегія розміщення вузлів. ``"quantile"`` доречно для
        нерівномірно розподілених ознак.
    max_iter : int, default=500
        Ліміт ітерацій LBFGS у логістичній регресії.
    random_state : int, optional
        Seed для відтворюваності.

    Attributes
    ----------
    classes_ : numpy.ndarray
        Унікальні значення цільової змінної (заповнюється після ``fit``).

    See Also
    --------
    classifiers.hyperparam_tuning.space_gam :
        Простір гіперпараметрів для CMA-ES tuning.

    Examples
    --------
    >>> from sklearn.datasets import make_classification
    >>> X, y = make_classification(n_samples=200, n_features=5, random_state=0)
    >>> clf = GAMClassifier(n_knots=8, C=2.0).fit(X, y)
    >>> proba = clf.predict_proba(X[:3])
    >>> proba.shape
    (3, 2)
    """

    def __init__(
        self,
        n_knots: int = 5,
        degree: int = 3,
        C: float = 1.0,
        knots: str = "uniform",
        max_iter: int = 500,
        random_state: Optional[int] = 42,
    ):
        self.n_knots = n_knots
        self.degree = degree
        self.C = C
        self.knots = knots
        self.max_iter = max_iter
        self.random_state = random_state

    def fit(self, X, y):
        """Навчити пайплайн ``Spline → LogReg`` на ``(X, y)``.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Числові ознаки (після препроцесингу).
        y : array-like of shape (n_samples,)
            Цільова змінна (бінарна або мультикласова).

        Returns
        -------
        self : GAMClassifier
            Навчений класифікатор.
        """
        self._pipeline = Pipeline([
            ("splines", SplineTransformer(
                degree=int(self.degree),
                n_knots=int(self.n_knots),
                knots=self.knots,
                include_bias=False,
            )),
            ("logreg", LogisticRegression(
                C=float(self.C),
                max_iter=int(self.max_iter),
                random_state=self.random_state,
                solver="lbfgs",
            )),
        ])
        self._pipeline.fit(X, y)
        self.classes_ = self._pipeline.named_steps["logreg"].classes_
        return self

    def predict(self, X):
        """Спрогнозувати мітки класів для ``X``.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)

        Returns
        -------
        numpy.ndarray of shape (n_samples,)
            Прогнозовані мітки з ``self.classes_``.
        """
        return self._pipeline.predict(X)

    def predict_proba(self, X):
        """Ймовірності класів для ``X``.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)

        Returns
        -------
        numpy.ndarray of shape (n_samples, n_classes)
            Рядки сумуються до 1.
        """
        return self._pipeline.predict_proba(X)
