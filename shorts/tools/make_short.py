#!/usr/bin/env python3
"""YouTube Shorts maker: 3 sparkly quote cards (어르신 좋은글귀), 1080x1920, ~25s.

usage: python3 make_short.py spec.json out.mp4
       PREVIEW_ONLY=1 python3 make_short.py spec.json out.mp4   -> out_preview_*.png only

spec.json:
{
  "scenes": [
    {"theme": "gold|rose|sky|green|lavender|red",
     "heading": "오늘의 좋은 글",
     "lines": ["성공의 비밀은", "[자신감]이며", "", "자신감의 비밀은", "[엄청난 준비]이다"],
     "footer": "행복한 하루 되세요"}
  ]   # exactly 3 scenes;  [단어] = 크게 강조, "" = 빈 줄
}
All art (backgrounds, bokeh, flowers, sparkles, music) is generated here -> no copyright issues.
"""
import zlib, json, math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
W, H, FPS = 1080, 1920, 30
SCENE, XFADE = 9.0, 1.0
F_BODY = os.path.join(FD, "GowunBatang-Bold.ttf")
F_EMPH = os.path.join(FD, "BlackHanSans-Regular.ttf")
F_HEAD = os.path.join(FD, "NanumPenScript-Regular.ttf")

THEMES = {
    #        bg top, bg bottom, bokeh colors, ink, emphasis, flower colors, glow
    "gold":     dict(top=(236, 214, 178), bot=(120, 92, 62), bokeh=[(255, 236, 190), (255, 220, 150), (255, 250, 230)],
                     ink=(52, 34, 20), emph=(150, 40, 20), flowers=[(250, 236, 214), (246, 200, 160)], glow=(255, 248, 230)),
    "rose":     dict(top=(255, 222, 230), bot=(214, 120, 150), bokeh=[(255, 240, 245), (255, 190, 210), (255, 255, 240)],
                     ink=(90, 20, 50), emph=(200, 20, 80), flowers=[(255, 120, 160), (255, 180, 200), (255, 240, 245)], glow=(255, 250, 252)),
    "sky":      dict(top=(150, 200, 245), bot=(255, 214, 170), bokeh=[(255, 255, 255), (255, 240, 200), (210, 235, 255)],
                     ink=(20, 40, 90), emph=(220, 70, 30), flowers=[(255, 214, 90), (255, 255, 255), (255, 170, 120)], glow=(255, 255, 255)),
    "green":    dict(top=(222, 245, 214), bot=(90, 160, 110), bokeh=[(255, 255, 230), (220, 255, 200), (255, 255, 255)],
                     ink=(20, 60, 30), emph=(200, 60, 20), flowers=[(255, 255, 255), (255, 220, 80), (255, 190, 200)], glow=(250, 255, 245)),
    "lavender": dict(top=(236, 226, 255), bot=(130, 100, 190), bokeh=[(255, 255, 255), (220, 200, 255), (255, 230, 250)],
                     ink=(50, 20, 90), emph=(190, 30, 110), flowers=[(190, 150, 255), (255, 255, 255), (255, 200, 230)], glow=(252, 248, 255)),
    "red":      dict(top=(250, 238, 220), bot=(200, 60, 60), bokeh=[(255, 240, 200), (255, 200, 180), (255, 255, 255)],
                     ink=(80, 10, 10), emph=(200, 20, 20), flowers=[(230, 30, 50), (255, 255, 255), (255, 200, 60)], glow=(255, 250, 240)),
}


def font(p, s):
    return ImageFont.truetype(p, s)


# ---------------------------------------------------------------- sprites
def bokeh_sprite(r, color, hard=0.75):
    s = r * 2 + 8
    yy, xx = np.mgrid[0:s, 0:s] - s / 2
    d = np.sqrt(xx ** 2 + yy ** 2) / r
    a = np.clip((1 - d) / (1 - hard), 0, 1) * 0.55 + np.clip(1 - np.abs(d - 0.93) * 10, 0, 1) * 0.35
    a = np.clip(a, 0, 1) * (d < 1.02)
    img = np.zeros((s, s, 4), np.uint8)
    img[..., :3] = color
    img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img).filter(ImageFilter.GaussianBlur(1.5))


