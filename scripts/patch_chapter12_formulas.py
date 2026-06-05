"""Замінює OMML-формули в розділах 1-2 на PNG з нумерацією.

OMML-формули, успадковані з оригінального .docx, погано рендеряться в
LibreOffice, Word на Mac та при PDF-конвертації. Натомість PNG-формули
працюють скрізь. Скрипт читає ``диплом 1_BACKUP_polished.docx``,
проходить по параграфам, замінює основні блочні формули на PNG із
нумерацією (1.1)–(1.9) та (2.1)–(2.5), а допоміжні короткі OMML-руни
у блоках «Де:» прибирає (вони і так дублюють опис змінних поряд).
Додатково вирівнює "Де:"-блоки на лівий край (зараз вони центровані).

Запуск::

    python scripts/patch_chapter12_formulas.py
"""

from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT.parent / "диплом 1_BACKUP_polished.docx"
DST = REPO_ROOT.parent / "диплом 1_BACKUP_final.docx"
FIGURES_DIR = REPO_ROOT.parent / "diploma_figures"


# Зіставлення позиції OMML-параграфа з PNG і номером формули.
# Позиції визначено через _dump-аналіз polished-файлу.
# Решта OMML-параграфів — це короткі inline-руни в "Де:"-блоках,
# їх просто видаляємо.
FORMULA_MAP = {
    12:  ("formula_1_1_additive.png", "(1.1)", 11.0),
    20:  ("formula_1_2_linear.png",   "(1.2)", 13.0),
    25:  ("formula_1_3_gam_link.png", "(1.3)", 12.0),
    37:  ("formula_1_4_basis.png",    "(1.4)", 10.0),
    46:  ("formula_1_5_poly.png",     "(1.5)", 13.0),
    74:  ("formula_1_6_loss.png",     "(1.6)", 11.0),
    91:  ("formula_1_3_gam_link.png", "(1.3)", 12.0),  # повторне посилання
    99:  ("formula_1_7_identity.png", "(1.7)",  6.0),
    105: ("formula_1_8_log.png",      "(1.8)",  7.0),
    112: ("formula_1_9_logit.png",    "(1.9)",  8.0),
    156: ("formula_2_1_sample.png",   "(2.1)", 12.0),
    170: ("formula_2_2_sample2.png",  "(2.2)", 11.0),
    180: ("formula_2_3_mean.png",     "(2.3)", 11.0),
    190: ("formula_2_1_sample.png",   "(2.1)", 12.0),  # повторне посилання
    200: ("formula_2_3_mean.png",     "(2.3)", 11.0),  # повторне посилання
    215: ("formula_2_4_cov.png",      "(2.4)", 15.0),
    234: ("formula_2_5_sigma.png",    "(2.5)", 14.0),
}


def _para_has_block_formula(p) -> bool:
    return "<m:oMathPara" in p._p.xml


def _para_has_inline_math(p) -> bool:
    return "<m:oMath" in p._p.xml and "<m:oMathPara" not in p._p.xml


def _clear_paragraph(p) -> None:
    """Видаляє всі дочірні елементи параграфа, окрім pPr."""
    p_elem = p._p
    pPr = p_elem.find(qn("w:pPr"))
    for child in list(p_elem):
        if child.tag != qn("w:pPr"):
            p_elem.remove(child)


def _insert_png_with_number(p, png_path: Path, number: str,
                            width_cm: float) -> None:
    """Перетворює параграф на: [PNG по центру] [tab] [номер праворуч]."""
    _clear_paragraph(p)
    pf = p.paragraph_format
    pf.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    pf.first_line_indent = Cm(0)
    pf.left_indent = Cm(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    # tab stop праворуч для номера
    pf.tab_stops.add_tab_stop(Cm(16.0), WD_PARAGRAPH_ALIGNMENT.RIGHT)
    # картинка
    run_pic = p.add_run()
    run_pic.add_picture(str(png_path), width=Cm(width_cm))
    # таб + номер
    run_num = p.add_run(f"\t{number}")
    run_num.font.name = "Times New Roman"
    run_num.font.size = Pt(14)


def _is_where_marker(text: str) -> bool:
    """Чи це параграф з 'Де:' маркером."""
    t = text.strip().lower()
    return t in ("де:", "де :")


def _is_where_definition(text: str) -> bool:
    """Чи це рядок-визначення змінної з '-' маркером."""
    t = text.lstrip()
    return t.startswith("-") or t.startswith("—") or t.startswith("–")


def _align_left(p) -> None:
    """Вирівнює параграф на лівий край і прибирає first_line_indent."""
    pf = p.paragraph_format
    pf.alignment = WD_PARAGRAPH_ALIGNMENT.LEFT
    pf.first_line_indent = Cm(0)
    pf.left_indent = Cm(0.75)


def main() -> int:
    if not SRC.exists():
        print(f"ПОМИЛКА: {SRC} не знайдено", file=sys.stderr)
        return 1

    doc = Document(SRC)
    paragraphs = list(doc.paragraphs)

    n_replaced = 0
    n_removed = 0
    n_aligned = 0

    for i, p in enumerate(paragraphs):
        text = p.text.strip()

        # 1. Замінити цільові формули на PNG з нумерацією
        if i in FORMULA_MAP:
            png_name, number, width_cm = FORMULA_MAP[i]
            png_path = FIGURES_DIR / png_name
            if not png_path.exists():
                print(f"  ПОПЕРЕДЖЕННЯ: {png_path} не знайдено")
                continue
            _insert_png_with_number(p, png_path, number, width_cm)
            n_replaced += 1
            continue

        # 2. Видалити решту OMML-параграфів (короткі змінні в "Де:")
        if _para_has_block_formula(p):
            _clear_paragraph(p)
            n_removed += 1
            continue

        # 3. Вирівняти "Де:"-блоки та визначення на лівий край
        if _is_where_marker(text) or _is_where_definition(text):
            _align_left(p)
            n_aligned += 1

    doc.save(DST)
    print(f"Замінено формул на PNG : {n_replaced}")
    print(f"Прибрано порожніх OMML : {n_removed}")
    print(f"Вирівняно 'Де:'-рядків : {n_aligned}")
    print(f"Збережено: {DST.name} ({DST.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
