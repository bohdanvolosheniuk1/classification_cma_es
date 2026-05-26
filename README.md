# classification_cma_es

Практична частина дипломної роботи. Порівняльний аналіз класифікаторів
на трьох сучасних наборах даних з використанням розширеного алгоритму
CMA-ES (із сумішами нормальних розподілів) як п'ятого методу.

## Що порівнюємо

- Logistic Regression
- SVM (RBF kernel)
- kNN
- Багатошарова нейронна мережа (sklearn MLP)
- Нейронна мережа, навчена через CMA-ES (класичний — пакет `cma`;
  розширений зі сумішами нормальних розподілів — власна реалізація
  за роботою Літвінчук Ю.А., 2024)

Додатково — підбір гіперпараметрів кожної базової моделі через CMA-ES
(моделі з префіксом `tuned_`).

## Дані

| Датасет | Тип | Рік | Розмір |
|---|---|---|---|
| PhiUSIIL Phishing URL (UCI #967) | бінарна | 2024 | 235K × 54 |
| Steel Plate Defects (Kaggle PS S4E3) | мультикласова (7) | 2024 | 19K × 27 |
| Loan Approval (Kaggle PS S4E10) | бінарна | 2024 | 58K × 13 |

## Метрики

- Accuracy
- F1-score (binary для бінарних задач, weighted для мультикласу)
- ROC-AUC (бінарний; OvR weighted для мультикласу)

Логуються в MLflow як `test_*` (test set) і `cv_*_mean / cv_*_std`
(k-fold по тренувальній частині).

## Встановлення і запуск

```
python -m venv .venv
.venv\Scripts\activate          # Windows
# або: source .venv/bin/activate   (Linux/macOS)
pip install -e .
```

Завантажити дані:

```
python scripts/download.py --dataset phiusiil      # тягне з UCI автоматично
python scripts/download.py --dataset steel_plate   # через Kaggle CLI
python scripts/download.py --dataset loan_approval # через Kaggle CLI
```

Для Kaggle потрібен `kaggle.json` у `~/.kaggle/`. Якщо нема — скрипт
підкаже як завантажити вручну.

Запустити повний експеримент:

```
python scripts/run_experiment.py --dataset phiusiil
```

Корисні опції:

| Опція | Що робить |
|---|---|
| `--models logreg,svm,cma_mixture` | конкретні моделі через кому |
| `--sample 8000` | підсемплити датасет (на великих PhiUSIIL варто) |
| `--folds 5` | кількість фолдів |
| `--cma-iter 60` | ітерацій CMA-ES |
| `--no-tuning` | пропустити `tuned_*` моделі |
| `--no-mlflow` | не логувати в MLflow |

Перегляд результатів у MLflow:

```
mlflow ui
```

і відкрити http://localhost:5000.

### Графічний інтерфейс (Streamlit)

```
streamlit run app.py
```

Відкриє http://localhost:8501. У бічній панелі — вибір датасету, моделей,
розмір вибірки, кількість фолдів, ітерації CMA-ES. Після кнопки
"Запустити" — таблиця з метриками, стовпчасті діаграми по acc/F1/AUC,
графік збіжності для CMA-моделей, експорт результатів у CSV.

## Структура проекту

```
classifiers/                  # пакет
  data.py                     # завантаження датасетів
  preprocessing.py            # масштабування, one-hot, імпутація
  models.py                   # базові класифікатори (sklearn)
  cma_es.py                   # обгортка над класичним CMA-ES
  mixture_cma_es.py           # розширений CMA-ES зі сумішами + EM
  cma_nn.py                   # NN, що навчається CMA-ES
  hyperparam_tuning.py        # підбір гіперпараметрів через CMA-ES
  crossval.py                 # k-fold + train/test split
  metrics.py                  # accuracy, f1, AUC
  tracking.py                 # MLflow
  pipeline.py                 # спільна логіка для CLI та UI
scripts/
  download.py
  run_experiment.py           # CLI
app.py                        # Streamlit GUI
tests/                        # pytest
```

## Тести

```
pytest -q
```

## Алгоритм mixture CMA-ES — короткі нотатки

На кожній ітерації:

1. Семплуємо `N` точок із суміші `Σ_s w_s · N(m_s, C_s)`.
2. Обчислюємо `f(x_i)` для кожної.
3. Беремо найкращу половину.
4. EM-алгоритм оновлює `(w_s, m_s, C_s)` за цими точками.
5. Коваріації оновлюються з моментум-коефіцієнтом `cov_lr` (за
   аналогією з rank-μ оновленням у класичному CMA-ES — без цього
   маємо передчасний колапс дисперсії на унімодальних задачах).
6. У адаптивному режимі: пік з очікуваною масою < `sqrt(N/2)`
   видаляється; якщо немає прогресу `patience` ітерацій — додаємо
   новий пік розщепленням найбільшого.

Подробиці — у `classifiers/mixture_cma_es.py`.

## Літературна основа

Літвінчук Ю.А. *Побудова самоадаптивних алгоритмів на основі
нейронних мереж*. Дис. ... доктора філософії, 113 — Прикладна
математика. ЧНУ ім. Юрія Федьковича, 2024.
