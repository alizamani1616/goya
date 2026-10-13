# -*- coding: utf-8 -*-
"""گویا استودیو — محیط ویژوال ساخت نرم‌افزار ویندوزی

اجرا:  goya studio [پروژه.goya]
پنجره‌ی بومی (pywebview) + طراح درگ‌دراپ + ادیتور کد + اجرای F5.
برنامه‌ها در پروسه‌ی جدا اجرا می‌شن — استودیو همیشه واکنش‌گرا می‌مونه.
"""

import base64
import json
import io
import os
import subprocess
import sys
import tempfile
import threading
import contextlib
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDIO_STATIC = os.path.join(_HERE, "studio_static")


def _serve_dist():
    """سرو محلی نسخه‌ی بیلدشده روی 127.0.0.1 — ماژول‌های ES روی پروتکل file:// بسته‌اند"""
    import http.server

    dist = os.path.join(_STUDIO_STATIC, "dist")

    class _Handler(http.server.SimpleHTTPRequestHandler):
        # بدون directory=dist هندلر از پوشه‌ی جاری پروسه سرو می‌کند — نه از dist
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=dist, **kwargs)

        extensions_map = {
            **http.server.SimpleHTTPRequestHandler.extensions_map,
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".mjs": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".woff2": "font/woff2",
            ".svg": "image/svg+xml",
        }

        def log_message(self, fmt, *args):
            pass  # بی‌سروصدا

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _log(msg):
    """لاگ سبک برای اشکال‌زدایی — کنار فایل موقت"""
    try:
        with open(os.path.join(tempfile.gettempdir(), "goya_studio.log"), "a", encoding="utf-8") as f:
            f.write(msg + chr(10))
    except OSError:
        pass


def _window_hwnd(w):
    """هندل ویندوزی پنجره‌ی pywebview (فرم WinForms)"""
    try:
        h = w.native.Handle
        try:
            return int(h.ToInt64())
        except Exception:
            return int(h)
    except Exception:
        return 0


