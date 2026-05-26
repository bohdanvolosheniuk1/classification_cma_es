# classification_cma_es

Практична частина дипломної роботи. Порівняльний аналіз класифікаторів
на трьох сучасних наборах даних з використанням розширеного алгоритму
CMA-ES (із сумішами розподілів) як п'ятого методу.

## Що порівнюємо

- Logistic Regression
- SVM
- kNN
- Багатошарова нейронна мережа (MLP)
- Нейронна мережа, навчена за допомогою CMA-ES (класичного та
  розширеного зі сумішами нормальних розподілів)

Додатково — підбір гіперпараметрів базових моделей за допомогою CMA-ES.

## Дані

| Датасет | Тип | Рік |
|---|---|---|
| PhiUSIIL Phishing URL (UCI) | бінарна класифікація | 2024 |
| Steel Plate Defects (Kaggle PS S4E3) | 7 класів | 2024 |
| Loan Approval Prediction (Kaggle PS S4E10) | бінарна | 2024 |

Як завантажити — див. `scripts/download.py`.

## Метрики

Accuracy, F1-score (weighted для мультикласу), ROC-AUC (OvR для мультикласу).

## Запуск

```
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# завантажити дані
python scripts/download.py --dataset phiusiil
python scripts/download.py --dataset steel_plate
python scripts/download.py --dataset loan_approval

# запустити експеримент
python scripts/run_experiment.py --dataset phiusiil --model all
```

Метрики й артефакти логуються у MLflow (локально, тека `mlruns/`).
Перегляд: `mlflow ui` у корені проекту.

## Структура

```
classifiers/        # пакет
  data.py           # завантаження датасетів
  preprocessing.py  # масштабування, енкодинг
  models.py         # базові класифікатори
  cma_es.py         # обгортка над класичним CMA-ES
  mixture_cma_es.py # розширений CMA-ES зі сумішами (за Літвінчук Ю.А.)
  cma_nn.py         # NN, що навчається CMA-ES
  hyperparam_tuning.py
  metrics.py
  crossval.py
  tracking.py       # MLflow
scripts/            # CLI
tests/              # pytest
notebooks/          # EDA
```

## Літературна основа

Дисертація: Літвінчук Ю.А. Побудова самоадаптивних алгоритмів на основі
нейронних мереж. ЧНУ ім. Юрія Федьковича, 2024.

Розширений CMA-ES використовує суміш нормальних розподілів та
EM-алгоритм для оцінки параметрів — як описано в розділі 2 дисертації.
