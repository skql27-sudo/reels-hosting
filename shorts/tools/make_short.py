#!/usr/bin/env python3
"""YouTube Shorts maker — '어르신 좋은글 짤' style. 3 cards, 1080x1920, 25s.

usage: python3 make_short.py spec.json out.mp4
       PREVIEW_ONLY=1 python3 make_short.py spec.json out.mp4  -> out_preview_{1,2,3}.png

spec.json:
{"scenes": [   # exactly 3
  {"theme": "purple|roses|sunset|night|card|gold",
   "heading": "오늘의 좋은 글",          # optional ribbon at top
   "lines": ["[福]", "웃으면 복이 온대요", "", ...],   # [..] = big emphasis, "" = blank line
   "footer": "하하호호 웃어보세요"}      # optional, bottom, slanted
]}
Every picture element (roses, stars, sun, smileys, hearts, music) is drawn here -> no copyright issues.
"""
import json, math, os, random, subprocess, sys, wave, zlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30
SCENE, XFADE = 9.0, 1.0
F_BODY = os.path.join(FD, "Jua-Regular.ttf")
F_EMPH = os.path.join(FD, "BlackHanSans-Regular.ttf")
F_HEAD = os.path.join(FD, "YeonSung-Regular.ttf")
F_FOOT = os.path.join(FD, "EastSeaDokdo-Regular.ttf")
F_HANJA = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"

THEMES = {
    "purple": dict(ink=(255, 255, 255), stroke=(200, 0, 90), emph=(255, 30, 60), emph_stroke=(120, 255, 40),
                   head=(255, 0, 140), foot=(255, 240, 0), foot_stroke=(140, 40, 0)),
    "roses":  dict(ink=(255, 240, 0), stroke=(170, 0, 0), emph=(255, 255, 255), emph_stroke=(220, 0, 60),
                   head=(220, 0, 40), foot=(255, 240, 0), foot_stroke=(150, 0, 0)),
    "sunset": dict(ink=(255, 255, 255), stroke=(150, 20, 90), emph=(255, 235, 0), emph_stroke=(200, 30, 0),
                   head=(240, 60, 120), foot=(255, 255, 255), foot_stroke=(120, 20, 80)),
    "night":  dict(ink=(255, 230, 120), stroke=(20, 20, 90), emph=(255, 120, 200), emph_stroke=(255, 255, 255),
                   head=(60, 60, 200), foot=(255, 240, 160), foot_stroke=(30, 30, 100)),
    "card":   dict(ink=(25, 25, 25), stroke=(255, 255, 255), emph=(220, 0, 30), emph_stroke=(255, 255, 255),
                   head=(200, 30, 30), foot=(255, 255, 255), foot_stroke=(30, 90, 30)),
    "gold":   dict(ink=(60, 30, 10), stroke=(255, 250, 235), emph=(190, 20, 20), emph_stroke=(255, 255, 255),
                   head=(170, 90, 20), foot=(255, 240, 120), foot_stroke=(110, 50, 10)),
}
STAR_COLS = [(255, 255, 255), (80, 220, 255), (255, 80, 220), (255, 240, 80), (120, 255, 120), (255, 150, 60)]


def font(p, s, idx=0):
    return ImageFont.truetype(p, s, index=idx)


def is_hanja(s):
    return any(0x4E00 <= ord(c) <= 0x9FFF for c in s)


def grad(top, bot, power=1.0):
    g = np.linspace(0, 1, H)[:, None, None] ** power
    a = np.array(top, float) * (1 - g) + np.array(bot, float) * g
    return np.repeat(a, W, axis=1)


def to_img(arr):
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")


def radial(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W]
    return np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))


# ---------------------------------------------------------------- drawn elements
def star_sprite(size, color, diag=True):
    s = size * 2
    yy, xx = np.mgrid[0:s, 0:s] - s / 2
    ax, ay = np.abs(xx) / size, np.abs(yy) / size
    ray = np.exp(-(ay * 22) ** 2) * np.clip(1 - ax, 0, 1) ** 1.5 + np.exp(-(ax * 22) ** 2) * np.clip(1 - ay, 0, 1) ** 1.5
    if diag:
        u, v = np.abs(xx + yy) / (size * 1.414), np.abs(xx - yy) / (size * 1.414)
        ray += 0.6 * (np.exp(-(v * 30) ** 2) * np.clip(1 - u * 1.8, 0, 1) + np.exp(-(u * 30) ** 2) * np.clip(1 - v * 1.8, 0, 1))
    rr = np.sqrt(ax ** 2 + ay ** 2)
    core = np.exp(-(rr * 7) ** 2)
    halo = np.exp(-(rr * 3) ** 2) * 0.35
    a = np.clip(ray + core + halo, 0, 1)
    img = np.zeros((s, s, 4), np.uint8)
    col = np.array(color, float)
    img[..., :3] = (col * (1 - core[..., None]) + 255 * core[..., None]).clip(0, 255)
    img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img)


