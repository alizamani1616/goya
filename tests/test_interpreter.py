# -*- coding: utf-8 -*-
import re
import unittest

from common import run_error, run_source
from goya.normalize import to_latin_digits


class TestBasics(unittest.TestCase):
    def test_hello(self):
        self.assertEqual(run_source('بگو("سلام دنیا!")'), "سلام دنیا!\n")

    def test_arithmetic_priority(self):
        self.assertEqual(run_source("بگو(۲ + ۳ * ۴)"), "۱۴\n")

    def test_persian_output_digits(self):
        self.assertEqual(run_source("بگو(۱۲۳)"), "۱۲۳\n")

    def test_string_concat(self):
        self.assertEqual(run_source('بگو("سلام " + "علی")'), "سلام علی\n")

    def test_var_and_display(self):
        src = "نام = «علی»\nبگو(\"سلام \" + نام)"
        self.assertEqual(run_source(src), "سلام علی\n")

    def test_constants_display(self):
        self.assertEqual(run_source("بگو(درست، غلط، پوچ)"), "درست غلط پوچ\n")

    def test_word_operators(self):
        self.assertEqual(run_source("بگو(۶ ضربدر ۷)"), "۴۲\n")
        self.assertEqual(run_source("بگو(۷ تقسیم بر ۲)"), "۳٫۵\n")

    def test_negative(self):
        self.assertEqual(run_source("بگو(-۵ + ۲)"), "-۳\n")


class TestControlFlow(unittest.TestCase):
    def test_if_else(self):
        src = "سن = ۲۰\nاگر سن > ۱۸\n    بگو(\"بزرگسال\")\nوگرنه\n    بگو(\"نوجوان\")"
        self.assertEqual(run_source(src), "بزرگسال\n")

    def test_if_else_false_branch(self):
        src = "سن = ۱۰\nاگر سن > ۱۸\n    بگو(\"بزرگسال\")\nوگرنه\n    بگو(\"نوجوان\")"
        self.assertEqual(run_source(src), "نوجوان\n")

    def test_elif_chain(self):
        src = (
            "نمره = ۱۷\n"
            "اگر نمره >= ۱۹\n"
            "    بگو(\"عالی\")\n"
            "وگرنه اگر نمره >= ۱۵\n"
            "    بگو(\"خوب\")\n"
            "وگرنه\n"
            "    بگو(\"سعی کن\")"
        )
        self.assertEqual(run_source(src), "خوب\n")

    def test_while_loop(self):
        src = "شمار = ۰\nتا وقتی که شمار < ۳\n    شمار = شمار + ۱\nبگو(شمار)"
        self.assertEqual(run_source(src), "۳\n")

    def test_for_range(self):
        src = "جمع = ۰\nبرای هر عدد از ۱ تا ۱۰\n    جمع = جمع + عدد\nبگو(جمع)"
        self.assertEqual(run_source(src), "۵۵\n")

    def test_for_in_list(self):
        src = 'برای هر حرف در «سلام»\n    بگو(حرف)'
        self.assertEqual(run_source(src), "س\nل\nا\nم\n")

    def test_break_continue(self):
        src = (
            "جمع = ۰\n"
            "برای هر عدد از ۱ تا ۱۰\n"
            "    اگر عدد > ۵\n"
            "        بشکن\n"
            "    اگر عدد % ۲ == ۰\n"
            "        ادامه\n"
            "    جمع = جمع + عدد\n"
            "بگو(جمع)"
        )
        # ۱ + ۳ + ۵ = ۹
        self.assertEqual(run_source(src), "۹\n")

    def test_and_or_not(self):
        self.assertEqual(run_source("بگو(درست و غلط)"), "غلط\n")
        self.assertEqual(run_source("بگو(درست یا غلط)"), "درست\n")
        self.assertEqual(run_source("بگو(نه درست)"), "غلط\n")


class TestFunctions(unittest.TestCase):
    def test_simple_function(self):
        src = "تابع مربع(عدد)\n    برگردان عدد * عدد\nبگو(مربع(۷))"
        self.assertEqual(run_source(src), "۴۹\n")

    def test_recursion(self):
        src = (
            "تابع فاکتوریل(عدد)\n"
            "    اگر عدد <= ۱\n"
            "        برگردان ۱\n"
            "    برگردان عدد * فاکتوریل(عدد - ۱)\n"
            "بگو(فاکتوریل(۶))"
        )
        self.assertEqual(run_source(src), "۷۲۰\n")

    def test_function_without_return(self):
        src = "تابع سلام()\n    بگو(\"سلام\")\nسلام()"
        self.assertEqual(run_source(src), "سلام\n")

    def test_arity_error(self):
        err = run_error("تابع جمع(الف، ب)\n    برگردان الف + ب\nجمع(۱)")
        self.assertIn("ورودی", err.message)

    def test_word_comparison(self):
        src = "اگر ۵ بزرگتر از ۳\n    بگو(\"درست\")"
        self.assertEqual(run_source(src), "درست\n")


