"""CLI для пайплайну експерименту."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Windows console — щоб не падало на українській
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd

from classifiers.pipeline import (
    ALL_MODELS, DATASETS, results_to_table, run_experiment,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Експеримент порівняння класифікаторів")
    p.add_argument("--dataset", required=True, choices=DATASETS)
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


def _on_start(name: str, i: int, total: int):
    print(f"\n[{i}/{total}] {name}")


def _on_done(name: str, r: dict):
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


def _on_error(name: str, e: Exception):
    print(f"  ПОМИЛКА: {e}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    models = ALL_MODELS if args.models == "all" else args.models.split(",")
    if args.no_tuning:
        models = [m for m in models if not m.startswith("tuned_")]

    print(f"=== {args.dataset} ===  моделей: {len(models)}")

    results, info = run_experiment(
        dataset=args.dataset,
        models=models,
        sample=args.sample,
        folds=args.folds,
        cma_iter=args.cma_iter,
        seed=args.seed,
        use_mlflow=(not args.no_mlflow),
        experiment_name=args.experiment,
        mlflow_uri=args.mlflow_uri,
        on_model_start=_on_start,
        on_model_done=_on_done,
        on_model_error=_on_error,
    )

    print(f"\nDataset: {info}")
    print("\n=== підсумок ===")
    if not results:
        print("  жодна модель не виконалась успішно")
        return 1

    rows = results_to_table(results)
    df = pd.DataFrame(rows)[
        ["model", "test_accuracy", "test_f1", "test_auc", "cv_f1_mean", "fit_time_s"]
    ]
    print(df.to_string(index=False))

    out_dir = Path("results") / args.dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_dir / "summary.csv", index=False)
    print(f"\nЗбережено: {out_dir / 'summary.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
