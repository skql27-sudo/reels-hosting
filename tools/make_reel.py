#!/usr/bin/env python3
"""Build a ~20s 1080x1920 product-intro reel.

Usage: make_reel.py spec.json out.mp4
spec = {"style": "cute"|"modern", "title": "...", "subtitle": "...",
        "outro": "...", "items": [{"brand","name","price","note","img"}]}
"""
import json, os, subprocess, sys, math, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
CJK_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
CJK_BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"

STYLES = {
    "cute": dict(
        bg=(255, 244, 238), bg2=(255, 226, 226), card=(255, 255, 255),
        ink=(92, 64, 64), accent=(255, 128, 140), accent2=(140, 200, 170),
        tag_bg=(255, 214, 120), price_bg=(255, 128, 140), price_ink=(255, 255, 255),
        title_font=os.path.join(FONTS, "Jua-Regular.ttf"),
        body_font=os.path.join(FONTS, "Jua-Regular.ttf"), radius=70,
        brand_colors={"다이소": (232, 64, 80), "무인양품": (125, 30, 40), "모던하우스": (60, 110, 170)},
    ),
    "modern": dict(
        bg=(242, 240, 236), bg2=(226, 222, 215), card=(255, 255, 255),
        ink=(28, 28, 30), accent=(28, 28, 30), accent2=(168, 150, 120),
        tag_bg=(28, 28, 30), price_bg=(28, 28, 30), price_ink=(255, 255, 255),
        title_font=CJK_BLACK, body_font=CJK_BOLD, radius=8,
        brand_colors={"다이소": (28, 28, 30), "무인양품": (28, 28, 30), "모던하우스": (28, 28, 30)},
    ),
}


def font(path, size):
    return ImageFont.truetype(path, size)


def text_w(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0]


def wrap(d, s, f, maxw):
    lines, cur = [], ""
    for ch in s:
        if text_w(d, cur + ch, f) > maxw and cur:
            # break at last space if possible
            if " " in cur:
                head, tail = cur.rsplit(" ", 1)
                lines.append(head)
                cur = tail + ch
            else:
                lines.append(cur)
                cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def background(st, cute_deco=True):
    img = Image.new("RGB", (W, H), st["bg"])
    d = ImageDraw.Draw(img)
    if st is STYLES["cute"]:
        # soft polka dots + gingham-ish band
        for y in range(0, H, 120):
            for x in range((y // 120) % 2 * 60, W, 120):
                d.ellipse([x - 9, y - 9, x + 9, y + 9], fill=st["bg2"])
    else:
        d.rectangle([0, H - 260, W, H], fill=st["bg2"])
        d.line([80, 150, W - 80, 150], fill=st["ink"], width=3)
    return img


def fit_image(path, box_w, box_h):
    im = Image.open(path).convert("RGB")
    # trim near-white margins so small products fill the card
    g = im.convert("L").point(lambda v: 255 if v < 238 else 0)
    bb = g.getbbox()
    if bb:
        pad = int(0.06 * max(bb[2] - bb[0], bb[3] - bb[1]))
        bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad))
        if (bb[2] - bb[0]) * (bb[3] - bb[1]) < 0.85 * im.width * im.height:
            im = im.crop(bb)
    scale = min(box_w / im.width, box_h / im.height)
    im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    return im


