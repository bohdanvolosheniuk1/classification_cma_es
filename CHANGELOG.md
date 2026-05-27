# Changelog

Усі вагомі зміни проекту фіксуються тут. Формат — [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/),
версіонування — [SemVer](https://semver.org/lang/uk/).

## [0.1.0] — 2026-05-27

Перший повноцінний реліз. Покриває всі вимоги куратора плюс розширення.

### Додано
- **Завантаження датасетів** (`classifiers/data.py`):
  PhiUSIIL Phishing URL (UCI #967, 2024), Steel Plate Defects
  (UCI #198 fallback або Kaggle PS S4E3), Default of Credit Card Clients
  (UCI #350 fallback або Kaggle PS S4E10).
- **Препроцесинг** (`classifiers/preprocessing.py`):
  імпутація, StandardScaler, OneHotEncoder через ColumnTransformer.
- **5 базових класифікаторів** (`classifiers/models.py`):
  LogisticRegression, SVM (RBF), kNN, MLPClassifier.
- **GAM-класифікатор** (`classifiers/gam.py`):
  SplineTransformer + LogisticRegression — реалізація узагальненої
  адитивної моделі з розділу 1 диплома.
- **Класичний CMA-ES** (`classifiers/cma_es.py`):
  обгортка над пакетом `cma`.
- **Розширений CMA-ES зі сумішами** (`classifiers/mixture_cma_es.py`):
  власна реалізація за дисертацією Літвінчук Ю.А. (2024) — суміші
  нормальних розподілів, EM-алгоритм, самоадаптивний підбір кількості
  піків.
- **CMA-NN** (`classifiers/cma_nn.py`):
  нейронна мережа, ваги якої навчаються через CMA-ES. Підтримує
  обидва режими (класичний і розширений). Це і є "5-й метод" із
  завдання куратора.
- **Підбір гіперпараметрів** (`classifiers/hyperparam_tuning.py`):
  моделі `tuned_*` — CMA-ES оптимізує гіперпараметри базових
  класифікаторів. Особлива модель `tuned_gam` об'єднує обидва
  розділи диплома (CMA-ES шукає оптимальні `n_knots` і `λ`).
- **Перехресна валідація** (`classifiers/crossval.py`):
  Stratified K-Fold (k=5 за замовчуванням), train/test split 80/20.
- **Метрики** (`classifiers/metrics.py`):
  Accuracy, F1-score (binary і weighted multiclass), ROC-AUC
  (binary і OvR weighted для мультикласу).
- **MLflow tracking** (`classifiers/tracking.py`):
  автоматичне логування параметрів, метрик і артефактів.
- **Pipeline** (`classifiers/pipeline.py`):
  оркестратор експерименту, спільний для CLI і Streamlit UI.
- **CLI** (`scripts/run_experiment.py`):
  запуск експерименту з налаштовуваними прапорцями.
- **Streamlit-дашборд** (`app.py`):
  графічний інтерфейс з вибором параметрів, таблицею результатів
  (ProgressColumn з адаптивним zoom), графіком часу і кривими
  збіжності CMA-ES. Збереження стану на диск (recovery після
  розриву websocket).
- **Pytest-набір** (`tests/`): 34 тести покривають усі модулі.
- **Лаунчери** (`run_app.bat`, `run_mlflow.bat`): запуск подвійним
  кліком на Windows без термінала.
- **PDF-гайд** (`../docs/guide.pdf`): детальне пояснення програми
  з 7 схематичними діаграмами (12 розділів).

### Виправлено в процесі розробки
- Чисте EM-оновлення коваріаційних матриць у розширеному CMA-ES
  на унімодальних задачах призводило до передчасного колапсу
  дисперсії. Додано параметр `cov_lr` (момент-усереднення між
  ітераціями) — аналог rank-μ оновлення в класичному CMA-ES.
  Без цього фіксу алгоритм не сходився на простих функціях.
- Пакет `cma` падає на 1-вимірних просторах пошуку (`kNN` має
  лише один гіперпараметр `n_neighbors`). Додано fallback на
  random search для випадку `dim == 1`.
- `cmd.exe` на Windows читає `.bat` у OEM-кодуванні (cp866),
  а Write-tool зберігає в UTF-8 — українські повідомлення
  виглядали як мусор. Лаунчери переписано в ASCII.
- Streamlit з Altair-чартами тормозив і іноді не рендерив
  бари на тёмному фоні. Замінено на `st.dataframe` з
  `ProgressColumn` (нативний, миттєвий рендер).

### Підходи й принципи
- Хешування для Streamlit preview через `@st.cache_data` —
  щоб дашборд не перечитував CSV при кожному русі слайдера.
- Адаптивні діапазони ProgressColumn — щоб видно було різницю
  в 4-му знаку метрик типу 0.9985 vs 0.9990.
- UCI fallback для двох із трьох датасетів — програма працює
  без Kaggle-налаштувань (`kaggle.json` опційний).