class TestLists(unittest.TestCase):
    def test_list_len_index(self):
        src = "خرید = [«نان»، «شیر»]\nبگو(طول(خرید))\nبگو(خرید[۰])"
        self.assertEqual(run_source(src), "۲\nنان\n")

    def test_list_sum_loop(self):
        src = (
            "قیمت‌ها = [۱۲۰۰۰، ۴۵۰۰۰]\n"
            "جمع = ۰\n"
            "برای هر قیمت در قیمت‌ها\n"
            "    جمع = جمع + قیمت\n"
            "بگو(جمع)"
        )
        self.assertEqual(run_source(src), "۵۷۰۰۰\n")

    def test_list_concat(self):
        src = "بگو(طول([۱، ۲] + [۳]))"
        self.assertEqual(run_source(src), "۳\n")

    def test_index_out_of_range(self):
        err = run_error("اعداد = [۱]\nبگو(اعداد[۵])")
        self.assertIn("محدوده", err.message)


class TestBuiltins(unittest.TestCase):
    def test_round(self):
        self.assertEqual(run_source("بگو(گرد(۲٫۷))"), "۳\n")

    def test_num_conversion(self):
        src = 'بگو(عدد("۱۲") + ۳)'
        self.assertEqual(run_source(src), "۱۵\n")

    def test_text_conversion(self):
        self.assertEqual(run_source('بگو("سال " + متن(۱۴۰۵))'), "سال ۱۴۰۵\n")

    def test_random_within_bounds(self):
        out = to_latin_digits(run_source("برای هر عدد از ۱ تا ۲۰\n    بگو(تصادفی(۵، ۹))"))
        values = [int(line) for line in out.strip().split("\n")]
        self.assertTrue(all(5 <= v <= 9 for v in values))

    def test_today_format(self):
        out = to_latin_digits(run_source("بگو(امروز())")).strip()
        self.assertTrue(re.fullmatch(r"\d{4}/\d{2}/\d{2}", out), out)

    def test_alias_benevis(self):
        self.assertEqual(run_source('بنویس("سلام")'), "سلام\n")


class TestErrors(unittest.TestCase):
    def test_undefined_variable(self):
        err = run_error("بگو(ناشناخته)")
        self.assertIn("تعریف نشده", err.message)

    def test_division_by_zero(self):
        err = run_error("بگو(۱ / ۰)")
        self.assertIn("صفر", err.message)

    def test_plus_mixed_types(self):
        err = run_error('بگو("سلام" + ۵)')
        self.assertIn("متن()", err.message)

    def test_compare_text_number(self):
        err = run_error('اگر «الف» < ۵\n    بگو(۱)')
        self.assertIn("مقایسه", err.message)


class TestInputInjection(unittest.TestCase):
    def test_injected_input(self):
        import io as _io
        import contextlib as _contextlib
        from goya.interpreter import Interpreter
        from goya.lexer import Lexer
        from goya.parser import Parser
        interp = Interpreter(input_fn=lambda prompt: "علی")
        buf = _io.StringIO()
        with _contextlib.redirect_stdout(buf):
            prog = Parser(Lexer('بگو("سلام " + بپرس("نام؟"))').lex()).parse()
            interp.run(prog)
        self.assertEqual(buf.getvalue(), "سلام علی\n")


class TestLoopGuard(unittest.TestCase):
    def test_infinite_loop_stopped(self):
        import io as _io
        import contextlib as _contextlib
        from goya.errors import GoyaRuntimeError
        from goya.interpreter import Interpreter
        from goya.lexer import Lexer
        from goya.parser import Parser
        interp = Interpreter(input_fn=lambda p: "", time_limit=0.4)
        with self.assertRaises(GoyaRuntimeError) as ctx:
            with _contextlib.redirect_stdout(_io.StringIO()):
                prog = Parser(Lexer("تا وقتی که درست\n    بگو(۱)").lex()).parse()
                interp.run(prog)
        self.assertIn("طول کشید", ctx.exception.message)


class TestBreakOutsideLoop(unittest.TestCase):
    def test_break_at_top_level(self):
        err = run_error("بشکن")
        self.assertIn("داخل حلقه", err.message)

    def test_continue_at_top_level(self):
        err = run_error("ادامه")
        self.assertIn("داخل حلقه", err.message)

    def test_break_in_function_outside_loop(self):
        err = run_error("تابع نام()\n    بشکن\nنام()")
        self.assertIn("داخل حلقه", err.message)


if __name__ == "__main__":
    unittest.main()
