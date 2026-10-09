# -*- coding: utf-8 -*-
import unittest

from goya.lexer import Lexer
from goya.normalize import to_latin_digits


def types_of(src):
    return [t.type for t in Lexer(src).lex()]


class TestNumbers(unittest.TestCase):
    def test_persian_digits(self):
        toks = Lexer("۱۲۳").lex()
        self.assertEqual(toks[0].type, "NUM")
        self.assertEqual(toks[0].value, 123)

    def test_latin_digits(self):
        toks = Lexer("45").lex()
        self.assertEqual(toks[0].value, 45)

    def test_decimal_persian(self):
        toks = Lexer("۲٫۵").lex()
        self.assertEqual(toks[0].value, 2.5)

    def test_decimal_latin(self):
        toks = Lexer("3.14").lex()
        self.assertEqual(toks[0].value, 3.14)

    def test_arabic_digits_normalized(self):
        toks = Lexer("٤٥").lex()  # ارقام عربی
        self.assertEqual(toks[0].value, 45)


class TestStrings(unittest.TestCase):
    def test_double_quote(self):
        toks = Lexer('"سلام دنیا"').lex()
        self.assertEqual(toks[0].type, "STR")
        self.assertEqual(toks[0].value, "سلام دنیا")

    def test_guillemet(self):
        toks = Lexer("«سلام»").lex()
        self.assertEqual(toks[0].value, "سلام")

    def test_escapes(self):
        toks = Lexer(r'"الف\nب"').lex()
        self.assertEqual(toks[0].value, "الف\nب")


class TestNamesAndKeywords(unittest.TestCase):
    def test_arabic_chars_normalized(self):
        toks = Lexer("علي").lex()  # با ی عربی
        self.assertEqual(toks[0].value, "علی")

    def test_while_phrase_merged(self):
        toks = Lexer("تا وقتی که درست").lex()
        self.assertEqual(toks[0].value, "تا وقتی که")
        self.assertEqual(toks[0].type, "NAME")

    def test_zwnj_keyword_variant(self):
        # نیم‌فاصله داخل یک کلمه‌ی عبارت کلمه‌ای: بزرگ‌تر از == بزرگتر از
        toks = Lexer("بزرگ‌تر از ۳").lex()
        self.assertEqual(toks[0].value, "بزرگتر از")

    def test_comparison_phrase(self):
        toks = Lexer("عدد بزرگتر از ۳").lex()
        self.assertEqual(toks[1].value, "بزرگتر از")

    def test_latin_ident_rejected(self):
        from goya.errors import GoyaSyntaxError
        with self.assertRaises(GoyaSyntaxError):
            Lexer("x = ۵").lex()


class TestMisc(unittest.TestCase):
    def test_comment_line_skipped(self):
        self.assertEqual(types_of("## این کامنته\nبگو(۱)"), ["NAME", "OP", "NUM", "OP", "NEWLINE", "EOF"])

    def test_trailing_comment(self):
        toks = Lexer("بگو(۱) ## توضیح").lex()
        self.assertEqual([t.type for t in toks], ["NAME", "OP", "NUM", "OP", "NEWLINE", "EOF"])

    def test_persian_comma(self):
        toks = Lexer("[۱، ۲]").lex()
        self.assertEqual([t.type for t in toks], ["OP", "NUM", "OP", "NUM", "OP", "NEWLINE", "EOF"])

    def test_indent_dedent(self):
        src = "اگر درست\n    بگو(۱)\nبگو(۲)"
        kinds = [(t.type, to_latin_digits(str(t.value)) if t.value else t.type)
                 for t in Lexer(src).lex()]
        kinds = [t[0] for t in kinds]
        self.assertEqual(
            kinds,
            ["NAME", "NAME", "NEWLINE", "INDENT", "NAME", "OP", "NUM", "OP",
             "NEWLINE", "DEDENT", "NAME", "OP", "NUM", "OP", "NEWLINE", "EOF"],
        )

    def test_unterminated_string(self):
        from goya.errors import GoyaSyntaxError
        with self.assertRaises(GoyaSyntaxError):
            Lexer('"سلام').lex()


if __name__ == "__main__":
    unittest.main()