def star_sprite(size, color=(255, 255, 255)):
    s = size * 2
    yy, xx = np.mgrid[0:s, 0:s] - s / 2
    ax, ay = np.abs(xx) / size, np.abs(yy) / size
    ray = np.exp(-(ay * 18) ** 2) * np.clip(1 - ax, 0, 1) + np.exp(-(ax * 18) ** 2) * np.clip(1 - ay, 0, 1)
    rr = np.sqrt(ax ** 2 + ay ** 2)
    core = np.exp(-(rr * 6) ** 2)
    a = np.clip(ray * 0.9 + core, 0, 1)
    img = np.zeros((s, s, 4), np.uint8)
    img[..., :3] = color
    img[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(img)


def flower(d, cx, cy, r, color, petals, rot):
    for k in range(petals):
        ang = rot + k * 2 * math.pi / petals
        px, py = cx + math.cos(ang) * r * 0.62, cy + math.sin(ang) * r * 0.62
        pr = r * 0.48
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=color + (235,))
    dark = tuple(max(0, c - 40) for c in color)
    for k in range(petals):
        ang = rot + k * 2 * math.pi / petals
        px, py = cx + math.cos(ang) * r * 0.45, cy + math.sin(ang) * r * 0.45
        pr = r * 0.22
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=dark + (90,))
    cr = r * 0.26
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 200, 60, 255))
    for k in range(7):
        a2 = k * 2 * math.pi / 7
        x, y = cx + math.cos(a2) * cr * 0.55, cy + math.sin(a2) * cr * 0.55
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(200, 120, 20, 255))


