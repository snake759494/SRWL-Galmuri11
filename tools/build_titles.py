# -*- coding: utf-8 -*-
"""Build Korean scenario title cards + time cards (IMG+SCR replacement)."""
import os, sys, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from imglib import get_sub, payload, parse_plt
from compose import parse_scr, img_tiles
from PIL import Image, ImageFont, ImageDraw
from collections import Counter

SCRATCH = os.path.dirname(__file__)
OUT = _CFG.OUT_DIR
STATE = _CFG.STATE
os.makedirs(os.path.join(STATE, "newres"), exist_ok=True)

BATANG = _CFG.BATANG

def luminance(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

def build_ramp(plt, bank, exclude=(0,)):
    """indices sorted dark->bright with luminance, from one 16-color bank."""
    idxs = [i for i in range(16) if i not in exclude]
    pairs = [(luminance(plt[bank * 16 + i]), i) for i in idxs]
    pairs.sort()
    return pairs  # list of (lum, idx)

def quantize_to_ramp(v, ramp, vmax=255.0):
    """v in 0..255 (0=darkest visible) -> nearest ramp index by relative position."""
    # map v to target luminance between ramp[0].lum and ramp[-1].lum
    lo, hi = ramp[0][0], ramp[-1][0]
    tgt = lo + (hi - lo) * (v / vmax)
    best = min(ramp, key=lambda p: abs(p[0] - tgt))
    return best[1]

def render_text_gray(text, font, stroke=1):
    """Render AA text with black stroke on transparent -> (L image, mask image)."""
    W = 16 * len(text) + 64
    H = 64
    img = Image.new("L", (W, H), 0)      # luminance of glyph (white text)
    alp = Image.new("L", (W, H), 0)      # coverage incl. stroke
    d1 = ImageDraw.Draw(img)
    d2 = ImageDraw.Draw(alp)
    d1.text((32, 16), text, font=font, fill=255, stroke_width=stroke, stroke_fill=40)
    d2.text((32, 16), text, font=font, fill=255, stroke_width=stroke, stroke_fill=255)
    bb = alp.getbbox()
    return img.crop(bb), alp.crop(bb)

def tiles_from_canvas(canvas):
    """canvas: 2D index grid (h*8 rows x 256 cols) -> unique tiles + 32-wide map."""
    H = len(canvas) // 8
    tiles = []
    tmap = {}
    entries = []
    for ty in range(H):
        for tx in range(32):
            key = tuple(canvas[ty * 8 + r][tx * 8 + c] for r in range(8) for c in range(8))
            if key not in tmap:
                tmap[key] = len(tiles)
                tiles.append(key)
            entries.append(tmap[key])
    return tiles, entries

def make_img_payload(tiles):
    n = len(tiles)
    w = 32
    h = (n + w - 1) // w
    out = bytearray(b"IMG\x00" + struct.pack("<HH", w, h))
    for ti in range(w * h):
        t = tiles[ti] if ti < len(tiles) else (0,) * 64
        for i in range(0, 64, 2):
            out.append((t[i] & 0xF) | ((t[i + 1] & 0xF) << 4))
    return bytes(out)

def make_scr_payload(entries, w, h, bank=0):
    out = bytearray(b"SCR\x00" + bytes([0, w, h, 0]))
    for e in entries:
        out += struct.pack("<H", (bank << 12) | e)
    return bytes(out)

def compose_screen(img_i, scr_i, plt):
    tiles = img_tiles(payload(get_sub("arc03", img_i)))
    w, h, entries = parse_scr(payload(get_sub("arc03", scr_i)))
    grid = [[0] * (w * 8) for _ in range(h * 8)]
    for ty in range(h):
        for tx in range(w):
            e = entries[ty * w + tx]
            tn, hf, vf = e & 0x3FF, (e >> 10) & 1, (e >> 11) & 1
            if tn >= len(tiles):
                continue
            t = tiles[tn]
            for i in range(64):
                x, y = i % 8, i // 8
                grid[ty * 8 + y][tx * 8 + x] = t[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
    return grid, w, h

def text_rows(grid, bg=0):
    return [y for y in range(len(grid)) if any(v != bg for v in grid[y])]

# ---------- scenario titles ----------
titles = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "titles_ko.json"), encoding="utf-8"))
plt = parse_plt(payload(get_sub("arc03", 3395)))
ramp = build_ramp(plt, 0, exclude=(0,))
f14 = ImageFont.truetype(BATANG, 14)
f16 = ImageFont.truetype(BATANG, 16)
f13 = ImageFont.truetype(BATANG, 13)

new_resources = {}   # sub_idx -> payload bytes
review = []

