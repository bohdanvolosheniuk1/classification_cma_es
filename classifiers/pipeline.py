"""Оркестратор експерименту — спільна логіка для CLI і Streamlit.

Центральна функція :func:`run_experiment` бере назву датасету і список
моделей, проганяє повний пайплайн:

1. :func:`prepare_data` — завантаження, препроцесинг, train/test split;
2. для кожної моделі — :func:`run_one_model` — k-fold CV на train +
   фінальна оцінка на test, опційно з MLflow-логуванням;
3. колбеки ``on_dataset_ready`` / ``on_model_start`` / ``on_model_done`` /
   ``on_model_error`` — для UI-прогресу.

Звідси викликаються і :mod:`scripts.run_experiment` (CLI), і :mod:`app`
(Streamlit GUI) — спільна точка ділить логіку без дублювання.
"""

from __future__ import annotations

import time
import traceback
from contextlib import nullcontext
from typing import Callable, Optional

import numpy as np

from . import tracking
from .cma_nn import CMAESNeuralNet
from .crossval import kfold_evaluate, split_train_test
from .data import load_dataset
from .hyperparam_tuning import SPACES, tune_with_cma
from .metrics import aggregate_folds, compute_metrics
from .models import make_gam, make_knn, make_logreg, make_mlp, make_svm
from .preprocessing import build_preprocessor, encode_target


DATASETS = ["phiusiil", "steel_plate", "loan_approval"]
"""Доступні датасети — ключі для :func:`classifiers.data.load_dataset`."""

ALL_MODELS = [
    "logreg", "svm", "knn", "mlp", "gam",
    "cma_classic", "cma_mixture",
    "tuned_logreg", "tuned_svm", "tuned_knn", "tuned_mlp", "tuned_gam",
]
"""Усі моделі, які підтримує pipeline.

* ``logreg``, ``svm``, ``knn``, ``mlp``, ``gam`` — базові
  (фабрики у :data:`BASE_FACTORIES`);
* ``cma_classic`` / ``cma_mixture`` — нейромережа, навчена CMA-ES
  (див. :class:`classifiers.cma_nn.CMAESNeuralNet`);
* ``tuned_*`` — базова модель + CMA-ES tuning гіперпараметрів
  (див. :mod:`classifiers.hyperparam_tuning`).
"""

BASE_FACTORIES = {
    "logreg": make_logreg,
    "svm": make_svm,
    "knn": make_knn,
    "mlp": make_mlp,
    "gam": make_gam,
}
"""Реєстр фабрик базових моделей. Аналог :data:`classifiers.models.BASE_MODELS`."""


def make_cma_factory(method: str, max_iter: int, n_components: int = 3) -> Callable:
    """Створити фабрику CMA-ES-нейромережі з відповідним режимом.

    Default-параметри (hidden=8, max_features=20, max_train_samples=3000)
    підібрані для компромісу між якістю та швидкістю на 3 датасетах
    проекту.

    Parameters
    ----------
    method : {"classic", "mixture"}
        Тип CMA-ES.
    max_iter : int
        Ліміт ітерацій оптимізатора.
    n_components : int, default=3
        Кількість піків (тільки для ``mixture``).

    Returns
    -------
    callable
        Фабрика без аргументів, що повертає новий
        :class:`classifiers.cma_nn.CMAESNeuralNet`.
    """
    def factory():
        return CMAESNeuralNet(
            hidden_layer_sizes=(8,),
            method=method,
            n_components=n_components,
            adaptive=(method == "mixture"),
            max_iter=max_iter,
            max_features=20,
            max_train_samples=3000,
            random_state=42,
        )
    return factory


def _evaluate_factory(factory, X_tr, y_tr, X_te, y_te, task, folds):
    folds_data = kfold_evaluate(factory, X_tr, y_tr, n_splits=folds, task=task)
    cv = aggregate_folds(folds_data)

    t0 = time.time()
    model = factory()
    model.fit(X_tr, y_tr)
    fit_time = time.time() - t0

    y_pred = model.predict(X_te)
    y_proba = None
    if hasattr(model, "predict_proba"):
        try:
            y_proba = np.asarray(model.predict_proba(X_te))
        except Exception:
            y_proba = None
    test = compute_metrics(y_te, y_pred, y_proba=y_proba, task=task)

    out = {"cv": cv, "test": test, "fit_time": fit_time}
    # для CMA-моделей збираємо історію збіжності, якщо є
    if hasattr(model, "history_"):
        out["history"] = list(model.history_)
    return out


