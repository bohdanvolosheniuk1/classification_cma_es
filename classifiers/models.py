"""Фабрики базових класифікаторів.

Кожна функція ``make_*`` приймає опціональні ``**kwargs`` (передаються
напряму до конструктора sklearn-моделі) і повертає **необучений**
естіматор. Default-параметри підібрані для стабільної роботи на трьох
датасетах проекту.

Усі моделі сумісні з sklearn API: ``fit(X, y)``, ``predict(X)``,
``predict_proba(X)``.

Реєстр :data:`BASE_MODELS` дозволяє вибрати модель за рядковим ім'ям —
використовується pipeline'ом і CLI.
"""

from __future__ import annotations

from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC

from .gam import GAMClassifier


def make_logreg(**kwargs) -> LogisticRegression:
    """Логістична регресія (sklearn).

    Defaults: ``max_iter=1000``, ``random_state=42``. Підходить як
    бейзлайн для бінарних і мультикласових задач (multinomial).
    """
    params = dict(max_iter=1000, random_state=42)
    params.update(kwargs)
    return LogisticRegression(**params)


def make_svm(**kwargs) -> SVC:
    """SVM з RBF-ядром (sklearn).

    Defaults: ``C=1.0``, ``kernel="rbf"``, ``probability=True``,
    ``random_state=42``.

    Параметр ``probability=True`` потрібен для коректного обчислення
    AUC (виклик ``predict_proba``), але робить ``fit`` помітно
    повільнішим — особливо на великих датасетах.
    """
    params = dict(C=1.0, kernel="rbf", probability=True, random_state=42)
    params.update(kwargs)
    return SVC(**params)


def make_knn(**kwargs) -> KNeighborsClassifier:
    """k-найближчих сусідів (sklearn).

    Defaults: ``n_neighbors=5``, ``n_jobs=-1`` (всі ядра). Не "навчається"
    — лише запам'ятовує тренувальні точки. Чутлива до масштабу ознак,
    тому обов'язковий ``StandardScaler`` у препроцесорі.
    """
    params = dict(n_neighbors=5, n_jobs=-1)
    params.update(kwargs)
    return KNeighborsClassifier(**params)


def make_mlp(**kwargs) -> MLPClassifier:
    """Багатошарова нейронна мережа (sklearn).

    Defaults: два приховані шари ``(64, 32)``, ``max_iter=300``,
    ``early_stopping=True``, ``random_state=42``. Навчається методом
    зворотного поширення (gradient descent).
    """
    params = dict(
        hidden_layer_sizes=(64, 32),
        max_iter=300,
        random_state=42,
        early_stopping=True,
    )
    params.update(kwargs)
    return MLPClassifier(**params)


def make_gam(**kwargs) -> GAMClassifier:
    """Узагальнена адитивна модель (GAM).

    Defaults: ``n_knots=5``, ``degree=3``, ``C=1.0``. Це власна реалізація
    GAM поверх sklearn (B-сплайни + LogisticRegression) — див.
    :class:`classifiers.gam.GAMClassifier` і розділ 1 диплома.
    """
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
"""Реєстр фабрик базових моделей. Ключі використовуються у CLI
(``--models logreg,svm,...``) і в Streamlit-дашборді.

Не включає ``cma_classic`` / ``cma_mixture`` (вони у
:mod:`classifiers.cma_nn`) і ``tuned_*`` (формуються динамічно
у :mod:`classifiers.pipeline`).
"""
