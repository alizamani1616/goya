# -*- coding: utf-8 -*-
"""گویا استودیو — محیط ویژوال ساخت نرم‌افزار ویندوزی

اجرا:  goya studio [پروژه.goya]
پنجره‌ی بومی (pywebview) + طراح درگ‌دراپ + ادیتور کد + اجرای F5.
برنامه‌ها در پروسه‌ی جدا اجرا می‌شن — استودیو همیشه واکنش‌گرا می‌مونه.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDIO_STATIC = os.path.join(_HERE, "studio_static")


def _log(msg):
    """لاگ سبک برای اشکال‌زدایی — کنار فایل موقت"""
    try:
        with open(os.path.join(tempfile.gettempdir(), "goya_studio.log"), "a", encoding="utf-8") as f:
            f.write(msg + chr(10))
    except OSError:
        pass


class StudioApi:
    """پل بین رابط وب استودیو و پایتون (فایل، اجرا، دیالوگ‌ها)"""

    def __init__(self, initial_project=None):
        self.window = None
        self.initial_project = initial_project  # مسیر فایل داده‌شده به goya studio
        self._proc = None

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
        cmd = [sys.executable, "-m", "goya", "run", path]
        _log("spawn: " + " ".join(cmd))
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

    def _emit_out(self, text):
        if not self.window:
            return
        try:
            payload = json.dumps(text, ensure_ascii=False)
            self.window.evaluate_js("studioAppendOut({});".format(payload))
        except Exception:
            pass
        finally:
            _log("child exited: " + str(proc.returncode))

    # ── فایل پروژه ──

    def load_initial(self):
        """پروژه‌ای که هنگام لانچ به goya studio داده شده"""
        if self.initial_project and os.path.isfile(self.initial_project):
            try:
                with open(self.initial_project, encoding="utf-8") as f:
                    return {"ok": True, "content": f.read(), "path": self.initial_project}
            except OSError as e:
                return {"ok": False, "err": str(e)}
        return {"ok": True, "content": "", "path": ""}

    def save_project(self, content):
        result = self.window.create_file_dialog(
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
        result = self.window.create_file_dialog(
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
        return {"ok": True}


def start(project_path=None):
    try:
        import webview
    except ImportError:
        print("گویا استودیو به pywebview نیاز داره:")
        print("    pip install pywebview")
        sys.exit(1)

    api = StudioApi(project_path)
    html = os.path.join(_STUDIO_STATIC, "studio.html")
    webview.create_window(
        "گویا استودیو",
        url=html,
        js_api=api,
        width=1340,
        height=860,
        min_size=(1050, 700),
        background_color="#FFF3E4",
    )
    api.window = webview.windows[0]
    webview.start(gui="edgechromium" if sys.platform == "win32" else None)


if __name__ == "__main__":
    start(sys.argv[1] if len(sys.argv) > 1 else None)
