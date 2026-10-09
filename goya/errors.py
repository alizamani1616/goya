# -*- coding: utf-8 -*-
"""خطاهای گویا — همه پیام‌ها فارسی و آدم‌فهم"""

from .normalize import to_persian_digits


class GoyaError(Exception):
    """پایه همه خطاهای گویا"""

    kind = "خطا"

    def __init__(self, message, line=None):
        super().__init__(message)
        self.message = message
        self.line = line


class GoyaSyntaxError(GoyaError):
    kind = "خطای نگارشی"


class GoyaRuntimeError(GoyaError):
    kind = "خطای اجرا"


class IncompleteInput(GoyaSyntaxError):
    """ورودی هنوز تموم نشده — REPL از این استفاده می‌کنه تا چند سطری بخونه"""

    def __init__(self, message="ورودی ناتمام است", line=None):
        super().__init__(message, line)


def _fa_num(n):
    return to_persian_digits(str(n))


def show_error(err, source=""):
    """نمایش خطا به شکل خوانا: شماره سطر + پیام فارسی + خود سطر خطادار"""
    if err.line is not None:
        head = "{} در سطر {}: {}".format(err.kind, _fa_num(err.line), err.message)
    else:
        head = "{}: {}".format(err.kind, err.message)

    lines = source.splitlines() if source else []
    if err.line is not None and 1 <= err.line <= len(lines):
        return "{}\n\n    {}\n".format(head, lines[err.line - 1])
    return head