def rose(d, cx, cy, r, base, rng):
    dark = tuple(int(c * 0.45) for c in base)
    mid = tuple(int(c * 0.75) for c in base)
    light = tuple(min(255, int(c * 1.15 + 25)) for c in base)
    rot = rng.uniform(0, 6.28)
    for k in range(6):
        a = rot + k * 1.047
        px, py = cx + math.cos(a) * r * 0.45, cy + math.sin(a) * r * 0.45
        pr = r * 0.55
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=mid, outline=dark, width=max(1, int(r * 0.05)))
    for k in range(5):
        a = rot + 0.5 + k * 1.256
        px, py = cx + math.cos(a) * r * 0.25, cy + math.sin(a) * r * 0.25
        pr = r * 0.42
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=base, outline=dark, width=max(1, int(r * 0.05)))
    cr = r * 0.38
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=light)
    for j in range(4):
        rr = cr * (1 - j * 0.22)
        st = math.degrees(rot) + j * 80
        d.arc([cx - rr, cy - rr * 0.85, cx + rr, cy + rr * 0.85], st, st + 220, fill=dark, width=max(2, int(r * 0.07)))


def leaf(d, cx, cy, ln, ang, color):
    pts = []
    for i in range(21):
        t = i / 20
        pts.append((t * ln, math.sin(t * math.pi) * ln * 0.24))
    pts += [(x, -y) for x, y in reversed(pts)]
    ca, sa = math.cos(ang), math.sin(ang)
    d.polygon([(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts], fill=color + (255,))
    d.line([(cx, cy), (cx + ln * ca, cy + ln * sa)], fill=tuple(min(255, c + 50) for c in color) + (200,), width=3)


def rose_bed(img, y0, y1, rng, cols, density=1.0, rmin=55, rmax=95):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(int(60 * density)):
        x, y = rng.uniform(-50, W + 50), rng.uniform(y0, y1)
        leaf(d, x, y, rng.uniform(80, 150), rng.uniform(0, 6.28), (30 + rng.randint(0, 40), 110 + rng.randint(0, 50), 40))
    n = int((y1 - y0) * W / (rmax * rmax * 1.6) * density)
    pts = sorted([(rng.uniform(-40, W + 40), rng.uniform(y0, y1)) for _ in range(n)], key=lambda p: p[1])
    for x, y in pts:
        r = rng.uniform(rmin, rmax) * (0.75 + 0.35 * (y - y0) / max(1, y1 - y0))
        rose(d, x, y, r, rng.choice(cols), rng)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(1.2)))


def cup_flower(img, cx, cy, r, color, rng):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.line([(cx, cy), (cx - r * 0.3, cy + r * 3.5)], fill=(60, 140, 50, 255), width=int(r * 0.12))
    leaf(d, cx - r * 0.2, cy + r * 2.0, r * 1.6, 3.6, (60, 150, 50))
    leaf(d, cx - r * 0.25, cy + r * 2.6, r * 1.3, 0.3, (50, 130, 45))
    dark = tuple(int(c * 0.7) for c in color)
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * 0.55
        px, py = cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.45
        d.ellipse([px - r * 0.5, py - r * 0.62, px + r * 0.5, py + r * 0.62], fill=color + (255,), outline=dark + (255,), width=4)
    d.ellipse([cx - r * 0.8, cy - r * 0.2, cx + r * 0.8, cy + r * 0.55], fill=color + (255,), outline=dark + (255,), width=4)
    for k in range(18):
        a = rng.uniform(-2.6, -0.5)
        ln = rng.uniform(0.2, 0.45) * r
        x2, y2 = cx + math.cos(a) * ln, cy - r * 0.05 + math.sin(a) * ln
        d.line([(cx, cy), (x2, y2)], fill=(230, 160, 20, 255), width=3)
        d.ellipse([x2 - 6, y2 - 6, x2 + 6, y2 + 6], fill=(255, 240, 120, 255))
    glow = layer.filter(ImageFilter.GaussianBlur(25))
    gl = Image.new("RGBA", img.size, color + (0,)); gl.putalpha(glow.getchannel("A").point(lambda v: v * 0.6))
    img.alpha_composite(gl)
    img.alpha_composite(layer)


