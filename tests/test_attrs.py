# -*- coding: utf-8 -*-
"""دسترسی نقطه‌ای به ویژگی‌ها — فاز ۱ گویا استودیو"""
import io
import contextlib
import unittest

from goya.errors import GoyaPropError, GoyaRuntimeError, GoyaSyntaxError
from goya.interpreter import Interpreter
from goya.lexer import Lexer
from goya.parser import Attr, AttrAssign, Parser


class FakeControl:
    """شیء کنترل ساختگی — بدون هیچ وابستگی گرافیکی"""

    def __init__(self):
        self.goya_name = None
        self.props = {}

    def goya_get(self, name):
        if name in self.props:
            return self.props[name]
        raise GoyaPropError("ویژگی «{}» نیست".format(name))

    def goya_set(self, name, value):
        self.props[name] = value

    def goya_set_name(self, name):
        self.goya_name = name


def run_with(control, source):
    interp = Interpreter()
    interp.global_env.define("کادر۱", control)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        program = Parser(Lexer(source).lex()).parse()
        interp.run(program)
    return interp, buf.getvalue()


class TestLexerDot(unittest.TestCase):
    def test_dot_token(self):
        toks = Lexer("کادر۱.متن").lex()
        self.assertEqual([t.type for t in toks], ["NAME", "OP", "NAME", "NEWLINE", "EOF"])
        self.assertEqual(toks[1].value, ".")

    def test_decimal_not_broken(self):
        toks = Lexer("۲.۵").lex()
        self.assertEqual(toks[0].type, "NUM")
        self.assertEqual(toks[0].value, 2.5)


class TestParserDot(unittest.TestCase):
    def test_attr_expression(self):
        prog = Parser(Lexer("بگو(کادر۱.متن)").lex()).parse()
        call = prog.statements[0].expr
        self.assertEqual(call.args[0].name, "متن")
        self.assertEqual(call.args[0].obj.name, "کادر۱")

    def test_attr_assignment(self):
        prog = Parser(Lexer('کادر۱.متن = "سلام"').lex()).parse()
        st = prog.statements[0]
        self.assertIsInstance(st, AttrAssign)
        self.assertEqual(st.name, "متن")

    def test_reserved_attr_rejected(self):
        with self.assertRaises(GoyaSyntaxError):
            Parser(Lexer("کادر۱.اگر").lex()).parse()

    def test_dot_without_name(self):
        with self.assertRaises(GoyaSyntaxError):
            Parser(Lexer("کادر۱. = ۵").lex()).parse()


class TestInterpreterDot(unittest.TestCase):
    def test_write_and_read_attr(self):
        ctrl = FakeControl()
        interp, out = run_with(ctrl, 'کادر۱.متن = "سلام"\nبگو(کادر۱.متن)')
        self.assertEqual(ctrl.props["متن"], "سلام")
        self.assertEqual(out, "سلام\n")

    def test_tagging_on_assign(self):
        ctrl = FakeControl()
        interp, _ = run_with(ctrl, "کنترل = کادر۱")
        self.assertEqual(ctrl.goya_name, "کنترل")

    def test_unknown_attr_error(self):
        with self.assertRaises(GoyaRuntimeError) as ctx:
            run_with(FakeControl(), "بگو(کادر۱.نداره)")
        self.assertIn("نداره", ctx.exception.message)

    def test_attr_on_number_error(self):
        with self.assertRaises(GoyaRuntimeError) as ctx:
            run_with(FakeControl(), "عدد = ۵\nبگو(عدد.متن)")
        self.assertIn("ویژگی", ctx.exception.message)

    def test_attr_assign_number_value(self):
        ctrl = FakeControl()
        interp, out = run_with(ctrl, "کادر۱.متن = ۱۲\nبگو(کادر۱.متن)")
        self.assertEqual(ctrl.props["متن"], 12)
        self.assertEqual(out, "۱۲\n")


if __name__ == "__main__":
    unittest.main()
