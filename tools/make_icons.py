# -*- coding: utf-8 -*-
"""ساخت آیکون‌های WebP گویا — جایگزین ایموجی تا تو همه سیستم‌ها یکسان دیده بشن

اجرا:  python tools/make_icons.py
خروجی: goya/ide_static/icons/  +  docs/icons/  +  assets/icons/
"""

import os
from PIL import Image, ImageDraw, ImageFont

S = 96
HERE = os.path.dirname(os.path.abspath(__file__))
OUTS = [
    os.path.join(HERE, "..", "goya", "ide_static", "icons"),
    os.path.join(HERE, "..", "docs", "icons"),
    os.path.join(HERE, "..", "assets", "icons"),
]

VIOLET = (112, 72, 232, 255)
PURPLE2 = (151, 117, 250, 255)
CORAL = (229, 72, 77, 255)
TEAL = (12, 166, 120, 255)
BLUE = (59, 130, 246, 255)
YELLOW = (255, 212, 59, 255)
ORANGE = (247, 103, 7, 255)
NAVY = (30, 42, 74, 255)
MINT = (56, 217, 169, 255)
GREEN = (47, 158, 68, 255)
RED = (224, 49, 49, 255)
WHITE = (255, 255, 255, 255)
GOLD = (255, 200, 40, 255)


def font(size, bold=True):
    name = "tahomabd.ttf" if bold else "tahoma.ttf"
    return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", name), size)


def badge(fill):
    """بج گرد رنگی به‌عنوان زمینه"""
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([3, 3, S - 3, S - 3], radius=24, fill=fill)
    return img, d


def save(img, name):
    for out in OUTS:
        os.makedirs(out, exist_ok=True)
        img.save(os.path.join(out, name + ".webp"), "WEBP", quality=92)


def text_center(d, xy_c, txt, f, fill):
    l, t, r, b = d.textbbox((0, 0), txt, font=f)
    w, h = r - l, b - t
    d.text((xy_c[0] - w / 2 - l, xy_c[1] - h / 2 - t), txt, font=f, fill=fill)


# ─── آیکون‌های بج‌دار ───

def i_flag():  # پرچم ایران
    img, d = badge(WHITE)
    d.rounded_rectangle([3, 3, S - 3, 34], radius=24, fill=GREEN)
    d.rectangle([3, 20, S - 3, 34], fill=GREEN)
    d.rectangle([3, 34, S - 3, 62], fill=WHITE)
    d.rounded_rectangle([3, 62, S - 3, S - 3], radius=24, fill=RED)
    d.rectangle([3, 62, S - 3, 76], fill=RED)
    return img


def i_numbers():
    img, d = badge(VIOLET)
    text_center(d, (S / 2, S / 2 - 2), "۱۲۳", font(30), WHITE)
    return img


def i_chat():
    img, d = badge(CORAL)
    d.rounded_rectangle([16, 22, 80, 64], radius=14, fill=WHITE)
    d.polygon([(34, 62), (50, 62), (34, 80)], fill=WHITE)
    for i, cx in enumerate((36, 48, 60)):
        d.ellipse([cx - 4, 39 - 4, cx + 4, 39 + 4], fill=CORAL)
    return img


def i_calendar():
    img, d = badge(TEAL)
    d.rounded_rectangle([18, 22, 78, 78], radius=12, fill=WHITE)
    d.rounded_rectangle([18, 22, 78, 40], radius=12, fill=NAVY)
    d.rectangle([18, 34, 78, 40], fill=NAVY)
    for r in range(3):
        for c in range(4):
            cx, cy = 30 + c * 14, 50 + r * 11
            d.ellipse([cx - 3.4, cy - 3.4, cx + 3.4, cy + 3.4], fill=TEAL)
    return img


def i_keyboard():
    img, d = badge(NAVY)
    d.rounded_rectangle([12, 28, 84, 70], radius=10, fill=WHITE)
    for r in range(2):
        for c in range(6):
            cx, cy = 21 + c * 11, 38 + r * 11
            d.rounded_rectangle([cx - 3.5, cy - 3.5, cx + 3.5, cy + 3.5], radius=2, fill=NAVY)
    d.rounded_rectangle([30, 58, 66, 65], radius=3, fill=CORAL)
    return img


def i_py():
    img, d = badge(BLUE)
    text_center(d, (S / 2, S / 2 - 2), "Py", font(34), WHITE)
    return img


def i_rocket():
    img, d = badge(VIOLET)
    d.ellipse([34, 14, 62, 66], fill=WHITE)                    # بدنه
    d.polygon([(36, 58), (24, 76), (40, 70)], fill=GOLD)       # باله چپ
    d.polygon([(60, 58), (72, 76), (56, 70)], fill=GOLD)       # باله راست
    d.ellipse([43, 28, 53, 38], fill=VIOLET)                   # پنجره
    d.polygon([(44, 68), (52, 68), (48, 84)], fill=ORANGE)     # شعله
    return img


def i_sparkle():
    img, d = badge(YELLOW)
    cx, cy = S / 2, S / 2
    pts = []
    import math
    for k in range(8):
        r = 30 if k % 2 == 0 else 11
        a = math.pi / 4 * k - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=WHITE)
    return img


def i_search():
    img, d = badge(TEAL)
    d.ellipse([24, 22, 60, 58], outline=WHITE, width=8)
    d.line([(58, 56), (76, 74)], fill=WHITE, width=9)
    return img


