"""Основний скрипт експерименту.

Завантажує датасет, проводить препроцесинг, ділить train/test,
запускає k-fold для кожної моделі, логує у MLflow.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from contextlib import nullcontext
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from classifiers import tracking
from classifiers.cma_nn import CMAESNeuralNet
from classifiers.crossval import kfold_evaluate, split_train_test
from classifiers.data import load_dataset
from classifiers.hyperparam_tuning import SPACES, tune_with_cma
from classifiers.metrics import aggregate_folds, compute_metrics
from classifiers.models import make_knn, make_logreg, make_mlp, make_svm
from classifiers.preprocessing import build_preprocessor, encode_target


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


def evaluate_factory(
    factory: Callable,
    X_tr, y_tr, X_te, y_te,
    task: str,
    folds: int,
) -> dict:
    """K-fold CV на train + фінальна оцінка на test."""
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
    return {"cv": cv, "test": test, "fit_time": fit_time}


def evaluate_tuned(
    name: str,
    base_factory: Callable,
    space_fn: Callable,
    X_tr, y_tr, X_te, y_te,
    task: str,
    folds: int,
    cma_iter: int,
) -> dict:
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

    res = evaluate_factory(tuned_factory, X_tr, y_tr, X_te, y_te, task, folds)
    res["best_params"] = best_params
    res["tune_score"] = best_score
    res["tune_time"] = tune_time
    return res


def run_one_model(
    name: str,
    X_tr, y_tr, X_te, y_te,
    task: str,
    folds: int,
    cma_iter: int,
) -> dict:
    if name in BASE_FACTORIES:
        return evaluate_factory(BASE_FACTORIES[name], X_tr, y_tr, X_te, y_te, task, folds)
    if name == "cma_classic":
        return evaluate_factory(
            make_cma_factory("classic", cma_iter),
            X_tr, y_tr, X_te, y_te, task, folds,
        )
    if name == "cma_mixture":
        return evaluate_factory(
            make_cma_factory("mixture", cma_iter, n_components=3),
            X_tr, y_tr, X_te, y_te, task, folds,
        )
    if name.startswith("tuned_"):
        base = name.split("_", 1)[1]
        if base not in BASE_FACTORIES:
            raise ValueError(f"для {name} немає базової моделі {base}")
        return evaluate_tuned(
            name, BASE_FACTORIES[base], SPACES[base],
            X_tr, y_tr, X_te, y_te, task, folds, cma_iter,
        )
    raise ValueError(f"невідома модель: {name}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Експеримент порівняння класифікаторів")
    p.add_argument("--dataset", required=True,
                   choices=["phiusiil", "steel_plate", "loan_approval"])
    p.add_argument("--models", default="all", help="csv або 'all'")
    p.add_argument("--folds", type=int, default=5)
    p.add_argument("--sample", type=int, default=None,
                   help="підсемплити датасет до N рядків")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--cma-iter", type=int, default=60)
    p.add_argument("--experiment", default="classification_cma_es")
    p.add_argument("--mlflow-uri", default=None)
    p.add_argument("--no-mlflow", action="store_true")
    p.add_argument("--no-tuning", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    np.random.seed(args.seed)

    print(f"=== {args.dataset} ===")
    ds = load_dataset(args.dataset)
    print(ds)

    X = ds.X
    y = ds.y
    if args.sample is not None and len(X) > args.sample:
        rng = np.random.default_rng(args.seed)
        idx = rng.choice(len(X), size=args.sample, replace=False)
        X = X.iloc[idx].reset_index(drop=True)
        y = y.iloc[idx].reset_index(drop=True)
        print(f"  ↪ підсемпл до {args.sample}")

    pre = build_preprocessor(X)
    X_arr = pre.fit_transform(X)
    y_arr, classes = encode_target(y)
    print(f"  X shape: {X_arr.shape}, класів: {len(classes)}")

    X_tr, X_te, y_tr, y_te = split_train_test(
        X_arr, y_arr, test_size=0.2, random_state=args.seed,
    )

    models = ALL_MODELS if args.models == "all" else args.models.split(",")
    if args.no_tuning:
        models = [m for m in models if not m.startswith("tuned_")]
    print(f"  моделей: {models}")

    use_mlflow = not args.no_mlflow
    results = []

    for m in models:
        print(f"\n-- {m} --")
        if use_mlflow:
            cm = tracking.run(args.experiment, f"{args.dataset}_{m}",
                              tracking_uri=args.mlflow_uri)
        else:
            cm = nullcontext()

        with cm:
            if use_mlflow:
                tracking.log_params({
                    "dataset": args.dataset,
                    "model": m,
                    "n_train": int(X_tr.shape[0]),
                    "n_test": int(X_te.shape[0]),
                    "n_features": int(X_tr.shape[1]),
                    "n_classes": int(len(classes)),
                    "task": ds.task,
                    "folds": args.folds,
                    "sample_limit": args.sample if args.sample else "none",
                    "cma_iter": args.cma_iter,
                    "seed": args.seed,
                })
            try:
                r = run_one_model(m, X_tr, y_tr, X_te, y_te,
                                  ds.task, args.folds, args.cma_iter)
            except Exception as e:
                print(f"  ПОМИЛКА: {e}", file=sys.stderr)
                traceback.print_exc()
                if use_mlflow:
                    tracking.log_params({"error": str(e)[:250]})
                continue

            r["model"] = m
            results.append(r)

            tm = r["test"]
            cv = r["cv"]
            print(
                f"  test: acc={tm['accuracy']:.4f}  f1={tm['f1']:.4f}  "
                f"auc={tm['auc']:.4f}  (fit {r['fit_time']:.1f}s)"
            )
            print(
                f"  cv  : f1_mean={cv.get('f1_mean', float('nan')):.4f} "
                f"f1_std={cv.get('f1_std', float('nan')):.4f}"
            )

            if use_mlflow:
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

    print("\n=== підсумок ===")
    if results:
        rows = []
        for r in results:
            rows.append({
                "model": r["model"],
                "acc": r["test"]["accuracy"],
                "f1": r["test"]["f1"],
                "auc": r["test"]["auc"],
                "cv_f1_mean": r["cv"].get("f1_mean", float("nan")),
                "fit_time_s": r["fit_time"],
            })
        df = pd.DataFrame(rows)
        print(df.to_string(index=False))

        out_dir = Path("results") / args.dataset
        out_dir.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_dir / "summary.csv", index=False)
        print(f"\nЗбережено: {out_dir / 'summary.csv'}")
    else:
        print("  жодна модель не виконалась успішно")

    return 0


if __name__ == "__main__":
    sys.exit(main())
