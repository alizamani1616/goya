# -*- coding: utf-8 -*-
"""محیط گویا (IDE) — سرور وب محلی، فقط روی همین کامپیوتر

اجرا:
    goya ide          یا:    python -m goya ide
بعد مرورگر خودش باز می‌شه روی http://127.0.0.1:...
"""

import contextlib
import io
import json
import os
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .errors import GoyaError, GoyaRuntimeError, show_error
from .interpreter import Interpreter
from .lexer import Lexer
from .parser import Parser

_STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ide_static")
_EXAMPLES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples")
)

_EXAMPLE_TITLES = {
    "salam": "سلام دنیا",
    "fizzbuzz": "فیزباز",
    "factoriel": "فاکتوریل بازگشتی",
    "jam-list": "فاکتور خرید",
    "hads-adad": "بازی حدس عدد",
    "emrooz": "امروز و ترفندها",
    "demo": "تور همه‌ی قابلیت‌ها",
    "jadval-zarb": "جدول ضرب (حلقه تو در تو)",
    "adad-avval": "اعداد اول تا ۵۰",
    "fibonachi": "فیبوناچی",
    "mashin-hesab": "ماشین‌حساب ساده",
    "ghorreh-keshi": "قرعه‌کشی 🎲",
    "faslha": "فصل سال",
    "bozorgtarin": "گران‌ترین و میانگین",
    "makoos": "معکوس کردن متن",
}


def list_examples():
    """فهرست نمونه‌های پوشه‌ی examples (اگر کنار پکیج بود)"""
    items = []
    if os.path.isdir(_EXAMPLES_DIR):
        for name in sorted(os.listdir(_EXAMPLES_DIR)):
            if not name.endswith(".goya"):
                continue
            path = os.path.join(_EXAMPLES_DIR, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    code = f.read()
            except OSError:
                continue
            base = name[:-5]
            items.append(
                {
                    "file": name,
                    "title": _EXAMPLE_TITLES.get(base, base),
                    "code": code,
                }
            )
    return items


def run_code(code, inputs=None):
    """اجرای کد گویا — خروجی/خطای آماده برای محیط"""
    inputs = list(inputs or [])
    pos = {"i": 0}

    def input_fn(prompt=""):
        if pos["i"] >= len(inputs):
            raise GoyaRuntimeError(
                "ورودی‌ها تموم شدن — تو پنل «ورودی‌ها» بنویس (هر سطر = یک بپرس)"
            )
        value = inputs[pos["i"]]
        pos["i"] += 1
        return value

    interp = Interpreter(input_fn=input_fn, time_limit=6.0)
    buf = io.StringIO()
    t0 = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buf):
            program = Parser(Lexer(code).lex()).parse()
            interp.run(program)
        return {
            "ok": True,
            "output": buf.getvalue(),
            "error": "",
            "elapsed": round((time.perf_counter() - t0) * 1000),
        }
    except GoyaError as e:
        return {
            "ok": False,
            "output": buf.getvalue(),
            "error": show_error(e, code),
            "elapsed": round((time.perf_counter() - t0) * 1000),
        }
    except RecursionError:
        return {
            "ok": False,
            "output": buf.getvalue(),
            "error": "خطای اجرا: تابع‌ها خیلی تو در تو شدن (بازگشت بی‌پایان؟)",
            "elapsed": round((time.perf_counter() - t0) * 1000),
        }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(_STATIC, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except OSError:
                self._json({"error": "index.html پیدا نشد"}, 500)
        elif self.path in ("/logo.png", "/logo-mark.png", "/favicon.png"):
            names = {
                "/logo.png": "logo-full.png",
                "/logo-mark.png": "logo-mark.png",
                "/favicon.png": "favicon.png",
            }
            try:
                with open(os.path.join(_STATIC, names[self.path]), "rb") as f:
                    self._send(200, f.read(), "image/png")
            except OSError:
                self._json({"error": "فایل پیدا نشد"}, 404)
        elif self.path == "/api/examples":
            self._json({"examples": list_examples()})
        else:
            self._json({"error": "پیدا نشد"}, 404)

    def do_POST(self):
        if self.path != "/api/run":
            self._json({"error": "پیدا نشد"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            code = payload.get("code", "")
            inputs = payload.get("inputs") or []
        except (ValueError, UnicodeDecodeError):
            self._json({"error": "درخواست بد بود"}, 400)
            return
        self._json(run_code(code, inputs))

    def log_message(self, fmt, *args):
        pass  # لاگ پرحجوب اضافه نمی‌خوایم


def start():
    server = None
    for port in list(range(8765, 8776)) + [0]:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if server is None:
        print("پورت آزاد پیدا نشد")
        return

    url = "http://127.0.0.1:{}".format(server.server_address[1])
    print("محیط گویا روشنه: " + url)
    print("برای بستن: Ctrl+C")
    threading.Timer(0.4, webbrowser.open, [url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
        print("خداحافظ!")