for n, (idx_s, (line1, line2)) in enumerate(sorted(titles.items())):
    idx = int(idx_s)
    scr_idx = 3340 + (idx - 3285)
    ogrid, sw, sh = compose_screen(idx, scr_idx, plt)
    orows = text_rows(ogrid)
    o_top, o_bot = (min(orows), max(orows)) if orows else (88, 116)
    canvas = [[0] * 256 for _ in range(sh * 8)]
    # render lines
    imgs = []
    for li, (txt, fnt) in enumerate(((line1, f14), (line2, f16))):
        # squeeze long lines
        use = fnt
        g, a = render_text_gray(txt, use)
        if a.width > 250:
            g, a = render_text_gray(txt, f13)
        if a.width > 250:
            sc = 250 / a.width
            g = g.resize((int(g.width * sc), g.height), Image.LANCZOS)
            a = a.resize((int(a.width * sc), a.height), Image.LANCZOS)
        imgs.append((g, a))
    gap = 6
    total_h = imgs[0][1].height + gap + imgs[1][1].height
    o_center = (o_top + o_bot) // 2
    y0 = max(0, o_center - total_h // 2)
    for li, (g, a) in enumerate(imgs):
        x0 = (256 - a.width) // 2
        yy = y0 if li == 0 else y0 + imgs[0][1].height + gap
        ga, aa = g.load(), a.load()
        for y in range(a.height):
            for x in range(a.width):
                cov = aa[x, y]
                if cov < 40:
                    continue
                lum = ga[x, y]
                canvas[yy + y][x0 + x] = quantize_to_ramp(lum, ramp)
    tiles, entries = tiles_from_canvas(canvas)
    if len(tiles) > 1023:
        print("TILE OVERFLOW", idx, len(tiles))
    new_resources[idx] = make_img_payload(tiles)
    new_resources[scr_idx] = make_scr_payload(entries, 32, sh)
    review.append((idx, canvas, sh))

# ---------- time cards ----------
tc_texts = {3006: "며칠 후…", 3009: "1년 후…", 3012: "아득한 옛날…", 3015: "현재…"}
for idx, txt in tc_texts.items():
    plt_tc = parse_plt(payload(get_sub("arc03", idx + 2)))
    ogrid, sw, sh = compose_screen(idx, idx + 1, plt_tc and None or None) if False else (None, None, None)
    # compose original with its own palette-independent grid
    tiles_o = img_tiles(payload(get_sub("arc03", idx)))
    w, h, entries_o = parse_scr(payload(get_sub("arc03", idx + 1)))
    grid = [[0] * (w * 8) for _ in range(h * 8)]
    for ty in range(h):
        for tx in range(w):
            e = entries_o[ty * w + tx]
            tn, hf, vf = e & 0x3FF, (e >> 10) & 1, (e >> 11) & 1
            if tn >= len(tiles_o):
                continue
            t = tiles_o[tn]
            for i in range(64):
                x, y = i % 8, i // 8
                grid[ty * 8 + y][tx * 8 + x] = t[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
    # band = rows where idx1(black) dominates; text rows inside band
    band_rows = [y for y in range(len(grid)) if Counter(grid[y]).most_common(1)[0][0] == 1]
    b0, b1 = min(band_rows), max(band_rows)
    canvas = [[0] * 256 for _ in range(h * 8)]
    for y in range(b0, b1 + 1):
        for x in range(256):
            canvas[y][x] = 1
    ramp_tc = build_ramp(plt_tc, 0, exclude=(0,))
    g, a = render_text_gray(txt, f14, stroke=0)
    x0 = (256 - a.width) // 2
    yc = (b0 + b1) // 2 - a.height // 2
    ga, aa = g.load(), a.load()
    for y in range(a.height):
        for x in range(a.width):
            if aa[x, y] < 40:
                continue
            canvas[yc + y][x0 + x] = quantize_to_ramp(ga[x, y], ramp_tc)
    tiles, entries = tiles_from_canvas(canvas)
    new_resources[idx] = make_img_payload(tiles)
    new_resources[idx + 1] = make_scr_payload(entries, 32, h)
    review.append((idx, canvas, h))

# save resources
import pickle
pickle.dump(new_resources, open(os.path.join(STATE, "newres", "titles_tc.pkl"), "wb"))
print("resources:", len(new_resources))

# review sheet
crops = []
for idx, canvas, sh in review:
    rows = [y for y in range(len(canvas)) if any(canvas[y])]
    if not rows:
        continue
    y0, y1 = max(0, min(rows) - 2), min(len(canvas), max(rows) + 3)
    im = Image.new("RGB", (256, y1 - y0), (100, 170, 90))
    px = im.load()
    use_plt = plt if idx >= 3285 else parse_plt(payload(get_sub("arc03", idx + 2)))
    for y in range(y0, y1):
        for x in range(256):
            v = canvas[y][x]
            if v:
                px[x, y - y0] = use_plt[v]
    crops.append((idx, im))
total = sum(c.height + 14 for _, c in crops)
sheet = Image.new("RGB", (310, total), (25, 25, 33))
dr = ImageDraw.Draw(sheet)
y = 0
for idx, c in crops:
    dr.text((2, y + 3), str(idx), fill=(255, 220, 80))
    sheet.paste(c, (44, y + 2))
    y += c.height + 14
sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
half = sheet.height // 2
sheet.crop((0, 0, sheet.width, half)).save(os.path.join(OUT, "ko_titles_0.png"))
sheet.crop((0, half, sheet.width, sheet.height)).save(os.path.join(OUT, "ko_titles_1.png"))
print("review sheets saved")
