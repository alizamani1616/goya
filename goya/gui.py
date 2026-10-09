# -*- coding: utf-8 -*-
"""موتور گرافیکی گویا — پنجره و کنترل‌های ویژوال (VB6 مدرن)

ترجیحاً CustomTkinter؛ نبود، به tkinter/ttk خام برمی‌گرده.
برنامه‌نویس گویا فقط با فرم/دکمه/برچسب/کادر/پیام سروکار داره.
"""

import os

try:
    import customtkinter as ctk
    BACKEND = "customtkinter"
except ImportError:
    ctk = None
    BACKEND = "tkinter"

if os.environ.get("GOYA_HEADLESS"):
    BACKEND = "dummy"  # برای تست‌ها — هیچ پنجره‌ای ساخته نمی‌شه

import tkinter as tk
from tkinter import messagebox as _messagebox

from .errors import GoyaPropError, GoyaRuntimeError

# ─── وضعیت سراسری GUI ───

STATE = {
    "active": False,      # آیا فرمی ساخته شده؟
    "forms": [],          # ترتیب ساخت
    "controls": [],       # همه کنترل‌ها (برای اتصال رویداد)
    "current_form": None, # فرمی که کنترل‌های جدید توش ساخته می‌شن
}


def reset_state():
    STATE.update(active=False, forms=[], controls=[], current_form=None)


def is_active():
    return STATE["active"]


class _DummyWidget:
    """ویجت ساختگی برای تست‌های بدون پنجره"""

    def __init__(self, **kw):
        self._kw = kw

    def configure(self, **kw):
        self._kw.update(kw)

    def cget(self, key):
        return self._kw.get(key, "")

    def get(self):
        return self._kw.get("_value", "")

    def delete(self, *a):
        self._kw["_value"] = ""

    def insert(self, index, text):
        self._kw["_value"] = text

    def place(self, **kw):
        self._kw["place"] = kw


class _DummyRoot(_DummyWidget):
    def title(self, value=None):
        if value is None:
            return self._kw.get("title", "")
        self._kw["title"] = value

    def geometry(self, geo):
        self._kw["geometry"] = geo

    def resizable(self, a, b):
        pass

    def after(self, ms, fn):
        pass

    def mainloop(self):
        pass

    def destroy(self):
        pass


def _backend_root():
    if BACKEND == "dummy":
        return _DummyRoot(title="", geometry="")
    if BACKEND == "customtkinter":
        win = ctk.CTk()
    else:
        win = tk.Tk()
    return win


# ─── ویجت‌ها ───

class GoyaControl:
    """پایه همه کنترل‌ها — پروتکل goya_get/goya_set برای مفسر"""

    _PROPS = {}  # اسم گویا → اسم واقعی ویجت

    def goya_set_name(self, name):
        """وقتی کنترل به یه متغیر داده می‌شه، اسم متغیر اسم کنترل می‌شه (قرارداد رویداد)"""
        if not getattr(self, "goya_name", None):
            self.goya_name = name

    def goya_get(self, name):
        prop = self._PROPS.get(name)
        if prop is None:
            raise GoyaPropError("کنترل «{}» ویژگی «{}» نداره".format(self.kind, name))
        return self._get_prop(prop)

    def goya_set(self, name, value):
        prop = self._PROPS.get(name)
        if prop is None:
            raise GoyaPropError("کنترل «{}» ویژگی «{}» نداره".format(self.kind, name))
        self._set_prop(prop, value)

    def _get_prop(self, prop):
        raise NotImplementedError

    def _set_prop(self, prop, value):
        raise NotImplementedError


class GoyaForm:
    """پنجره‌ی برنامه"""

    is_goya_widget = True

    def __init__(self, title, width, height):
        self.goya_name = None
        self.window = _backend_root()
        self.window.title(title)
        self.window.geometry("{}x{}".format(width, height))
        self.window.resizable(True, True)

    def goya_get(self, name):
        if name == "عنوان":
            return self.window.title()
        raise GoyaPropError("فرم ویژگی «{}» نداره".format(name))

    def goya_set(self, name, value):
        if name == "عنوان":
            self.window.title(str(value))
            return
        raise GoyaPropError("فرم ویژگی «{}» نداره".format(name))

    def run(self):
        if os.environ.get("GOYA_SMOKE"):
            # تست دودی: پنجره ۱.۵ ثانیه باز می‌مونه و خودش بسته می‌شه
            self.window.after(1500, self.window.destroy)
        self.window.mainloop()


