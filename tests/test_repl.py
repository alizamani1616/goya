# -*- coding: utf-8 -*-
"""تست‌های محیط تعاملی (REPL)"""

import contextlib
import io
import unittest
from unittest import mock

from goya import repl


def run_repl(lines):
    """REPL را با سطرهای داده‌شده اجرا می‌کند و خروجی چاپ‌شده را برمی‌گرداند."""
    it = iter(lines)

    def fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    buf = io.StringIO()
    with mock.patch("builtins.input", fake_input):
        with contextlib.redirect_stdout(buf):
            repl.start()
    return buf.getvalue()


class ReplTests(unittest.TestCase):

    def test_function_definition_spans_lines(self):
        """تعریف چندسطری تابع باید ادامه‌ی ورودی حساب بشه و صدا زدنش جواب بده."""
        out = run_repl([
            "تابع مربع(عدد)",
            "    برگردان عدد * عدد",
            "",
            "مربع(۷)",
        ])
        self.assertIn("۴۹", out)

    def test_expression_is_echoed(self):
        out = run_repl(["۲ + ۳ * ۴"])
        self.assertIn("=> ۱۴", out)

    def test_null_result_is_not_echoed(self):
        """مقدار پوچ در REPL چاپ نمی‌شه (مثل پایتون)."""
        out = run_repl(["بگو(۲ + ۳ * ۴)"])
        self.assertIn("۱۴", out)
        self.assertNotIn("=> پوچ", out)

    def test_empty_line_in_incomplete_block_keeps_buffer(self):
        """سطر خالی وسط بلوک ناتمام، ورودی کاربر رو دور نمی‌ریزه."""
        out = run_repl([
            "تابع جمع(الف، ب)",
            "",
            "    برگردان الف + ب",
            "",
            "جمع(۲، ۳)",
        ])
        self.assertIn("ناقصه", out)
        self.assertIn("=> ۵", out)


if __name__ == "__main__":
    unittest.main()
