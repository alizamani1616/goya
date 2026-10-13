# -*- coding: utf-8 -*-
"""خروجی گرفتن از برنامه‌ی گویا — هم‌زمان exe ویندوز و اجرایی لینوکس

ویندوز: PyInstaller onefile محلی (--noconsole) — سورس برنامه داخلش باندل می‌شود.
لینوکس (به ترتیب تلاش):
  ۱. داکر (اگر نصب باشد) → باینری واقعی ELF با python:3.12
  ۲. WSL (اگر پایتون+پایل‌نالر+tcl/tk داشته باشد) → باینری واقعی ELF
  ۳. بسته‌ی قابل‌حمل tar.gz — goya + customtkinter + لانچر؛ روی مقصد فقط
     python3 با tkinter لازم است (اکثر توزیع‌های دسکتاپ: python3-tk)
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))          # پکیج goya
_STUDIO_STATIC = os.path.join(_HERE, "studio_static")
_GOYA_PARENT = os.path.dirname(_HERE)                        # والد پکیج — برای import

_LAUNCHER = '''# -*- coding: utf-8 -*-
"""لانچر برنامه‌ی ساخته‌شده با گویا — سورس برنامه به نام program.goya کنارش باندل می‌شود"""
import os
import sys
import traceback


def _show(title, text):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, text)
        root.destroy()
    except Exception:
        sys.stderr.write(text + "\\n")


def main():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, "program.goya"), encoding="utf-8") as f:
        source = f.read()
    from goya.errors import GoyaError, show_error
    from goya.interpreter import Interpreter
    from goya.lexer import Lexer
    from goya.parser import Parser
    try:
        Interpreter().run(Parser(Lexer(source).lex()).parse())
    except GoyaError as e:
        _show("خطای گویا", show_error(e, source))
    except Exception:
        _show("خطای غیرمنتظره", traceback.format_exc())


if __name__ == "__main__":
    main()
'''

_RUN_SH = """#!/bin/sh
# اجرای برنامه‌ی گویا — روی مقصد python3 با tkinter لازم است (debian/ubuntu: sudo apt install python3-tk)
cd "$(dirname "$0")"
exec python3 launcher.py
"""

_README = """بسته‌ی قابل‌حمل گویا برای لینوکس
=================================
اجرا:  ./run.sh

نیازمندی مقصد: python3 با tkinter
(در اکثر توزیع‌ها نصب است؛ نبود: sudo apt install python3-tk)

