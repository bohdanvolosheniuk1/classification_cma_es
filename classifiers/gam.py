"""Узагальнена адитивна модель (GAM) для класифікації.

Базується на матеріалі розділу 1 дипломної роботи:
кожна неперервна ознака проходить через сплайнове базисне перетворення
(B-сплайни), потім результат подається в LogisticRegression. Така
конструкція еквівалентна узагальненій адитивній моделі з логіт-зв'язком
(розділ 1.6 диплома) і параметризується:

  k         — кількість вузлів сплайну (control over flexibility);
  degree    — степінь сплайну (3 для класичних кубічних);
  C = 1/λ   — обернений параметр згладжування (L2-штраф LogisticRegression
              грає роль штрафу за надмірну складність функції, розд. 1.5).

Класифікатор сумісний зі sklearn API (fit/predict/predict_proba).
Реалізовано без зовнішніх залежностей (тільки sklearn).
"""

from __future__ import annotations

from typing import Optional

from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import SplineTransformer


class GAMClassifier(BaseEstimator, ClassifierMixin):
    """GAM для класифікації: B-сплайни на кожну ознаку + LogReg."""

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
        return self._pipeline.predict(X)

    def predict_proba(self, X):
        return self._pipeline.predict_proba(X)