def leaf(d, cx, cy, ln, ang, color=(90, 160, 80)):
    pts = []
    for i in range(21):
        t = i / 20
        w = math.sin(t * math.pi) * ln * 0.22
        pts.append((t * ln, w))
    pts += [(x, -y) for x, y in reversed(pts)]
    ca, sa = math.cos(ang), math.sin(ang)
    d.polygon([(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts], fill=color + (230,))


def bouquet(img, cx, cy, th, rng, scale=1.0):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(9):
        leaf(d, cx + rng.uniform(-150, 150) * scale, cy + rng.uniform(-60, 80) * scale,
             rng.uniform(110, 190) * scale, rng.uniform(0, 2 * math.pi),
             (int(70 + rng.uniform(0, 40)), int(140 + rng.uniform(0, 40)), int(70 + rng.uniform(0, 30))))
    for _ in range(7):
        flower(d, cx + rng.uniform(-170, 170) * scale, cy + rng.uniform(-90, 70) * scale,
               rng.uniform(55, 95) * scale, rng.choice(th["flowers"]), rng.choice([5, 6, 8]), rng.uniform(0, 6.28))
    sh = layer.filter(ImageFilter.GaussianBlur(10))
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    shadow.putalpha(sh.getchannel("A").point(lambda v: v * 0.35))
    img.alpha_composite(shadow, (0, 8))
    img.alpha_composite(layer)


# ---------------------------------------------------------------- scene assets
def base_image(th, seed):
    rng = random.Random(seed)
    g = np.linspace(0, 1, H)[:, None, None] ** 1.2
    top, bot = np.array(th["top"], float), np.array(th["bot"], float)
    arr = top * (1 - g) + bot * g
    arr = np.repeat(arr, W, axis=1)
    # soft central light
    yy, xx = np.mgrid[0:H, 0:W]
    glow = np.exp(-(((xx - W / 2) / 650) ** 2 + ((yy - H * 0.42) / 800) ** 2))
    arr = arr * (1 - glow[..., None] * 0.55) + np.array(th["glow"], float) * glow[..., None] * 0.55
    img = Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")
    # static blurred far bokeh
    far = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _ in range(60):
        r = rng.randint(40, 130)
        sp = bokeh_sprite(r, rng.choice(th["bokeh"]))
        far.alpha_composite(sp, (rng.randint(-r, W - r), rng.randint(-r, int(H * 0.75))))
    img.alpha_composite(far.filter(ImageFilter.GaussianBlur(14)))
    # flowers bottom + top corner
    bouquet(img, rng.choice([180, 250]), H - 150, th, rng, 1.1)
    bouquet(img, W - rng.choice([180, 250]), H - 110, th, rng, 1.0)
    bouquet(img, W - 120, 140, th, rng, 0.7)
    return img


def parse_line(s):
    """'abc [def] ghi' -> [(text, emph)]"""
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


def text_sprite(segs, th, body_size, emph_size, maxw=960):
    def fits(bs, es):
        fb, fe = font(F_BODY, bs), font(F_EMPH, es)
        w = sum((fe if e else fb).getlength(t) for t, e in segs)
        return w, fb, fe
    w, fb, fe = fits(body_size, emph_size)
    while w > maxw and body_size > 40:
        body_size -= 4; emph_size -= 5
        w, fb, fe = fits(body_size, emph_size)
    hgt = int(max(emph_size if any(e for _, e in segs) else 0, body_size) * 1.45)
    pad = 30
    layer = Image.new("RGBA", (int(w) + pad * 2, hgt + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = pad
    base_y = pad + hgt * 0.78
    for t, e in segs:
        f = fe if e else fb
        col = th["emph"] if e else th["ink"]
        d.text((x, base_y), t, font=f, fill=col + (255,), anchor="ls",
               stroke_width=6 if e else 5, stroke_fill=(255, 255, 255, 255))
        x += f.getlength(t)
    halo = layer.getchannel("A").filter(ImageFilter.GaussianBlur(12)).point(lambda v: min(255, v * 1.6))
    out = Image.new("RGBA", layer.size, th["glow"] + (0,))
    out.putalpha(halo)
    out.alpha_composite(layer)
    return out


def heading_sprite(text, th):
    f = font(F_HEAD, 104)
    w = int(f.getlength(text)) + 160
    layer = Image.new("RGBA", (w, 170), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([10, 25, w - 10, 150], radius=62, fill=th["emph"] + (225,), outline=(255, 255, 255, 255), width=5)
    d.text((w / 2, 92), text, font=f, fill=(255, 255, 255, 255), anchor="mm")
    return layer


class Scene:
    def __init__(self, sc, seed):
        self.th = th = THEMES[sc.get("theme", "gold")]
        rng = random.Random(seed)
        self.base = base_image(th, seed)
        self.rng = rng
        # animated bokeh
        self.bokeh = []
        for _ in range(26):
            r = rng.randint(18, 70)
            self.bokeh.append(dict(sp=bokeh_sprite(r, rng.choice(th["bokeh"])), r=r,
                                   x=rng.uniform(0, W), y=rng.uniform(0, H), vx=rng.uniform(-12, 12),
                                   vy=rng.uniform(-40, -10), ph=rng.uniform(0, 6.28), sp_f=rng.uniform(0.6, 1.6)))
        # twinkle stars
        self.stars = []
        for _ in range(34):
            sz = rng.randint(26, 78)
            col = rng.choice([(255, 255, 255), (255, 244, 200), (255, 230, 160)])
            self.stars.append(dict(sp=star_sprite(sz, col), sz=sz, x=rng.uniform(30, W - 30), y=rng.uniform(40, H - 60),
                                   ph=rng.uniform(0, 6.28), f=rng.uniform(0.8, 2.0)))
        # glitter rain
        self.glit = [dict(x=rng.uniform(0, W), y=rng.uniform(-H, H), v=rng.uniform(60, 180), s=rng.uniform(2, 5),
                          ph=rng.uniform(0, 6.28)) for _ in range(140)]
        # text
        self.head = heading_sprite(sc["heading"], th) if sc.get("heading") else None
        lines = sc["lines"]
        n = len([l for l in lines if l.strip()])
        bs = 92 if n <= 5 else 82 if n <= 7 else 70
        self.lines = []
        for l in lines:
            if not l.strip():
                self.lines.append(None)
            else:
                self.lines.append(text_sprite(parse_line(l), th, bs, int(bs * 1.42)))
        self.footer = text_sprite([(sc["footer"], False)], th, 62, 62) if sc.get("footer") else None
        # layout
        gap = int(bs * 1.0)
        heights = [(s.size[1] - 60 if s else gap) for s in self.lines]
        total = sum(heights)
        top = 330 + max(0, (1180 - total) // 2)
        self.ypos = []
        y = top
        for hgt in heights:
            self.ypos.append(y); y += hgt

    def frame(self, t):
        # slow zoom on background
        z = 1.0 + 0.05 * (t / SCENE)
        bw, bh = int(W * z), int(H * z)
        img = self.base.resize((bw, bh), Image.BILINEAR).crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))
        for b in self.bokeh:
            x = (b["x"] + b["vx"] * t) % (W + 200) - 100
            y = (b["y"] + b["vy"] * t) % (H + 200) - 100
            a = 0.45 + 0.55 * (0.5 + 0.5 * math.sin(b["ph"] + t * b["sp_f"]))
            sp = b["sp"]
            if a < 0.98:
                sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v, a=a: int(v * a)))
            img.alpha_composite(sp, (int(x - b["r"]), int(y - b["r"])))
        # glitter
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(gl)
        for g in self.glit:
            y = (g["y"] + g["v"] * t) % (H + 40) - 20
            x = g["x"] + 18 * math.sin(t * 1.5 + g["ph"])
            a = int(255 * (0.4 + 0.6 * abs(math.sin(t * 4 + g["ph"]))))
            s = g["s"]
            d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 245, 200, a))
        img.alpha_composite(gl)
        # text reveal
        if self.head:
            a = min(1, max(0, (t - 0.2) / 0.6))
            if a > 0:
                hs = self.head
                if a < 1:
                    hs = hs.copy(); hs.putalpha(hs.getchannel("A").point(lambda v: int(v * a)))
                img.alpha_composite(hs, ((W - hs.size[0]) // 2, 150 + int((1 - a) * -30)))
        k = 0
        for sp, y in zip(self.lines, self.ypos):
            if sp is None:
                continue
            st = 0.7 + k * 0.45
            k += 1
            a = min(1, max(0, (t - st) / 0.5))
            if a <= 0:
                continue
            s2 = sp
            if a < 1:
                s2 = sp.copy(); s2.putalpha(sp.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(s2, ((W - sp.size[0]) // 2, int(y - 30 + (1 - a) * 40)))
        if self.footer:
            a = min(1, max(0, (t - (0.9 + k * 0.45)) / 0.6))
            if a > 0:
                fs = self.footer
                if a < 1:
                    fs = fs.copy(); fs.putalpha(fs.getchannel("A").point(lambda v: int(v * a)))
                img.alpha_composite(fs, ((W - fs.size[0]) // 2, 1560))
        # twinkle stars on top
        for s in self.stars:
            v = math.sin(s["ph"] + t * s["f"] * 2.2)
            if v <= 0.15:
                continue
            sc = (v - 0.15) / 0.85
            size = max(4, int(s["sz"] * 2 * (0.4 + 0.6 * sc)))
            sp = s["sp"].resize((size, size), Image.BILINEAR)
            img.alpha_composite(sp, (int(s["x"] - size / 2), int(s["y"] - size / 2)))
        return img


def flash(img, amt):
    if amt <= 0:
        return img
    w = Image.new("RGBA", (W, H), (255, 250, 235, int(255 * amt)))
    img.alpha_composite(w)
    return img


# ---------------------------------------------------------------- music
def synth_music(path, dur):
    """Original gentle music-box waltz + warm pad (generated, royalty-free)."""
    sr = 44100
    n = int(sr * dur)
    out = np.zeros(n)
    bpm = 96
    beat = 60 / bpm
    prog = [[60, 64, 67], [57, 60, 64], [65, 69, 72], [67, 71, 74]]  # C Am F G
    mel = [76, 79, 84, 79, 76, 72, 74, 76, 72, 69, 72, 76, 77, 76, 74, 72, 74, 79, 83, 79]
    i = 0
    while i * beat < dur:
        f = 440 * 2 ** ((mel[i % len(mel)] - 69) / 12)
        s0 = int(i * beat * sr); ln = min(int(2.0 * sr), n - s0)
        if ln <= 0: break
        tt = np.arange(ln) / sr
        tone = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2 * f * tt) + 0.12 * np.sin(2 * np.pi * 3.01 * f * tt)) * np.exp(-tt * 3.2)
        out[s0:s0 + ln] += 0.20 * tone
        i += 1
    bar = beat * 3
    for k in range(int(dur / bar) + 1):
        chord = prog[k % 4]
        s0 = int(k * bar * sr); ln = min(int(bar * 1.3 * sr), n - s0)
        if ln <= 0: break
        tt = np.arange(ln) / sr
        env = np.minimum(1, tt * 2.5) * np.exp(-tt * 0.5)
        for nt in chord:
            f = 440 * 2 ** ((nt - 12 - 69) / 12)
            out[s0:s0 + ln] += 0.06 * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * env
    # shimmer chimes at transitions
    for tc in [SCENE - XFADE / 2, 2 * SCENE - 1.5 * XFADE]:
        for j, nt in enumerate([96, 100, 103, 108]):
            s0 = int((tc + j * 0.06) * sr); ln = min(int(1.5 * sr), n - s0)
            tt = np.arange(ln) / sr
            f = 440 * 2 ** ((nt - 69) / 12)
            out[s0:s0 + ln] += 0.05 * np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3)
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
    scs = spec["scenes"]
    assert len(scs) == 3, "scenes must be 3"
    scenes = [Scene(s, 1000 + i * 77 + zlib.crc32(json.dumps(s, ensure_ascii=False).encode()) % 997) for i, s in enumerate(scs)]
    total = 3 * SCENE - 2 * XFADE
    if os.environ.get("PREVIEW_ONLY"):
        for i, s in enumerate(scenes):
            s.frame(SCENE - 1.6).convert("RGB").save(os.path.splitext(out)[0] + f"_preview_{i + 1}.png")
        return
    nfr = int(total * FPS)
    silent = out + ".v.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                          "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    for fi in range(nfr):
        t = fi / FPS
        idx = min(2, int(t // (SCENE - XFADE)))
        lt = t - idx * (SCENE - XFADE)
        img = scenes[idx].frame(lt)
        # crossfade from previous scene
        if idx > 0 and lt < XFADE:
            a = lt / XFADE
            prev = scenes[idx - 1].frame(lt + SCENE - XFADE)
            img = Image.blend(prev, img, a)
            img = flash(img, 0.35 * math.sin(a * math.pi))
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
