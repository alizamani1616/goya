# -*- coding: utf-8 -*-
"""خط فرمان گویا:

    goya run برنامه.goya    اجرای فایل
    goya repl               محیط تعاملی
    goya version            شماره نسخه
"""

import argparse
import sys

from . import __version__


def _run_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        print("فایل باز نشد: {}".format(e))
        return 1

    from .errors import GoyaError, show_error
    from .interpreter import Interpreter
    from .lexer import Lexer
    from .parser import Parser

    try:
        tokens = Lexer(source).lex()
        program = Parser(tokens).parse()
        Interpreter().run(program)
    except GoyaError as e:
        print(show_error(e, source))
        return 1
    except RecursionError:
        print("خطای اجرا: تابع‌ها خیلی تو در تو صدا زده شدن (بازگشت بی‌پایان؟)")
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="goya",
        description="گویا — زبان برنامه‌نویسی فارسی",
    )
    parser.add_argument(
        "--version", action="version", version="goya {}".format(__version__)
    )
    sub = parser.add_subparsers(dest="cmd")
    run_parser = sub.add_parser("run", help="اجرای یک فایل گویا")
    run_parser.add_argument("file", help="مسیر فایل .goya")
    sub.add_parser("repl", help="محیط تعاملی گویا")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        sys.exit(_run_file(args.file))
    if args.cmd == "repl":
        from .repl import start
        start()
        sys.exit(0)
    parser.print_help()
    sys.exit(0)
