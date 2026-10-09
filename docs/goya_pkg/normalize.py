# -*- coding: utf-8 -*-
"""نرمال‌سازی متن فارسی

هم‌ارز کردن حروف عربی/فارسی و ارقام فارسی/عربی/لاتین،
تا کاربر با هر کیبوردی تایپ کنه نتیجه یکی باشه.
"""

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"

# حروف عربی → فارسی، حذف کشیده (تطویل)، ارقام عربی و لاتین → فارسی
_TO_PERSIAN = str.maketrans(
    {
        "ي": "ی",
        "ك": "ک",
        "ى": "ی",
        "ـ": "",
        **{d: _PERSIAN_DIGITS[i] for i, d in enumerate("٠١٢٣٤٥٦٧٨٩")},
        **{str(i): _PERSIAN_DIGITS[i] for i in range(10)},
    }
)

_TO_LATIN = str.maketrans(
    {
        **{d: str(i) for i, d in enumerate("٠١٢٣٤٥٦٧٨٩")},
        **{p: str(i) for i, p in enumerate(_PERSIAN_DIGITS)},
    }
)
_TO_FA_DIGITS = str.maketrans({str(i): p for i, p in enumerate(_PERSIAN_DIGITS)})


def normalize_name(text):
    """نرمال‌سازی شناسه‌ها و کلیدواژه‌ها (محتوای رشته‌ها دست‌نخورده می‌مونه)"""
    return text.translate(_TO_PERSIAN)


def strip_zwnj(text):
    """حذف نیم‌فاصله — برای مقایسه کلیدواژه‌ها (بزرگ‌تر == بزرگتر)"""
    return text.replace("\u200c", "")


def to_latin_digits(text):
    return text.translate(_TO_LATIN)


def to_persian_digits(text):
    return text.translate(_TO_FA_DIGITS)