def _set_window_icon(hwnd, ico_path):
    """آیکون پنجره و تسک‌بار با WM_SETICON — ارسال از هر threadی امن است"""
    if not ico_path or not hwnd:
        return
    import ctypes
    u32 = ctypes.windll.user32
    IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
    hbig = u32.LoadImageW(None, ico_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
    hsmall = u32.LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
    u32.SendMessageW(hwnd, 0x80, 1, hbig)    # ICON_BIG — تسک‌بار و Alt-Tab
    u32.SendMessageW(hwnd, 0x80, 0, hsmall)  # ICON_SMALL — نوار عنوان


_SPLASH_HTML = """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<style>
  @font-face {
    font-family: 'VazirmatnSplash';
    src: url(data:font/woff2;base64,__FONT__) format('woff2');
    font-weight: 800;
    font-display: block;
  }
  html, body { margin: 0; height: 100%; background: #FFF4E6; overflow: hidden; }
  body { display: flex; align-items: center; justify-content: center; }
  .box { display: flex; flex-direction: column; align-items: center; gap: 20px;
         font-family: VazirmatnSplash, Vazirmatn, Tahoma, sans-serif; }
  .logo { height: 58px; }
  .spinner { width: 34px; height: 34px; border-radius: 50%;
             border: 4px solid #EBDDC2; border-top-color: #9775FA;
             animation: spin 0.9s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  p { margin: 0; font-size: 15px; font-weight: 800; color: #8a7452; }
</style></head><body>
  <div class="box">
    <img class="logo" src="data:image/png;base64,__LOGO__" alt="">
    <div class="spinner"></div>
    <p>در حال باز شدن گویا استودیو…</p>
  </div>
</body></html>"""


def _splash_html():
    """اسپلش با لوگو و فونت وزیرمتنِ جاسازی‌شده (base64) — بدون وابستگی به سرور/شبکه"""
    def _raw(path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except OSError:
            return b""

    logo_b64 = ""
    logo_bytes = _raw(os.path.join(_STUDIO_STATIC, "dist", "logo-full.png"))
    if logo_bytes:
        try:
            # نسخه‌ی کوچک برای نمایش ۵۸ پیکسلی — html سبک‌تر، اسپلش سریع‌تر
            from io import BytesIO
            from PIL import Image
            img = Image.open(BytesIO(logo_bytes))
            scale = 116 / img.height
            img = img.resize((max(1, int(img.width * scale)), 116), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, "PNG", optimize=True)
            logo_bytes = buf.getvalue()
        except Exception:
            pass  # بدون PIL: همان فایل اصلی
        logo_b64 = base64.b64encode(logo_bytes).decode("ascii")

    # فونت برای متن اسپلش — وب‌فونتِ بیلد در این پنجره‌ی جدا لود نمی‌شود
    font_b64 = ""
    assets = os.path.join(_STUDIO_STATIC, "dist", "assets")
    if os.path.isdir(assets):
        for fn in sorted(os.listdir(assets)):
            if fn.startswith("Vazirmatn-ExtraBold") and fn.endswith(".woff2"):
                font_b64 = base64.b64encode(_raw(os.path.join(assets, fn))).decode("ascii")
                break

    html = _SPLASH_HTML.replace("__LOGO__", logo_b64)
    html = html.replace("__FONT__", font_b64)
    return html


class StudioApi:
    """پل بین رابط وب استودیو و پایتون (فایل، اجرا، دیالوگ‌ها)"""

    def __init__(self, initial_project=None):
        self._window = None
        self.initial_project = initial_project  # مسیر فایل داده‌شده به goya studio
        self._proc = None
        self._repl = None  # نشست پایدار REPL (مفسر درون‌پروسه‌ای)
        self._ai_thread = None
        self._ai_stop = None

    # ── اجرا ──

    def run(self, code):
        """اجرای برنامه در پروسه‌ی جدا — خروجی زنده به پنل استودیو برمی‌گرده"""
        if self._proc is not None and self._proc.poll() is None:
            return {"ok": False, "err": "یه برنامه در حال اجراست — اول پنجره‌ش رو ببند"}

        from .errors import GoyaError, show_error
        from .lexer import Lexer
        from .parser import Parser

        try:
            Parser(Lexer(code).lex()).parse()  # اعتبارسنجی نگارشی فوری
        except GoyaError as e:
            return {"ok": False, "err": show_error(e, code)}

        fd, path = tempfile.mkstemp(suffix=".goya")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)

        env = dict(os.environ)
        # پایپ فرزند UTF-8 — وگرنه متن فارسی خطاها به شکل \u0645… escape می‌شود
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        cmd = [sys.executable, "-m", "goya", "run", path]
        _log("spawn: " + " ".join(cmd))
        self._repl = None  # نشست REPL با اجرای برنامه‌ی تازه ریست می‌شود
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        threading.Thread(target=self._pump_output, daemon=True).start()
        return {"ok": True, "note": "پنجره‌ی برنامه باز شد"}

    def _pump_output(self):
        proc = self._proc
        try:
            for line in proc.stdout:
                self._emit_out(line.rstrip("\n"))
            code = proc.wait()
            self._emit_out("── برنامه پایان یافت (کد خروج: {}) ──".format(code))
        except Exception:
            pass

    def _emit_js(self, script):
        """اجرای یک قطعه جاوااسکریپت در صفحه — اگر پنجره حاضر نبود بی‌سروصدا رد شو"""
        if not self._window:
            return
        try:
            self._window.evaluate_js(script)
        except Exception:
            pass

    def _emit_out(self, text):
        payload = json.dumps(text, ensure_ascii=False)
        self._emit_js("studioAppendOut({});".format(payload))

    # ── فایل پروژه ──

    def load_initial(self):
        """پروژه‌ای که هنگام لانچ به goya studio داده شده"""
        _log("bridge: load_initial called — پل pywebview زنده است")
        self._repl = None
        if self.initial_project and os.path.isfile(self.initial_project):
            try:
                with open(self.initial_project, encoding="utf-8") as f:
                    return {"ok": True, "content": f.read(), "path": self.initial_project}
            except OSError as e:
                return {"ok": False, "err": str(e)}
        return {"ok": True, "content": "", "path": ""}

    def read_file(self, path):
        """خواندن یک فایل .goya مشخص"""
        self._repl = None
        try:
            with open(path, encoding="utf-8") as f:
                return {"ok": True, "content": f.read(), "path": path}
        except (OSError, UnicodeDecodeError) as e:
            return {"ok": False, "err": str(e)}

    def list_recent_files(self):
        """فهرست فایل‌های .goya در پوشه‌ی پروژه‌های کاربر"""
        docs = os.path.join(os.path.expanduser("~"), "Documents", "Goya")
        if not os.path.isdir(docs):
            docs = os.path.expanduser("~")
        files = []
        try:
            for name in sorted(os.listdir(docs)):
                if name.endswith(".goya"):
                    path = os.path.join(docs, name)
                    size = os.path.getsize(path)
                    mtime = os.path.getmtime(path)
                    files.append({"name": name, "path": path, "size": size, "mtime": mtime})
        except OSError:
            pass
        files.sort(key=lambda x: x["mtime"], reverse=True)
        return files[:20]

    def save_project(self, content):
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename="برنامه.goya",
            file_types=("پروژه گویا (*.goya)", "*.goya"),
        )
        if not result:
            return {"ok": False}
        path = result if isinstance(result, str) else result[0]
        if not path.endswith(".goya"):
            path += ".goya"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": path}

    def open_project(self):
        self._repl = None
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("پروژه گویا (*.goya)", "*.goya", "همه فایل‌ها (*.*)", "*.*"),
        )
        if not result:
            return {"ok": False}
        path = result if isinstance(result, str) else result[0]
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            return {"ok": False, "err": str(e)}
        return {"ok": True, "content": content, "path": path}

    def new_project(self):
        self._repl = None
        return {"ok": True}

    # ── REPL ترمینال ──

    def repl_eval(self, code):
        """اجرای فوری یک قطعه کد گویا در نشست REPL — متغیرها بین ورودی‌ها می‌مانند"""
        from .errors import GoyaError, show_error
        from .interpreter import Interpreter
        from .lexer import Lexer
        from .parser import Parser

        if self._repl is None:
            self._repl = Interpreter(input_fn=lambda p="": "", time_limit=6.0)
        buf = io.StringIO()
        try:
            program = Parser(Lexer(code).lex()).parse()
            with contextlib.redirect_stdout(buf):
                self._repl.run(program)
            return {"ok": True, "out": buf.getvalue()}
        except GoyaError as e:
            return {"ok": False, "out": buf.getvalue(), "err": show_error(e, code)}
        except RecursionError:
            return {"ok": False, "out": buf.getvalue(), "err": "خطای اجرا: تابع‌ها خیلی تو در تو شدن"}
        except Exception as e:  # خطای غیرمنتظره — نشست خراب است، از نو بساز
            self._repl = None
            return {"ok": False, "out": buf.getvalue(), "err": "خطای داخلی REPL: " + str(e)}

    # ── دستیار هوش مصنوعی (سازگار با OpenAI — Ollama، LM Studio، vLLM و…) ──

    def ai_models(self, cfg):
        """فهرست مدل‌های موجود روی سرویس کاربر"""
        from .ai import AiError, list_models

        try:
            return {"ok": True, "models": list_models(cfg.get("baseUrl", ""), cfg.get("apiKey", ""))}
        except AiError as e:
            return {"ok": False, "err": str(e)}

    def ai_chat(self, cfg, messages):
        """چت با استریم — قطعه‌ها با studioAiChunk و پایان با studioAiDone به رابط می‌رسند"""
        from .ai import chat_stream

        if self._ai_thread is not None and self._ai_thread.is_alive():
            return {"ok": False, "err": "درخواست قبلی هنوز در جریان است — اول توقفش کن"}

        req_id = "ai{}".format(int(time.time() * 1000))
        stop = {"stop": False}
        self._ai_stop = stop

        def chunk_js(piece):
            self._emit_js("studioAiChunk({},{});".format(
                json.dumps(req_id), json.dumps(piece, ensure_ascii=False)))

        def worker():
            err = None
            try:
                chat_stream(
                    cfg.get("baseUrl", ""), cfg.get("apiKey", ""), cfg.get("model", ""),
                    messages, chunk_js, stop,
                )
            except Exception as e:  # AiError و هر چیز غیرمنتظره دیگر
                err = str(e)
            self._emit_js("studioAiDone({},{});".format(
                json.dumps(req_id),
                json.dumps(err, ensure_ascii=False) if err else "null",
            ))

        self._ai_thread = threading.Thread(target=worker, daemon=True)
        self._ai_thread.start()
        return {"ok": True, "id": req_id}

    def ai_stop(self):
        """درخواست توقف تولید پاسخ جاری"""
        if self._ai_stop is not None:
            self._ai_stop["stop"] = True
        return {"ok": True}

    # ── چندپنجره‌ای — کار هم‌زمان روی پروژه‌های مختلف ──

    def _spawn_studio(self, extra_args):
        kwargs = {}
        if os.name == "nt":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW — کنسول فلش نزند
        cwd = None
        if not getattr(sys, "frozen", False):
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        subprocess.Popen(
            [sys.executable, "-m", "goya", "studio"] + list(extra_args),
            cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)

    def open_new_window(self):
        """استودیوی تازه و خالی در پروسه‌ی جدا"""
        self._spawn_studio(["--inst", os.urandom(3).hex()])
        return {"ok": True}

    def open_project_in_new_window(self):
        """انتخاب پروژه و باز کردنش در پنجره‌ی جدید — پنجره‌ی فعلی دست‌نخورده"""
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=("پروژه گویا (*.goya)", "*.goya", "همه فایل‌ها (*.*)", "*.*"),
        )
        if not result:
            return {"ok": False}
        path = result if isinstance(result, str) else result[0]
        self._spawn_studio([path])
        return {"ok": True, "path": path}

    # ── خروجی گرفتن (exe ویندوز + اجرایی لینوکس — هم‌زمان) ──

    def pick_export_dir(self):
        """انتخاب پوشه‌ی خروجی"""
        result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if not result:
            return {"ok": False}
        path = result if isinstance(result, str) else result[0]
        return {"ok": True, "path": path}

    def reveal_export(self, path):
        """باز کردن پوشه‌ی خروجی در اکسپلورر سیستم"""
        try:
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            if os.name == "nt":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "err": str(e)}

    def build_export(self, code, targets, out_dir, name):
        """ساخت موازی هدف‌های انتخابی — لاگ زنده با studioBuildLog و پایان با studioBuildDone

        targets: {"win64": bool, "win32": bool, "lin64": bool, "lin32": bool}
        """
        from .errors import GoyaError, show_error
        from .lexer import Lexer
        from .parser import Parser

        try:
            Parser(Lexer(code).lex()).parse()  # اعتبارسنجی نگارشی فوری
        except GoyaError as e:
            return {"ok": False, "err": show_error(e, code)}

        out_dir = out_dir or os.path.join(os.path.expanduser("~"), "Documents", "Goya", "خروجی")
        build_id = "b{}".format(int(time.time() * 1000))
        fd, project_file = tempfile.mkstemp(suffix=".goya", prefix="export-")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)

        def emit(entry):
            self._emit_js("studioBuildLog({},{});".format(
                json.dumps(build_id), json.dumps(entry, ensure_ascii=False)))

        def done(payload):
            self._emit_js("studioBuildDone({},{});".format(
                json.dumps(build_id), json.dumps(payload, ensure_ascii=False)))

        def log(msg):
            emit({"msg": str(msg), "kind": "info"})

        def worker():
            from . import export as exporter
            results = exporter.build(
                project_file, exporter._safe_name(name or "GoyaApp"),
                out_dir, targets or {}, log,
            )
            try:
                os.unlink(project_file)
            except OSError:
                pass
            done({"results": results, "outDir": out_dir})

        threading.Thread(target=worker, daemon=True).start()
        return {"ok": True, "id": build_id}


