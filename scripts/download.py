"""Завантаження датасетів локально у теку data/."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def download_phiusiil(target_dir: Path) -> None:
    try:
        from ucimlrepo import fetch_ucirepo
        import pandas as pd
    except ImportError:
        print("Потрібно: pip install ucimlrepo pandas", file=sys.stderr)
        sys.exit(1)
    print("Завантажую PhiUSIIL з UCI (id=967)...")
    ds = fetch_ucirepo(id=967)
    X = ds.data.features
    y = ds.data.targets.iloc[:, 0].rename("label")
    target_dir.mkdir(parents=True, exist_ok=True)
    out = target_dir / "PhiUSIIL_Phishing_URL_Dataset.csv"
    pd.concat([X, y], axis=1).to_csv(out, index=False)
    print(f"OK: {out} ({len(X)} рядків)")


def download_kaggle(competition: str, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Kaggle: {competition} -> {target_dir}")
    rc = subprocess.call([
        "kaggle", "competitions", "download",
        "-c", competition,
        "-p", str(target_dir),
        "--unzip",
    ])
    if rc != 0:
        print(
            f"Автозавантаження не вдалось. Скачайте вручну: "
            f"https://www.kaggle.com/competitions/{competition}/data "
            f"і покладіть train.csv у {target_dir}",
            file=sys.stderr,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Завантаження датасетів")
    parser.add_argument(
        "--dataset",
        required=True,
        choices=["phiusiil", "steel_plate", "loan_approval", "all"],
    )
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()

    base = Path(args.data_dir) if args.data_dir else REPO_ROOT / "data"

    names = (
        ["phiusiil", "steel_plate", "loan_approval"]
        if args.dataset == "all"
        else [args.dataset]
    )
    for name in names:
        if name == "phiusiil":
            download_phiusiil(base / "phiusiil")
        elif name == "steel_plate":
            download_kaggle("playground-series-s4e3", base / "steel_plate")
        elif name == "loan_approval":
            download_kaggle("playground-series-s4e10", base / "loan_approval")
    return 0


if __name__ == "__main__":
    sys.exit(main())
