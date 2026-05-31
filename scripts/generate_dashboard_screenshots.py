"""Робить реальні скриншоти Streamlit-дашборду для диплома.

Запускає Streamlit у фоні, через playwright відкриває браузер,
натискає Запустити, дочікується завершення експерименту, робить
3 скриншоти:

* dashboard_main.png  — головна сторінка з настройками + результатами
* dashboard_table.png — крупно таблиця з метриками
* dashboard_charts.png — графіки часу і збіжності CMA-ES

Виклик::

    python scripts/generate_dashboard_screenshots.py
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright


REPO_ROOT = Path(__file__).resolve().parent.parent
FIGURES_DIR = REPO_ROOT.parent / "diploma_figures"
PORT = 8765  # окремий порт щоб не конфліктувати з ручним запуском


async def _take_shots(out_dir: Path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1500, "height": 950})
        await page.goto(f"http://localhost:{PORT}", wait_until="networkidle",
                        timeout=30000)
        # дочекатися повного завантаження
        await page.wait_for_selector("text=Конфігурація", timeout=20000)
        await asyncio.sleep(2)

        # 1) скрин стартового стану дашборду
        await page.screenshot(path=str(out_dir / "dashboard_main.png"),
                              full_page=False)
        print("  dashboard_main.png — стартовий стан")

        # знайти кнопку Запустити і натиснути
        run_btn = page.get_by_role("button", name="Запустити")
        await run_btn.click()
        print("  -> натиснуто Запустити, чекаю результати...")

        # дочекатися появи таблиці результатів (або зміни тексту)
        try:
            await page.wait_for_selector("text=Метрики на тесті",
                                         timeout=180000)
            await asyncio.sleep(5)  # дати графікам прорендеритись
        except Exception:
            print("  (не дочекались — продовжуємо)")

        # 2) повний скриншот всієї сторінки після прогону
        await page.screenshot(
            path=str(out_dir / "dashboard_results.png"),
            full_page=True,
        )
        print("  dashboard_results.png — результати")

        # 3) окремий скрин лише таблиці
        try:
            table = await page.query_selector("text=Метрики на тесті")
            if table:
                # знайти найближчий контейнер
                container = await table.evaluate_handle(
                    "el => el.closest('[data-testid=stVerticalBlock]')")
                bbox = await container.bounding_box()
                if bbox:
                    await page.screenshot(
                        path=str(out_dir / "dashboard_table.png"),
                        clip={
                            "x": bbox["x"],
                            "y": bbox["y"],
                            "width": bbox["width"],
                            "height": min(700, bbox["height"]),
                        },
                    )
                    print("  dashboard_table.png — таблиця крупно")
        except Exception as e:
            print(f"  (table shot skipped: {e})")

        await browser.close()


def main() -> int:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Запускаю Streamlit на порті {PORT}...")
    streamlit_proc = subprocess.Popen(
        [
            str(REPO_ROOT / ".venv" / "Scripts" / "streamlit.exe"),
            "run", "app.py",
            "--server.port", str(PORT),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # дати серверу час на старт
    time.sleep(12)

    try:
        asyncio.run(_take_shots(FIGURES_DIR))
    finally:
        print("Зупиняю Streamlit...")
        streamlit_proc.terminate()
        try:
            streamlit_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            streamlit_proc.kill()

    print("\nГотово! Скриншоти у:")
    for f in sorted(FIGURES_DIR.glob("dashboard_*.png")):
        kb = f.stat().st_size // 1024
        print(f"  {f.name} [{kb} KB]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
