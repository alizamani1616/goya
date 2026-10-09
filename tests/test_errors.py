# -*- coding: utf-8 -*-
import unittest

from goya.errors import GoyaSyntaxError, IncompleteInput, show_error
from goya.lexer import Lexer
from goya.parser import Parser


def parse(src):
    return Parser(Lexer(src).lex()).parse()


class TestErrorMessages(unittest.TestCase):
    def test_syntax_error_line_number(self):
        try:
            parse("بگو(۱)\nبگو(۲\n")
        except GoyaSyntaxError as e:
            shown = show_error(e, "بگو(۱)\nبگو(۲\n")
            self.assertIn("سطر", shown)
            self.assertIn("بگو(۲", shown)
        else:
            self.fail("خطای نگارشی انتظار می‌رفت")

    def test_error_line_shown_in_output(self):
        try:
            parse("جمع = ۱\nبگو(جمع\n")
        except GoyaSyntaxError as e:
            shown = show_error(e, "جمع = ۱\nبگو(جمع\n")
            self.assertIn("خطای نگارشی", shown)
        else:
            self.fail("خطای نگارشی انتظار می‌رفت")

    def test_incomplete_single_line_if(self):
        with self.assertRaises(IncompleteInput):
            parse("اگر درست")

    def test_unbalanced_paren_incomplete(self):
        with self.assertRaises(IncompleteInput):
            parse('بگو("سلام"')

    def test_bad_indent(self):
        with self.assertRaises(GoyaSyntaxError):
            parse("اگر درست\n    بگو(۱)\n  بگو(۲)")

    def test_decimal_without_digit(self):
        with self.assertRaises(GoyaSyntaxError):
            parse("بگو(۲.)")


if __name__ == "__main__":
    unittest.main()