def _instance_key(project_path, inst=None):
    """کلید پایدار نمونه — هر پروژه فضای ذخیره‌سازی خودش را دارد تا دو پنجره
    روی state هم ننویسند. پروژه‌ی بی‌مسیر با --inst یکتا از والد می‌آید."""
    if inst:
        return inst
    if project_path:
        import hashlib
        return "p" + hashlib.sha1(os.path.abspath(project_path).encode("utf-8")).hexdigest()[:8]
    return None


def start(project_path=None, inst=None):
    # pythonw هیچ stdout/stderr ندارد (None) و اولین نوشته‌ی pywebview/pythonnet
    # پروسه را بی‌صدا می‌کشد — جریان‌ها را به فایل لاگ وصل کن
    if sys.stdout is None or sys.stderr is None:
        _f = open(
            os.path.join(tempfile.gettempdir(), "goya_studio.log"),
            "a", buffering=1, encoding="utf-8", errors="replace",
        )
        if sys.stdout is None:
            sys.stdout = _f
        if sys.stderr is None:
            sys.stderr = _f
    _log("boot: start() entered, pythonw={}".format(sys.executable.endswith("pythonw.exe")))
    try:
        import webview
    except ImportError:
        print("گویا استودیو به pywebview نیاز داره:")
        print("    pip install pywebview")
        sys.exit(1)

    api = StudioApi(project_path)
    dist_index = os.path.join(_STUDIO_STATIC, "dist", "index.html")
    srv = None
    if os.path.isfile(dist_index):
        srv = _serve_dist()
        url = "http://127.0.0.1:{}/".format(srv.server_address[1])
    else:
        url = os.path.join(_STUDIO_STATIC, "studio.html")
    key = _instance_key(project_path, inst)
    if key and srv:
        url = url + "?inst=" + key
    _log("boot: serving {} → {} (inst={})".format("dist" if srv else "fallback", url, key or "-"))

    smoke = bool(os.environ.get("GOYA_SMOKE"))

    # اسپلش: فوری بالا می‌آید تا شروعِ خالی دیده نشود؛ پنجره‌ی اصلی مخفی لود
    # می‌شود و وقتی آماده شد (لود + نیم ثانیه برای رندر ری‌اکت) جای آن را می‌گیرد
    splash = None
    if not smoke:
        # maximized روی پنجره‌ی frameless کار نمی‌کند — اندازه‌ی صفحه را صریح
        # می‌دهیم؛ پروسه هنوز DPI-aware نشده پس متریک‌ها در فضای منطقی‌اند
        # (همان فضایی که pywebview برای width/height استفاده می‌کند)
        sw, sh = 800, 600
        if os.name == "nt":
            import ctypes
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
        splash = webview.create_window(
            "گویا استودیو",
            html=_splash_html(),
            width=sw,
            height=sh,
            x=0,
            y=0,
            frameless=True,
            resizable=False,
            on_top=True,
            background_color="#FFF4E6",
        )
    main = webview.create_window(
        "گویا استودیو",
        url=url,
        js_api=api,
        width=1340,
        height=860,
        min_size=(1050, 700),
        maximized=True,  # پنجره همیشه تمام‌صفحه باز می‌شود
        hidden=not smoke,  # تا آماده‌شدن محتوا پنهان
        background_color="#FFF4E6",  # هم‌رنگ پس‌زمینه‌ی تم روشن — بدون فلش تیره در شروع
    )
    api._window = main
    _log("boot: windows created ({}main hidden), starting gui loop".format(
        "splash + " if splash else ""))

    def _on_closed():
        # بستن پنجره = پایان کار؛ با خروج قطعی جلوی خراب‌شدن کد خروج توسط
        # teardown‌ی CLR/WebView2 (0xCFFFFFFF) را می‌گیریم — همه‌چیز از قبل ذخیره شده
        _log("teardown: window closed")
        os._exit(0)

    events = getattr(api._window, "events", None)
    if events is not None and hasattr(events, "closed"):
        events.closed += _on_closed

    if splash is not None:
        revealed = {"done": False}
        reveal_lock = threading.Lock()

        def _reveal():
            with reveal_lock:
                if revealed["done"]:
                    return
                revealed["done"] = True
            try:
                main.show()
            except Exception as e:
                _log("boot: main.show failed: {!r}".format(e))
            try:
                splash.destroy()
            except Exception:
                pass
            _log("boot: main window revealed, splash gone")

        def _on_loaded():
            # نیم ثانیه فرصت برای رندر نهایی ری‌اکت قبل از رونمایی
            threading.Timer(0.5, _reveal).start()

        def _apply_icons():
            from .export import ensure_ico
            ico = ensure_ico()
            if ico:
                for w in (main, splash):
                    _set_window_icon(_window_hwnd(w), ico)

        def _on_splash_loaded():
            _apply_icons()

        main_events = getattr(main, "events", None)
        if main_events is not None and hasattr(main_events, "loaded"):
            main_events.loaded += _on_loaded
        splash_events = getattr(splash, "events", None)
        if splash_events is not None and hasattr(splash_events, "loaded"):
            splash_events.loaded += _on_splash_loaded
        # تور ایمنی: اگر رویداد لود به هر دلیل نیامد، حداکثر تا ۲۰ ثانیه رونمایی کن
        threading.Timer(20.0, _reveal).start()

    if smoke:
        # تست دودی: بعد از لود کامل صفحه، پنجره را ببند — بستنِ وسطِ لود،
        # مسیر نابودی WebView2 را تا ۳۰ ثانیه قفل می‌کند
        import time as _smoke_time

        def _smoke_close():
            try:
                api._window.events.loaded.wait(30)
            except Exception:
                pass
            _smoke_time.sleep(1.0)
            api._window.destroy()

        threading.Thread(target=_smoke_close, daemon=True).start()
    try:
        webview.start(gui="edgechromium" if sys.platform == "win32" else None)
    except Exception as e:
        _log("boot: gui loop CRASHED: {!r}".format(e))
        raise
    if srv:
        srv.shutdown()
    # مسیر پشتیبان: اگر رویداد closed نرسیده باشد اینجا به پاکی تمیز می‌کنیم
    _log("teardown: after start")


if __name__ == "__main__":
    start(sys.argv[1] if len(sys.argv) > 1 else None)