def product_frame(st, item, idx, total):
    img = background(st)
    d = ImageDraw.Draw(img)
    cute = st is STYLES["cute"]
    # card
    cx0, cy0, cx1, cy1 = 90, 300, W - 90, 1330
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rounded_rectangle([cx0 + 12, cy0 + 22, cx1 + 12, cy1 + 22], st["radius"], fill=70)
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    img.paste((0, 0, 0) if not cute else (230, 170, 170), (0, 0), shadow)
    d.rounded_rectangle([cx0, cy0, cx1, cy1], st["radius"], fill=st["card"])
    pic = fit_image(item["img"], cx1 - cx0 - 100, cy1 - cy0 - 100)
    px = (W - pic.width) // 2
    py = cy0 + (cy1 - cy0 - pic.height) // 2
    mask = Image.new("L", pic.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pic.width, pic.height], 30 if cute else 0, fill=255)
    img.paste(pic, (px, py), mask)

    # counter badge
    f_cnt = font(st["title_font"], 64)
    label = f"{idx}/{total}"
    if cute:
        d.ellipse([60, 210, 240, 390], fill=st["accent"])
        tw = text_w(d, label, f_cnt)
        d.text((150 - tw / 2, 262), label, font=f_cnt, fill=(255, 255, 255))
    else:
        d.text((80, 175), f"No.{idx:02d}", font=font(st["title_font"], 56), fill=st["ink"])

    # brand tag
    brand = item["brand"]
    f_tag = font(st["body_font"], 50)
    tw = text_w(d, brand, f_tag)
    bc = st["brand_colors"].get(brand, st["ink"])
    tx0 = W - 90 - tw - 70
    d.rounded_rectangle([tx0, 200, W - 90, 290], 45 if cute else 4, fill=bc)
    d.text((tx0 + 35, 212), brand, font=f_tag, fill=(255, 255, 255))

    # name
    f_name = font(st["body_font"], 72 if cute else 64)
    lines = wrap(d, item["name"], f_name, W - 180)[:2]
    y = 1390
    for ln in lines:
        lw = text_w(d, ln, f_name)
        d.text(((W - lw) / 2, y), ln, font=f_name, fill=st["ink"])
        y += 92
    # price pill
    f_price = font(st["title_font"], 110)
    price = item["price"]
    pw = text_w(d, price, f_price)
    py0 = max(y + 20, 1600)
    d.rounded_rectangle([(W - pw) / 2 - 60, py0, (W + pw) / 2 + 60, py0 + 160], 80 if cute else 6, fill=st["price_bg"])
    d.text(((W - pw) / 2, py0 + 5), price, font=f_price, fill=st["price_ink"])
    if item.get("note"):
        f_note = font(st["body_font"], 44)
        nw = text_w(d, item["note"], f_note)
        d.text(((W - nw) / 2, py0 + 185), item["note"], font=f_note, fill=st["accent2"] if not cute else st["accent"])
    return img


def title_frame(st, title, subtitle):
    img = background(st)
    d = ImageDraw.Draw(img)
    cute = st is STYLES["cute"]
    f_t = font(st["title_font"], 130 if cute else 120)
    lines = title.split("\n")
    total_h = len(lines) * 165
    y = (H - total_h) // 2 - 120
    for ln in lines:
        lw = text_w(d, ln, f_t)
        if cute:
            # outline for sticker feel
            d.text(((W - lw) / 2, y), ln, font=f_t, fill=st["ink"], stroke_width=14, stroke_fill=(255, 255, 255))
        else:
            d.text(((W - lw) / 2, y), ln, font=f_t, fill=st["ink"])
        y += 165
    f_s = font(st["body_font"], 58)
    sw = text_w(d, subtitle, f_s)
    if cute:
        d.rounded_rectangle([(W - sw) / 2 - 45, y + 40, (W + sw) / 2 + 45, y + 150], 55, fill=st["accent"])
        d.text(((W - sw) / 2, y + 55), subtitle, font=f_s, fill=(255, 255, 255))
    else:
        d.line([(W - sw) / 2, y + 30, (W + sw) / 2, y + 30], fill=st["ink"], width=4)
        d.text(((W - sw) / 2, y + 60), subtitle, font=f_s, fill=st["ink"])
    return img


def outro_frame(st, text):
    img = background(st)
    d = ImageDraw.Draw(img)
    f = font(st["title_font"], 96)
    lines = text.split("\n")
    y = (H - len(lines) * 130) // 2
    for ln in lines:
        lw = text_w(d, ln, f)
        d.text(((W - lw) / 2, y), ln, font=f, fill=st["ink"])
        y += 130
    f2 = font(st["body_font"], 46)
    s = "* 가격은 게시일 기준 온라인몰 가격이에요"
    sw = text_w(d, s, f2)
    d.text(((W - sw) / 2, y + 60), s, font=f2, fill=st["ink"])
    return img