class GoyaButton(GoyaControl):
    kind = "دکمه"
    _PROPS = {"متن": "text"}

    def __init__(self, form, text, x, y):
        self.goya_name = None
        self._on_click = None
        self.x, self.y = x, y
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=text, x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkButton(form.window, text=text, width=120, height=34)
        else:
            self._widget = tk.Button(form.window, text=text, width=12)
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        return self._widget.cget("text")

    def _set_prop(self, prop, value):
        self._widget.configure(text=str(value))

    def set_on_click(self, fn):
        self._on_click = fn
        self._widget.configure(command=lambda: fn())

    def click(self):
        """اجرای مستقیم رویداد — برای تست‌ها"""
        if self._on_click:
            self._on_click()


class GoyaLabel(GoyaControl):
    kind = "برچسب"
    _PROPS = {"متن": "text"}

    def __init__(self, form, text, x, y):
        self.goya_name = None
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=text, x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkLabel(form.window, text=text, font=("Tahoma", 14))
        else:
            self._widget = tk.Label(form.window, text=text, font=("Tahoma", 11))
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        return self._widget.cget("text")

    def _set_prop(self, prop, value):
        self._widget.configure(text=str(value))


class GoyaTextBox(GoyaControl):
    kind = "کادر"
    _PROPS = {"متن": "text"}

    def __init__(self, form, placeholder, x, y):
        self.goya_name = None
        if BACKEND == "dummy":
            self._widget = _DummyWidget(placeholder=placeholder, x=x, y=y, _value=placeholder)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkEntry(form.window, placeholder_text=placeholder, width=160, height=32)
        else:
            self._widget = tk.Entry(form.window, width=22)
            self._widget.insert(0, placeholder)
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        return self._widget.get()

    def _set_prop(self, prop, value):
        self._widget.delete(0, "end")
        self._widget.insert(0, str(value))


# ─── کارخانه‌ها (تابع‌های داخلی زبان) ───

def factory_form(title, width=420, height=320):
    form = GoyaForm(title, int(width), int(height))
    STATE["forms"].append(form)
    STATE["current_form"] = form
    STATE["active"] = True
    return form


def _current_form():
    if STATE["current_form"] is None:
        # مثل VB6: بدون فرم هم کنترل بسازی، یه Form1 خودکار ساخته می‌شه
        factory_form("برنامه گویا")
    return STATE["current_form"]


def factory_button(text, x, y):
    ctrl = GoyaButton(_current_form(), str(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_label(text, x, y):
    ctrl = GoyaLabel(_current_form(), str(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_textbox(placeholder, x, y):
    ctrl = GoyaTextBox(_current_form(), str(placeholder), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def show_message(text):
    parent = STATE["current_form"].window if STATE["current_form"] else None
    _messagebox.showinfo("گویا", str(text), parent=parent)


# ─── اتصال رویدادها و حلقه‌ی اصلی ───

def _bind_events(interp):
    """قرارداد VB6: کنترل «محاسبه» → تابع محاسبه_کلیک"""
    bound = 0
    for ctrl in STATE["controls"]:
        name = getattr(ctrl, "goya_name", None)
        if not name:
            continue
        try:
            fn = interp.global_env.get(name + "_کلیک")
        except GoyaRuntimeError:
            continue
        ctrl.set_on_click(lambda fn=fn: interp.call_function(fn, []))
        bound += 1
    return bound


def finish_gui_if_active(interp):
    """انتهای هر برنامه: اتصال رویدادهای قراردادی + باز نگه داشتن پنجره"""
    if not STATE["active"]:
        return
    _bind_events(interp)
    if BACKEND == "dummy":
        return  # حالت تست: وضعیت برای بررسی می‌مونه (تست‌ها با setUp تمیز می‌کنن)
    form = STATE["forms"][0]  # اولین فرم = پنجره‌ی اصلی (میزبان حلقه‌ی رویداد)
    if os.environ.get("GOYA_SMOKE"):
        # تست دودی: پنجره ۱.۵ ثانیه باز می‌مونه و خودش بسته می‌شه
        form.window.after(1500, form.window.destroy)
    form.run()
    reset_state()
