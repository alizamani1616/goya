# -*- coding: utf-8 -*-
"""منطق موتور GUI — بدون باز شدن هیچ پنجره‌ای (GOYA_HEADLESS)"""
import unittest

from common import run_source
from goya.gui import STATE, reset_state


class GUITestCase(unittest.TestCase):
    """هر تست با وضعیت تازه‌ی GUI شروع و تمیز می‌شه"""

    def setUp(self):
        reset_state()

    def tearDown(self):
        reset_state()


class TestFormAndControls(GUITestCase):
    def test_form_registered(self):
        run_source('پنجره = فرم("برنامه من")')
        self.assertTrue(STATE["active"])
        self.assertEqual(len(STATE["forms"]), 1)
        self.assertEqual(STATE["forms"][0].window.title(), "برنامه من")

    def test_form_default_size(self):
        run_source('پنجره = فرم("برنامه")')
        self.assertEqual(STATE["forms"][0].window._kw["geometry"], "420x320")

    def test_button_named_by_variable(self):
        run_source('محاسبه = دکمه("محاسبه کن"، ۲۰، ۳۰)')
        btn = None
        # کنترل از وضعیت برداشته می‌شه
        for c in STATE["controls"]:
            btn = c
        self.assertEqual(btn.goya_name, "محاسبه")
        self.assertEqual(btn._widget.cget("text"), "محاسبه کن")

    def test_control_without_form_creates_default(self):
        # مثل VB6: بدون فرم هم کنترل بسازی، Form1 خودکار ساخته می‌شه
        run_source('امتیاز = برچسب("صفر"، ۱۰، ۱۰)')
        self.assertTrue(STATE["active"])
        self.assertEqual(STATE["forms"][0].window.title(), "برنامه گویا")


class TestClickWiring(GUITestCase):
    def test_convention_click_fires_function(self):
        src = (
            'ورودی = کادر("۵"، ۱۰، ۱۰)\n'
            'دکمه_اجرا = دکمه("بزن"، ۱۰، ۵۰)\n'
            'خروجی = برچسب("…"، ۱۰، ۹۰)\n'
            "تابع دکمه_اجرا_کلیک()\n"
            "    خروجی.متن = متن(عدد(ورودی.متن) * ۲)\n"
        )
        run_source(src)
        # دکمه رو از وضعیت پیدا کن و رویدادش رو دستی اجرا کن
        btn = STATE["controls"][1]
        self.assertEqual(btn.goya_name, "دکمه_اجرا")
        label = STATE["controls"][2]
        btn.click()
        self.assertEqual(label._widget.cget("text"), "۱۰")  # ۵ * ۲

    def test_control_without_handler_is_fine(self):
        run_source('ساده = دکمه("بدون رویداد"، ۰، ۰)')
        # بدون تابع ساده_کلیک — نباید خطایی رخ داده باشه و اجرا رسیده باشه تا اینجا
        self.assertEqual(STATE["controls"][0].goya_name, "ساده")


if __name__ == "__main__":
    unittest.main()
