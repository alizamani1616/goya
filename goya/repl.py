# -*- coding: utf-8 -*-
"""محیط تعاملی گویا (REPL)

سطرهای تکی فوراً اجرا می‌شن؛ بلوک‌های چندسطری با یک سطر خالی اجرا می‌شن.
"""

from .errors import GoyaError, IncompleteInput, show_error
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import ExprStmt, Parser
from .stdlib import display
from .normalize import to_persian_digits


def _try_entry(interp, source):
    """یک ورودی کامل رو اجرا می‌کنه. برمی‌گردونه: تموم شد یا ناتمام بود؟"""
    try:
        tokens = Lexer(source).lex()
        program = Parser(tokens).parse()
    except IncompleteInput:
        return False
    except GoyaError as e:
        print(show_error(e, source))
        return True

    try:
        if len(program.statements) == 1 and isinstance(program.statements[0], ExprStmt):
            value = interp.evaluate(program.statements[0].expr)
            print("=> " + display(value))
        else:
            interp.run(program)
    except GoyaError as e:
        print(show_error(e, source))
    except RecursionError:
        print("خطای اجرا: تابع‌ها خیلی تو در تو صدا زده شدن (بازگشت بی‌پایان؟)")
    return True


def start():
    import os
    if os.name == "nt":
        os.system("")  # رنگ ANSI در ویندوز
    print("\033[96mگویا " + to_persian_digits("0.1.0") +
          " — زبان برنامه‌نویسی فارسی\033[0m")
    print("برای خروج: Ctrl+C یا Ctrl+Z و بعد Enter")
    print()
    interp = Interpreter()
    buf = []
    while True:
        try:
            prompt = "گویا> " if not buf else "  ... "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not buf and not line.strip():
            continue

        buf.append(line)
        source = "\n".join(buf)

        if len(buf) == 1:
            # سطر تکی: فوراً اجرا؛ اگه ناتمام بود می‌ریم حالت چندسطری
            if _try_entry(interp, source):
                buf = []
        else:
            # چندسطری: با سطر خالی اجرا می‌شه
            if not line.strip():
                _try_entry(interp, source)
                buf = []
