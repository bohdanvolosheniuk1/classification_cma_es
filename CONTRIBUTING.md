# Як розширювати проект

Якщо потрібно додати новий датасет, модель або змінити пайплайн —
ось як зробити це послідовно, щоб усе залишилось консистентним.

## Розробницьке середовище

```
py -3 -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install pdoc pyflakes  # для документації та лінту
```

Усі тести мають проходити перед коммітом:

```
pytest -q
```

Швидка перевірка чистоти імпортів:

```
python -m pyflakes classifiers/ scripts/ app.py tests/
```

## Додати новий датасет

1. Відкрити [classifiers/data.py](classifiers/data.py).
2. Додати функцію `load_<name>(data_dir=None) -> Dataset` за зразком
   існуючих (PhiUSIIL / Steel Plate / Loan Approval). Підтримати
   автозавантаження через `ucimlrepo` як fallback, якщо можливо.
3. Зареєструвати в `LOADERS` і додати в `DATASETS` у
   [classifiers/pipeline.py](classifiers/pipeline.py).
4. Додати рядок у [`scripts/download.py`](scripts/download.py).
5. Додати тест у [tests/test_data.py](tests/test_data.py) (за зразком —
   мокнути `ucimlrepo` або використати чистий tmp-каталог).
6. Прогнати: `python scripts/run_experiment.py --dataset <name>
   --sample 1000 --no-mlflow --no-tuning`.

## Додати новий класифікатор

1. Створити модуль `classifiers/<name>.py` із класом
   `<Name>Classifier(BaseEstimator, ClassifierMixin)`. Реалізувати
   `fit`, `predict`, `predict_proba` (sklearn-сумісність обов'язкова —
   на цьому базується вся оцінка).
2. У [classifiers/models.py](classifiers/models.py) додати фабрику
   `make_<name>(**kwargs)` і запис у `BASE_MODELS`.
3. У [classifiers/pipeline.py](classifiers/pipeline.py) додати
   `"<name>"` у списки `ALL_MODELS` і `BASE_FACTORIES`.
4. (Опційно) додати простір гіперпараметрів у
   [classifiers/hyperparam_tuning.py](classifiers/hyperparam_tuning.py)
   — `space_<name>()` + запис у `SPACES`. Це автоматично активує
   модель `tuned_<name>` у списку.
5. Додати тести в `tests/test_<name>.py` за зразком
   [tests/test_gam.py](tests/test_gam.py).

## Стиль коду

* **Docstring'и** — NumPy-style (Parameters / Returns / Examples).
* **Імена** — англійська (стандарт Python), коментарі — українська.
* **Без емодзі** в коді, коммітах і README.
* **Коротко й по суті** — без надмірного коментування очевидного.

## Документація

Після зміни docstring'ів — оновити HTML API і PDF-гайд:

```
python scripts/generate_api_docs.py   # ../docs/api/index.html
python scripts/generate_guide.py      # ../docs/guide.pdf
```

## Коміти

Conventional-style на українській, без префіксу типу `feat:` (це
не строго потрібно):

```
init: каркас проекту
data: loaders для PhiUSIIL, Steel Plate, Loan Approval
fix: моментум на коваріацію в mixture CMA-ES
docs: numpy-style docstrings для data, preprocessing, models, gam
```

## Поточна структура

```
classifiers/         пакет (sklearn-сумісні класи, оркестратор, MLflow)
scripts/             CLI (run_experiment, download, генератори доків)
tests/               pytest (34 тести)
app.py               Streamlit GUI
run_*.bat            лаунчери для подвійного клика
../docs/             зовнішня тека з PDF-гайдом і HTML API
```
