# -*- coding: utf-8 -*-
"""توکنایزر گویا: متن فارسی → فهرست توکن‌ها

سطرمحور با تورفتگی (مثل پایتون): INDENT/DEDENT تولید می‌کنه.
رشته‌ها هم با "..." و هم با «...» قبولن. اعداد با ارقام فارسی یا لاتین.
"""

from .errors import GoyaSyntaxError, IncompleteInput
from .normalize import normalize_name, strip_zwnj, to_latin_digits

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ALL_DIGITS = PERSIAN_DIGITS + ARABIC_DIGITS + "0123456789"
DECIMALS = ".٫"
ARABIC_COMMA = "،"

# عبارت‌های چندکلمه‌ای که باید یکی بشن (اپراتورهای کلمه‌ای)
PHRASES = [
    ("تا", "وقتی", "که"),
    ("برای", "هر"),
    ("بزرگتر", "از"),
    ("کوچکتر", "از"),
    ("بزرگتر", "مساوی"),
    ("کوچکتر", "مساوی"),
    ("تقسیم", "بر"),
]
PHRASE_STARTS = {p[0] for p in PHRASES}


class Token:
    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_, value, line, col=0):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return "Token({}, {!r})".format(self.type, self.value)


def _is_ident_start(c):
    return ("\u0600" <= c <= "\u06FF" and c != ARABIC_COMMA) or c == "_"


def _is_ident_part(c):
    return _is_ident_start(c) or c == "\u200c" or c in ALL_DIGITS


def _is_digit(c):
    return c in ALL_DIGITS


def _merge_phrases(tokens):
    """ادغام عبارت‌های کلمه‌ای مجاور: بزرگتر + از → «بزرگتر از»"""
    out = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.type == "NAME":
            key = strip_zwnj(t.value)
            if key in PHRASE_STARTS:
                merged = False
                for phrase in PHRASES:
                    if phrase[0] != key:
                        continue
                    rest = phrase[1:]
                    ok = True
                    for j, part in enumerate(rest):
                        if i + 1 + j >= len(tokens):
                            ok = False
                            break
                        nt = tokens[i + 1 + j]
                        if nt.type != "NAME" or strip_zwnj(nt.value) != part:
                            ok = False
                            break
                    if ok:
                        out.append(Token("NAME", " ".join(phrase), t.line, t.col))
                        i += 1 + len(rest)
                        merged = True
                        break
                if merged:
                    continue
        out.append(t)
        i += 1
    return out


