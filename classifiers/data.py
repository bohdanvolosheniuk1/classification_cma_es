"""Завантаження трьох датасетів проекту.

Модуль забезпечує єдиний інтерфейс :func:`load_dataset` для трьох
наборів даних:

* ``phiusiil`` — PhiUSIIL Phishing URL Dataset (UCI #967, 2024).
* ``steel_plate`` — Steel Plate Defects (Kaggle Playground S4E3, 2024,
  з UCI #198 fallback).
* ``loan_approval`` — Loan Approval / Default of Credit Card Clients
  (Kaggle Playground S4E10, 2024, з UCI #350 fallback).

Якщо локальний CSV не знайдено — для phiusiil та fallback-варіантів
датасет автоматично завантажується через ``ucimlrepo``. Kaggle-файли
завантажуються вручну через ``scripts/download.py`` (потрібен kaggle.json).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
"""Базова тека для CSV-файлів — ``<repo>/data/<dataset_name>/``."""


@dataclass
class Dataset:
    """Контейнер для одного завантаженого датасету.

    Attributes
    ----------
    name : str
        Ідентифікатор датасету (``"phiusiil"`` / ``"steel_plate"`` /
        ``"loan_approval"``).
    X : pandas.DataFrame
        Матриця ознак до препроцесингу. Може містити числові
        й категоріальні колонки. Препроцесинг виконує
        :func:`classifiers.preprocessing.build_preprocessor`.
    y : pandas.Series
        Цільова змінна. Для бінарних задач — 0/1; для мультикласу
        — строкові імена класів (наприклад, типи дефектів).
    task : str
        Тип задачі: ``"binary"`` або ``"multiclass"``.
    n_classes : int
        Кількість унікальних класів у ``y``.
    """

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
    """Завантажити PhiUSIIL Phishing URL Dataset.

    UCI dataset #967 (2024). Бінарна класифікація phishing-сайтів
    за 54 числовими ознаками URL-адреси (довжина, кількість крапок,
    наявність HTTPS, ентропія тощо).

    При першому виклику завантажує дані через ``ucimlrepo`` і кешує
    у вигляді CSV. Наступні виклики читають із кешу.

    Parameters
    ----------
    data_dir : pathlib.Path, optional
        Тека для CSV. За замовчуванням — ``<repo>/data/phiusiil/``.

    Returns
    -------
    Dataset
        З ``task="binary"``, ``n_classes=2``. ``y == 1`` — справжній сайт,
        ``y == 0`` — phishing.

    Raises
    ------
    FileNotFoundError
        Якщо CSV відсутній і ``ucimlrepo`` не встановлено.
    """
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


def _load_steel_plate_uci(cache_dir: Path) -> pd.DataFrame:
    """Fallback на UCI #198 — оригінальний Steel Plates Faults (база Kaggle S4E3)."""
    cache = cache_dir / "uci_steel_plates_faults.csv"
    if cache.exists():
        return pd.read_csv(cache)
    try:
        from ucimlrepo import fetch_ucirepo
    except ImportError as e:
        raise FileNotFoundError(
            "Ні Kaggle-файлу, ні ucimlrepo. Поставте: pip install ucimlrepo"
        ) from e
    ds = fetch_ucirepo(id=198)
    X = ds.data.features
    y_raw = ds.data.targets
    df = pd.concat([X, y_raw], axis=1)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache, index=False)
    return df