def i_book():
    img, d = badge(CORAL)
    d.rounded_rectangle([16, 24, 44, 74], radius=6, fill=WHITE)
    d.rounded_rectangle([52, 24, 80, 74], radius=6, fill=WHITE)
    d.rectangle([44, 22, 52, 78], fill=CORAL)
    d.rectangle([24, 34, 38, 38], fill=(245, 180, 180, 255))
    d.rectangle([24, 44, 38, 48], fill=(245, 180, 180, 255))
    d.rectangle([58, 34, 72, 38], fill=(245, 180, 180, 255))
    d.rectangle([58, 44, 72, 48], fill=(245, 180, 180, 255))
    return img


def i_download():
    img, d = badge(VIOLET)
    d.rectangle([42, 20, 54, 50], fill=WHITE)
    d.polygon([(32, 46), (64, 46), (48, 66)], fill=WHITE)
    d.rounded_rectangle([28, 70, 68, 78], radius=4, fill=WHITE)
    return img


def i_map():
    img, d = badge(TEAL)
    d.polygon([(18, 28), (38, 22), (38, 74), (18, 80)], fill=WHITE)
    d.polygon([(38, 22), (58, 28), (58, 80), (38, 74)], fill=(232, 246, 255, 255))
    d.polygon([(58, 28), (78, 22), (78, 74), (58, 80)], fill=WHITE)
    return img


def i_pin():
    img, d = badge(CORAL)
    d.ellipse([30, 18, 66, 54], fill=WHITE)
    d.ellipse([41, 29, 55, 43], fill=CORAL)
    d.polygon([(36, 48), (60, 48), (48, 80)], fill=WHITE)
    return img


def i_monitor():
    img, d = badge(VIOLET)
    d.rounded_rectangle([16, 24, 80, 62], radius=8, fill=WHITE)
    d.rectangle([24, 32, 72, 54], fill=PURPLE2)
    d.rectangle([42, 62, 54, 72], fill=WHITE)
    d.rounded_rectangle([30, 70, 66, 78], radius=4, fill=WHITE)
    return img


def i_palette():
    img, d = badge(MINT)
    d.ellipse([18, 20, 78, 80], fill=WHITE)
    d.ellipse([52, 52, 70, 70], fill=MINT)
    for (cx, cy), c in [((36, 38), CORAL), ((56, 34), BLUE), ((34, 56), YELLOW)]:
        d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=c)
    return img


def i_bulb():
    img, d = badge(YELLOW)
    d.ellipse([30, 16, 66, 52], fill=WHITE)
    d.rounded_rectangle([40, 52, 56, 66], radius=4, fill=WHITE)
    d.rectangle([42, 68, 54, 74], fill=WHITE)
    return img


def i_file():
    img, d = badge(BLUE)
    d.polygon([(28, 18), (58, 18), (70, 32), (70, 78), (28, 78)], fill=WHITE)
    d.polygon([(58, 18), (58, 32), (70, 32)], fill=(190, 216, 250, 255))
    for y in (44, 54, 64):
        d.rounded_rectangle([36, y, 62, y + 5], radius=2.5, fill=BLUE)
    return img


# ─── آیکون‌های شفاف (بدون بج — برای داخل دکمه‌ها) ───

def _transparent():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def i_play():
    img, d = _transparent()
    d.polygon([(30, 18), (78, 48), (30, 78)], fill=WHITE)
    return img


def i_star():
    img, d = _transparent()
    import math
    cx, cy = S / 2, S / 2 + 3
    pts = []
    for k in range(10):
        r = 38 if k % 2 == 0 else 16
        a = math.pi / 5 * k - math.pi / 2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=GOLD)
    return img


def i_heart():
    img, d = _transparent()
    d.ellipse([12, 22, 50, 60], fill=CORAL)
    d.ellipse([46, 22, 84, 60], fill=CORAL)
    d.polygon([(14, 48), (82, 48), (48, 82)], fill=CORAL)
    return img


def i_moon():
    img, d = _transparent()
    d.ellipse([18, 12, 82, 76], fill=GOLD)
    d.ellipse([34, 4, 94, 64], fill=(0, 0, 0, 0))
    # هلال: دایره‌ی طلایی منهای دایره‌ی بالا-راست (با ماسک)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([18, 12, 82, 76], fill=255)
    md.ellipse([36, 2, 96, 62], fill=0)
    solid = Image.new("RGBA", (S, S), GOLD)
    img.paste(solid, (0, 0), mask)
    return img


def i_sun():
    img, d = _transparent()
    d.ellipse([26, 26, 70, 70], fill=GOLD)
    import math
    for k in range(8):
        a = math.pi / 4 * k
        x1, y1 = 48 + 34 * math.cos(a), 48 + 34 * math.sin(a)
        x2, y2 = 48 + 44 * math.cos(a), 48 + 44 * math.sin(a)
        d.line([(x1, y1), (x2, y2)], fill=GOLD, width=8)
    return img


def i_clock():
    img, d = _transparent()
    d.ellipse([14, 14, 82, 82], outline=NAVY, width=8)
    d.line([(48, 30), (48, 50)], fill=NAVY, width=7)
    d.line([(48, 50), (62, 58)], fill=NAVY, width=7)
    return img


def i_github():
    img, d = _transparent()
    d.ellipse([12, 12, 84, 84], fill=NAVY)
    text_center(d, (48, 48), "G", font(44), WHITE)
    return img


if __name__ == "__main__":
    import inspect
    made = []
    for name, fn in sorted(globals().items()):
        if name.startswith("i_") and callable(fn):
            save(fn(), name[2:])
            made.append(name[2:])
    print("built", len(made), "icons:", ", ".join(made))
