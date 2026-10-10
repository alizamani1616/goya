# -*- coding: utf-8 -*-
"""کنترل‌های کامل گویا استودیو — ۱۳ کنترل با رویدادها (تست headless)"""
import io
import contextlib
import unittest

from common import run_source
from goya import gui as g
from goya.gui import STATE, GoyaTimer, reset_state


class StudioCase(unittest.TestCase):
    """هر تست با وضعیت تازه‌ی GUI"""

    def setUp(self):
        reset_state()

    def tearDown(self):
        reset_state()

    @staticmethod
    def last():
        return STATE["controls"][-1]


class TestFactories(StudioCase):
    def test_checkbox(self):
        run_source('خبرنامه = چک_باکس("خبرنامه می‌خوام؟"، ۱۰، ۲۰)')
        ctrl = self.last()
        self.assertIsInstance(ctrl, g.GoyaCheckBox)
        self.assertEqual(ctrl.goya_name, "خبرنامه")
        self.assertEqual(ctrl._get_prop("text"), "خبرنامه می‌خوام؟")

    def test_radio_group_exclusive(self):
        run_source(
            "ر۱ = رادیو(\"پیتزا\"، ۱۰، ۱۰)\n"
            "ر۲ = رادیو(\"برگر\"، ۱۰، ۴۰)\n"
        )
        r1, r2 = STATE["controls"]
        r2.select()
        self.assertTrue(r2._checked)
        self.assertFalse(r1._checked)
        r1.select()
        self.assertTrue(r1._checked)
        self.assertFalse(r2._checked)

    def test_switch(self):
        run_source('حالت_شب = کلید("حالت شب"، ۱۰، ۱۰)')
        sw = self.last()
        self.assertFalse(sw._get_prop("on"))
        sw._flip()
        self.assertTrue(sw._get_prop("on"))

    def test_combo_items(self):
        run_source('شهرها = کامبو(["تهران"، "شیراز"، "تبریز"]، ۱۰، ۱۰)')
        combo = self.last()
        self.assertIsInstance(combo, g.GoyaCombo)
        self.assertEqual(combo._get_prop("items"), ["تهران", "شیراز", "تبریز"])
        self.assertEqual(combo._get_prop("selected"), "تهران")

    def test_list_items(self):
        run_source('کارها = لیست(["مطالعه"، "ورزش"، "خرید"]، ۱۰، ۱۰)')
        lst = self.last()
        self.assertIsInstance(lst, g.GoyaList)
        self.assertEqual(lst._get_prop("items"), ["مطالعه", "ورزش", "خرید"])

    def test_slider(self):
        run_source("صدا = لغزنده(۰، ۱۰۰، ۱۰، ۱۰)")
        slider = self.last()
        self.assertIsInstance(slider, g.GoyaSlider)
        self.assertEqual(slider._get_prop("low"), 0)
        self.assertEqual(slider._get_prop("high"), 100)
        self.assertEqual(slider._get_prop("value"), 0)

    def test_timer(self):
        run_source("ساعت = تایمر(۵۰۰)")
        self.assertTrue(STATE["active"])
        timers = [c for c in STATE["controls"] if isinstance(c, GoyaTimer)]
        self.assertEqual(len(timers), 1)
        self.assertEqual(timers[0].interval, 500)

    def test_multiline(self):
        run_source('یادداشت = چندخطی("سلام\\nخوبی؟"، ۱۰، ۱۰)')
        ml = self.last()
        self.assertIsInstance(ml, g.GoyaMultiline)
        self.assertIn("خوبی؟", ml._get_prop("text"))

    def test_image_dummy(self):
        run_source('عکس_لوگو = تصویر("نمونه.png"، ۱۰، ۱۰)')
        img = self.last()
        self.assertIsInstance(img, g.GoyaImage)
        self.assertEqual(img._get_prop("file"), "نمونه.png")


class TestEvents(StudioCase):
    def test_checkbox_change_event(self):
        run_source(
            'خبرنامه = چک_باکس("خبرنامه؟"، ۱۰، ۱۰)\n'
            "تابع خبرنامه_تغییر()\n"
            "    بگو(\"رویداد تغییر رسید\")\n"
        )
        ctrl = self.last()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ctrl.fire()
        self.assertIn("رویداد تغییر رسید", buf.getvalue())

    def test_textbox_change_event(self):
        run_source(
            'جستجو = کادر("جستجو…", ۱۰, ۱۰)\n'
            "تابع جستجو_تغییر()\n"
            "    بگو(\"در حال جستجو…\")\n"
        )
        ctrl = self.last()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ctrl._change_fn()
        self.assertIn("در حال جستجو", buf.getvalue())

    def test_slider_change_event(self):
        run_source(
            "صدا = لغزنده(۰، ۱۰۰، ۱۰، ۱۰)\n"
            "تابع صدا_تغییر()\n"
            "    بگو(\"صدا عوض شد\")\n"
        )
        slider = self.last()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            slider._widget._kw["_value"] = "42"
            slider._moved()
        self.assertIn("صدا عوض شد", buf.getvalue())
        self.assertEqual(slider._get_prop("value"), 42)

    def test_list_pick_updates_selection(self):
        run_source('کارها = لیست(["مطالعه"، "ورزش"]، ۱۰، ۱۰)')
        lst = self.last()
        fired = []
        lst.bind_event("انتخاب", lambda: fired.append(lst._get_prop("selected")))
        lst._pick("ورزش")
        self.assertEqual(fired, ["ورزش"])


class TestEventMetadata(unittest.TestCase):
    """هر نوع کنترل رویدادهای خودش رو معرفی می‌کنه"""

    def test_events_lists(self):
        form = g.GoyaForm("تست", 400, 300)
        cases = [
            (g.GoyaButton(form, "متن", 0, 0), ["کلیک", "دبل‌کلیک"]),
            (g.GoyaLabel(form, "متن", 0, 0), ["کلیک"]),
            (g.GoyaTextBox(form, "راهنما", 0, 0), ["تغییر"]),
            (g.GoyaMultiline(form, "متن", 0, 0), ["تغییر"]),
            (g.GoyaCheckBox(form, "متن", 0, 0), ["تغییر"]),
            (g.GoyaRadio(form, "متن", 0, 0), ["تغییر"]),
            (g.GoyaSwitch(form, "متن", 0, 0), ["تغییر"]),
            (g.GoyaCombo(form, ["الف"], 0, 0), ["انتخاب", "تغییر"]),
            (g.GoyaList(form, ["الف"], 0, 0), ["انتخاب"]),
            (g.GoyaSlider(form, 0, 100, 0, 0), ["تغییر"]),
            (g.GoyaProgress(form, 0, 0), []),
            (g.GoyaImage(form, "فایل.png", 0, 0), ["کلیک"]),
            (g.GoyaTimer(1000), ["تیک"]),
        ]
        for ctrl, evs in cases:
            with self.subTest(kind=ctrl.kind):
                self.assertEqual(ctrl.goya_events(), evs)


if __name__ == "__main__":
    unittest.main()
