"""Інтеграція з MLflow для логування метрик і артефактів."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import mlflow


def _stringify(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


@contextmanager
def run(experiment: str, run_name: str, tracking_uri: Optional[str] = None):
    """Один MLflow-запуск як context-manager."""
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=run_name) as active:
        yield active


def log_params(params: dict) -> None:
    mlflow.log_params(_stringify(params))


def log_metrics(metrics: dict, step: Optional[int] = None) -> None:
    safe = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
    if step is None:
        mlflow.log_metrics(safe)
    else:
        for k, v in safe.items():
            mlflow.log_metric(k, v, step=step)


def log_json(name: str, data: dict, tmp_dir: Optional[Path] = None) -> None:
    tmp = tmp_dir or Path.cwd() / ".mlflow_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    mlflow.log_artifact(str(path))


def log_text(name: str, text: str, tmp_dir: Optional[Path] = None) -> None:
    tmp = tmp_dir or Path.cwd() / ".mlflow_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / name
    path.write_text(text, encoding="utf-8")
    mlflow.log_artifact(str(path))
