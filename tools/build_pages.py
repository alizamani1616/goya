# -*- coding: utf-8 -*-
"""ساخت نسخه‌ی استاتیک GitHub Pages در docs/

اجرا:  python tools/build_pages.py
- docs/index.html  ← صفحه‌ی معرفی (از goya/ide_static/landing.html)
- docs/ide.html    ← محیط تست سریع آنلاین (از goya/ide_static/index.html + Pyodide)
- docs/goya_pkg/   ← پکیج پایتون گویا برای اجرای داخل مرورگر
"""

import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
STATIC = os.path.join(ROOT, "goya", "ide_static")
DOCS = os.path.join(ROOT, "docs")
EXAMPLES_DIR = os.path.join(ROOT, "examples")

TITLES = {
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


def rel_to_abs_paths(html):
    """مسیرهای مطلق محلی → نسبی برای Pages (سایت زیر /goya/ سرو می‌شه)"""
    html = html.replace('href="/favicon.png"', 'href="favicon.png"')
    html = html.replace('src="/logo.png"', 'src="logo.png"')
    html = html.replace('src="/icons/', 'src="icons/"')
    return html


def build_landing():
    src = open(os.path.join(STATIC, "landing.html"), encoding="utf-8").read()
    html = rel_to_abs_paths(src)
    html = html.replace(">تست سریع توی مرورگر</a>", ">تست سریع توی مرورگر</a>")
    html = html.replace('href="/ide"', 'href="ide.html"')
    open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8").write(html)
    print("docs/index.html ✓")


def examples_data():
    items = []
    if os.path.isdir(EXAMPLES_DIR):
        for name in sorted(os.listdir(EXAMPLES_DIR)):
            if not name.endswith(".goya"):
                continue
            code = open(os.path.join(EXAMPLES_DIR, name), encoding="utf-8").read()
            base = name[:-5]
            items.append({"file": name, "title": TITLES.get(base, base), "code": code})
    return items


def build_ide():
    src = open(os.path.join(STATIC, "index.html"), encoding="utf-8").read()
    html = rel_to_abs_paths(src)
    html = html.replace('href="/"', 'href="index.html"')
    html = html.replace(
        "تست سریع زبان — محیط کامل، محلی و آفلاین",
        "تست سریع زبان — پایتون واقعی، اجرا داخل مرورگر تو",
    )
    inject = (
        '<script>window.GOYA_ONLINE=true;window.EXAMPLES_DATA='
        + json.dumps(examples_data(), ensure_ascii=False)
        + ';</script>\n'
        '<script src="https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js"></script>\n'
        "</head>"
    )
    html = html.replace("</head>", inject, 1)
    open(os.path.join(DOCS, "ide.html"), "w", encoding="utf-8").write(html)
    print("docs/ide.html ✓")


def build_pkg():
    pkg_dir = os.path.join(DOCS, "goya_pkg")
    os.makedirs(pkg_dir, exist_ok=True)
    pkg_src = os.path.join(ROOT, "goya")
    files = [
        "__init__.py", "normalize.py", "errors.py",
        "lexer.py", "parser.py", "interpreter.py", "stdlib.py",
    ]
    for f in files:
        shutil.copy(os.path.join(pkg_src, f), os.path.join(pkg_dir, f))
    print("docs/goya_pkg ✓", len(files), "files")


def copy_static():
    shutil.copy(os.path.join(STATIC, "logo-full.png"), os.path.join(DOCS, "logo.png"))
    shutil.copy(os.path.join(STATIC, "favicon.png"), os.path.join(DOCS, "favicon.png"))
    print("static assets ✓")


if __name__ == "__main__":
    os.makedirs(DOCS, exist_ok=True)
    build_landing()
    build_ide()
    build_pkg()
    copy_static()