def heart_sprite(size, color):
    s = size
    layer = Image.new("RGBA", (s + 20, s + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = []
    for i in range(80):
        t = i / 80 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((10 + s / 2 + x * s / 34, 10 + s / 2 + y * s / 34))
    dark = tuple(int(c * 0.6) for c in color)
    d.polygon(pts, fill=color + (255,), outline=dark + (255,))
    hl = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(hl).ellipse([s * 0.25, s * 0.22, s * 0.48, s * 0.42], fill=(255, 255, 255, 170))
    layer.alpha_composite(hl.filter(ImageFilter.GaussianBlur(s * 0.03)))
    return layer


def smiley_sprite(size, big_mouth=True):
    s = size
    arr = np.zeros((s, s, 4), np.uint8)
    yy, xx = np.mgrid[0:s, 0:s] - s / 2
    rr = np.sqrt(xx ** 2 + yy ** 2) / (s / 2)
    shade = np.clip(1 - np.sqrt(((xx + s * 0.15) / (s * 0.6)) ** 2 + ((yy + s * 0.15) / (s * 0.6)) ** 2), 0, 1)
    arr[..., 0] = 255
    arr[..., 1] = (190 + 60 * shade).clip(0, 255)
    arr[..., 2] = (20 + 120 * shade ** 3).clip(0, 255)
    arr[..., 3] = ((rr < 0.97) * 255).astype(np.uint8)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    d.ellipse([s * 0.05, s * 0.05, s * 0.95, s * 0.95], outline=(200, 120, 0, 255), width=max(2, s // 30))
    for ex in (0.34, 0.66):
        d.ellipse([s * (ex - 0.07), s * 0.27, s * (ex + 0.07), s * 0.45], fill=(40, 20, 0, 255))
    if big_mouth:
        d.chord([s * 0.25, s * 0.38, s * 0.75, s * 0.8], 0, 180, fill=(150, 20, 20, 255))
        d.chord([s * 0.37, s * 0.6, s * 0.63, s * 0.8], 0, 180, fill=(255, 90, 90, 255))
    else:
        d.arc([s * 0.27, s * 0.35, s * 0.73, s * 0.75], 20, 160, fill=(80, 30, 0, 255), width=max(3, s // 18))
    return img


def baby_breath(d, x0, y0, x1, y1, rng, n=180):
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(3, 8)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rng.randint(170, 255)))


# ---------------------------------------------------------------- backgrounds
def bg_purple(rng):
    arr = np.zeros((H, W, 3)) + 5
    arr += np.array([150, 60, 230]) * radial(W / 2, H * 0.47, 620, 760)[..., None] ** 0.9
    arr += np.array([255, 230, 120]) * radial(W / 2, H * 0.72, 260, 300)[..., None] * 0.55
    img = to_img(arr)
    cup_flower(img, W * 0.40, H * 0.73, 150, (255, 220, 0), rng)
    l = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    d.line([(W * 0.76, H * 0.76), (W * 0.55, H * 0.95)], fill=(60, 130, 40, 255), width=14)
    leaf(d, W * 0.68, H * 0.82, 150, 0.4, (60, 150, 50))
    rose(d, W * 0.76, H * 0.75, 110, (250, 110, 160), rng)
    img.alpha_composite(l)
    return img, dict(smileys=3, hearts=0, stars=70)


def bg_roses(rng):
    img = to_img(grad((255, 245, 248), (255, 200, 210), 1.0))
    hs = heart_sprite(820, (255, 120, 160))
    hs.putalpha(hs.getchannel("A").point(lambda v: v * 0.45))
    img.alpha_composite(hs, ((W - hs.size[0]) // 2, 300))
    baby_breath(ImageDraw.Draw(img), W * 0.62, 150, W + 20, 700, rng, 240)
    baby_breath(ImageDraw.Draw(img), -20, 1100, W * 0.35, 1300, rng, 120)
    rose_bed(img, 1280, H + 60, rng, [(215, 0, 20), (190, 0, 15), (235, 20, 40)], 1.15)
    rose_bed(img, -60, 160, rng, [(215, 0, 20), (235, 20, 40)], 0.8, 45, 70)
    return img, dict(smileys=0, hearts=10, stars=45)


def bg_sunset(rng):
    arr = grad((70, 40, 110), (255, 120, 120), 0.8)
    arr += np.array([255, 220, 200]) * radial(W / 2, H * 0.48, 420, 300)[..., None] * 0.6
    sun = radial(W / 2, H * 0.47, 150, 150) ** 0.35
    arr = arr * (1 - sun[..., None]) + 255 * sun[..., None]
    yy = np.arange(H)[:, None]
    streak = np.exp(-((yy - H * 0.53) / 10) ** 2) * np.exp(-((np.arange(W)[None] - W / 2) / 420) ** 2)
    arr += 230 * streak[..., None]
    img = to_img(arr)
    d = ImageDraw.Draw(img)
    for col, base in [((60, 60, 80), 0.58), ((35, 70, 45), 0.66), ((20, 50, 30), 0.74)]:
        pts = [(0, H)]
        ph = rng.uniform(0, 6)
        for x in range(0, W + 20, 20):
            pts.append((x, H * base + 60 * math.sin(x / 170 + ph) + 30 * math.sin(x / 70 + ph * 2)))
        pts.append((W, H))
        d.polygon(pts, fill=col + (255,))
    cup_flower(img, W * 0.55, H * 0.8, 130, (255, 235, 240), rng)
    return img, dict(smileys=0, hearts=0, stars=40)


def bg_night(rng):
    arr = grad((10, 10, 60), (60, 20, 90), 1.0)
    arr += np.array([120, 120, 255]) * radial(W / 2, H * 0.45, 600, 700)[..., None] * 0.35
    img = to_img(arr)
    d = ImageDraw.Draw(img)
    for _ in range(400):
        x, y, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1, 3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, rng.randint(120, 255)))
    moon = Image.new("RGBA", img.size, (0, 0, 0, 0)); md = ImageDraw.Draw(moon)
    md.ellipse([760, 120, 980, 340], fill=(255, 245, 190, 255))
    md.ellipse([700, 90, 920, 310], fill=(0, 0, 0, 0))
    gl = moon.filter(ImageFilter.GaussianBlur(30))
    img.alpha_composite(gl); img.alpha_composite(gl); img.alpha_composite(moon)
    rose_bed(img, 1500, H + 60, rng, [(255, 120, 180), (255, 200, 220), (230, 60, 140)], 0.9, 50, 85)
    return img, dict(smileys=0, hearts=6, stars=80)


def bg_card(rng):
    arr = grad((236, 240, 236), (215, 225, 215), 1.0)
    noise = np.random.default_rng(rng.randint(0, 99999)).normal(0, 4, (H, W, 1))
    img = to_img(arr + noise)
    l = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(l)
    cx, cy = 900, 1180
    for k in range(10):
        a = k * 0.628
        d.line([(cx + math.cos(a) * 130, cy + math.sin(a) * 130), (cx + math.cos(a) * 175, cy + math.sin(a) * 175)],
               fill=(255, 220, 0, 255), width=12)
    pts = []
    for k in range(10):
        a = -math.pi / 2 + k * math.pi / 5
        rr = 115 if k % 2 == 0 else 52
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    d.polygon(pts, fill=(255, 235, 30, 255), outline=(230, 180, 0, 255))
    img.alpha_composite(l)
    rose_bed(img, 1420, H + 60, rng, [(220, 0, 20), (255, 140, 180), (250, 100, 150)], 0.85, 70, 120)
    l2 = Image.new("RGBA", img.size, (0, 0, 0, 0)); d2 = ImageDraw.Draw(l2)
    for (x, y) in [(70, 110), (W - 70, 110)]:
        rose(d2, x, y, 70, (220, 0, 20), rng)
    img.alpha_composite(l2)
    return img, dict(smileys=0, hearts=0, stars=25)


def bg_gold(rng):
    arr = grad((236, 214, 178), (120, 92, 62), 1.2)
    arr += np.array([255, 245, 220]) * radial(W / 2, H * 0.42, 650, 800)[..., None] * 0.45
    img = to_img(arr)
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(far)
    for _ in range(70):
        r = rng.randint(40, 130); x, y = rng.uniform(0, W), rng.uniform(0, H * 0.8)
        d.ellipse([x - r, y - r, x + r, y + r], fill=rng.choice([(255, 236, 190), (255, 220, 150), (255, 250, 230)]) + (110,))
    img.alpha_composite(far.filter(ImageFilter.GaussianBlur(22)))
    rose_bed(img, 1550, H + 60, rng, [(250, 236, 214), (246, 200, 160), (230, 170, 140)], 0.8, 55, 90)
    return img, dict(smileys=0, hearts=0, stars=45)


BACKGROUNDS = dict(purple=bg_purple, roses=bg_roses, sunset=bg_sunset, night=bg_night, card=bg_card, gold=bg_gold)


# ---------------------------------------------------------------- text
def parse_line(s):
    out, cur, emph = [], "", False
    for ch in s:
        if ch == "[" and not emph:
            if cur: out.append((cur, False))
            cur, emph = "", True
        elif ch == "]" and emph:
            if cur: out.append((cur, True))
            cur, emph = "", False
        else:
            cur += ch
    if cur: out.append((cur, emph))
    return out


def seg_font(t, e, bs):
    if is_hanja(t):
        return font(F_HANJA, int(bs * (2.4 if e else 1.0)), 1)
    return font(F_EMPH, int(bs * 1.45)) if e else font(F_BODY, bs)


def styled_text(segs, th, bs, maxw=980):
    while True:
        fonts = [seg_font(t, e, bs) for t, e in segs]
        w = sum(f.getlength(t) for f, (t, e) in zip(fonts, segs))
        if w <= maxw or bs < 40: break
        bs -= 4
    asc = max(f.getmetrics()[0] for f in fonts)
    desc = max(f.getmetrics()[1] for f in fonts)
    pad = 40
    layer = Image.new("RGBA", (int(w) + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    sw = max(6, bs // 9)
    x = pad
    for f, (t, e) in zip(fonts, segs):
        fill, stroke = (th["emph"], th["emph_stroke"]) if e else (th["ink"], th["stroke"])
        d.text((x, pad + asc), t, font=f, fill=fill + (255,), anchor="ls", stroke_width=sw + (4 if e else 0), stroke_fill=stroke + (255,))
        x += f.getlength(t)
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.getchannel("A").filter(ImageFilter.GaussianBlur(6)).point(lambda v: int(v * 0.7)))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (6, 8))
    out.alpha_composite(layer)
    return out


def ribbon(text, th):
    f = font(F_HEAD, 92)
    w = int(f.getlength(text)) + 190
    layer = Image.new("RGBA", (w, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    col = th["head"]
    d.rounded_rectangle([10, 30, w - 10, 155], radius=62, fill=col + (240,), outline=(255, 240, 120, 255), width=7)
    d.text((w / 2, 95), text, font=f, fill=(255, 255, 255, 255), anchor="mm", stroke_width=4,
           stroke_fill=tuple(int(c * 0.5) for c in col) + (255,))
    for sx in (55, w - 55):
        hs = heart_sprite(44, (255, 235, 90))
        layer.alpha_composite(hs, (int(sx - hs.size[0] / 2), 95 - hs.size[1] // 2))
    return layer


def footer_sprite(text, th):
    f = font(F_FOOT, 120)
    w = int(f.getlength(text)) + 80
    layer = Image.new("RGBA", (w, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text((40, 150), text, font=f, fill=th["foot"] + (255,), anchor="ls", stroke_width=9, stroke_fill=th["foot_stroke"] + (255,))
    if w > 1040:
        layer = layer.resize((1040, int(200 * 1040 / w)), Image.LANCZOS)
    return layer.rotate(4, resample=Image.BICUBIC, expand=True)


# ---------------------------------------------------------------- scene
class Scene:
    def __init__(self, sc, seed):
        theme = sc.get("theme", "purple")
        self.th = th = THEMES[theme]
        rng = random.Random(seed)
        self.base, opts = BACKGROUNDS[theme](rng)
        self.stars = []
        for _ in range(opts["stars"]):
            sz = rng.randint(22, 75)
            col = rng.choice(STAR_COLS) if theme in ("purple", "night", "sunset") else rng.choice([(255, 255, 255), (255, 240, 160)])
            self.stars.append(dict(sp=star_sprite(sz, col), sz=sz, x=rng.uniform(20, W - 20), y=rng.uniform(30, H - 40),
                                   ph=rng.uniform(0, 6.28), f=rng.uniform(0.7, 1.8)))
        self.glit = [dict(x=rng.uniform(0, W), y=rng.uniform(-H, H), v=rng.uniform(60, 170), s=rng.uniform(2, 5),
                          ph=rng.uniform(0, 6.28), c=rng.choice([(255, 250, 200), (255, 200, 240), (200, 240, 255)])) for _ in range(120)]
        self.hearts = []
        for _ in range(opts["hearts"]):
            sz = rng.randint(50, 110)
            self.hearts.append(dict(sp=heart_sprite(sz, rng.choice([(240, 20, 60), (255, 80, 150), (255, 40, 100)])),
                                    x=rng.uniform(40, W - 120), y=rng.uniform(0, H), v=rng.uniform(50, 110), ph=rng.uniform(0, 6.28)))
        self.smileys = []
        spots = [(130, 1330), (950, 1180), (920, 230), (150, 230), (960, 1500)]
        rng.shuffle(spots)
        for i in range(opts["smileys"]):
            sz = rng.randint(110, 160)
            self.smileys.append(dict(sp=smiley_sprite(sz, i % 2 == 0), x=spots[i][0], y=spots[i][1], ph=rng.uniform(0, 6.28)))
        self.head = ribbon(sc["heading"], th) if sc.get("heading") else None
        n = len([l for l in sc["lines"] if l.strip()])
        bs = 96 if n <= 4 else 88 if n <= 5 else 76 if n <= 7 else 64
        self.lines = [styled_text(parse_line(l), th, bs) if l.strip() else None for l in sc["lines"]]
        self.footer = footer_sprite(sc["footer"], th) if sc.get("footer") else None
        gap = int(bs * 1.0)
        heights = [(s.size[1] - 45 if s else gap) for s in self.lines]
        area_top, area_h = 330, (1150 if self.footer else 1300)
        top = area_top + max(0, (area_h - sum(heights)) // 2)
        self.ypos, y = [], top
        for hgt in heights:
            self.ypos.append(y); y += hgt

    @staticmethod
    def _fade(sp, a):
        if a >= 1: return sp
        s2 = sp.copy(); s2.putalpha(sp.getchannel("A").point(lambda v: int(v * a))); return s2

    def frame(self, t):
        z = 1.0 + 0.05 * (t / SCENE)
        bw, bh = int(W * z), int(H * z)
        img = self.base.resize((bw, bh), Image.BILINEAR).crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))
        for h in self.hearts:
            y = (h["y"] - h["v"] * t) % (H + 200) - 100
            x = h["x"] + 25 * math.sin(t * 1.3 + h["ph"])
            img.alpha_composite(h["sp"], (int(x), int(y)))
        for s in self.smileys:
            dy = 18 * math.sin(t * 2.2 + s["ph"])
            sp = s["sp"].rotate(8 * math.sin(t * 1.7 + s["ph"]), resample=Image.BICUBIC)
            img.alpha_composite(sp, (int(s["x"] - sp.size[0] / 2), int(s["y"] - sp.size[1] / 2 + dy)))
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(gl)
        for g in self.glit:
            y = (g["y"] + g["v"] * t) % (H + 40) - 20
            x = g["x"] + 18 * math.sin(t * 1.5 + g["ph"])
            a = int(255 * (0.4 + 0.6 * abs(math.sin(t * 4 + g["ph"]))))
            r = g["s"]
            d.ellipse([x - r, y - r, x + r, y + r], fill=g["c"] + (a,))
        img.alpha_composite(gl)
        if self.head:
            a = min(1, max(0, (t - 0.2) / 0.5))
            if a > 0:
                hs = self._fade(self.head, a)
                img.alpha_composite(hs, ((W - hs.size[0]) // 2, 140 - int((1 - a) * 40)))
        k = 0
        for sp, y in zip(self.lines, self.ypos):
            if sp is None: continue
            st = 0.6 + k * 0.45; k += 1
            a = min(1, max(0, (t - st) / 0.45))
            if a <= 0: continue
            sc = 1.0 + 0.25 * (1 - a) ** 2
            s2 = self._fade(sp, a)
            if sc > 1.001:
                s2 = s2.resize((int(sp.size[0] * sc), int(sp.size[1] * sc)), Image.BILINEAR)
            img.alpha_composite(s2, ((W - s2.size[0]) // 2, int(y - 35 - (s2.size[1] - sp.size[1]) / 2)))
        if self.footer:
            a = min(1, max(0, (t - (0.8 + k * 0.45)) / 0.5))
            if a > 0:
                fs = self._fade(self.footer, a)
                img.alpha_composite(fs, ((W - fs.size[0]) // 2, 1500 + int(8 * math.sin(t * 2.5))))
        for s in self.stars:
            v = math.sin(s["ph"] + t * s["f"] * 2.2)
            if v <= 0.1: continue
            size = max(4, int(s["sz"] * 2 * (0.35 + 0.65 * (v - 0.1) / 0.9)))
            sp = s["sp"].resize((size, size), Image.BILINEAR)
            img.alpha_composite(sp, (int(s["x"] - size / 2), int(s["y"] - size / 2)))
        return img


def flash(img, amt):
    if amt <= 0: return img
    img.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 235, int(255 * amt))))
    return img


# ---------------------------------------------------------------- music
def synth_music(path, dur):
    """Original gentle music-box waltz + warm pad (generated, royalty-free)."""
    sr = 44100
    n = int(sr * dur)
    out = np.zeros(n)
    beat = 60 / 96
    prog = [[60, 64, 67], [57, 60, 64], [65, 69, 72], [67, 71, 74]]
    mel = [76, 79, 84, 79, 76, 72, 74, 76, 72, 69, 72, 76, 77, 76, 74, 72, 74, 79, 83, 79]
    i = 0
    while i * beat < dur:
        f = 440 * 2 ** ((mel[i % len(mel)] - 69) / 12)
        s0 = int(i * beat * sr); ln = min(int(2.0 * sr), n - s0)
        if ln <= 0: break
        tt = np.arange(ln) / sr
        out[s0:s0 + ln] += 0.20 * (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(2 * np.pi * 3.01 * f * tt)) * np.exp(-tt * 3.2)
        i += 1
    bar = beat * 3
    for k in range(int(dur / bar) + 1):
        s0 = int(k * bar * sr); ln = min(int(bar * 1.3 * sr), n - s0)
        if ln <= 0: break
        tt = np.arange(ln) / sr
        env = np.minimum(1, tt * 2.5) * np.exp(-tt * 0.5)
        for nt in prog[k % 4]:
            f = 440 * 2 ** ((nt - 12 - 69) / 12)
            out[s0:s0 + ln] += 0.06 * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * env
    for tc in [SCENE - XFADE, 2 * SCENE - 2 * XFADE]:
        for j, nt in enumerate([96, 100, 103, 108]):
            s0 = int((tc + j * 0.06) * sr); ln = min(int(1.5 * sr), n - s0)
            tt = np.arange(ln) / sr
            out[s0:s0 + ln] += 0.05 * np.sin(2 * np.pi * 440 * 2 ** ((nt - 69) / 12) * tt) * np.exp(-tt * 3)
    fade = int(sr * 1.2)
    out[:int(sr * 0.3)] *= np.linspace(0, 1, int(sr * 0.3))
    out[-fade:] *= np.linspace(1, 0, fade)
    out = out / max(1e-6, np.abs(out).max()) * 0.55
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- main
def main():
    spec = json.load(open(sys.argv[1]))
    out = os.path.abspath(sys.argv[2])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    scs = spec["scenes"]
    assert len(scs) == 3, "scenes must be 3"
    scenes = [Scene(s, 1000 + i * 77 + zlib.crc32(json.dumps(s, ensure_ascii=False).encode()) % 997) for i, s in enumerate(scs)]
    total = 3 * SCENE - 2 * XFADE
    if os.environ.get("PREVIEW_ONLY"):
        for i, s in enumerate(scenes):
            s.frame(SCENE - 1.6).convert("RGB").save(os.path.splitext(out)[0] + f"_preview_{i + 1}.png")
        return
    silent = out + ".v.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                          "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    for fi in range(int(total * FPS)):
        t = fi / FPS
        idx = min(2, int(t // (SCENE - XFADE)))
        lt = t - idx * (SCENE - XFADE)
        img = scenes[idx].frame(lt)
        if idx > 0 and lt < XFADE:
            a = lt / XFADE
            img = Image.blend(scenes[idx - 1].frame(lt + SCENE - XFADE), img, a)
            img = flash(img, 0.4 * math.sin(a * math.pi))
        if t < 0.4:
            img = flash(img, 1 - t / 0.4)
        p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    wav = out + ".wav"
    synth_music(wav, total)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out], check=True)
    os.remove(silent); os.remove(wav)
    print(out, round(total, 1), "s")


if __name__ == "__main__":
    main()