def render_scene(png, dur, out, zoom=True):
    tmp = out + ".tmp.mp4"
    frames = int(round(dur * FPS))
    if zoom:
        vf = (f"scale=1188:2112,zoompan=z='min(1+0.06*on/{frames},1.06)':x='iw/2-(iw/zoom/2)':"
              f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
              f"fade=t=in:st=0:d=0.2,format=yuv420p")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", png, "-vf", vf, "-frames:v", str(frames)]
    else:
        vf = f"format=yuv420p,loop=-1:1,trim=duration={dur},fade=t=in:st=0:d=0.2"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", png, "-vf", vf]
    cmd += ["-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), tmp]
    subprocess.run(cmd, check=True)
    os.replace(tmp, out)


def synth_music(path, dur, style):
    """Original simple loop: music-box arpeggio (cute) or soft lo-fi chords (modern)."""
    sr = 44100
    n = int(sr * dur)
    t = np.arange(n) / sr
    out = np.zeros(n)
    if style == "cute":
        bpm, prog = 112, [[72, 76, 79, 84], [69, 72, 76, 81], [65, 69, 72, 77], [67, 71, 74, 79]]
    else:
        bpm, prog = 84, [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 65]]
    beat = 60 / bpm
    step = beat / 2
    i = 0
    while i * step < dur:
        chord = prog[int(i * step / (beat * 4)) % 4]
        note = chord[i % 4] if style == "cute" else chord[(i * 3) % 4]
        f = 440 * 2 ** ((note - 69) / 12)
        s0 = int(i * step * sr)
        ln = int(min(1.2, dur - i * step) * sr)
        tt = np.arange(ln) / sr
        if style == "cute":
            tone = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 5)
            amp = 0.22
        else:
            tone = (np.sin(2 * np.pi * f * tt) + 0.15 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 2.2)
            amp = 0.16
        out[s0:s0 + ln] += amp * tone[: max(0, min(ln, n - s0))]
        i += 1
    # bass / pad
    for k in range(int(dur / (beat * 4)) + 1):
        chord = prog[k % 4]
        f = 440 * 2 ** ((chord[0] - 12 - 69) / 12)
        s0 = int(k * beat * 4 * sr)
        ln = min(int(beat * 4 * sr), n - s0)
        if ln <= 0:
            break
        tt = np.arange(ln) / sr
        env = np.minimum(1, tt * 8) * np.exp(-tt * 0.6)
        out[s0:s0 + ln] += 0.12 * np.sin(2 * np.pi * f * tt) * env
    # fade in/out
    fade = int(sr * 0.6)
    out[:fade] *= np.linspace(0, 1, fade)
    out[-fade:] *= np.linspace(1, 0, fade)
    out = out / max(1e-6, np.abs(out).max()) * 0.6
    data = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(data.tobytes())


def main():
    spec = json.load(open(sys.argv[1]))
    out = os.path.abspath(sys.argv[2])
    st = STYLES[spec["style"]]
    work = os.path.splitext(out)[0] + "_parts"
    os.makedirs(work, exist_ok=True)
    items = spec["items"]
    t_intro, t_outro = 2.4, 1.8
    per = round((20.4 - t_intro - t_outro) / len(items), 2)
    scenes = []
    p = os.path.join(work, "s00.png"); title_frame(st, spec["title"], spec["subtitle"]).save(p)
    scenes.append((p, t_intro))
    for i, it in enumerate(items, 1):
        p = os.path.join(work, f"s{i:02d}.png"); product_frame(st, it, i, len(items)).save(p)
        scenes.append((p, per))
    p = os.path.join(work, "s99.png"); outro_frame(st, spec["outro"]).save(p)
    scenes.append((p, t_outro))
    if os.environ.get("PREVIEW_ONLY"):
        return
    lst = os.path.join(work, "list.txt")
    with open(lst, "w") as fh:
        for j, (png, dur) in enumerate(scenes):
            mp4 = png[:-4] + ".mp4"
            render_scene(png, dur, mp4, zoom=(0 < j < len(scenes) - 1))
            fh.write(f"file '{mp4}'\n")
    total = sum(d for _, d in scenes)
    silent = os.path.join(work, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    wav = os.path.join(work, "music.wav")
    synth_music(wav, total, spec["style"])
    tmp = out + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    print(out, total)


if __name__ == "__main__":
    main()
