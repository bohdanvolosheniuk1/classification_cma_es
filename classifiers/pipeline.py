"""Логіка експерименту, спільна для CLI та Streamlit UI."""

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
from .models import make_knn, make_logreg, make_mlp, make_svm
from .preprocessing import build_preprocessor, encode_target


DATASETS = ["phiusiil", "steel_plate", "loan_approval"]

ALL_MODELS = [
    "logreg", "svm", "knn", "mlp",
    "cma_classic", "cma_mixture",
    "tuned_logreg", "tuned_svm", "tuned_knn", "tuned_mlp",
]

BASE_FACTORIES = {
    "logreg": make_logreg,
    "svm": make_svm,
    "knn": make_knn,
    "mlp": make_mlp,
}


def make_cma_factory(method: str, max_iter: int, n_components: int = 3) -> Callable:
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
    """Завантажує, препроцесить, ділить train/test. Повертає всі важливі шматки."""
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
    on_model_start: Optional[Callable[[str, int, int], None]] = None,
    on_model_done: Optional[Callable[[str, dict], None]] = None,
    on_model_error: Optional[Callable[[str, Exception], None]] = None,
) -> tuple[list[dict], dict]:
    """Виконує експеримент. Повертає (results, dataset_info).

    Колбеки on_model_start/on_model_done/on_model_error використовуються
    для відображення прогресу в UI (Streamlit) або в CLI.
    """
    np.random.seed(seed)

    X_tr, X_te, y_tr, y_te, info = prepare_data(dataset, sample=sample, seed=seed)
    task = info["task"]
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