class Lexer:
    def __init__(self, source):
        self.lines = source.splitlines()
        self.tokens = []
        self.indents = [0]
        self.paren_depth = 0
        self.line_no = 0

    def _emit(self, type_, value, col=0):
        self.tokens.append(Token(type_, value, self.line_no, col))

    def _error(self, msg, col=None):
        raise GoyaSyntaxError(msg, self.line_no)

    def lex(self):
        for raw in self.lines:
            self.line_no += 1
            self._lex_line(raw)

        if self.paren_depth > 0:
            raise IncompleteInput("پرانتز بسته نشده", self.line_no)

        # تورفتگی‌های باز مانده در انتهای فایل بسته می‌شن (مثل پایتون)
        while len(self.indents) > 1:
            self.indents.pop()
            self._emit("DEDENT", None)
        self._emit("EOF", None)
        return _merge_phrases(self.tokens)

    def _lex_line(self, raw):
        expanded = raw.replace("\t", "    ")
        if not expanded.strip():
            return

        n = len(expanded) - len(expanded.lstrip(" "))
        content = expanded[n:]

        # سطر کامنت کامل
        if content.startswith("#"):
            return

        # مدیریت تورفتگی نسبت به پشته
        cur = self.indents[-1]
        if n > cur:
            self.indents.append(n)
            self._emit("INDENT", n)
        elif n < cur:
            while len(self.indents) > 1 and self.indents[-1] > n:
                self.indents.pop()
                self._emit("DEDENT", None)
            if self.indents[-1] != n:
                self._error("تورفتگی این سطر با هیچ سطری هم‌تراز نیست")

        self._scan(content)

        if self.paren_depth == 0:
            self._emit("NEWLINE", None)

    def _scan(self, content):
        i = 0
        L = len(content)
        while i < L:
            c = content[i]

            if c == " ":
                i += 1
                continue

            # کامنت انتهای سطر
            if c == "#":
                break

            # رشته با "
            if c == '"':
                i += 1
                start = i
                buf = []
                while i < L and content[i] != '"':
                    ch = content[i]
                    if ch == "\\" and i + 1 < L:
                        nxt = content[i + 1]
                        if nxt == "n":
                            buf.append("\n")
                        elif nxt == "t":
                            buf.append("\t")
                        elif nxt == '"':
                            buf.append('"')
                        elif nxt == "\\":
                            buf.append("\\")
                        else:
                            buf.append(ch)
                            buf.append(nxt)
                        i += 2
                        continue
                    buf.append(ch)
                    i += 1
                if i >= L:
                    self._error("رشته بسته نشده — گیومه جا مونده")
                i += 1  # گیومه پایانی
                self._emit("STR", "".join(buf), start)
                continue

            # رشته با «...» — بدون کاراکتر کنترلی
            if c == "«":
                end = content.find("»", i + 1)
                if end == -1:
                    self._error("رشته بسته نشده — «» جا مونده")
                self._emit("STR", content[i + 1 : end], i)
                i = end + 1
                continue

            # عدد
            if _is_digit(c):
                start = i
                while i < L and _is_digit(content[i]):
                    i += 1
                if i < L and content[i] in DECIMALS:
                    if i + 1 < L and _is_digit(content[i + 1]):
                        i += 1
                        while i < L and _is_digit(content[i]):
                            i += 1
                    else:
                        self._error("بعد از ممیز باید رقم بیاد")
                text = to_latin_digits(content[start:i]).replace("٫", ".")
                value = float(text) if "." in text else int(text)
                self._emit("NUM", value, start)
                continue

            # ویرگول فارسی یا لاتین
            if c == "," or c == ARABIC_COMMA:
                self._emit("OP", ",", i)
                i += 1
                continue

            # شناسه / کلیدواژه
            if _is_ident_start(c):
                start = i
                while i < L and _is_ident_part(content[i]):
                    i += 1
                self._emit("NAME", normalize_name(content[start:i]), start)
                continue

            if ("a" <= c <= "z") or ("A" <= c <= "Z"):
                self._error("شناسه‌های گویا فارسی‌ان — حروف لاتین مجاز نیستن")

            if c in "([{":
                self.paren_depth += 1
                self._emit("OP", c, i)
                i += 1
                continue
            if c in ")]}":
                self.paren_depth = max(0, self.paren_depth - 1)
                self._emit("OP", c, i)
                i += 1
                continue
            if c in "+-*":
                self._emit("OP", c, i)
                i += 1
                continue
            if c == "/":
                self._emit("OP", "/", i)
                i += 1
                continue
            if c == "%":
                self._emit("OP", "%", i)
                i += 1
                continue
            if c == "<" or c == ">":
                if i + 1 < L and content[i + 1] == "=":
                    self._emit("OP", c + "=", i)
                    i += 2
                else:
                    self._emit("OP", c, i)
                    i += 1
                continue
            if c == "=":
                if i + 1 < L and content[i + 1] == "=":
                    self._emit("OP", "==", i)
                    i += 2
                else:
                    self._emit("OP", "=", i)
                    i += 1
                continue
            if c == "!":
                if i + 1 < L and content[i + 1] == "=":
                    self._emit("OP", "!=", i)
                    i += 2
                else:
                    self._error('منظورت "!=" بود؟')
                continue
            if c == ":":
                self._emit("OP", ":", i)
                i += 1
                continue

            self._error('کاراکتر ناشناخته "{}"'.format(c))
