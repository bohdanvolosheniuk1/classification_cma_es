"""Інтеграція з MLflow для трекінгу експериментів.

Куратор просив можливість завантаження метрик і артефактів на MLflow
або іншу платформу. Цей модуль надає тонкий шар над ``mlflow`` API,
що автоматично:

* стрингує не-примітивні значення (numpy типи, кортежі тощо) перед
  записом — щоб MLflow не падав на ``log_params``;
* фільтрує не-числові поля з метрик;
* надає зручний context-manager :func:`run` для одного запуску.

Базова схема використання::

    from classifiers import tracking

    with tracking.run(experiment="my_exp", run_name="logreg_baseline"):
        tracking.log_params({"dataset": "phiusiil", "folds": 5})
        tracking.log_metrics({"test_f1": 0.99, "test_auc": 1.0})
        tracking.log_json("config.json", {"sample": 5000})

За замовчуванням MLflow пише у локальну теку ``./mlruns/``. Перегляд —
``mlflow ui`` або через лаунчер ``run_mlflow.bat``.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import mlflow


def _stringify(d: dict) -> dict:
    """Привести значення до типів, які MLflow приймає у ``log_params``.

    Примітиви (int/float/str/bool/None) залишаються як є,
    решта — стрингується через ``str()``.
    """
    out = {}
    for k, v in d.items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)
    return out


@contextmanager
def run(experiment: str, run_name: str, tracking_uri: Optional[str] = None):
    """Створити MLflow-запуск як context-manager.

    Parameters
    ----------
    experiment : str
        Ім'я MLflow-експерименту (групи запусків). Створюється
        автоматично якщо не існує.
    run_name : str
        Ім'я конкретного запуску всередині експерименту.
    tracking_uri : str, optional
        URI MLflow-сервера. ``None`` — локальний ``./mlruns/``.

    Yields
    ------
    mlflow.ActiveRun
        Активний запуск MLflow (для прямого використання його API).

    Examples
    --------
    >>> with run("test_exp", "trial_1"):  # doctest: +SKIP
    ...     log_params({"lr": 0.01})
    ...     log_metrics({"loss": 0.5})
    """
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    with mlflow.start_run(run_name=run_name) as active:
        yield active


def log_params(params: dict) -> None:
    """Залогувати гіперпараметри (стрингує non-primitive значення).

    Parameters
    ----------
    params : dict
        Назва -> значення. Numpy типи, кортежі тощо автоматично
        перетворюються на рядки.
    """
    mlflow.log_params(_stringify(params))


def log_metrics(metrics: dict, step: Optional[int] = None) -> None:
    """Залогувати числові метрики.

    Не-числові поля ігноруються (MLflow вимагає float).

    Parameters
    ----------
    metrics : dict
        Назва метрики -> float.
    step : int, optional
        Номер кроку для тимчасових серій (наприклад, ітерація навчання).
        ``None`` — точкове логування без кроку.
    """
    safe = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
    if step is None:
        mlflow.log_metrics(safe)
    else:
        for k, v in safe.items():
            mlflow.log_metric(k, v, step=step)


def log_json(name: str, data: dict, tmp_dir: Optional[Path] = None) -> None:
    """Зберегти dict як JSON-файл у артефактах MLflow.

    Parameters
    ----------
    name : str
        Ім'я файлу всередині артефактів (наприклад, ``"config.json"``).
    data : dict
        Дані для серіалізації.
    tmp_dir : pathlib.Path, optional
        Тимчасова тека. За замовчуванням — ``./.mlflow_tmp/``.
    """
    tmp = tmp_dir or Path.cwd() / ".mlflow_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    mlflow.log_artifact(str(path))


def log_text(name: str, text: str, tmp_dir: Optional[Path] = None) -> None:
    """Зберегти текстовий файл у артефактах MLflow.

    Зручно для пояснень, README запуску, текстових логів.

    Parameters
    ----------
    name : str
        Ім'я файлу.
    text : str
        Вміст.
    tmp_dir : pathlib.Path, optional
        Тимчасова тека.
    """
    tmp = tmp_dir or Path.cwd() / ".mlflow_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / name
    path.write_text(text, encoding="utf-8")
    mlflow.log_artifact(str(path))
