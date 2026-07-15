# -*- coding: utf-8 -*-
"""Translate copyright screens arc03#3619(+3620) and #3621(+3622)."""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(__file__))
import build_intro  # side effect: regenerates titles_tc.pkl incl. titles/tc/intro
from imglib import get_sub, payload, parse_plt
from compose import parse_scr, img_tiles
from build_titles import (build_ramp, quantize_to_ramp, render_text_gray,
                          tiles_from_canvas, make_img_payload, make_scr_payload)
from PIL import Image, ImageFont

SCRATCH = os.path.dirname(__file__)
OUT = os.path.join(SCRATCH, "out")
STATE = os.path.join(SCRATCH, "state")
BATANG = r"C:\Windows\Fonts\batang.ttc"

SCREENS = {
    (3619, 3620): [
        "©카라",
        "©쿠보서점·AIC",
        "©소츠·선라이즈",
        "©소츠·선라이즈·마이니치방송",
        "©토에이",
        "©토에이 애니메이션",
        "©나가이 고/다이나믹 기획·빌드베이스",
    ],
    (3621, 3622): [
        "©후지와라 시노부/단쿠가 노바 제작위원회",
        "©2001 나가이 고/다이나믹 기획·광자력연구소",
        "©2003 나가이 고/다이나믹 기획·광자력연구소",
        "©2003 Project GODANNAR",
        "©2007 빅웨스트/마크로스F 제작위원회·MBS",
        "©2008 시미즈 에이이치·시모구치 토모히로·아키타서점/GONZO/라인바렐 파트너즈",
    ],
}

plt = parse_plt(payload(get_sub("arc03", 3618)))
ramp = build_ramp(plt, 0, exclude=(0,))
f13 = ImageFont.truetype(BATANG, 13)
f12 = ImageFont.truetype(BATANG, 12)

res = pickle.load(open(os.path.join(STATE, "newres", "titles_tc.pkl"), "rb"))

for (img_i, scr_i), lines in SCREENS.items():
    imgp = payload(get_sub("arc03", img_i))
    scrp = payload(get_sub("arc03", scr_i))
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
    from collections import Counter
    cnt = Counter()
    for row in grid:
        cnt.update(row)
    bg = cnt.most_common(1)[0][0]
    ink_rows = [y for y in range(len(grid)) if any(v != bg for v in grid[y])]
    bands = []
    start = prev = ink_rows[0]
    for y in ink_rows[1:]:
        if y - prev > 3:
            bands.append((start, prev))
            start = y
        prev = y
    bands.append((start, prev))
    print(img_i, "bg idx:", bg, "bands:", len(bands), bands)
    canvas = [[bg] * 256 for _ in range(h * 8)]
    for bi in range(min(len(bands), len(lines))):
        b0, b1 = bands[bi]
        g, a = render_text_gray(lines[bi], f13, stroke=0)
        if a.width > 250:
            g, a = render_text_gray(lines[bi], f12, stroke=0)
        if a.width > 250:
            g = g.resize((250, g.height), Image.LANCZOS)
            a = a.resize((250, a.height), Image.LANCZOS)
        x0 = (256 - a.width) // 2
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
    print(img_i, "unique tiles:", len(new_tiles))
    res[img_i] = make_img_payload(new_tiles)
    res[scr_i] = make_scr_payload(new_entries, 32, h)
    # preview
    im = Image.new("RGB", (256, h * 8), (0, 0, 0))
    px = im.load()
    for y in range(h * 8):
        for x in range(256):
            v = canvas[y][x]
            if v:
                px[x, y] = plt[v]
    im.resize((512, h * 16), Image.NEAREST).save(os.path.join(OUT, f"credits_ko_{img_i}.png"))

pickle.dump(res, open(os.path.join(STATE, "newres", "titles_tc.pkl"), "wb"))
print("saved; titles_tc total:", len(res))