def _evaluate_tuned(base_factory, space_fn, X_tr, y_tr, X_te, y_te,
                    task, folds, cma_iter):
    scoring = "f1_weighted" if task == "multiclass" else "f1"

    t0 = time.time()
    best_params, best_score, _ = tune_with_cma(
        base_factory, space_fn(),
        X_tr, y_tr,
        cv=3, scoring=scoring,
        method="classic",
        max_iter=max(10, cma_iter // 3),
        pop_size=8,
    )
    tune_time = time.time() - t0

    def tuned_factory():
        return base_factory(**best_params)

    res = _evaluate_factory(tuned_factory, X_tr, y_tr, X_te, y_te, task, folds)
    res["best_params"] = best_params
    res["tune_score"] = best_score
    res["tune_time"] = tune_time
    return res


def run_one_model(name: str, X_tr, y_tr, X_te, y_te,
                  task: str, folds: int, cma_iter: int) -> dict:
    """Запустити одну модель за іменем — k-fold CV + фінальна оцінка на test.

    Parameters
    ----------
    name : str
        Ім'я моделі з :data:`ALL_MODELS`.
    X_tr, y_tr, X_te, y_te : array-like
        Тренувальні і тестові дані (вже після препроцесингу і
        train/test split).
    task : {"binary", "multiclass"}
        Тип задачі.
    folds : int
        Кількість фолдів CV.
    cma_iter : int
        Ліміт ітерацій CMA-ES (для ``cma_*`` і ``tuned_*`` моделей).

    Returns
    -------
    dict
        З полями ``cv`` (агрегований mean/std по фолдах), ``test``
        (метрики на тесті), ``fit_time``. Для CMA-моделей додається
        ``history`` (крива збіжності), для ``tuned_*`` — ``best_params``,
        ``tune_score``, ``tune_time``.

    Raises
    ------
    ValueError
        Якщо ``name`` не міститься в :data:`ALL_MODELS`.
    """
    if name in BASE_FACTORIES:
        return _evaluate_factory(BASE_FACTORIES[name], X_tr, y_tr, X_te, y_te, task, folds)
    if name == "cma_classic":
        return _evaluate_factory(
            make_cma_factory("classic", cma_iter),
            X_tr, y_tr, X_te, y_te, task, folds,
        )
    if name == "cma_mixture":
        return _evaluate_factory(
            make_cma_factory("mixture", cma_iter, n_components=3),
            X_tr, y_tr, X_te, y_te, task, folds,
        )
    if name.startswith("tuned_"):
        base = name.split("_", 1)[1]
        if base not in BASE_FACTORIES:
            raise ValueError(f"для {name} немає базової моделі {base}")
        return _evaluate_tuned(
            BASE_FACTORIES[base], SPACES[base],
            X_tr, y_tr, X_te, y_te, task, folds, cma_iter,
        )
    raise ValueError(f"невідома модель: {name}")


def prepare_data(dataset_name: str, sample: Optional[int] = None,
                 seed: int = 42, test_size: float = 0.2):
    """Повний препроцесинг для одного датасету.

    Завантажує датасет → опційно семплить → запускає препроцесор →
    кодує цільову → ділить train/test.

    Parameters
    ----------
    dataset_name : {"phiusiil", "steel_plate", "loan_approval"}
        Ідентифікатор датасету.
    sample : int, optional
        Якщо задано і кількість рядків більша — випадково субсемплити
        датасет до цього розміру. Корисно для великих PhiUSIIL.
    seed : int, default=42
        Seed для семплування та split.
    test_size : float, default=0.2
        Частка тесту.

    Returns
    -------
    X_tr, X_te : numpy.ndarray
        Тренувальна / тестова матриці ознак (масштабовані, OHE).
    y_tr, y_te : numpy.ndarray
        Закодовані цільові змінні (цілі числа).
    info : dict
        Метадані: ``name``, ``task``, ``n_classes``, ``classes``,
        ``n_features``, ``n_train``, ``n_test``, ``sample_limit``.
        Передається в Streamlit-дашборд для відображення.
    """
    ds = load_dataset(dataset_name)
    X = ds.X
    y = ds.y
    if sample is not None and len(X) > sample:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(X), size=sample, replace=False)
        X = X.iloc[idx].reset_index(drop=True)
        y = y.iloc[idx].reset_index(drop=True)

    pre = build_preprocessor(X)
    X_arr = pre.fit_transform(X)
    y_arr, classes = encode_target(y)
    X_tr, X_te, y_tr, y_te = split_train_test(
        X_arr, y_arr, test_size=test_size, random_state=seed,
    )
    info = {
        "name": ds.name,
        "task": ds.task,
        "n_classes": int(len(classes)),
        "classes": list(classes),
        "n_features": int(X_arr.shape[1]),
        "n_train": int(X_tr.shape[0]),
        "n_test": int(X_te.shape[0]),
        "sample_limit": sample,
    }
    return X_tr, X_te, y_tr, y_te, info


