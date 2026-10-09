# -*- coding: utf-8 -*-
"""ابزار مشترک تست‌ها"""

import contextlib
import io

from goya.errors import GoyaError
from goya.interpreter import Interpreter
from goya.lexer import Lexer
from goya.parser import Parser


def run_source(source):
    """اجازه یک برنامه گویا و برگردوندن خروجی چاپ‌شده"""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        program = Parser(Lexer(source).lex()).parse()
        Interpreter().run(program)
    return buf.getvalue()


def run_error(source):
    """اجازه برنامه‌ای که باید خطا بده و برگردوندن خود خطا"""
    try:
        run_source(source)
    except GoyaError as e:
        return e
    raise AssertionError("انتظار خطا می‌رفت ولی خطایی رخ نداد")