def load_steel_plate(data_dir: Path | None = None) -> Dataset:
    """Завантажити Steel Plate Defects.

    Мультикласова класифікація 7 типів дефектів металевих пластин
    (Pastry, Z_Scratch, K_Scratch, Stains, Dirtiness, Bumps, Other_Faults).

    Спочатку шукає Kaggle-варіант (``train.csv`` із Playground Series
    S4E3, 2024, ~19 219 рядків × 27 ознак). Якщо локального файлу немає
    — автоматично завантажує UCI #198 (1 941 × 27 рядків), який є
    першоджерелом Kaggle-датасету.

    Колонка ``K_Scatch`` у Kaggle (з опечаткою) автоматично
    перейменовується на ``K_Scratch`` як у UCI.

    Parameters
    ----------
    data_dir : pathlib.Path, optional
        Тека для CSV. За замовчуванням — ``<repo>/data/steel_plate/``.

    Returns
    -------
    Dataset
        З ``task="multiclass"``, ``n_classes=7``. ``y`` — строкові
        імена типів дефектів.

    Raises
    ------
    ValueError
        Якщо у датасеті відсутня хоча б одна з очікуваних 7 колонок
        міток.
    FileNotFoundError
        Якщо й Kaggle-файлу немає, і ``ucimlrepo`` не встановлено.
    """
    if data_dir is None:
        data_dir = DATA_DIR / "steel_plate"
    csv_path = data_dir / "train.csv"

    if csv_path.exists():
        df = pd.read_csv(csv_path)
    else:
        print(f"  [load_steel_plate] {csv_path} не знайдено — fallback UCI #198")
        df = _load_steel_plate_uci(data_dir)

    # Kaggle має опечатку K_Scatch, UCI пише правильно K_Scratch — нормалізуємо
    df = df.rename(columns={"K_Scatch": "K_Scratch"})
    label_cols = [
        "Pastry", "Z_Scratch", "K_Scratch", "Stains",
        "Dirtiness", "Bumps", "Other_Faults",
    ]
    missing = [c for c in label_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Не знайдено колонки міток: {missing}")

    y = df[label_cols].idxmax(axis=1).rename("defect")
    drop = label_cols + (["id"] if "id" in df.columns else [])
    X = df.drop(columns=drop, errors="ignore")
    return Dataset(name="steel_plate", X=X, y=y, task="multiclass", n_classes=7)


_CREDIT_DEFAULT_COLS = {
    "X1": "LIMIT_BAL",
    "X2": "SEX",
    "X3": "EDUCATION",
    "X4": "MARRIAGE",
    "X5": "AGE",
    "X6": "PAY_0", "X7": "PAY_2", "X8": "PAY_3",
    "X9": "PAY_4", "X10": "PAY_5", "X11": "PAY_6",
    "X12": "BILL_AMT1", "X13": "BILL_AMT2", "X14": "BILL_AMT3",
    "X15": "BILL_AMT4", "X16": "BILL_AMT5", "X17": "BILL_AMT6",
    "X18": "PAY_AMT1", "X19": "PAY_AMT2", "X20": "PAY_AMT3",
    "X21": "PAY_AMT4", "X22": "PAY_AMT5", "X23": "PAY_AMT6",
}


def _load_credit_default_uci(cache_dir: Path) -> pd.DataFrame:
    """Fallback: UCI #350 Default of Credit Card Clients (2016)."""
    cache = cache_dir / "uci_credit_default.csv"
    if cache.exists():
        df = pd.read_csv(cache)
    else:
        try:
            from ucimlrepo import fetch_ucirepo
        except ImportError as e:
            raise FileNotFoundError(
                "Ні Kaggle-файлу, ні ucimlrepo. Поставте: pip install ucimlrepo"
            ) from e
        ds = fetch_ucirepo(id=350)
        X = ds.data.features
        y = ds.data.targets.iloc[:, 0].rename("loan_status")
        df = pd.concat([X, y], axis=1)
        cache.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cache, index=False)

    # перейменування X1..X23 у людські назви (LIMIT_BAL, AGE, PAY_*, BILL_AMT*, PAY_AMT*)
    return df.rename(columns=_CREDIT_DEFAULT_COLS)


def load_loan_approval(data_dir: Path | None = None) -> Dataset:
    """Завантажити кредитну класифікацію (Loan Approval / Credit Default).

    Бінарна задача: спрогнозувати, чи буде клієнт у дефолті.

    Спочатку шукає Kaggle-варіант (``train.csv`` із Playground Series
    S4E10, 2024, ~58 645 рядків × 13 ознак). Якщо немає — fallback на
    UCI #350 *Default of Credit Card Clients* (2016, 30 000 × 23). UCI-
    варіант перейменовує колонки ``X1..X23`` на стандартні імена
    ``LIMIT_BAL``, ``AGE``, ``PAY_*``, ``BILL_AMT*``, ``PAY_AMT*``.

    Класи незбалансовані (~78% / 22%) — це робить задачу складнішою
    й корисною для порівняння моделей за F1 / AUC.

    Parameters
    ----------
    data_dir : pathlib.Path, optional
        Тека для CSV. За замовчуванням — ``<repo>/data/loan_approval/``.

    Returns
    -------
    Dataset
        З ``task="binary"``, ``n_classes=2``. ``y == 1`` — дефолт.

    Raises
    ------
    ValueError
        Якщо у датасеті відсутня колонка ``loan_status``.
    FileNotFoundError
        Якщо й Kaggle-файлу немає, і ``ucimlrepo`` не встановлено.
    """
    if data_dir is None:
        data_dir = DATA_DIR / "loan_approval"
    csv_path = data_dir / "train.csv"

    if csv_path.exists():
        df = pd.read_csv(csv_path)
        if "id" in df.columns:
            df = df.drop(columns=["id"])
    else:
        print(f"  [load_loan_approval] {csv_path} не знайдено — fallback UCI #350")
        df = _load_credit_default_uci(data_dir)

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
"""Реєстр доступних датасетів. Використовується :func:`load_dataset`."""


def load_dataset(name: str) -> Dataset:
    """Універсальний завантажувач за іменем.

    Parameters
    ----------
    name : {"phiusiil", "steel_plate", "loan_approval"}
        Ідентифікатор датасету.

    Returns
    -------
    Dataset
        Готовий до подальшого препроцесингу й навчання моделей.

    Raises
    ------
    ValueError
        Якщо ``name`` не міститься у :data:`LOADERS`.

    Examples
    --------
    >>> ds = load_dataset("phiusiil")
    >>> ds.task
    'binary'
    >>> ds.n_classes
    2
    """
    if name not in LOADERS:
        raise ValueError(f"Невідомий датасет {name!r}, доступні: {list(LOADERS)}")
    return LOADERS[name]()
