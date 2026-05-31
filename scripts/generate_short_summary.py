"""Коротка презентація (5 слайдів) — що зроблено по проєкту.

Не для захисту, а як summary-показ прогресу. Виводить файл
``../../presentation/short_summary.pptx``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm, Pt


REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT.parent / "presentation"
OUT_PATH = OUT_DIR / "short_summary.pptx"


SLIDES = [
    {
        "layout": "title",
        "title": "Дипломна робота бакалавра",
        "subtitle": "Підсумок виконаної роботи по проєкту",
        "footer": "Богдан Волошенюк   |   ЧНУ ім. Юрія Федьковича   |   2026",
    },
    {
        "layout": "bullets",
        "title": "1. Теоретична частина",
        "bullets": [
            "Розділ 1 — Узагальнені адитивні моделі (GAM): 6 підрозділів",
            "Розділ 2 — Алгоритм CMA-ES і його розширення: 6 підрозділів",
            "Опрацьовано матеріал дисертації Літвінчук Ю.А. (2024)",
            "Висновки по кожному розділу",
            "≈ 30 сторінок основного тексту",
        ],
    },
    {
        "layout": "bullets",
        "title": "2. Програмна реалізація (classification_cma_es)",
        "bullets": [
            "12 моделей: LogReg, SVM, kNN, MLP, GAM, CMA-NN classic/mixture, "
            "5 tuned-варіантів",
            "3 датасети: PhiUSIIL (2024), Steel Plate Defects, "
            "Default of Credit Card Clients",
            "Власна реалізація розширеного CMA-ES за дисертацією + "
            "технічна поправка cov_lr",
            "GUI на Streamlit, CLI, MLflow-трекінг, 34 тести pytest",
            "Код у відкритому репозиторії GitHub",
        ],
    },
    {
        "layout": "bullets",
        "title": "3. Розділи 3-4 диплома + матеріали",
        "bullets": [
            "Розділ 3 — Програмна реалізація (8 підрозділів)",
            "Розділ 4 — Результати експериментів (5 підрозділів)",
            "7 рисунків з реальних прогонів: confusion matrices, "
            "ROC-криві, коваріаційна матриця, збіжність CMA-ES",
            "9 математичних формул (GAM, EM-крок, CMA-ES, метрики)",
            "3 скрини дашборду + зведений графік 12 моделей",
        ],
    },
    {
        "layout": "bullets",
        "title": "4. Документація + підсумок",
        "bullets": [
            "Зміст з номерами сторінок, бібліографія (13 джерел)",
            "Фінальний диплом: 657 KB, 456 параграфів, 17 рисунків",
            "Додатково: PDF-гайд, HTML API через pdoc, "
            "Word-документація, презентація захисту",
            "GitHub: github.com/bohdanvolosheniuk1/classification_cma_es",
            "Проєкт повністю готовий до захисту",
        ],
    },
]


def _set_text(text_frame, text, *, size=24, bold=False, color=None,
              align=None):
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


def _set_bullets(text_frame, bullets, *, size=18):
    text_frame.clear()
    for i, line in enumerate(bullets):
        p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        run = p.add_run()
        run.text = line
        run.font.name = "Calibri"
        run.font.size = Pt(size)
        run.font.color.rgb = RGBColor(0x22, 0x22, 0x22)


def _clear_default(slide):
    for shape in list(slide.shapes):
        if shape.has_text_frame:
            shape.text_frame.text = ""


def _build_title_slide(prs, data):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    _clear_default(slide)

    box = slide.shapes.add_textbox(Cm(1), Cm(6.5), Cm(23), Cm(4))
    _set_text(box.text_frame, data["title"],
              size=40, bold=True, color=RGBColor(0x26, 0x46, 0x53),
              align=PP_ALIGN.CENTER)

    sub = slide.shapes.add_textbox(Cm(1), Cm(11), Cm(23), Cm(2.5))
    _set_text(sub.text_frame, data["subtitle"],
              size=22, color=RGBColor(0x44, 0x44, 0x44),
              align=PP_ALIGN.CENTER)

    foot = slide.shapes.add_textbox(Cm(1), Cm(17), Cm(23), Cm(1.5))
    _set_text(foot.text_frame, data["footer"],
              size=14, color=RGBColor(0x77, 0x77, 0x77),
              align=PP_ALIGN.CENTER)


def _build_bullets_slide(prs, data):
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    _clear_default(slide)

    title = slide.shapes.add_textbox(Cm(1), Cm(0.7), Cm(23), Cm(2))
    _set_text(title.text_frame, data["title"],
              size=32, bold=True, color=RGBColor(0x26, 0x46, 0x53))

    body = slide.shapes.add_textbox(Cm(1.5), Cm(3.5), Cm(22), Cm(14))
    _set_bullets(body.text_frame, data["bullets"], size=20)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Cm(25.4)
    prs.slide_height = Cm(19.05)

    for data in SLIDES:
        if data["layout"] == "title":
            _build_title_slide(prs, data)
        else:
            _build_bullets_slide(prs, data)

    prs.save(str(OUT_PATH))
    kb = OUT_PATH.stat().st_size // 1024
    print(f"Згенеровано: {OUT_PATH} ({kb} KB)")
    print(f"Слайдів: {len(SLIDES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
