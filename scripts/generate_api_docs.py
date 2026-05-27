"""Генерує HTML API-документацію для пакету classifiers.

Виклик::

    python scripts/generate_api_docs.py

Виводить HTML у ``../docs/api/`` (поруч із PDF-гайдом і диплома .docx).
Відкривати — ``docs/api/index.html`` у браузері.

Скрипт також створює власну стартову сторінку ``index.html`` зі списком
модулів і посиланням на PDF-гайд, бо pdoc у мультимодульному режимі
залишає ``index.html`` порожнім.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_API = REPO_ROOT.parent / "docs" / "api"


_INDEX_HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8">
<title>classification_cma_es — документація</title>
<style>
body { font-family: -apple-system, Segoe UI, sans-serif; max-width: 900px;
       margin: 40px auto; padding: 0 20px; line-height: 1.5; color: #222; }
h1 { color: #264653; border-bottom: 2px solid #2a9d8f; padding-bottom: 8px; }
h2 { color: #2a9d8f; margin-top: 30px; }
ul { padding-left: 20px; }
li { margin: 6px 0; }
a { color: #1976d2; text-decoration: none; }
a:hover { text-decoration: underline; }
.note { background: #f5f5f5; padding: 12px 16px; border-left: 3px solid #f4a261;
        margin: 16px 0; font-size: 14px; }
code { background: #eee; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; }
th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #ddd; }
th { background: #fafafa; }
</style>
</head>
<body>

<h1>classification_cma_es — документація</h1>

<p>Програмна частина дипломної роботи. Порівняння класифікаторів
із застосуванням розширеного алгоритму CMA-ES (за дисертацією
Літвінчук Ю.А., 2024) та GAM (розділ 1 диплома).</p>

<div class="note">
  <b>Початок:</b> якщо просто хочеш зрозуміти що це за програма —
  читай <a href="../guide.pdf">guide.pdf</a> (PDF, 12 розділів зі схемами).
  Якщо потрібні деталі API — нижче кожен модуль окремо.
</div>

<h2>Високорівневий огляд</h2>
<ul>
  <li><b><a href="../guide.pdf">../guide.pdf</a></b> — PDF-гайд із діаграмами</li>
  <li><a href="classifiers.html">classifiers</a> — головна сторінка пакета</li>
</ul>

<h2>Дані й оцінка</h2>
<table>
  <tr><th>Модуль</th><th>Що робить</th></tr>
  <tr><td><a href="classifiers/data.html">data</a></td>
      <td>Завантаження 3 датасетів (PhiUSIIL, Steel Plate, Loan Approval)</td></tr>
  <tr><td><a href="classifiers/preprocessing.html">preprocessing</a></td>
      <td>StandardScaler + OneHotEncoder + імпутація</td></tr>
  <tr><td><a href="classifiers/crossval.html">crossval</a></td>
      <td>train/test split + Stratified K-Fold</td></tr>
  <tr><td><a href="classifiers/metrics.html">metrics</a></td>
      <td>Accuracy, F1, ROC-AUC (binary + multiclass)</td></tr>
</table>

<h2>Класифікатори</h2>
<table>
  <tr><th>Модуль</th><th>Що робить</th></tr>
  <tr><td><a href="classifiers/models.html">models</a></td>
      <td>Фабрики LogReg, SVM, kNN, MLP, GAM</td></tr>
  <tr><td><a href="classifiers/gam.html">gam</a></td>
      <td><b>GAM-класифікатор (розділ 1 диплома)</b></td></tr>
  <tr><td><a href="classifiers/cma_nn.html">cma_nn</a></td>
      <td>5-й метод — NN, навчена CMA-ES</td></tr>
</table>

<h2>Оптимізація (розділ 2 диплома)</h2>
<table>
  <tr><th>Модуль</th><th>Що робить</th></tr>
  <tr><td><a href="classifiers/cma_es.html">cma_es</a></td>
      <td>Класичний CMA-ES (обгортка над пакетом cma)</td></tr>
  <tr><td><a href="classifiers/mixture_cma_es.html">mixture_cma_es</a></td>
      <td><b>Розширений CMA-ES зі сумішами (за Літвінчук Ю.А.)</b></td></tr>
  <tr><td><a href="classifiers/hyperparam_tuning.html">hyperparam_tuning</a></td>
      <td>CMA-ES як тюнер гіперпараметрів (моделі tuned_*)</td></tr>
</table>

<h2>Інфраструктура</h2>
<table>
  <tr><th>Модуль</th><th>Що робить</th></tr>
  <tr><td><a href="classifiers/pipeline.html">pipeline</a></td>
      <td>Оркестратор експерименту — функція <code>run_experiment</code></td></tr>
  <tr><td><a href="classifiers/tracking.html">tracking</a></td>
      <td>MLflow-логування</td></tr>
</table>

<div class="note">
  <b>Як запустити програму:</b> подвійний клік на <code>run_app.bat</code>
  у теці <code>classification_cma_es/</code> → Streamlit-дашборд на
  <code>http://localhost:8501</code>.
</div>

</body>
</html>
"""

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

    # Перезаписуємо порожній index.html, який pdoc створює в
    # мультимодульному режимі — на повноцінну стартову сторінку.
    index = DOCS_API / "index.html"
    index.write_text(_INDEX_HTML, encoding="utf-8")
    print("Перезаписано index.html на навігаційну сторінку")

    files = list(DOCS_API.rglob("*.html"))
    print(f"Створено {len(files)} HTML-файлів:")
    for f in sorted(files):
        kb = f.stat().st_size // 1024
        print(f"  {f.relative_to(DOCS_API)} [{kb} KB]")
    print(f"\nВідкривати: {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
