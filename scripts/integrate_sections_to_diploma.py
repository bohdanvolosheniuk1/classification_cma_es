"""Інтегрує розділи 3 і 4 у файл ``диплом 1.docx``.

Перед інтеграцією робить резервну копію оригінала у файл
``диплом 1_BACKUP_до_інтеграції.docx``. Потім відкриває оригінал,
додає перенесення сторінки і два нові розділи у кінець, зберігає
назад у той самий ``диплом 1.docx``.

Запуск::

    python scripts/integrate_sections_to_diploma.py

Опція ``--no-backup`` пропускає резервне копіювання (для повторних
запусків коли бекап уже зроблено)::

    python scripts/integrate_sections_to_diploma.py --no-backup
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from docx import Document

from generate_diploma_sections import add_sections_to


REPO_ROOT = Path(__file__).resolve().parent.parent
DIPLOMA_PATH = REPO_ROOT.parent / "диплом 1.docx"
BACKUP_PATH = REPO_ROOT.parent / "диплом 1_BACKUP_до_інтеграції.docx"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-backup", action="store_true",
                        help="не робити резервну копію оригінала")
    args = parser.parse_args()

    if not DIPLOMA_PATH.exists():
        print(f"ПОМИЛКА: файл {DIPLOMA_PATH} не знайдено", file=sys.stderr)
        return 1

    if not args.no_backup:
        if BACKUP_PATH.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamped = BACKUP_PATH.with_name(f"диплом 1_BACKUP_{ts}.docx")
            shutil.copy2(BACKUP_PATH, timestamped)
            print(f"Старий бекап перейменовано: {timestamped.name}")
        shutil.copy2(DIPLOMA_PATH, BACKUP_PATH)
        print(f"Створено бекап: {BACKUP_PATH.name}")

    print(f"Відкриваю: {DIPLOMA_PATH.name}")
    doc = Document(str(DIPLOMA_PATH))

    # перенесення сторінки перед новими розділами
    doc.add_page_break()

    print("Додаю розділ 3 і розділ 4...")
    add_sections_to(doc)

    doc.save(str(DIPLOMA_PATH))
    size_kb = DIPLOMA_PATH.stat().st_size // 1024
    print(f"Збережено: {DIPLOMA_PATH.name} ({size_kb} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
