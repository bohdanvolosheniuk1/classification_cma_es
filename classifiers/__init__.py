"""Програмна частина дипломної роботи.

Пакет реалізує порівняльне дослідження класифікаторів на трьох
сучасних наборах даних із застосуванням двох технік, описаних
у теоретичній частині диплома:

* **GAM** (узагальнені адитивні моделі, розділ 1) — реалізовано
  в :mod:`classifiers.gam` через ``SplineTransformer + LogisticRegression``.
* **CMA-ES** (еволюційна стратегія з адаптацією коваріаційної матриці,
  розділ 2) — класичний варіант у :mod:`classifiers.cma_es` (обгортка
  над пакетом ``cma``) і розширений зі сумішами нормальних розподілів
  у :mod:`classifiers.mixture_cma_es` (за дисертацією Літвінчук Ю.А., 2024).

Точка входу для запуску експерименту — :func:`classifiers.pipeline.run_experiment`.

Examples
--------
Завантажити датасет і запустити одну модель::

    from classifiers.data import load_dataset
    from classifiers.crossval import split_train_test, kfold_evaluate
    from classifiers.models import make_logreg
    from classifiers.preprocessing import build_preprocessor, encode_target

    ds = load_dataset("phiusiil")
    X = build_preprocessor(ds.X).fit_transform(ds.X)
    y, classes = encode_target(ds.y)
    X_tr, X_te, y_tr, y_te = split_train_test(X, y)
    folds = kfold_evaluate(make_logreg, X_tr, y_tr, n_splits=5, task="binary")

Запустити повний експеримент у одну команду::

    from classifiers.pipeline import run_experiment
    results, info = run_experiment(
        dataset="loan_approval",
        models=["logreg", "gam", "cma_mixture", "tuned_gam"],
        sample=5000, folds=5,
    )
"""

__version__ = "0.1.0"
__all__ = ["__version__"]
