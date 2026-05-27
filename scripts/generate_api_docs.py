"""Генерує HTML API-документацію для пакету classifiers.

Виклик::

    python scripts/generate_api_docs.py

Виводить HTML у ``../docs/api/`` (поруч із PDF-гайдом і диплома .docx).
Відкривати — ``docs/api/index.html`` у браузері.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_API = REPO_ROOT.parent / "docs" / "api"

MODULES = [
    "classifiers",
    "classifiers.data",
    "classifiers.preprocessing",
    "classifiers.models",
    "classifiers.gam",
    "classifiers.cma_es",
    "classifiers.mixture_cma_es",
    "classifiers.cma_nn",
    "classifiers.hyperparam_tuning",
    "classifiers.crossval",
    "classifiers.metrics",
    "classifiers.tracking",
    "classifiers.pipeline",
]


def main() -> int:
    # Чистимо лише .html-файли — щоб не падати на OneDrive sync, який
    # часом блокує rmdir на каталогах
    if DOCS_API.exists():
        for f in DOCS_API.rglob("*"):
            if f.is_file():
                try:
                    f.unlink()
                except PermissionError:
                    pass
    DOCS_API.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "pdoc",
        *MODULES,
        "-o", str(DOCS_API),
        "--docformat", "numpy",
    ]
    print(f"Генерую API-доки у {DOCS_API}")
    rc = subprocess.call(cmd, cwd=str(REPO_ROOT))
    if rc != 0:
        print(f"pdoc впав з кодом {rc}", file=sys.stderr)
        return rc

    files = list(DOCS_API.rglob("*.html"))
    print(f"Створено {len(files)} HTML-файлів:")
    for f in sorted(files):
        kb = f.stat().st_size // 1024
        print(f"  {f.relative_to(DOCS_API)} [{kb} KB]")
    print(f"\nВідкривати: {DOCS_API / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