پوشه‌ی goya/ موتور زبان و پوشه‌ی customtkinter/ رابط گرافیکی است —
هر دو همراه برنامه‌اند و نصب چیز دیگری لازم نیست.
"""


def _pkg_dir(name):
    spec = importlib.util.find_spec(name)
    if not spec or not spec.origin:
        return None
    return os.path.dirname(spec.origin)


def _safe_name(title):
    """نام پروژه → نام فایل خروجی (لاتین/عدد/خط تیره — امن برای همه‌ی سیستم‌ها)"""
    out = []
    for ch in title.strip():
        if ch.isascii() and (ch.isalnum() or ch in "-_"):
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    s = "".join(out).strip("-")
    return s or "GoyaApp"


def _stream(cmd, cwd, log, env=None):
    """اجرای دستور با انتقال زنده‌ی خروجی به لاگ — کد خروج برمی‌گردد"""
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    p = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", env=env,
        creationflags=flags,
    )
    for line in p.stdout:
        log(line.rstrip("\n"))
    return p.wait()


def _stage_build_dir(project_path):
    """پوشه‌ی ساخت: لانچر + program.goya + پکیج goya (خودکفا برای داکر/WSL)"""
    tmp = tempfile.mkdtemp(prefix="goya-export-")
    with open(os.path.join(tmp, "launcher.py"), "w", encoding="utf-8") as f:
        f.write(_LAUNCHER)
    shutil.copyfile(project_path, os.path.join(tmp, "program.goya"))
    shutil.copytree(_HERE, os.path.join(tmp, "goya"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    return tmp


# ───────────────────────── ویندوز ─────────────────────────

def _ensure_pyinstaller(log):
    try:
        import PyInstaller  # noqa: F401
        return True
    except ImportError:
        log("pyinstaller نصب نیست — در حال نصب…")
        code = _stream([sys.executable, "-m", "pip", "install", "pyinstaller"],
                       None, log)
        if code != 0:
            log("نصب pyinstaller ناموفق بود — با «pip install pyinstaller» دستی نصبش کن")
            return False
        try:
            import PyInstaller  # noqa: F401
            return True
        except ImportError:
            return False


def _find_python_32(log):
    """پایتون ۳۲بیتی برای بیلد x86 — با لانچر رسمی py"""
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        r = subprocess.run(
            ["py", "-3-32", "-c", "import struct;print(struct.calcsize('P')*8)"],
            capture_output=True, text=True, timeout=30, creationflags=flags)
        if r.returncode == 0 and "32" in (r.stdout or ""):
            return ["py", "-3-32"]
    except Exception:
        pass
    log("پایتون ۳۲بیتی پیدا نشد — از python.org نسخه‌ی x86 نصب کن (لانچر py آن را می‌یابد)")
    return None


def build_windows(project_path, name, out_dir, log, bits=64):
    """exe تک‌فایلی ویندوز — سورس برنامه داخلش باندل است"""
    try:
        log("── ویندوز: ساخت exe با PyInstaller ──")
        if not _ensure_pyinstaller(log):
            return {"ok": False, "err": "pyinstaller در دسترس نیست"}
        if bits == 32:
            pycmd = _find_python_32(log)
            if not pycmd:
                return {"ok": False, "err": "برای خروجی ۳۲بیتی باید پایتون x86 (۳۲بیتی) نصب باشد"}
            suffix = "-x86"
        else:
            pycmd = [sys.executable]
            suffix = "-x64"

        tmp = tempfile.mkdtemp(prefix="goya-export-win-")
        with open(os.path.join(tmp, "launcher.py"), "w", encoding="utf-8") as f:
            f.write(_LAUNCHER)
        shutil.copyfile(project_path, os.path.join(tmp, "program.goya"))
        dist = os.path.join(tmp, "dist")
        fonts = os.path.join(_HERE, "fonts")
        cmd = [
            *pycmd, "-m", "PyInstaller",
            "--noconfirm", "--onefile", "--noconsole",
            "--name", name,
            "--add-data", os.path.join(tmp, "program.goya") + os.pathsep + ".",
            "--collect-data", "customtkinter",
        ]
        if os.path.isdir(fonts):
            # فونت وزیرمتن — gui.py در حالت فروزن از _MEIPASS/goya/fonts برمی‌دارد
            cmd += ["--add-data", fonts + os.pathsep + os.path.join("goya", "fonts")]
        ico = ensure_ico()
        if ico:
            cmd += ["--icon", ico]
        cmd += [
            "--paths", _GOYA_PARENT,
            "--distpath", dist,
            "--workpath", os.path.join(tmp, "work"),
            "--specpath", tmp,
            os.path.join(tmp, "launcher.py"),
        ]
        code = _stream(cmd, tmp, log)
        exe = os.path.join(dist, name + ".exe")
        target_name = name + suffix + ".exe"
        if code != 0 or not os.path.isfile(exe):
            return {"ok": False, "err": "ساخت exe ناموفق بود — جزئیات در لاگ بالا"}
        os.makedirs(out_dir, exist_ok=True)
        target = os.path.join(out_dir, target_name)
        shutil.copyfile(exe, target)
        log("── ویندوز: انجام شد → " + target)
        return {"ok": True, "path": target, "kind": "exe"}
    except Exception as e:
        return {"ok": False, "err": str(e)}


# ───────────────────────── لینوکس ─────────────────────────

def ensure_ico():
    """goya.ico چندسایزی از لوگو — آیکون پنجره‌ی استودیو و خروجی exe (یک بار می‌سازد)"""
    ico = os.path.join(_STUDIO_STATIC, "goya.ico")
    if os.path.isfile(ico):
        return ico
    src = os.path.join(_STUDIO_STATIC, "dist", "logo-full.png")
    if not os.path.isfile(src):
        return None
    try:
        from PIL import Image
        Image.open(src).save(ico, sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
        return ico
    except Exception:
        return None


def _docker_alive():
    if not shutil.which("docker"):
        return False
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        r = subprocess.run(["docker", "info", "--format", "ok"],
                           capture_output=True, text=True, timeout=30,
                           creationflags=flags)
        return r.returncode == 0 and "ok" in (r.stdout or "")
    except Exception:
        return False


def build_linux_docker(project_path, name, out_dir, log, bits=64):
    """باینری واقعی ELF داخل کانتینر python:3.12 — اولین بار تصویر دانلود می‌شود"""
    if not _docker_alive():
        return None
    try:
        if bits == 32:
            log("── لینوکس x86: ساخت ELF ۳۲بیتی داخل کانتینر i386 ──")
            image = "i386/debian:bookworm"
            prelude = ("apt-get update -qq && apt-get install -y -qq python3 python3-pip python3-pil >/dev/null && "
                       "pip install --quiet --break-system-packages pyinstaller customtkinter && ")
        else:
            log("── لینوکس: ساخت ELF با داکر (اگر تصویر python:3.12 نباشد، دانلود می‌شود) ──")
            image = "python:3.12"
            prelude = "pip install --quiet --no-input pyinstaller customtkinter && "
        suffix = "-x86" if bits == 32 else "-x64"
        tmp = _stage_build_dir(project_path)
        cmd = [
            "docker", "run", "--rm",
            "-v", tmp + ":/build", "-v", out_dir + ":/out",
            "-w", "/build", image,
            "bash", "-lc",
            prelude +
            "pyinstaller --noconfirm --onefile --name '{name}' "
            "--add-data program.goya:. --add-data goya/fonts:goya/fonts "
            "--collect-data customtkinter "
            "--distpath /out launcher.py".format(name=name),
        ]
        code = _stream(cmd, tmp, log)
        built = os.path.join(out_dir, name)
        target = os.path.join(out_dir, name + suffix)
        if os.path.isfile(built):
            os.replace(built, target)
        if code != 0 or not os.path.isfile(target):
            return {"ok": False, "err": "ساخت داخل داکر ناموفق بود — جزئیات در لاگ بالا"}
        os.chmod(target, 0o755)
        log("── لینوکس: ELF ساخته شد → " + target)
        return {"ok": True, "path": target, "kind": "elf"}
    except Exception as e:
        log("داکر ناموفق: " + str(e))
        return None


def build_linux_wsl(project_path, name, out_dir, log):
    """باینری ELF داخل WSL — فقط اگر پایتون+tcl/tk+pyinstaller آماده باشد"""
    wsl = shutil.which("wsl") or shutil.which("wsl.exe")
    if not wsl:
        return None
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

    def wsl_run(cmdline, timeout=120):
        return subprocess.run([wsl, "-e", "bash", "-lc", cmdline],
                              capture_output=True, text=True, timeout=timeout,
                              errors="replace", creationflags=flags)

    def wsl_path(win_path):
        r = wsl_run("wslpath -u '{}'".format(win_path.replace("'", "'\\''")))
        return (r.stdout or "").strip()

    try:
        wsl_run("true", timeout=20)
    except Exception:
        return None
    try:
        log("── لینوکس: تلاش با WSL ──")
        r = wsl_run("python3 -c 'import tkinter, PyInstaller' 2>&1")
        if r.returncode != 0:
            log("WSL: pyinstaller یا tkinter نیست — نصب تلاش می‌شود…")
            wsl_run("python3 -m pip install --user --quiet pyinstaller customtkinter",
                    timeout=600)
            r = wsl_run("python3 -c 'import tkinter, PyInstaller' 2>&1")
            if r.returncode != 0:
                log("WSL آماده نیست — به بسته‌ی قابل‌حمل برمی‌گردم")
                return None
        build_dir = _stage_build_dir(project_path)
        bdir, odir = wsl_path(build_dir), wsl_path(out_dir)
        if not bdir or not odir:
            log("WSL: تبدیل مسیر ناموفق بود")
            return None
        cmd = (
            "cd '{b}' && python3 -m PyInstaller --noconfirm --onefile "
            "--name '{n}' --add-data program.goya:. --add-data goya/fonts:goya/fonts "
            "--collect-data customtkinter "
            "--distpath '{o}' launcher.py"
        ).format(b=bdir, n=name, o=odir)
        r = wsl_run(cmd, timeout=1200)
        target = os.path.join(out_dir, name)
        if r.returncode != 0 or not os.path.isfile(target):
            log("WSL: ساخت ناموفق — " + (r.stdout or r.stderr or "").strip()[-300:])
            return None
        log("── لینوکس: ELF با WSL ساخته شد → " + target)
        return {"ok": True, "path": target, "kind": "elf"}
    except Exception as e:
        log("WSL ناموفق: " + str(e))
        return None


def build_linux_bundle(project_path, name, out_dir, log, bits=64):
    """بسته‌ی قابل‌حمل tar.gz — روی مقصد فقط python3 با tkinter لازم است"""
    try:
        log("── لینوکس: ساخت بسته‌ی قابل‌حمل (بدون داکر/WSL) ──")
        stage = tempfile.mkdtemp(prefix="goya-bundle-")
        root = os.path.join(stage, name)
        os.makedirs(root)
        shutil.copytree(_HERE, os.path.join(root, "goya"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        ctk = _pkg_dir("customtkinter")
        if ctk:
            shutil.copytree(ctk, os.path.join(root, "customtkinter"),
                            ignore=shutil.ignore_patterns("__pycache__"))
        pil = _pkg_dir("PIL")
        if pil:
            # customtkinter به pillow نیاز دارد — بدون آن بسته روی مقصد import نمی‌شود
            shutil.copytree(pil, os.path.join(root, "PIL"),
                            ignore=shutil.ignore_patterns("__pycache__", "*.dylib"))
        with open(os.path.join(root, "launcher.py"), "w", encoding="utf-8") as f:
            f.write(_LAUNCHER)
        shutil.copyfile(project_path, os.path.join(root, "program.goya"))
        with open(os.path.join(root, "README.txt"), "w", encoding="utf-8", newline="\n") as f:
            f.write(_README)

        # run.sh بیرون از ریشه نوشته می‌شود تا با mode اجرایی (۰۷۵۵) داخل tar بیاید —
        # روی ویندوز chmod دیسک کاری نمی‌کند و باید روی خودِ عضو tar ست شود
        runsh = os.path.join(stage, "run.sh")
        with open(runsh, "w", encoding="utf-8", newline="\n") as f:
            f.write(_RUN_SH)

        suffix = "-x86" if bits == 32 else "-x64"
        os.makedirs(out_dir, exist_ok=True)
        target = os.path.join(out_dir, name + suffix + "-linux.tar.gz")
        with tarfile.open(target, "w:gz") as tf:
            tf.add(root, arcname=name)
            ti = tf.gettarinfo(runsh, arcname=name + "/run.sh")
            ti.mode = 0o755
            with open(runsh, "rb") as f:
                tf.addfile(ti, f)
        log("── لینوکس: بسته ساخته شد → " + target)
        log("یادآوری: این بسته روی مقصد به python3 با tkinter نیاز دارد "
            "(بدون داکر/WSL ساخت باینری تک‌فایلی ممکن نبود)")
        return {"ok": True, "path": target, "kind": "bundle"}
    except Exception as e:
        return {"ok": False, "err": str(e)}


# ───────────────────────── ورودی اصلی ─────────────────────────

def build(project_path, name, out_dir, targets, log):
    """ساخت موازی همه‌ی هدف‌های انتخابی — هر کدام نخ خودش

    targets: {"win64": bool, "win32": bool, "lin64": bool, "lin32": bool}
    log: تابع دریافت هر خط
    """
    results = {}
    lock = threading.Lock()

    def do(key):
        try:
            if key.startswith("win"):
                r = build_windows(project_path, name, out_dir, log,
                                  bits=32 if key == "win32" else 64)
            else:
                bits = 32 if key == "lin32" else 64
                r = build_linux_docker(project_path, name, out_dir, log, bits=bits)
                if r is None and bits == 64:
                    r = build_linux_wsl(project_path, name, out_dir, log)
                if r is None:
                    r = build_linux_bundle(project_path, name, out_dir, log, bits=bits)
            with lock:
                results[key] = r
        except Exception as e:
            with lock:
                results[key] = {"ok": False, "err": str(e)}

    active = [k for k in ("win64", "win32", "lin64", "lin32") if targets.get(k)]
    threads = [threading.Thread(target=do, args=(k,), daemon=True) for k in active]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results
