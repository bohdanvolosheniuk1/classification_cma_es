"""Завантаження датасетів."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class Dataset:
    name: str
    X: pd.DataFrame
    y: pd.Series
    task: str
    n_classes: int

    def __repr__(self) -> str:
        return (
            f"Dataset(name={self.name!r}, n={len(self.X)}, "
            f"features={self.X.shape[1]}, task={self.task})"
        )


def _read_or_fetch_phiusiil(csv_path: Path) -> pd.DataFrame:
    if csv_path.exists():
        return pd.read_csv(csv_path)
    try:
        from ucimlrepo import fetch_ucirepo
    except ImportError as e:
        raise FileNotFoundError(
            f"Файл {csv_path} не знайдено. Встановіть ucimlrepo "
            "або завантажте датасет з UCI (id=967) вручну."
        ) from e
    ds = fetch_ucirepo(id=967)
    X = ds.data.features
    y = ds.data.targets.iloc[:, 0].rename("label")
    df = pd.concat([X, y], axis=1)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return df


def load_phiusiil(data_dir: Path | None = None) -> Dataset:
    """PhiUSIIL Phishing URL (UCI, 2024). Бінарна класифікація."""
    if data_dir is None:
        data_dir = DATA_DIR / "phiusiil"
    csv_path = data_dir / "PhiUSIIL_Phishing_URL_Dataset.csv"
    df = _read_or_fetch_phiusiil(csv_path)

    # цільова колонка
    target_col = "label" if "label" in df.columns else df.columns[-1]
    y = df[target_col]
    X = df.drop(columns=[target_col])

    # текстові поля типу URL/Domain/Title не використовуємо для табличних моделей
    drop_text = [
        c for c in X.columns
        if X[c].dtype == object and c.lower() in {"url", "domain", "title", "tld"}
    ]
    if drop_text:
        X = X.drop(columns=drop_text)

    return Dataset(name="phiusiil", X=X, y=y, task="binary", n_classes=2)


def load_steel_plate(data_dir: Path | None = None) -> Dataset:
    """Steel Plate Defects (Kaggle PS S4E3, 2024). Мультиклас, 7 типів."""
    if data_dir is None:
        data_dir = DATA_DIR / "steel_plate"
    csv_path = data_dir / "train.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} не знайдено. Завантажте train.csv з Kaggle: "
            "kaggle competitions download -c playground-series-s4e3 "
            f"-p {data_dir} --unzip"
        )
    df = pd.read_csv(csv_path)

    label_cols = [
        "Pastry", "Z_Scratch", "K_Scatch", "Stains",
        "Dirtiness", "Bumps", "Other_Faults",
    ]
    missing = [c for c in label_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Не знайдено колонки міток: {missing}")

    y = df[label_cols].idxmax(axis=1).rename("defect")
    drop = label_cols + (["id"] if "id" in df.columns else [])
    X = df.drop(columns=drop)
    return Dataset(name="steel_plate", X=X, y=y, task="multiclass", n_classes=7)


def load_loan_approval(data_dir: Path | None = None) -> Dataset:
    """Loan Approval (Kaggle PS S4E10, 2024). Бінарна класифікація."""
    if data_dir is None:
        data_dir = DATA_DIR / "loan_approval"
    csv_path = data_dir / "train.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} не знайдено. Завантажте з Kaggle: "
            "kaggle competitions download -c playground-series-s4e10 "
            f"-p {data_dir} --unzip"
        )
    df = pd.read_csv(csv_path)
    if "id" in df.columns:
        df = df.drop(columns=["id"])
    if "loan_status" not in df.columns:
        raise ValueError("Очікувана колонка 'loan_status' відсутня")
    y = df["loan_status"]
    X = df.drop(columns=["loan_status"])
    return Dataset(name="loan_approval", X=X, y=y, task="binary", n_classes=2)


LOADERS = {
    "phiusiil": load_phiusiil,
    "steel_plate": load_steel_plate,
    "loan_approval": load_loan_approval,
}


def load_dataset(name: str) -> Dataset:
    if name not in LOADERS:
        raise ValueError(f"Невідомий датасет {name!r}, доступні: {list(LOADERS)}")
    return LOADERS[name]()
