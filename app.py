"""Streamlit-дашборд для запуску і перегляду експериментів."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from classifiers.pipeline import (
    ALL_MODELS, DATASETS, prepare_data, results_to_table, run_experiment,
)


# куди скидаємо проміжний стан — щоб після розриву websocket рефреш
# сторінки відновив останні результати
STATE_FILE = Path("results") / "_last_run.json"


def _save_state(results: list[dict], info: dict, config: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    def safe(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.integer, np.floating)):
            return o.item()
        return o
    payload = {
        "results": [
            {k: ([safe(x) for x in v] if isinstance(v, list) else safe(v))
             for k, v in r.items()}
            for r in results
        ],
        "info": {k: safe(v) for k, v in info.items()},
        "config": {k: safe(v) for k, v in config.items()},
        "ts": time.time(),
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, default=str),
                          encoding="utf-8")


def _load_state() -> Optional[dict]:
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


st.set_page_config(
    page_title="classification_cma_es",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Порівняння класифікаторів з розширеним CMA-ES")
st.caption(
    "Практична частина дипломної роботи. Дані: PhiUSIIL / Steel Plate / "
    "Loan Approval. Метод #5 — NN, що навчається CMA-ES."
)


# ----- sidebar: налаштування -------------------------------------------------

with st.sidebar:
    st.header("Конфігурація")

    dataset = st.selectbox("Датасет", DATASETS, index=0)

    default_models = ["logreg", "svm", "knn", "mlp", "cma_classic", "cma_mixture"]
    models = st.multiselect(
        "Моделі", ALL_MODELS, default=default_models,
        help="tuned_* — базова модель з гіперпараметрами, підібраними CMA-ES",
    )

    folds = st.slider("k у k-fold CV", 3, 10, 5)

    use_sample = st.checkbox("Підсемплити датасет", value=True,
                             help="Для PhiUSIIL обовʼязково — на повних 235K SVM довго")
    sample_value = st.number_input(
        "Розмір вибірки", min_value=500, max_value=200000,
        value=5000, step=500, disabled=not use_sample,
    )
    sample = int(sample_value) if use_sample else None

    cma_iter = st.slider("Ітерації CMA-ES", 15, 120, 30)

    use_mlflow = st.checkbox("Логувати в MLflow", value=False)

    seed = st.number_input("Random seed", value=42, step=1)

    run_btn = st.button("Запустити", type="primary", use_container_width=True)


# ----- session state ---------------------------------------------------------

if "results" not in st.session_state:
    # відновлюємо з диска, якщо є — після рефреша або розриву websocket
    persisted = _load_state()
    if persisted is not None:
        st.session_state["results"] = persisted.get("results")
        st.session_state["info"] = persisted.get("info")
        st.session_state["config"] = persisted.get("config")
    else:
        st.session_state["results"] = None
        st.session_state["info"] = None
        st.session_state["config"] = None


# ----- show dataset preview --------------------------------------------------

with st.expander(f"Інформація про датасет: {dataset}", expanded=False):
    try:
        _, _, _, _, info_preview = prepare_data(dataset, sample=sample, seed=int(seed))
        st.json(info_preview)
    except FileNotFoundError as e:
        st.warning(
            f"Файл датасету не знайдено. Спочатку завантажте: "
            f"`python scripts/download.py --dataset {dataset}`."
        )
        st.text(str(e))
    except Exception as e:
        st.error(f"Помилка: {e}")


# ----- run experiment --------------------------------------------------------

if run_btn:
    if not models:
        st.error("Виберіть хоча б одну модель")
        st.stop()

    progress = st.progress(0.0, text="Підготовка...")
    log_area = st.empty()
    log_lines: list[str] = []
    partial_results: list[dict] = []
    cur_config = {
        "dataset": dataset, "sample": sample, "folds": folds,
        "cma_iter": cma_iter, "seed": int(seed),
    }
    cur_info_holder = {"info": None}

    def on_start(name: str, i: int, total: int):
        progress.progress((i - 1) / total, text=f"[{i}/{total}] {name}...")
        log_lines.append(f"▶ {name}")
        log_area.code("\n".join(log_lines))

    def on_done(name: str, r: dict):
        tm = r["test"]
        cv = r["cv"]
        log_lines[-1] = (
            f"✓ {name}: acc={tm['accuracy']:.4f} f1={tm['f1']:.4f} "
            f"auc={tm['auc']:.4f} (fit {r['fit_time']:.1f}s)"
        )
        log_area.code("\n".join(log_lines))
        # копія результату для збереження на диск
        snapshot = dict(r)
        snapshot["model"] = name
        partial_results.append(snapshot)
        if cur_info_holder["info"] is not None:
            _save_state(partial_results, cur_info_holder["info"], cur_config)

    def on_error(name: str, e: Exception):
        log_lines[-1] = f"✗ {name}: ПОМИЛКА {e}"
        log_area.code("\n".join(log_lines))

    def on_ready(info: dict):
        cur_info_holder["info"] = info

    t0 = time.time()
    try:
        results, info = run_experiment(
            dataset=dataset,
            models=models,
            sample=sample,
            folds=folds,
            cma_iter=cma_iter,
            seed=int(seed),
            use_mlflow=use_mlflow,
            on_dataset_ready=on_ready,
            on_model_start=on_start,
            on_model_done=on_done,
            on_model_error=on_error,
        )
    except FileNotFoundError as e:
        st.error(
            f"Датасет не знайдено: {e}\n\n"
            f"Завантажте через `python scripts/download.py --dataset {dataset}`"
        )
        st.stop()

    elapsed = time.time() - t0
    progress.progress(1.0, text=f"Готово за {elapsed:.1f}с")

    st.session_state["results"] = results
    st.session_state["info"] = info
    st.session_state["config"] = cur_config
    # фінальний snapshot на диск
    _save_state(results, info, cur_config)


# ----- display results -------------------------------------------------------

results = st.session_state["results"]
info = st.session_state["info"]

if results:
    st.divider()

    cfg = st.session_state["config"] or {}
    info = info or {}
    cols = st.columns(5)
    cols[0].metric("Датасет", cfg.get("dataset", "?"))
    cols[1].metric("Train", info.get("n_train", "?"))
    cols[2].metric("Test", info.get("n_test", "?"))
    cols[3].metric("Ознак", info.get("n_features", "?"))
    cols[4].metric("Класів", info.get("n_classes", "?"))

    df = pd.DataFrame(results_to_table(results))

    st.subheader("Метрики")

    show_cols = ["model", "test_accuracy", "test_f1", "test_auc",
                 "cv_f1_mean", "cv_f1_std", "fit_time_s"]
    if "tune_time_s" in df.columns:
        show_cols.append("tune_time_s")
    display_df = df[show_cols].copy()

    styled = display_df.style.format({
        "test_accuracy": "{:.4f}", "test_f1": "{:.4f}", "test_auc": "{:.4f}",
        "cv_f1_mean": "{:.4f}", "cv_f1_std": "{:.4f}",
        "fit_time_s": "{:.2f}",
        "tune_time_s": "{:.2f}" if "tune_time_s" in show_cols else None,
    }).background_gradient(
        subset=["test_accuracy", "test_f1", "test_auc"],
        cmap="Greens", vmin=0.5, vmax=1.0,
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # завантаження CSV
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Завантажити CSV", data=csv_bytes,
        file_name=f"summary_{cfg.get('dataset', 'x')}.csv",
        mime="text/csv",
    )

    # ----- charts -----------------------------------------------------------

    st.subheader("Метрики на тесті")
    chart_df = df[["model", "test_accuracy", "test_f1", "test_auc"]].melt(
        id_vars="model", var_name="metric", value_name="value",
    )
    chart_df["metric"] = chart_df["metric"].str.replace("test_", "")
    bar = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("model:N", sort=None, title="Модель"),
            y=alt.Y("value:Q", scale=alt.Scale(domain=[0, 1.01]), title="Значення"),
            color=alt.Color("metric:N", title="Метрика"),
            xOffset=alt.XOffset("metric:N"),
            tooltip=["model", "metric", alt.Tooltip("value:Q", format=".4f")],
        )
        .properties(height=350)
    )
    st.altair_chart(bar, use_container_width=True)

    st.subheader("Час навчання")
    time_chart = (
        alt.Chart(df)
        .mark_bar(color="#888")
        .encode(
            x=alt.X("model:N", sort=None),
            y=alt.Y("fit_time_s:Q", title="Час, с"),
            tooltip=["model", alt.Tooltip("fit_time_s:Q", format=".2f")],
        )
        .properties(height=250)
    )
    st.altair_chart(time_chart, use_container_width=True)

    # ----- CMA convergence --------------------------------------------------

    cma_results = [r for r in results if "history" in r]
    if cma_results:
        st.subheader("Збіжність CMA-ES")
        rows = []
        for r in cma_results:
            for it, val in enumerate(r["history"]):
                rows.append({"model": r["model"], "iter": it, "loss": val})
        conv_df = pd.DataFrame(rows)
        conv_chart = (
            alt.Chart(conv_df)
            .mark_line()
            .encode(
                x=alt.X("iter:Q", title="Ітерація"),
                y=alt.Y("loss:Q", title="Найкраще значення (cross-entropy)"),
                color=alt.Color("model:N"),
                tooltip=["model", "iter", alt.Tooltip("loss:Q", format=".4f")],
            )
            .properties(height=300)
        )
        st.altair_chart(conv_chart, use_container_width=True)

    if use_mlflow:
        st.info("Метрики залоговано в MLflow. Перегляд: `mlflow ui` у корені проекту.")

else:
    st.info("Натисніть **Запустити** у бічній панелі, щоб провести експеримент.")
