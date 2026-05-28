"""Генерує комплект для захисту дипломної роботи:

* ``../presentation/diploma_presentation.pptx`` — слайди PowerPoint
  з вбудованими діаграмами і speaker notes (підказки доповідачу).
* ``../presentation/speech_script.docx`` — повний текст доповіді,
  розбитий за слайдами (для друку і підготовки до виступу).

Тривалість доповіді — ~7 хвилин, 16 слайдів.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm as DocxCm, Pt as DocxPt, RGBColor as DocxRGB

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm, Inches, Pt


REPO_ROOT = Path(__file__).resolve().parent.parent
PRESENTATION_DIR = REPO_ROOT.parent / "presentation"
FIGURES_DIR = REPO_ROOT.parent / "docs" / "figures"
PPTX_PATH = PRESENTATION_DIR / "diploma_presentation.pptx"
DOCX_PATH = PRESENTATION_DIR / "speech_script.docx"


# ============================================================================
# контент усіх слайдів

SLIDES = [
    {
        "title": "classification_cma_es",
        "subtitle": "Порівняння класифікаторів із застосуванням\nрозширеного алгоритму CMA-ES",
        "layout": "title",
        "speech": (
            "Шановний голово екзаменаційної комісії, шановні члени комісії. "
            "Представляю практичну частину моєї дипломної роботи з прикладної "
            "математики. Програмний модуль classification_cma_es реалізує "
            "порівняльне дослідження методів класифікації машинного навчання "
            "із застосуванням розширеного алгоритму CMA-ES, описаного у "
            "дисертації Літвінчук Юлії Анатоліївни 2024 року."
        ),
    },
    {
        "title": "Постановка задачі",
        "layout": "bullets",
        "bullets": [
            "Куратор поставив завдання провести порівняльний аналіз "
            "класифікації на сучасних наборах даних",
            "Використати п'ять методів: логістична регресія, SVM, "
            "kNN, нейронна мережа, метод з роботи Літвінчук Ю.А.",
            "Реалізувати train/test поділ і k-fold перехресну валідацію",
            "Метрики якості: accuracy, F1-score, ROC-AUC",
            "Код у вигляді сформованого модуля з документацією",
            "Інтеграція з MLflow для трекінгу експериментів",
        ],
        "speech": (
            "Завдання від куратора складалося з декількох пунктів. "
            "Провести порівняльний аналіз класифікації на сучасних наборах "
            "даних. Використати п'ять методів класифікації: логістичну "
            "регресію, метод опорних векторів, k-найближчих сусідів, "
            "нейронну мережу та метод, досліджений у роботі Літвінчук Ю.А. "
            "Застосувати стандартну методику оцінки — розбиття на тренувальну "
            "й тестову вибірки та k-fold перехресну валідацію. Реалізувати "
            "три метрики якості. Оформити код як модульний пакет, інтегрувати "
            "з MLflow."
        ),
    },
    {
        "title": "Зв'язок з теоретичною частиною диплома",
        "layout": "bullets",
        "bullets": [
            "Розділ 1 теорії — Узагальнені адитивні моделі (GAM)",
            "Розділ 2 теорії — Алгоритм CMA-ES",
            "У програмі реалізовано обидва напрямки:",
            "    GAM → модуль classifiers/gam.py",
            "    CMA-ES → cma_es.py + mixture_cma_es.py",
            "Окрема модель tuned_gam об'єднує обидва розділи",
        ],
        "speech": (
            "Теоретична частина диплома містить два розділи: розділ 1 — "
            "про узагальнені адитивні моделі GAM, розділ 2 — про алгоритм "
            "CMA-ES. Я свідомо побудував програму так, щоб обидва розділи "
            "теорії були представлені у працюючому коді. GAM реалізовано "
            "як окремий класифікатор у модулі gam.py. CMA-ES — у двох "
            "варіантах: класичний і розширений зі сумішами. Окрема модель "
            "tuned_gam, про яку розповім пізніше, є практичною інтеграцією "
            "обох теоретичних розділів."
        ),
    },
    {
        "title": "Архітектура програми",
        "layout": "image",
        "image": "01_architecture.png",
        "speech": (
            "Програма побудована як модульний Python-пакет classifiers. "
            "На схемі видно три шари: зверху — підготовка даних "
            "(завантаження, препроцесинг, перехресна валідація). Посередині "
            "— самі моделі: п'ять базових класифікаторів і CMA-ES оптимізатори. "
            "Знизу — оркестратор pipeline, метрики і MLflow-трекінг. "
            "Точки входу — командний скрипт run_experiment та "
            "графічний інтерфейс на Streamlit."
        ),
    },
    {
        "title": "Набори даних",
        "layout": "bullets",
        "bullets": [
            "PhiUSIIL Phishing URL (UCI #967, 2024) — "
            "235 тис. рядків, бінарна задача",
            "Steel Plate Defects (Kaggle PS S4E3 / UCI #198) — "
            "мультикласова, 7 типів дефектів",
            "Default of Credit Card Clients (Kaggle PS S4E10 / UCI #350) "
            "— 30 тис. рядків, бінарна, незбалансовані класи",
            "PhiUSIIL — 2024 рік, відповідає вимозі куратора щодо актуальності",
        ],
        "speech": (
            "Для дослідження обрано три датасети різного типу. PhiUSIIL — "
            "класифікація phishing-сайтів за 54 ознаками URL-адреси, 2024 "
            "рік, виконує вимогу куратора щодо актуальності даних. "
            "Steel Plate Defects — мультикласова задача з семи типів "
            "дефектів металевих пластин. Default of Credit Card Clients "
            "— прогнозування дефолту клієнтів банку, класи незбалансовані "
            "78 на 22 відсотки, що робить задачу складнішою і цікавішою для "
            "порівняння метрик."
        ),
    },
    {
        "title": "12 методів класифікації",
        "layout": "bullets",
        "bullets": [
            "5 базових: logreg, svm, knn, mlp, GAM",
            "2 з CMA-ES: cma_classic, cma_mixture (5-й метод)",
            "5 із підбором гіперпараметрів: tuned_logreg, tuned_svm, "
            "tuned_knn, tuned_mlp, tuned_gam",
            "Усі сумісні зі sklearn API",
            "Розширення поверх вимог куратора",
        ],
        "speech": (
            "Куратор просив п'ять методів — я реалізував дванадцять. "
            "Базові п'ять: логістична регресія, SVM, k-найближчих сусідів, "
            "багатошарова нейронна мережа та GAM. Окремо — два варіанти "
            "5-го методу за роботою Літвінчук: класичний CMA-ES і "
            "розширений зі сумішами. І п'ять моделей з префіксом tuned_, "
            "де CMA-ES автоматично підбирає гіперпараметри базової моделі. "
            "Усі дванадцять реалізують єдиний sklearn-сумісний інтерфейс."
        ),
    },
    {
        "title": "Класичний CMA-ES",
        "layout": "image",
        "image": "05_cmaes_cycle.png",
        "speech": (
            "Класичний CMA-ES — це стохастичний оптимізатор без похідних. "
            "Один цикл складається з чотирьох кроків. Перший — семплування "
            "нових кандидатів з багатовимірного нормального розподілу з "
            "поточним середнім, кроком і коваріаційною матрицею. Другий — "
            "оцінка цільової функції. Третій — відбір найкращих. Четвертий "
            "— оновлення параметрів розподілу. У моїй реалізації використано "
            "пакет cma Ніколаса Хансена, той самий, що в дисертації Літвінчук."
        ),
    },
    {
        "title": "Розширений CMA-ES зі сумішами (за Літвінчук Ю.А.)",
        "layout": "image",
        "image": "06_mixture.png",
        "speech": (
            "Літвінчук Юлія Анатоліївна у дисертації запропонувала замінити "
            "унімодальний нормальний розподіл класичного CMA-ES на суміш з "
            "k нормальних компонент. Параметри суміші — ваги, центри, "
            "коваріації — оцінюються EM-алгоритмом за найкращою половиною "
            "хромосом кожної ітерації. Опційно — самоадаптивний підбір "
            "кількості піків k за критеріями з кластерного аналізу. Я "
            "реалізував цей алгоритм самостійно з нуля у модулі "
            "mixture_cma_es. Зробив одне технічне доповнення: момент-"
            "усереднення коваріацій між ітераціями, без якого алгоритм "
            "колапсує на простих унімодальних задачах."
        ),
    },
    {
        "title": "GAM (розділ 1 диплома)",
        "layout": "image",
        "image": "04_gam.png",
        "speech": (
            "Узагальнена адитивна модель GAM — це сума гладких функцій від "
            "кожної ознаки. У моїй реалізації кожна ознака проходить через "
            "B-сплайнове базисне перетворення, а коефіцієнти підбирає "
            "логістична регресія. Це математично еквівалентно класичному "
            "GAM з логіт-функцією зв'язку, описаному у розділі 1.6 диплома. "
            "Параметри моделі — кількість вузлів k, степінь сплайну та "
            "параметр згладжування лямбда, що відповідає 1 поділене на "
            "C логістичної регресії."
        ),
    },
    {
        "title": "tuned_gam — місток між розділами 1 і 2",
        "layout": "bullets",
        "bullets": [
            "GAM має параметри: n_knots (k), degree, λ = 1/C",
            "Розділ 1 описує, які це параметри і як вони впливають",
            "Розділ 2 описує алгоритм CMA-ES для пошуку оптимуму",
            "tuned_gam: CMA-ES шукає оптимальні параметри GAM",
            "→ Обидва розділи теорії втілені в одній моделі",
        ],
        "speech": (
            "Це найцікавіша модель у моїй реалізації. У розділі 1 теорії "
            "описано параметри GAM — кількість вузлів сплайну, степінь, "
            "параметр згладжування. У розділі 2 описано CMA-ES як "
            "оптимізатор. Модель tuned_gam буквально показує, як алгоритм "
            "з розділу 2 шукає оптимальні значення параметрів з розділу 1. "
            "Це не просто послідовне використання двох концепцій, а їхня "
            "практична інтеграція в одну робочу модель. Вважаю це найбільш "
            "змістовною частиною своєї реалізації."
        ),
    },
    {
        "title": "Методика оцінки",
        "layout": "image",
        "image": "03_kfold.png",
        "speech": (
            "Якість моделей оцінюю за стандартною методикою. Спочатку "
            "стратифікований поділ на тренувальну і тестову вибірки у "
            "пропорції 80 на 20. На тренувальній частині додатково — "
            "Stratified K-Fold з k рівним 5. Це дає оцінку стабільності "
            "моделі. Обчислюємо три метрики: accuracy, F1-score та "
            "ROC-AUC. Для мультикласових задач F1 — weighted average, "
            "AUC — One-vs-Rest weighted."
        ),
    },
    {
        "title": "Графічний інтерфейс (Streamlit)",
        "layout": "bullets",
        "bullets": [
            "Запуск подвійним кліком на run_app.bat",
            "Вибір датасета, моделей, параметрів — у бічній панелі",
            "Прогрес експерименту в реальному часі",
            "Таблиця метрик з кольоровими progress-барами",
            "Графіки збіжності CMA-ES, час навчання",
            "Експорт результатів у CSV",
            "Recovery після розриву websocket — стан зберігається на диск",
        ],
        "speech": (
            "Для зручної роботи реалізовано графічний дашборд на Streamlit. "
            "Запускається подвійним кліком на bat-файл. У боковій панелі "
            "користувач обирає датасет, моделі для порівняння, кількість "
            "фолдів, обмеження вибірки. Після натискання Запустити "
            "виконання йде з відображенням прогресу. Результати показуються "
            "у вигляді таблиці з адаптивними кольоровими індикаторами, "
            "графіка часу навчання та кривої збіжності для CMA-моделей. "
            "Передбачено експорт у CSV для звітування."
        ),
    },
    {
        "title": "Результати порівняння",
        "layout": "bullets",
        "bullets": [
            "PhiUSIIL: GAM і tuned_gam — Accuracy=1.00, F1=1.00, AUC=1.00",
            "Steel Plate: tuned_svm найкращий — F1=0.76, AUC=0.93",
            "Loan Approval: tuned_gam і tuned_svm — F1=0.43, AUC=0.71",
            "CMA-NN порівнянна з sklearn-моделями на простих задачах",
            "Для мультимодальних задач mixture-варіант перспективний",
            "tuned_* моделі стабільно покращують базові",
        ],
        "speech": (
            "Результати порівняння на трьох датасетах. На PhiUSIIL GAM "
            "і tuned_gam показали максимальні значення всіх трьох метрик. "
            "На Steel Plate Defects з 7 класами найкращим виявився "
            "tuned_svm з F1 0.76 і AUC 0.93. На задачі дефолту "
            "tuned_gam та tuned_svm дали F1 близько 0.43 при сильному "
            "дисбалансі класів. CMA-NN на простих задачах порівнянна зі "
            "sklearn-моделями. Очікую вищу ефективність методу зі сумішами "
            "на мультимодальних цільових функціях, що було теоретично "
            "обґрунтовано Літвінчук."
        ),
    },
    {
        "title": "Технологічний стек і тестування",
        "layout": "bullets",
        "bullets": [
            "Python 3.14, scikit-learn 1.4+, NumPy, pandas",
            "CMA-ES — пакет cma Hansen (класичний)",
            "Розширений CMA-ES — власна реалізація",
            "Streamlit — графічний інтерфейс",
            "MLflow — трекінг експериментів",
            "Pytest — автоматизовані тести (34 шт., усі проходять)",
            "Документація: NumPy-style docstrings + pdoc HTML + PDF + Word",
        ],
        "speech": (
            "Програма розроблена на Python 3.14 із використанням scikit-learn, "
            "NumPy і pandas. Класичний CMA-ES — обгортка над пакетом cma. "
            "Розширений CMA-ES зі сумішами — власна реалізація. Графічний "
            "інтерфейс — Streamlit, трекінг — MLflow. Програма покрита "
            "автоматизованими тестами pytest — 34 тести, всі проходять. "
            "Документація оформлена у трьох форматах: HTML API через pdoc, "
            "PDF-гайд зі схемами та формальна Word-документація для здачі."
        ),
    },
    {
        "title": "Висновки",
        "layout": "bullets",
        "bullets": [
            "Виконано всі вимоги куратора (12 моделей замість 5)",
            "Розділи 1 і 2 теорії втілені в коді та з'єднані через tuned_gam",
            "Реалізовано розширений CMA-ES за Літвінчук Ю.А. з фіксом "
            "колапсу дисперсії",
            "Програма має CLI і GUI, тести, MLflow-трекінг, "
            "формальну документацію",
            "Готова до публікації на GitHub і подальшого розвитку",
        ],
        "speech": (
            "Підбиваючи підсумки. Усі вимоги куратора виконано — і навіть "
            "перевиконано: замість п'яти методів реалізовано дванадцять. "
            "Обидва теоретичні розділи диплома, GAM і CMA-ES, втілені в "
            "коді, причому модель tuned_gam буквально об'єднує їх в одну. "
            "Розширений CMA-ES зі сумішами реалізовано за дисертацією "
            "Літвінчук з технічним доповненням для практичної стабільності. "
            "Програма має повний набір інтерфейсів, тестів і документації. "
            "Готова до подальшого розвитку та публікації."
        ),
    },
    {
        "title": "Дякую за увагу",
        "subtitle": "Готовий відповісти на ваші запитання",
        "layout": "title",
        "speech": (
            "Дякую за увагу. Готовий відповісти на ваші запитання."
        ),
    },
]


# ============================================================================
# pptx генератор

def _set_pptx_text(text_frame, text, *, size=24, bold=False, color=None, align=None):
    text_frame.clear()
    p = text_frame.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.name = "Calibri"
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color


def _add_bullets(text_frame, bullets, *, size=20):
    text_frame.clear()
    for i, line in enumerate(bullets):
        if i == 0:
            p = text_frame.paragraphs[0]
        else:
            p = text_frame.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line
        run.font.name = "Calibri"
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)


def _add_notes(slide, text):
    notes = slide.notes_slide.notes_text_frame
    notes.clear()
    p = notes.paragraphs[0]
    run = p.add_run()
    run.text = text


def _build_title_slide(prs, slide_data):
    layout = prs.slide_layouts[5]  # title only
    slide = prs.slides.add_slide(layout)

    # очистити дефолтні placeholder'и
    for shp in list(slide.shapes):
        if shp.has_text_frame:
            shp.text_frame.text = ""

    # ручний заголовок по центру
    title_box = slide.shapes.add_textbox(Cm(1), Cm(6), Cm(23), Cm(4))
    _set_pptx_text(title_box.text_frame, slide_data["title"],
                   size=44, bold=True, color=RGBColor(0x26, 0x46, 0x53),
                   align=PP_ALIGN.CENTER)

    if "subtitle" in slide_data:
        sub_box = slide.shapes.add_textbox(Cm(1), Cm(11), Cm(23), Cm(3))
        _set_pptx_text(sub_box.text_frame, slide_data["subtitle"],
                       size=24, color=RGBColor(0x44, 0x44, 0x44),
                       align=PP_ALIGN.CENTER)

    # автор знизу
    author_box = slide.shapes.add_textbox(Cm(1), Cm(17), Cm(23), Cm(1.5))
    _set_pptx_text(author_box.text_frame,
                   "Богдан Волошенюк   |   ЧНУ ім. Юрія Федьковича   |   2026",
                   size=14, color=RGBColor(0x77, 0x77, 0x77),
                   align=PP_ALIGN.CENTER)

    _add_notes(slide, slide_data["speech"])


def _build_bullets_slide(prs, slide_data):
    layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(layout)
    for shp in list(slide.shapes):
        if shp.has_text_frame:
            shp.text_frame.text = ""

    title_box = slide.shapes.add_textbox(Cm(1), Cm(0.7), Cm(23), Cm(1.8))
    _set_pptx_text(title_box.text_frame, slide_data["title"],
                   size=30, bold=True, color=RGBColor(0x26, 0x46, 0x53))

    bullets_box = slide.shapes.add_textbox(Cm(1.5), Cm(3.2), Cm(22), Cm(13))
    _add_bullets(bullets_box.text_frame, slide_data["bullets"], size=20)

    _add_notes(slide, slide_data["speech"])


def _build_image_slide(prs, slide_data):
    layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(layout)
    for shp in list(slide.shapes):
        if shp.has_text_frame:
            shp.text_frame.text = ""

    title_box = slide.shapes.add_textbox(Cm(1), Cm(0.7), Cm(23), Cm(1.8))
    _set_pptx_text(title_box.text_frame, slide_data["title"],
                   size=30, bold=True, color=RGBColor(0x26, 0x46, 0x53))

    img_path = FIGURES_DIR / slide_data["image"]
    if img_path.exists():
        # вставка з центруванням
        slide_w = prs.slide_width
        target_w = Cm(20)
        left = (slide_w - target_w) // 2
        top = Cm(3.5)
        slide.shapes.add_picture(str(img_path), left, top, width=target_w)
    else:
        msg = slide.shapes.add_textbox(Cm(2), Cm(8), Cm(20), Cm(2))
        _set_pptx_text(msg.text_frame,
                       f"[не знайдено зображення: {slide_data['image']}]",
                       size=18, color=RGBColor(0xaa, 0x00, 0x00))

    _add_notes(slide, slide_data["speech"])


def build_pptx(out_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = Cm(25.4)   # стандарт widescreen 16:9
    prs.slide_height = Cm(19.05)

    for slide_data in SLIDES:
        layout = slide_data.get("layout", "bullets")
        if layout == "title":
            _build_title_slide(prs, slide_data)
        elif layout == "image":
            _build_image_slide(prs, slide_data)
        else:
            _build_bullets_slide(prs, slide_data)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out_path))


# ============================================================================
# docx генератор (текст доповіді)

def _docx_set_run(run, *, size=12, bold=False, italic=False,
                  font="Times New Roman", color=None):
    run.font.name = font
    run.font.size = DocxPt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), font)
    rfonts.set(qn("w:hAnsi"), font)
    rfonts.set(qn("w:cs"), font)


def _docx_para(doc, text, *, size=12, bold=False, italic=False,
               align=None, indent=DocxCm(1.25), space=DocxPt(6)):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.first_line_indent = indent
    pf.space_after = space
    pf.line_spacing = 1.5
    run = p.add_run(text)
    _docx_set_run(run, size=size, bold=bold, italic=italic)
    return p


def _docx_heading(doc, text, level=1):
    sizes = {1: 16, 2: 14}
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if level > 1 else WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before = DocxPt(14)
    pf.space_after = DocxPt(8)
    pf.line_spacing = 1.15
    pf.keep_with_next = True
    run = p.add_run(text)
    _docx_set_run(run, size=sizes.get(level, 12), bold=True)


def build_docx(out_path: Path) -> None:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = DocxPt(12)
    for section in doc.sections:
        section.left_margin = DocxCm(2.5)
        section.right_margin = DocxCm(1.5)
        section.top_margin = DocxCm(2)
        section.bottom_margin = DocxCm(2)

    # титулка
    for _ in range(3):
        doc.add_paragraph()
    _docx_para(doc, "ТЕКСТ ДОПОВІДІ", size=22, bold=True,
               align=WD_ALIGN_PARAGRAPH.CENTER, indent=None,
               space=DocxPt(12))
    _docx_para(doc, "до захисту дипломної роботи бакалавра",
               size=14, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER,
               indent=None, space=DocxPt(20))
    _docx_para(doc,
        "Програмний модуль classification_cma_es — порівняння класифікаторів "
        "із застосуванням розширеного алгоритму CMA-ES",
        size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
        indent=None, space=DocxPt(60))
    _docx_para(doc, "Виконав: Богдан Волошенюк",
               size=12, align=WD_ALIGN_PARAGRAPH.CENTER,
               indent=None, space=DocxPt(4))
    _docx_para(doc, "Науковий керівник: Малик Ігор Володимирович",
               size=12, align=WD_ALIGN_PARAGRAPH.CENTER,
               indent=None, space=DocxPt(4))
    _docx_para(doc, "ЧНУ ім. Юрія Федьковича, 2026",
               size=12, align=WD_ALIGN_PARAGRAPH.CENTER,
               indent=None, space=DocxPt(20))

    doc.add_page_break()

    # інструкція доповідачу
    _docx_heading(doc, "Інструкція доповідачу", level=1)
    _docx_para(doc,
        "Загальна тривалість доповіді — приблизно сім хвилин. На кожен "
        "слайд відведено від 25 до 50 секунд. Говорити спокійним темпом, "
        "приблизно 130 слів на хвилину. Перед виступом одноразово прочитати "
        "вголос — щоб відчути ритм.")
    _docx_para(doc,
        "Перед слайдом 12 (Графічний інтерфейс) бажано підготувати "
        "відкритий заздалегідь дашборд у браузері — для живої демонстрації. "
        "Якщо проєктор слабкий або немає інтернету — обмежитись описом за "
        "слайдом.")
    _docx_para(doc,
        "Питання комісії очікувано стосуватимуться: (а) у чому новизна "
        "вашої роботи порівняно з дисертацією Літвінчук; (б) чому CMA-NN "
        "не завжди перемагає sklearn-моделі; (в) як обиралися датасети. "
        "Готові відповіді — у файлі guide.pdf, розділ FAQ для захисту.")

    doc.add_page_break()

    # текст по слайдах
    _docx_heading(doc, "Текст по слайдах", level=1)
    for i, slide_data in enumerate(SLIDES, start=1):
        _docx_heading(doc, f"Слайд {i}. {slide_data['title']}", level=2)

        # підказки що на слайді
        if slide_data.get("layout") == "image":
            _docx_para(doc, f"На слайді: схема ({slide_data['image']})",
                       italic=True, indent=None, space=DocxPt(4))
        elif "bullets" in slide_data:
            _docx_para(doc, "На слайді: маркований список:",
                       italic=True, indent=None, space=DocxPt(2))
            for b in slide_data["bullets"]:
                p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_after = DocxPt(2)
                p.paragraph_format.line_spacing = 1.15
                run = p.add_run(b)
                _docx_set_run(run, size=11)
            doc.add_paragraph()
        elif "subtitle" in slide_data:
            _docx_para(doc, f"На слайді: заголовок і підзаголовок "
                            f"({slide_data['subtitle']})",
                       italic=True, indent=None, space=DocxPt(4))

        # сама репліка
        _docx_para(doc, "Доповідь:", size=12, bold=True,
                   indent=None, space=DocxPt(2))
        _docx_para(doc, slide_data["speech"], size=12)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_path))


def main() -> int:
    PRESENTATION_DIR.mkdir(parents=True, exist_ok=True)

    print("Генерую PowerPoint...")
    build_pptx(PPTX_PATH)
    pptx_kb = PPTX_PATH.stat().st_size // 1024
    print(f"  OK: {PPTX_PATH} ({pptx_kb} KB)")

    print("Генерую текст доповіді (.docx)...")
    build_docx(DOCX_PATH)
    docx_kb = DOCX_PATH.stat().st_size // 1024
    print(f"  OK: {DOCX_PATH} ({docx_kb} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
