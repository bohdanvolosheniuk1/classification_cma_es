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


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_prepare(dataset: str, sample: Optional[int], seed: int):
    """Кешуємо завантаження датасету (1 година TTL) щоб preview/expander
    не перечитував CSV і не робив PCA при кожному русі слайдера."""
    return prepare_data(dataset, sample=sample, seed=seed)


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
        _, _, _, _, info_preview = _cached_prepare(dataset, sample, int(seed))
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

    # ----- основна таблиця з progress-барами ---------------------------------

    def _zoomed_range(vals: np.ndarray, pad: float = 0.02, min_span: float = 0.05):
        """Адаптивний діапазон [lo, hi] для ProgressColumn — щоб видно
        було різницю при значеннях ~1.0."""
        finite = vals[np.isfinite(vals)]
        if len(finite) == 0:
            return 0.0, 1.0
        lo = max(0.0, float(finite.min()) - pad)
        hi = min(1.0, float(finite.max()) + 0.005)
        if hi - lo < min_span:
            lo = max(0.0, hi - min_span)
        return lo, hi

    st.subheader("Метрики на тесті")
    st.caption(
        "Кольорові бари в стовпцях Accuracy / F1 / AUC — це шкала zoomed "
        "по факту значень (щоб видно було різницю в 4-му знаку). Таблиця "
        "сортується кліком по заголовку стовпця."
    )

    table_df = df.sort_values("test_f1", ascending=False).reset_index(drop=True)

    acc_lo, acc_hi = _zoomed_range(df["test_accuracy"].to_numpy())
    f1_lo,  f1_hi  = _zoomed_range(df["test_f1"].to_numpy())
    auc_lo, auc_hi = _zoomed_range(df["test_auc"].to_numpy())

    col_config = {
        "model": st.column_config.TextColumn("Модель", width="small"),
        "test_accuracy": st.column_config.ProgressColumn(
            "Accuracy", format="%.4f",
            min_value=acc_lo, max_value=acc_hi,
        ),
        "test_f1": st.column_config.ProgressColumn(
            "F1", format="%.4f",
            min_value=f1_lo, max_value=f1_hi,
        ),
        "test_auc": st.column_config.ProgressColumn(
            "AUC", format="%.4f",
            min_value=auc_lo, max_value=auc_hi,
        ),
        "cv_f1_mean": st.column_config.NumberColumn("CV F1 mean", format="%.4f"),
        "cv_f1_std":  st.column_config.NumberColumn("CV F1 std",  format="%.4f"),
        "fit_time_s": st.column_config.NumberColumn("Час, с",     format="%.2f"),
    }
    cols_to_show = ["model", "test_accuracy", "test_f1", "test_auc",
                    "cv_f1_mean", "cv_f1_std", "fit_time_s"]
    if "tune_time_s" in table_df.columns:
        cols_to_show.append("tune_time_s")
        col_config["tune_time_s"] = st.column_config.NumberColumn(
            "Tune time, с", format="%.2f",
        )

    st.dataframe(
        table_df[cols_to_show],
        column_config=col_config,
        hide_index=True,
        use_container_width=True,
        height=min(640, 38 * len(table_df) + 50),
    )

    st.caption(
        f"Діапазони: Accuracy [{acc_lo:.3f} — {acc_hi:.3f}], "
        f"F1 [{f1_lo:.3f} — {f1_hi:.3f}], "
        f"AUC [{auc_lo:.3f} — {auc_hi:.3f}]"
    )

    # ----- CSV ---------------------------------------------------------------

    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Завантажити CSV", data=csv_bytes,
        file_name=f"summary_{cfg.get('dataset', 'x')}.csv",
        mime="text/csv",
    )

    # ----- time chart (нативний st.bar_chart — миттєво рендериться) ---------

    st.subheader("Час навчання")
    time_chart_df = (
        df[["model", "fit_time_s"]]
        .sort_values("fit_time_s", ascending=True)
        .set_index("model")
    )
    st.bar_chart(time_chart_df, horizontal=True, height=max(220, 32 * len(df)))

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
