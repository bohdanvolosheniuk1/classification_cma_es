"""OMML (Office Math Markup Language) helpers для нативних формул Word.

Word має власний редактор формул, який зберігає формули як XML у
просторі імен ``http://schemas.openxmlformats.org/officeDocument/2006/math``
(скорочено ``m:``). Цей модуль дає невеликий набір функцій, з яких
можна збирати справжні Word-формули — Word відображає їх як живі
рівняння, які можна редагувати кліком.

Базові ідеї:

* :func:`run` — звичайний фрагмент формули (літера, число, оператор).
  За замовчуванням літери в курсиві (як прийнято в математиці).
* :func:`sub`, :func:`sup`, :func:`sub_sup` — нижній/верхній/обидва індекси.
* :func:`frac` — дріб.
* :func:`nary` — сума, інтеграл, добуток та інші n-арні оператори.
* :func:`fenced` — вираз у дужках з автоматичним підлаштуванням розміру.
* :func:`omath` — контейнер inline-формули.
* :func:`add_block_formula` — додає блочну центровану формулу новим
  параграфом.
* :func:`add_inline_formula` — додає inline-формулу в існуючий параграф.
"""

from __future__ import annotations

from typing import Iterable

from docx.oxml import OxmlElement
from docx.oxml.ns import qn


# ----- низькорівневі ----------------------------------------------------------

def _m(tag: str):
    """Створити math-елемент з префіксом m:."""
    return OxmlElement(f"m:{tag}")


def _set_val(elem, attr: str, value: str) -> None:
    elem.set(qn(f"m:{attr}"), value)


# ----- публічне API ----------------------------------------------------------

def run(text: str, *, italic: bool = True):
    """Базовий run у формулі.

    Parameters
    ----------
    text : str
        Текст (літера, число, оператор).
    italic : bool, default=True
        Якщо False — текст відображається прямим шрифтом (для функцій
        типу sin, log або текстових позначень).
    """
    r = _m("r")
    if not italic:
        rpr = _m("rPr")
        sty = _m("sty")
        _set_val(sty, "val", "p")
        rpr.append(sty)
        r.append(rpr)
    t = _m("t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    r.append(t)
    return r


def sub(base, idx):
    """Індекс знизу: x_i."""
    ss = _m("sSub")
    e = _m("e")
    e.append(base)
    s = _m("sub")
    s.append(idx)
    ss.append(e)
    ss.append(s)
    return ss


def sup(base, exp):
    """Індекс зверху: x^2."""
    ss = _m("sSup")
    e = _m("e")
    e.append(base)
    s = _m("sup")
    s.append(exp)
    ss.append(e)
    ss.append(s)
    return ss


def sub_sup(base, idx, exp):
    """І знизу, і зверху: x_i^2."""
    ss = _m("sSubSup")
    e = _m("e")
    e.append(base)
    s = _m("sub")
    s.append(idx)
    p = _m("sup")
    p.append(exp)
    ss.append(e)
    ss.append(s)
    ss.append(p)
    return ss


def frac(num, den):
    """Дріб."""
    f = _m("f")
    n = _m("num")
    n.append(num)
    d = _m("den")
    d.append(den)
    f.append(n)
    f.append(d)
    return f


def nary(symbol: str, lower, upper, body, *, no_limit=False):
    """N-арний оператор (сума, добуток, інтеграл).

    Parameters
    ----------
    symbol : str
        Символ оператора (∑, ∏, ∫, ⊕, …).
    lower, upper :
        Нижній і верхній індекси оператора (можуть бути None).
    body :
        Підінтегральний вираз / тіло суми.
    no_limit : bool
        Якщо True — індекси розміщуються поряд з оператором, а не зверху/знизу.
    """
    n = _m("nary")
    pr = _m("naryPr")
    chr_elem = _m("chr")
    _set_val(chr_elem, "val", symbol)
    pr.append(chr_elem)
    if no_limit:
        lim = _m("limLoc")
        _set_val(lim, "val", "subSup")
        pr.append(lim)
    n.append(pr)
    if lower is not None:
        s = _m("sub")
        s.append(lower)
        n.append(s)
    if upper is not None:
        s = _m("sup")
        s.append(upper)
        n.append(s)
    if body is not None:
        e = _m("e")
        e.append(body)
        n.append(e)
    return n


def fenced(content, *, left: str = "(", right: str = ")"):
    """Вираз у дужках з автоматичним підлаштуванням розміру."""
    d = _m("d")
    pr = _m("dPr")
    if left != "(":
        b = _m("begChr")
        _set_val(b, "val", left)
        pr.append(b)
    if right != ")":
        b = _m("endChr")
        _set_val(b, "val", right)
        pr.append(b)
    d.append(pr)
    e = _m("e")
    e.append(content)
    d.append(e)
    return d


def group(*children):
    """Згрупувати кілька елементів у один контейнер.

    Якщо в одне місце потрібно вставити кілька run-ів або інших math-
    елементів (наприклад, у дріб у чисельник — а+b), використовуємо
    цю функцію для побудови групи.
    """
    e = _m("e")
    for c in children:
        e.append(c)
    return e


def omath(*children):
    """Контейнер inline-формули (<m:oMath>)."""
    m = _m("oMath")
    for c in children:
        m.append(c)
    return m


# ----- високорівневі: додавання в документ -----------------------------------

def add_inline_formula(paragraph, *children) -> None:
    """Додати inline-формулу в існуючий параграф.

    Створює <m:oMath> із заданих math-елементів та append'ить його
    у XML-дерево параграфа.
    """
    m = omath(*children)
    paragraph._p.append(m)


def add_block_formula(doc, *children, center: bool = True):
    """Додати центровану блочну формулу новим параграфом.

    Повертає створений параграф.
    """
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = None
    pf.space_after = None
    # math paragraph wrapper
    omath_para = _m("oMathPara")
    if center:
        para_pr = _m("oMathParaPr")
        jc = _m("jc")
        _set_val(jc, "val", "center")
        para_pr.append(jc)
        omath_para.append(para_pr)
    inner = omath(*children)
    omath_para.append(inner)
    p._p.append(omath_para)
    return p


# ----- скорочення для зручності ---------------------------------------------

def r_var(name: str):
    """Скорочення для математичної змінної (italic)."""
    return run(name, italic=True)


def r_op(text: str):
    """Скорочення для оператора чи цифри (прямий шрифт)."""
    return run(text, italic=False)


def r_text(text: str):
    """Скорочення для текстового позначення (прямий шрифт)."""
    return run(text, italic=False)
