# -*- coding: utf-8 -*-
"""موتور گرافیکی گویا — پنجره، کنترل‌ها و رویدادها (VB6 مدرن)

ترجیحاً CustomTkinter؛ نبود، به tkinter/ttk خام برمی‌گرده.
GOYA_HEADLESS=1 → بک‌اند ساختگی برای تست‌های بدون پنجره.
هر کنترل رویدادهای خودش رو داره: کلیک، تغییر، انتخاب، تیک...
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
    "active": False,
    "forms": [],
    "controls": [],
    "current_form": None,
}


def reset_state():
    STATE.update(active=False, forms=[], controls=[], current_form=None)


def is_active():
    return STATE["active"]


def _num(v, what, line=None):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise GoyaRuntimeError("{} باید عدد باشه".format(what), line)
    return v


def _text(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "درست" if v else "غلط"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)


# ─── بک‌اند ساختگی (تست بدون پنجره) ───

class _DummyWidget:
    def __init__(self, **kw):
        self._kw = kw

    def configure(self, **kw):
        self._kw.update(kw)

    def cget(self, key):
        return self._kw.get(key, "")

    def get(self, *a):
        return self._kw.get("_value", "")

    def delete(self, *a):
        self._kw["_value"] = ""

    def insert(self, index, text):
        self._kw["_value"] = text

    def place(self, **kw):
        self._kw["place"] = kw

    def bind(self, *a, **kw):
        pass


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
        self._kw.setdefault("_afters", []).append((ms, fn))

    def mainloop(self):
        pass

    def destroy(self):
        pass


def _backend_root():
    if BACKEND == "dummy":
        return _DummyRoot()
    if BACKEND == "customtkinter":
        return ctk.CTk()
    return tk.Tk()


# ─── پروتکل ویجت ───

class GoyaControl:
    """پایه همه کنترل‌ها

    goya_get/goya_set → ویژگی‌ها از دید کد گویا (کادر۱.متن)
    goya_events()     → فهرست رویدادهای این نوع (کلیک، تغییر، انتخاب، تیک...)
    bind_event(evt, fn) → وصل‌کردن رویداد به تابع گویا
    """

    is_goya_widget = True
    kind = "کنترل"
    _PROPS = {}
    _EVENTS = ["کلیک"]

    def goya_set_name(self, name):
        """اسم متغیر → اسم کنترل (قرارداد رویداد VB6)"""
        if not getattr(self, "goya_name", None):
            self.goya_name = name

    def goya_events(self):
        return list(self._EVENTS)

    def goya_get(self, name):
        prop = self._PROPS.get(name)
        if prop is None:
            raise GoyaPropError(
                "{} ویژگی «{}» نداره — ویژگی‌ها: {}".format(
                    self.kind, name, "، ".join(self._PROPS))
            )
        return self._get_prop(prop)

    def goya_set(self, name, value):
        prop = self._PROPS.get(name)
        if prop is None:
            raise GoyaPropError(
                "{} ویژگی «{}» نداره — ویژگی‌ها: {}".format(
                    self.kind, name, "، ".join(self._PROPS))
            )
        self._set_prop(prop, value)

    def _get_prop(self, prop):
        raise NotImplementedError

    def _set_prop(self, prop, value):
        raise NotImplementedError

    def bind_event(self, evt, fn):
        if evt == self._EVENTS[0] and hasattr(self, "set_on_click"):
            self.set_on_click(fn)

    def set_on_click(self, fn):
        self._on_click = fn

    def fire(self):
        if getattr(self, "_on_click", None):
            self._on_click()


class GoyaForm:
    """پنجره‌ی برنامه"""

    is_goya_widget = True

    def __init__(self, title, width, height):
        self.goya_name = None
        self.radios = []
        self.window = _backend_root()
        self.window.title(title)
        self.window.geometry("{}x{}".format(width, height))
        self.window.resizable(True, True)

    def goya_get(self, name):
        if name == "عنوان":
            return self.window.title()
        raise GoyaPropError("فرم ویژگی «{}» نداره — فقط «عنوان»".format(name))

    def goya_set(self, name, value):
        if name == "عنوان":
            self.window.title(_text(value))
            return
        raise GoyaPropError("فرم ویژگی «{}» نداره — فقط «عنوان»".format(name))

    def run(self):
        if os.environ.get("GOYA_SMOKE"):
            self.window.after(1500, self.window.destroy)
        self.window.mainloop()


# ─── کنترل‌ها ───

class GoyaButton(GoyaControl):
    kind = "دکمه"
    _PROPS = {"متن": "text"}
    _EVENTS = ["کلیک", "دبل‌کلیک"]

    def __init__(self, form, text, x, y):
        self.goya_name = None
        self._on_click = None
        self._on_double = None
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=_text(text), x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkButton(form.window, text=_text(text), width=140, height=34)
        else:
            self._widget = tk.Button(form.window, text=_text(text), width=12)
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        return self._widget.cget("text")

    def _set_prop(self, prop, value):
        self._widget.configure(text=_text(value))

    def set_on_click(self, fn):
        self._on_click = fn
        if BACKEND != "dummy":
            self._widget.configure(command=lambda: fn())

    def bind_event(self, evt, fn):
        if evt == "کلیک":
            self.set_on_click(fn)
        elif evt == "دبل‌کلیک":
            self._on_double = fn
            if BACKEND != "dummy":
                self._widget.bind("<Double-Button-1>", lambda e: fn())

    def click(self):
        self.fire()


class GoyaLabel(GoyaControl):
    kind = "برچسب"
    _PROPS = {"متن": "text"}
    _EVENTS = ["کلیک"]

    def __init__(self, form, text, x, y):
        self.goya_name = None
        self._on_click = None
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=_text(text), x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkLabel(form.window, text=_text(text), font=("Tahoma", 14))
        else:
            self._widget = tk.Label(form.window, text=_text(text), font=("Tahoma", 11))
        self._widget.place(x=x, y=y)
        if BACKEND != "dummy":
            self._widget.bind("<Button-1>", lambda e: self.fire())

    def _get_prop(self, prop):
        return self._widget.cget("text")

    def _set_prop(self, prop, value):
        self._widget.configure(text=_text(value))


class GoyaTextBox(GoyaControl):
    kind = "کادر"
    _PROPS = {"متن": "text"}
    _EVENTS = ["تغییر"]

    def __init__(self, form, placeholder, x, y):
        self.goya_name = None
        self._change_fn = None
        if BACKEND == "dummy":
            self._widget = _DummyWidget(placeholder=_text(placeholder), x=x, y=y, _value=_text(placeholder))
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkEntry(form.window, placeholder_text=_text(placeholder), width=160, height=32)
        else:
            self._widget = tk.Entry(form.window, width=22)
            self._widget.insert(0, _text(placeholder))
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        return self._widget.get()

    def _set_prop(self, prop, value):
        self._widget.delete(0, "end")
        self._widget.insert(0, _text(value))

    def bind_event(self, evt, fn):
        if evt == "تغییر":
            self._change_fn = fn
            if BACKEND != "dummy":
                self._widget.bind("<KeyRelease>", lambda e: fn())


class GoyaMultiline(GoyaControl):
    kind = "چندخطی"
    _PROPS = {"متن": "text"}
    _EVENTS = ["تغییر"]

    def __init__(self, form, text, x, y):
        self.goya_name = None
        self._change_fn = None
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=_text(text), x=x, y=y, _value=_text(text))
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkTextbox(form.window, width=200, height=90)
            self._widget.insert("1.0", _text(text))
        else:
            self._widget = tk.Text(form.window, width=24, height=4)
            self._widget.insert("1.0", _text(text))
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        return self._widget.get("1.0", "end").rstrip("\n")

    def _set_prop(self, prop, value):
        self._widget.delete("1.0", "end")
        self._widget.insert("1.0", _text(value))

    def bind_event(self, evt, fn):
        if evt == "تغییر":
            self._change_fn = fn
            if BACKEND != "dummy":
                self._widget.bind("<KeyRelease>", lambda e: fn())


class GoyaCheckBox(GoyaControl):
    kind = "چک‌باکس"
    _PROPS = {"متن": "text", "انتخاب‌شده": "checked"}
    _EVENTS = ["تغییر"]

    def __init__(self, form, text, x, y):
        self.goya_name = None
        self._change_fn = None
        self._checked = False
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=_text(text), x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkCheckBox(form.window, text=_text(text))
        else:
            self._widget = tk.Checkbutton(form.window, text=_text(text),
                                          command=lambda: self._on_toggle())
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        if prop == "text":
            return self._widget.cget("text")
        return self._checked

    def _set_prop(self, prop, value):
        if prop == "text":
            self._widget.configure(text=_text(value))
        else:
            self._checked = bool(value)
            if BACKEND == "customtkinter":
                (self._widget.select if self._checked else self._widget.deselect)()
            elif BACKEND == "tkinter":
                (self._widget.select if self._checked else self._widget.deselect)()

    def bind_event(self, evt, fn):
        if evt == "تغییر":
            self._change_fn = fn

    def _on_toggle(self):
        self._checked = not self._checked
        if self._change_fn:
            self._change_fn()

    def fire(self):
        self._on_toggle()


class GoyaRadio(GoyaControl):
    """دکمه رادیو — رادیوهای یک فرم یک گروه‌اند (انتخاب یکی، بقیه خاموش)"""
    kind = "رادیو"
    _PROPS = {"متن": "text", "انتخاب‌شده": "checked"}
    _EVENTS = ["تغییر"]

    def __init__(self, form, text, x, y):
        self.goya_name = None
        self._change_fn = None
        self._checked = False
        self._form = form
        if form is not None:
            form.radios = getattr(form, "radios", [])
            form.radios.append(self)
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=_text(text), x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkRadioButton(form.window, text=_text(text),
                                              command=lambda: self.select())
        else:
            self._widget = tk.Radiobutton(form.window, text=_text(text),
                                          value=_text(text),
                                          command=lambda: self.select())
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        if prop == "text":
            return self._widget.cget("text")
        return self._checked

    def _set_prop(self, prop, value):
        if prop == "text":
            self._widget.configure(text=_text(value))
        else:
            self.select()

    def select(self):
        if self._form is not None:
            for r in self._form.radios:
                r._checked = False
        self._checked = True
        if self._change_fn:
            self._change_fn()

    def bind_event(self, evt, fn):
        if evt == "تغییر":
            self._change_fn = fn


class GoyaSwitch(GoyaControl):
    kind = "کلید"
    _PROPS = {"متن": "text", "روشن": "on"}
    _EVENTS = ["تغییر"]

    def __init__(self, form, text, x, y):
        self.goya_name = None
        self._change_fn = None
        self._on = False
        if BACKEND == "dummy":
            self._widget = _DummyWidget(text=_text(text), x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkSwitch(form.window, text=_text(text))
        else:
            self._widget = tk.Checkbutton(form.window, text=_text(text), indicatoron=False)
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        if prop == "text":
            return self._widget.cget("text")
        return self._on

    def _set_prop(self, prop, value):
        if prop == "text":
            self._widget.configure(text=_text(value))
        else:
            self._on = bool(value)
            if BACKEND == "customtkinter":
                (self._widget.select if self._on else self._widget.deselect)()

    def bind_event(self, evt, fn):
        if evt == "تغییر":
            self._change_fn = fn
            if BACKEND == "customtkinter":
                self._widget.configure(command=lambda: self._flip())

    def _flip(self):
        self._on = not self._on
        if self._change_fn:
            self._change_fn()


class GoyaCombo(GoyaControl):
    """لیست بازشو"""
    kind = "کامبو"
    _PROPS = {"آیتم‌ها": "items", "انتخاب‌شده": "selected"}
    _EVENTS = ["انتخاب", "تغییر"]

    def __init__(self, form, items, x, y):
        self.goya_name = None
        self._select_fn = None
        self._items = [_text(i) for i in items]
        if BACKEND == "dummy":
            self._widget = _DummyWidget(items=list(self._items), x=x, y=y,
                                        _value=self._items[0] if self._items else "")
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkComboBox(form.window, values=list(self._items), width=160)
            if self._items:
                self._widget.set(self._items[0])
        else:
            self._widget = tk.Combobox(form.window, values=self._items, state="readonly")
            if self._items:
                self._widget.current(0)
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        if prop == "items":
            return list(self._items)
        return self._widget.get()

    def _set_prop(self, prop, value):
        if prop == "items":
            self._items = [_text(i) for i in value]
            if BACKEND == "customtkinter":
                self._widget.configure(values=list(self._items))
                if self._items:
                    self._widget.set(self._items[0])
        elif BACKEND == "customtkinter":
            self._widget.set(_text(value))

    def bind_event(self, evt, fn):
        if evt == "انتخاب":
            self._select_fn = fn
            if BACKEND == "customtkinter":
                self._widget.configure(command=lambda v: fn())


class GoyaList(GoyaControl):
    """لیست انتخابی — آیتم‌ها با کلیک انتخاب می‌شن"""
    kind = "لیست"
    _PROPS = {"آیتم‌ها": "items", "انتخاب‌شده": "selected"}
    _EVENTS = ["انتخاب"]

    def __init__(self, form, items, x, y):
        self.goya_name = None
        self._select_fn = None
        self._items = [_text(i) for i in items]
        self._selected = None
        if BACKEND == "dummy":
            self._widget = _DummyWidget(items=list(self._items), x=x, y=y)
        else:
            if BACKEND == "customtkinter":
                self._widget = ctk.CTkScrollableFrame(form.window, width=170, height=110)
            else:
                self._widget = tk.Frame(form.window)
            self._redraw()
        self._widget.place(x=x, y=y)

    def _redraw(self):
        if BACKEND == "dummy":
            return
        for w in self._widget.winfo_children():
            w.destroy()
        for item in self._items:
            if BACKEND == "customtkinter":
                b = ctk.CTkButton(self._widget, text=item, anchor="w",
                                  fg_color="transparent",
                                  text_color=("gray10", "#DCE4EE"), height=26)
            else:
                b = tk.Button(self._widget, text=item, anchor="w", relief="flat")
            b.configure(command=lambda it=item, b=b: self._pick(it, b))
            b.pack(fill="x", padx=2, pady=1)

    def _pick(self, item, b=None):
        self._selected = item
        if self._select_fn:
            self._select_fn()

    def _get_prop(self, prop):
        if prop == "items":
            return list(self._items)
        return self._selected or ""

    def _set_prop(self, prop, value):
        if prop == "items":
            self._items = [_text(i) for i in value]
            self._selected = None
            self._redraw()
        else:
            self._selected = _text(value)

    def bind_event(self, evt, fn):
        if evt == "انتخاب":
            self._select_fn = fn


class GoyaSlider(GoyaControl):
    kind = "لغزنده"
    _PROPS = {"مقدار": "value", "کمینه": "low", "بیشینه": "high"}
    _EVENTS = ["تغییر"]

    def __init__(self, form, low, high, x, y):
        self.goya_name = None
        self._change_fn = None
        self._low, self._high = int(low), int(high)
        self._value = self._low
        if BACKEND == "dummy":
            self._widget = _DummyWidget(low=self._low, high=self._high, x=x, y=y, _value=str(self._low))
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkSlider(form.window, from_=self._low, to=self._high,
                                         width=160, command=lambda v: self._moved())
            self._widget.set(self._low)
        else:
            self._widget = tk.Scale(form.window, from_=self._low, to=self._high,
                                    orient="horizontal", length=160,
                                    command=lambda v: self._moved())
        self._widget.place(x=x, y=y)

    def _moved(self):
        self._value = int(float(self._widget.get()))
        if self._change_fn:
            self._change_fn()

    def bind_event(self, evt, fn):
        if evt == "تغییر":
            self._change_fn = fn

    def _get_prop(self, prop):
        return {"value": self._value, "low": self._low, "high": self._high}[prop]

    def _set_prop(self, prop, value):
        v = int(value)
        if prop == "value":
            self._value = v
            if BACKEND != "dummy" and hasattr(self._widget, "set"):
                self._widget.set(v)
        elif prop == "low":
            self._low = v
        else:
            self._high = v


class GoyaProgress(GoyaControl):
    kind = "نوار پیشرفت"
    _PROPS = {"مقدار": "value"}
    _EVENTS = []

    def __init__(self, form, x, y):
        self.goya_name = None
        self._value = 0.0
        if BACKEND == "dummy":
            self._widget = _DummyWidget(x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkProgressBar(form.window, width=180)
            self._widget.set(0)
        else:
            self._widget = tk.Frame(form.window)
        self._widget.place(x=x, y=y)

    def _get_prop(self, prop):
        return round(self._value, 3)

    def _set_prop(self, prop, value):
        v = float(value)
        if v < 0 or v > 1:
            raise GoyaPropError("مقدار نوار پیشرفت باید بین ۰ و ۱ باشه")
        self._value = v
        if BACKEND == "customtkinter":
            self._widget.set(v)


class GoyaImage(GoyaControl):
    kind = "تصویر"
    _PROPS = {"فایل": "file"}
    _EVENTS = ["کلیک"]

    def __init__(self, form, path, x, y):
        self.goya_name = None
        self._on_click = None
        self._path = ""
        if BACKEND == "dummy":
            self._widget = _DummyWidget(file=path, x=x, y=y)
        elif BACKEND == "customtkinter":
            self._widget = ctk.CTkLabel(form.window, text="")
        else:
            self._widget = tk.Label(form.window, text="")
        self._widget.place(x=x, y=y)
        self.set_file(_text(path))

    def _get_prop(self, prop):
        return self._path

    def _set_prop(self, prop, value):
        self.set_file(_text(value))

    def set_file(self, path):
        self._path = path
        if BACKEND == "dummy" or not path:
            return
        try:
            from PIL import Image
            pil = Image.open(path)
            img = ctk.CTkImage(pil, size=(pil.width, pil.height))
            self._widget.configure(image=img, text="")
        except Exception as e:
            raise GoyaPropError("تصویر باز نشد: {}".format(e))

    def set_on_click(self, fn):
        self._on_click = fn
        if BACKEND != "dummy":
            self._widget.bind("<Button-1>", lambda e: fn())

    def fire(self):
        if self._on_click:
            self._on_click()


class GoyaTimer(GoyaControl):
    """تایمر نامرئی — هر «فاصله» میلی‌ثانیه یک‌بار تابع {نام}_تیک صدا زده می‌شه"""
    kind = "تایمر"
    _PROPS = {"فاصله": "interval"}
    _EVENTS = ["تیک"]

    def __init__(self, interval):
        self.goya_name = None
        self._tick_fn = None
        self.interval = int(interval)
        self._widget = None
        STATE["active"] = True  # تایمر هم برنامه را زنده نگه می‌دارد

    def _get_prop(self, prop):
        return self.interval

    def _set_prop(self, prop, value):
        self.interval = int(value)

    def bind_event(self, evt, fn):
        if evt == "تیک":
            self._tick_fn = fn

    def start(self, win):
        if BACKEND == "dummy" or not self._tick_fn:
            return

        def loop():
            self._tick_fn()
            win.after(self.interval, loop)

        win.after(self.interval, loop)


# ─── کارخانه‌ها (تابع‌های داخلی زبان) ───

def factory_form(title, width=420, height=320):
    form = GoyaForm(title, int(width), int(height))
    STATE["forms"].append(form)
    STATE["current_form"] = form
    STATE["active"] = True
    return form


def _current_form():
    if STATE["current_form"] is None:
        factory_form("برنامه گویا")
    return STATE["current_form"]


def factory_button(text, x, y):
    ctrl = GoyaButton(_current_form(), _text(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_label(text, x, y):
    ctrl = GoyaLabel(_current_form(), _text(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_textbox(placeholder, x, y):
    ctrl = GoyaTextBox(_current_form(), _text(placeholder), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_multiline(text, x, y):
    ctrl = GoyaMultiline(_current_form(), _text(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_checkbox(text, x, y):
    ctrl = GoyaCheckBox(_current_form(), _text(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_radio(text, x, y):
    ctrl = GoyaRadio(_current_form(), _text(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_switch(text, x, y):
    ctrl = GoyaSwitch(_current_form(), _text(text), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_combo(items, x, y):
    ctrl = GoyaCombo(_current_form(), items, int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_list(items, x, y):
    ctrl = GoyaList(_current_form(), items, int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_slider(low, high, x, y):
    ctrl = GoyaSlider(_current_form(), low, high, int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_progress(x, y):
    ctrl = GoyaProgress(_current_form(), int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_image(path, x, y):
    ctrl = GoyaImage(_current_form(), path, int(x), int(y))
    STATE["controls"].append(ctrl)
    return ctrl


def factory_timer(interval):
    ctrl = GoyaTimer(int(interval))
    STATE["controls"].append(ctrl)
    STATE["active"] = True
    return ctrl


def show_message(text):
    parent = STATE["current_form"].window if STATE["current_form"] else None
    _messagebox.showinfo("گویا", str(text), parent=parent)


# ─── اتصال رویدادها و حلقه‌ی اصلی ───

def _bind_events(interp):
    """قرارداد VB6 برای هر نوع کنترل: نام + پسوند رویداد → تابع گویا

    دکمه «محاسبه» → محاسبه_کلیک   |   کادر «جستجو» → جستجو_تغییر
    لیست «شهرها» → شهرها_انتخاب   |   تایمر «ساعت» → ساعت_تیک
    """
    bound = 0
    for ctrl in STATE["controls"]:
        name = getattr(ctrl, "goya_name", None)
        if not name:
            continue
        for evt in ctrl.goya_events():
            try:
                fn = interp.global_env.get(name + "_" + evt)
            except GoyaRuntimeError:
                continue
            ctrl.bind_event(evt, lambda fn=fn: interp.call_function(fn, []))
            bound += 1
    return bound


def finish_gui_if_active(interp):
    """انتهای هر برنامه: اتصال رویدادها + باز نگه داشتن پنجره (حلقه رویداد)"""
    if not STATE["active"]:
        return
    _bind_events(interp)
    if BACKEND == "dummy":
        return  # حالت تست: وضعیت برای بررسی می‌مونه (تست‌ها با setUp تمیز می‌کنن)
    form = STATE["forms"][0]
    if os.environ.get("GOYA_SMOKE"):
        form.window.after(1500, form.window.destroy)
    for ctrl in STATE["controls"]:
        if isinstance(ctrl, GoyaTimer):
            ctrl.start(form.window)
    form.run()
    reset_state()
