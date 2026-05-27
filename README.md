# classification_cma_es

Практична частина дипломної роботи. Порівняльний аналіз класифікаторів
на трьох сучасних наборах даних з використанням розширеного алгоритму
CMA-ES (із сумішами нормальних розподілів) як п'ятого методу.

## Що порівнюємо

- Logistic Regression
- SVM (RBF kernel)
- kNN
- Багатошарова нейронна мережа (sklearn MLP)
- **GAM** — узагальнена адитивна модель (B-сплайни + LogReg). Це той
  самий клас моделей, що описаний у розділі 1 диплома: степінь та
  кількість вузлів сплайну, штраф L2 = параметр згладжування λ.
- **CMA-ES NN** — нейронна мережа, ваги якої навчає CMA-ES. Класичний
  (пакет `cma`) і розширений зі сумішами нормальних розподілів
  (власна реалізація за роботою Літвінчук Ю.А., 2024).

Додатково — підбір гіперпараметрів кожної з цих моделей через CMA-ES
(моделі з префіксом `tuned_`). Особливо цікавий **`tuned_gam`** —
саме тут зустрічаються обидва розділи диплома: CMA-ES шукає оптимальну
кількість вузлів сплайну, степінь і параметр згладжування λ для GAM.

## Дані

| Датасет | Тип | Рік | Розмір | Джерело |
|---|---|---|---|---|
| PhiUSIIL Phishing URL | бінарна | 2024 | 235K × 54 | UCI #967 (auto) |
| Steel Plate Defects | мультикласова (7) | 2024 / 2010 | 19K × 27 / 1941 × 27 | Kaggle PS S4E3, fallback UCI #198 (auto) |
| Default of Credit Card Clients | бінарна | 2024 / 2016 | 58K × 13 / 30K × 23 | Kaggle PS S4E10, fallback UCI #350 (auto) |

Якщо є Kaggle CLI — використається Kaggle-варіант. Інакше — UCI
оригінал, що скачається автоматично через `ucimlrepo` без жодних
налаштувань.

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
  models.py                   # фабрики базових класифікаторів
  gam.py                      # GAM (B-сплайни + LogReg) — розділ 1
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

## PDF-гайд

Детальне пояснення програми "як для дитини" зі схемами:
[docs/guide.pdf](docs/guide.pdf).

Перегенерувати:

```
python scripts/generate_guide.py
```

Скрипт спочатку малює діаграми у `docs/figures/`, потім збирає PDF
через fpdf2 (DejaVu Sans для кирилиці).

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
