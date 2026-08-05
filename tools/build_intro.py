# -*- coding: utf-8 -*-
"""Translate intro text screen arc03#3147 (+SCR 3148)."""
import os, sys, pickle, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from imglib import get_sub, payload, parse_plt
from compose import parse_scr, img_tiles
from build_titles import (build_ramp, quantize_to_ramp, render_text_gray,
                          tiles_from_canvas, make_img_payload, make_scr_payload)
from PIL import Image, ImageFont, ImageDraw

SCRATCH = os.path.dirname(__file__)
OUT = _CFG.OUT_DIR
STATE = _CFG.STATE
BATANG = _CFG.BATANG

LINES = [
    "우주.",
    "그것은 인류에게 남겨진 최후의 프론티어.",
    "그 탄생의 순간부터 수많은 수수께끼에 싸여,",
    "팽창의 끝에 무엇이 일어날지 아무도 알지 못한다.",
    "사라진 초은하문명… 되풀이되는 역사…",
    "평행세계… 모든 가능성이 이곳에 있다.",
    "인간의 손이 아직 닿지 않은 곳이기에.",
]

plt = parse_plt(payload(get_sub("arc03", 3146)))
imgp = payload(get_sub("arc03", 3147))
scrp = payload(get_sub("arc03", 3148))

# compose original to find line bands
tiles = img_tiles(imgp)
w, h, entries = parse_scr(scrp)
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

ink_rows = [y for y in range(len(grid)) if any(grid[y])]
bands = []
if ink_rows:
    start = prev = ink_rows[0]
    for y in ink_rows[1:]:
        if y - prev > 3:
            bands.append((start, prev))
            start = y
        prev = y
    bands.append((start, prev))
print("original line bands:", bands)

ramp = build_ramp(plt, 0, exclude=(0,))
f13 = ImageFont.truetype(BATANG, 13)
f12 = ImageFont.truetype(BATANG, 12)

# keep >=1 tile (8px) margin on each side: text must fit within x[MARGIN, 256-MARGIN]
MARGIN = 8
MAXW = 256 - 2 * MARGIN  # 240
canvas = [[0] * 256 for _ in range(h * 8)]
n = min(len(bands), len(LINES))
for bi in range(n):
    b0, b1 = bands[bi]
    txt = LINES[bi]
    g, a = render_text_gray(txt, f13, stroke=0)
    if a.width > MAXW:
        g, a = render_text_gray(txt, f12, stroke=0)
    if a.width > MAXW:
        g = g.resize((MAXW, g.height), Image.LANCZOS)
        a = a.resize((MAXW, a.height), Image.LANCZOS)
    x0 = max(MARGIN, (256 - a.width) // 2)
    if x0 + a.width > 256 - MARGIN:
        x0 = 256 - MARGIN - a.width
    yc = (b0 + b1) // 2 - a.height // 2
    ga, aa = g.load(), a.load()
    for y in range(a.height):
        for x in range(a.width):
            if aa[x, y] < 40:
                continue
            yy, xx = yc + y, x0 + x
            if 0 <= yy < len(canvas) and 0 <= xx < 256:
                canvas[yy][xx] = quantize_to_ramp(ga[x, y], ramp)

new_tiles, new_entries = tiles_from_canvas(canvas)
print("unique tiles:", len(new_tiles))
res = pickle.load(open(os.path.join(STATE, "newres", "titles_tc.pkl"), "rb"))
res[3147] = make_img_payload(new_tiles)
res[3148] = make_scr_payload(new_entries, 32, h)
pickle.dump(res, open(os.path.join(STATE, "newres", "titles_tc.pkl"), "wb"))
print("saved; titles_tc total:", len(res))

# preview
im = Image.new("RGB", (256, h * 8), (0, 0, 0))
px = im.load()
for y in range(h * 8):
    for x in range(256):
        v = canvas[y][x]
        if v:
            px[x, y] = plt[v]
im = im.resize((512, h * 16), Image.NEAREST)
im.save(os.path.join(OUT, "intro_ko_preview.png"))
print("preview saved")
