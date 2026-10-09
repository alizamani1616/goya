# -*- coding: utf-8 -*-
"""کتابخانه پایه گویا — تابع‌های داخلی زبان

مثل وی‌بی: بگو (MsgBox متنی)، بپرس (InputBox)، و تاریخ شمسی از روز اول.
"""

import datetime
import random

from .errors import GoyaRuntimeError
from .normalize import to_latin_digits, to_persian_digits


class Builtin:
    """تابع داخلی — fn فهرست آرگومان‌ها رو می‌گیره"""

    def __init__(self, name, fn):
        self.name = name
        self.fn = fn


# ─── تبدیل تقویم میلادی → هجری شمسی (الگوریتم رایج jalaali) ───

_G_DAY_OF_MONTH = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def gregorian_to_jalali(gy, gm, gd):
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666
        + (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        + gd
        + _G_DAY_OF_MONTH[gm - 1]
    )
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


# ─── نمایش مقدارها ───

def display(v):
    """نمایش یک مقدار گویا به متن (با ارقام فارسی — هویت زبان)"""
    if v is None:
        return "پوچ"
    if v is True:
        return "درست"
    if v is False:
        return "غلط"
    if isinstance(v, int):
        return to_persian_digits(str(v))
    if isinstance(v, float):
        if v == int(v):
            return to_persian_digits(str(int(v)))
        return to_persian_digits(str(v)).replace(".", "٫")
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return "[" + "، ".join(display(item) for item in v) + "]"
    return str(v)


def _parse_number(v):
    """تبدیل متن به عدد — با ارقام فارسی هم کار می‌کنه"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        t = to_latin_digits(v.strip()).replace("٫", ".").replace(" ", "")
        if not t:
            return None
        try:
            return int(t)
        except ValueError:
            pass
        try:
            return float(t)
        except ValueError:
            return None
    return None


# ─── خود تابع‌های داخلی ───

def _bi_print(args):
    print(" ".join(display(a) for a in args))
    return None


def _default_input(prompt=""):
    try:
        return input(prompt)
    except EOFError:
        return ""


def _bi_len(args):
    if len(args) != 1:
        raise GoyaRuntimeError("طول() دقیقاً یک ورودی می‌خواد")
    v = args[0]
    if isinstance(v, (str, list)):
        return len(v)
    raise GoyaRuntimeError("طول() فقط با متن و لیست کار می‌کنه")


def _bi_num(args):
    if len(args) != 1:
        raise GoyaRuntimeError("عدد() دقیقاً یک ورودی می‌خواد")
    v = _parse_number(args[0])
    if v is None:
        raise GoyaRuntimeError('نشد «{}» رو عدد کنم'.format(display(args[0])))
    return v


def _bi_text(args):
    if len(args) != 1:
        raise GoyaRuntimeError("متن() دقیقاً یک ورودی می‌خواد")
    return display(args[0])


def _bi_round(args):
    if len(args) != 1:
        raise GoyaRuntimeError("گرد() دقیقاً یک ورودی می‌خواد")
    v = args[0]
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise GoyaRuntimeError("گرد() عدد می‌خواد")
    return round(v)


def _bi_random(args):
    if len(args) != 2:
        raise GoyaRuntimeError("تصادفی() دو ورودی می‌خواد: تصادفی(از، تا)")
    a, b = args[0], args[1]
    if (
        isinstance(a, bool) or isinstance(b, bool)
        or not isinstance(a, int) or not isinstance(b, int)
    ):
        raise GoyaRuntimeError("تصادفی() دو عدد صحیح می‌خواد")
    if a > b:
        raise GoyaRuntimeError("در تصادفی()، «از» نباید از «تا» بزرگ‌تر باشه")
    return random.randint(a, b)


def _bi_today(args):
    t = datetime.date.today()
    jy, jm, jd = gregorian_to_jalali(t.year, t.month, t.day)
    return to_persian_digits("{}/{:02d}/{:02d}".format(jy, jm, jd))


def _gui_int(v, what):
    """تبدیل محدود آرگومان مختصات/اندازه به عدد صحیح"""
    from .errors import GoyaRuntimeError
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise GoyaRuntimeError("{} باید عدد صحیح باشه".format(what))
    return int(v)


def _bi_form(args):
    from .gui import factory_form
    title = display(args[0]) if args else "برنامه گویا"
    w = _gui_int(args[1], "پهنای فرم") if len(args) > 1 else 420
    h = _gui_int(args[2], "ارتفاع فرم") if len(args) > 2 else 320
    return factory_form(title, w, h)


def _bi_button(args):
    from .gui import factory_button
    if len(args) < 3:
        raise GoyaRuntimeError("دکمه() سه ورودی می‌خواد: دکمه(\"متن\"، x، y)")
    return factory_button(display(args[0]), _gui_int(args[1], "x"), _gui_int(args[2], "y"))


def _bi_label(args):
    from .gui import factory_label
    if len(args) < 3:
        raise GoyaRuntimeError("برچسب() سه ورودی می‌خواد: برچسب(\"متن\"، x، y)")
    return factory_label(display(args[0]), _gui_int(args[1], "x"), _gui_int(args[2], "y"))


def _bi_textbox(args):
    from .gui import factory_textbox
    if len(args) < 3:
        raise GoyaRuntimeError("کادر() سه ورودی می‌خواد: کادر(\"راهنما\"، x، y)")
    return factory_textbox(display(args[0]), _gui_int(args[1], "x"), _gui_int(args[2], "y"))


def _bi_message(args):
    from .gui import show_message
    show_message(" ".join(display(a) for a in args) if args else "")
    return None


def install_builtins(env, input_fn=None):
    """ریختن تابع‌های داخلی تو محیط سراسری — بنویس و بگیر اسم مستعارن

    input_fn: جایگزین input() — محیط IDE ازش استفاده می‌کنه (صف ورودی).
    """
    if input_fn is None:
        input_fn = _default_input

    def _bi_input(args):
        prompt = display(args[0]) if args else ""
        try:
            return input_fn(prompt)
        except EOFError:
            return ""

    env.define("بگو", Builtin("بگو", _bi_print))
    env.define("بنویس", Builtin("بنویس", _bi_print))
    env.define("بپرس", Builtin("بپرس", _bi_input))
    env.define("بگیر", Builtin("بگیر", _bi_input))
    env.define("طول", Builtin("طول", _bi_len))
    env.define("عدد", Builtin("عدد", _bi_num))
    env.define("متن", Builtin("متن", _bi_text))
    env.define("گرد", Builtin("گرد", _bi_round))
    env.define("تصادفی", Builtin("تصادفی", _bi_random))
    env.define("امروز", Builtin("امروز", _bi_today))
    env.define("فرم", Builtin("فرم", _bi_form))
    env.define("دکمه", Builtin("دکمه", _bi_button))
    env.define("برچسب", Builtin("برچسب", _bi_label))
    env.define("کادر", Builtin("کادر", _bi_textbox))
    env.define("پیام", Builtin("پیام", _bi_message))
