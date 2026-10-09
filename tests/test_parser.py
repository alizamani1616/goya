# -*- coding: utf-8 -*-
import unittest

from goya.lexer import Lexer
from goya.parser import (
    Assign, Call, ExprStmt, ForRange, FuncDef, If, Parser, While,
)


def parse(src):
    return Parser(Lexer(src).lex()).parse()


class TestStatements(unittest.TestCase):
    def test_assignment(self):
        prog = parse("نام = «علی»")
        self.assertEqual(len(prog.statements), 1)
        st = prog.statements[0]
        self.assertIsInstance(st, Assign)
        self.assertEqual(st.name, "نام")

    def test_call_statement(self):
        prog = parse('بگو("سلام")')
        st = prog.statements[0]
        self.assertIsInstance(st, ExprStmt)
        self.assertIsInstance(st.expr, Call)
        self.assertEqual(st.expr.func.name, "بگو")

    def test_if_else(self):
        prog = parse("اگر درست\n    بگو(۱)\nوگرنه\n    بگو(۲)")
        st = prog.statements[0]
        self.assertIsInstance(st, If)
        self.assertEqual(len(st.then), 1)
        self.assertEqual(len(st.els), 1)

    def test_if_elif_chain(self):
        prog = parse("اگر غلط\n    بگو(۱)\nوگرنه اگر درست\n    بگو(۲)\nوگرنه\n    بگو(۳)")
        st = prog.statements[0]
        self.assertEqual(len(st.elifs), 1)

    def test_while(self):
        prog = parse("تا وقتی که غلط\n    بگو(۱)")
        self.assertIsInstance(prog.statements[0], While)

    def test_for_range(self):
        prog = parse("برای هر عدد از ۱ تا ۵\n    بگو(عدد)")
        self.assertIsInstance(prog.statements[0], ForRange)

    def test_func_def(self):
        prog = parse("تابع جمع(الف، ب)\n    برگردان الف + ب")
        st = prog.statements[0]
        self.assertIsInstance(st, FuncDef)
        self.assertEqual(st.params, ["الف", "ب"])

    def test_optional_colon(self):
        prog = parse("اگر درست:\n    بگو(۱)")
        self.assertIsInstance(prog.statements[0], If)

    def test_incomplete_block(self):
        from goya.errors import IncompleteInput
        with self.assertRaises(IncompleteInput):
            parse("اگر درست")

    def test_reserved_name(self):
        from goya.errors import GoyaSyntaxError
        with self.assertRaises(GoyaSyntaxError):
            parse("اگر = ۵")


if __name__ == "__main__":
    unittest.main()