def run_experiment(
    dataset: str,
    models: list[str],
    sample: Optional[int] = None,
    folds: int = 5,
    cma_iter: int = 60,
    seed: int = 42,
    use_mlflow: bool = False,
    experiment_name: str = "classification_cma_es",
    mlflow_uri: Optional[str] = None,
    on_dataset_ready: Optional[Callable[[dict], None]] = None,
    on_model_start: Optional[Callable[[str, int, int], None]] = None,
    on_model_done: Optional[Callable[[str, dict], None]] = None,
    on_model_error: Optional[Callable[[str, Exception], None]] = None,
) -> tuple[list[dict], dict]:
    """Виконати повний експеримент: датасет → моделі → метрики.

    Це **центральна функція проекту**. Викликається і з CLI
    (``scripts/run_experiment.py``), і з Streamlit-дашборду (``app.py``).

    Parameters
    ----------
    dataset : {"phiusiil", "steel_plate", "loan_approval"}
        Ідентифікатор датасету.
    models : list of str
        Імена моделей з :data:`ALL_MODELS`.
    sample : int, optional
        Ліміт розміру вибірки (для прискорення на великих PhiUSIIL).
    folds : int, default=5
        Кількість фолдів k-fold CV.
    cma_iter : int, default=60
        Ліміт ітерацій CMA-ES.
    seed : int, default=42
        Глобальний seed для відтворюваності.
    use_mlflow : bool, default=False
        Якщо True — кожна модель буде окремим MLflow-запуском.
    experiment_name : str, default="classification_cma_es"
        Ім'я MLflow-експерименту (групи запусків).
    mlflow_uri : str, optional
        URI MLflow-сервера (None — локальний ``./mlruns/``).
    on_dataset_ready : callable, optional
        Колбек ``(info_dict) -> None``, спрацьовує після препроцесингу,
        перед запуском першої моделі. Streamlit використовує це щоб
        зберегти ``info`` на диск для recovery.
    on_model_start : callable, optional
        Колбек ``(name, i, total) -> None`` перед запуском моделі.
    on_model_done : callable, optional
        Колбек ``(name, result_dict) -> None`` після успішного запуску.
    on_model_error : callable, optional
        Колбек ``(name, exception) -> None`` при помилці.

    Returns
    -------
    results : list of dict
        Один dict на успішно виконану модель. Структура — як у
        :func:`run_one_model`.
    info : dict
        Метадані датасету (як у :func:`prepare_data`).

    Examples
    --------
    >>> results, info = run_experiment(  # doctest: +SKIP
    ...     dataset="phiusiil",
    ...     models=["logreg", "gam"],
    ...     sample=2000, folds=3, use_mlflow=False,
    ... )
    >>> info["task"]  # doctest: +SKIP
    'binary'
    """
    np.random.seed(seed)

    X_tr, X_te, y_tr, y_te, info = prepare_data(dataset, sample=sample, seed=seed)
    task = info["task"]
    if on_dataset_ready is not None:
        on_dataset_ready(info)
    results: list[dict] = []

    total = len(models)
    for i, m in enumerate(models, start=1):
        if on_model_start is not None:
            on_model_start(m, i, total)

        if use_mlflow:
            cm = tracking.run(experiment_name, f"{dataset}_{m}", tracking_uri=mlflow_uri)
        else:
            cm = nullcontext()

        with cm:
            if use_mlflow:
                tracking.log_params({
                    "dataset": dataset,
                    "model": m,
                    "n_train": info["n_train"],
                    "n_test": info["n_test"],
                    "n_features": info["n_features"],
                    "n_classes": info["n_classes"],
                    "task": task,
                    "folds": folds,
                    "sample_limit": sample if sample else "none",
                    "cma_iter": cma_iter,
                    "seed": seed,
                })
            try:
                r = run_one_model(m, X_tr, y_tr, X_te, y_te, task, folds, cma_iter)
            except Exception as e:
                traceback.print_exc()
                if on_model_error is not None:
                    on_model_error(m, e)
                if use_mlflow:
                    tracking.log_params({"error": str(e)[:250]})
                continue

            r["model"] = m
            results.append(r)

            if use_mlflow:
                tm = r["test"]
                cv = r["cv"]
                tracking.log_metrics({
                    "test_accuracy": tm["accuracy"],
                    "test_f1": tm["f1"],
                    "test_auc": tm["auc"],
                    "cv_f1_mean": cv.get("f1_mean", float("nan")),
                    "cv_f1_std": cv.get("f1_std", float("nan")),
                    "cv_accuracy_mean": cv.get("accuracy_mean", float("nan")),
                    "cv_auc_mean": cv.get("auc_mean", float("nan")),
                    "fit_time_s": r["fit_time"],
                })
                if "best_params" in r:
                    tracking.log_params({
                        f"best_{k}": v for k, v in r["best_params"].items()
                    })
                    tracking.log_metrics({"tune_time_s": r["tune_time"]})

            if on_model_done is not None:
                on_model_done(m, r)

    return results, info


def results_to_table(results: list[dict]) -> list[dict]:
    """Розгортає результати у плоский список dict (для DataFrame чи CSV)."""
    rows = []
    for r in results:
        tm = r["test"]
        cv = r["cv"]
        row = {
            "model": r["model"],
            "test_accuracy": tm["accuracy"],
            "test_f1": tm["f1"],
            "test_auc": tm["auc"],
            "cv_f1_mean": cv.get("f1_mean", float("nan")),
            "cv_f1_std": cv.get("f1_std", float("nan")),
            "cv_acc_mean": cv.get("accuracy_mean", float("nan")),
            "cv_auc_mean": cv.get("auc_mean", float("nan")),
            "fit_time_s": r["fit_time"],
        }
        if "tune_time" in r:
            row["tune_time_s"] = r["tune_time"]
        rows.append(row)
    return rows
