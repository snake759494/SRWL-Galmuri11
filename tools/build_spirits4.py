# -*- coding: utf-8 -*-
"""Spirits v4: wide crisp glyphs, strong black outline, NO small variant."""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from imglib import get_sub, payload, parse_plt
from kredraw import img_to_grid, grid_to_img
from PIL import Image, ImageFont, ImageDraw

SCRATCH = os.path.dirname(__file__)
OUT = _CFG.OUT_DIR
STATE = _CFG.STATE
GALMURI = _CFG.GALMURI
GULIM = _CFG.GULIM

SPIRITS = {
    1988: "열혈", 1989: "혼", 1990: "투지", 1991: "섬광", 1992: "불굴",
    1993: "철벽", 1994: "교란", 1995: "집중", 1996: "필중", 1997: "감응",
    1998: "가속", 1999: "각성", 2000: "재동", 2001: "돌격", 2002: "근성",
    2003: "대근성", 2004: "신뢰", 2005: "우정", 2006: "유대", 2007: "보급",
    2008: "저격", 2009: "기합", 2010: "기백", 2011: "격려", 2012: "탈력",
    2013: "기대", 2014: "봐주기", 2015: "직격", 2016: "정찰", 2017: "사랑",
    2018: "직감", 2019: "행운", 2020: "축복", 2021: "노력", 2022: "응원",
}
SKILLS = {
    2024: "탄창회복", 2025: "마진 파워", 2027: "동탁 파워",
    2028: "제로시스템", 2029: "접속", 2030: "절단",
}

def to_logical(grid):
    L = [[0] * 64 for _ in range(32)]
    for y in range(16):
        for x in range(64):
            L[y][x] = grid[y][x]
            L[y + 16][x] = grid[y][x + 64]
    return L

def from_logical(L):
    grid = [[0] * 128 for _ in range(16)]
    for y in range(16):
        for x in range(64):
            grid[y][x] = L[y][x]
            grid[y][x + 64] = L[y + 16][x]
    return grid

def glyph_mask(text, px_h=15):
    """Crisp mask, no stroke merging: Galmuri ppem 12 scaled to px_h with NEAREST."""
    fnt = ImageFont.truetype(GALMURI, 12)
    img = Image.new("L", (14 * len(text) + 40, 40), 0)
    ImageDraw.Draw(img).text((8, 8), text, font=fnt, fill=255)
    img = img.crop(img.getbbox())
    # scale to target height with NEAREST (keeps crisp)
    sc = px_h / img.height
    img = img.resize((max(1, round(img.width * sc)), px_h), Image.NEAREST)
    p = img.load()
    return [[1 if p[x, y] >= 128 else 0 for x in range(img.width)] for y in range(px_h)]

def stretch_x(mask, target_w):
    w = len(mask[0])
    if w >= target_w:
        return mask
    img = Image.new("L", (w, len(mask)), 0)
    for y in range(len(mask)):
        for x in range(w):
            if mask[y][x]:
                img.putpixel((x, y), 255)
    img = img.resize((target_w, len(mask)), Image.NEAREST)
    p = img.load()
    return [[1 if p[x, y] >= 128 else 0 for x in range(target_w)] for y in range(len(mask))]

def thicken(mask, dx=1, dy=1):
    h, w = len(mask), len(mask[0])
    out = [[0] * (w + dx) for _ in range(h + dy)]
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                for ddy in range(dy + 1):
                    for ddx in range(dx + 1):
                        out[y + ddy][x + ddx] = 1
    return out

def shear_mask(mask, ratio=9):
    h = len(mask)
    w = len(mask[0])
    extra = (h - 1) // ratio + 1
    out = [[0] * (w + extra) for _ in range(h)]
    for y in range(h):
        dx = (h - 1 - y) // ratio
        for x in range(w):
            if mask[y][x]:
                out[y][x + dx] = 1
    return out

def grad_big(p):
    if p < 0.18: return 15
    if p < 0.45: return 14
    if p < 0.70: return 13
    return 12

def grad_skill(p):
    if p < 0.25: return 14
    if p < 0.55: return 15
    if p < 0.8: return 13
    return 12

def stamp(L, mask, ox, oy, lut, outline=1, outline_r=1, ymax=None):
    h, w = len(mask), len(mask[0])
    rng = list(range(-outline_r, outline_r + 1))
    for y in range(h):
        for x in range(w):
            if not mask[y][x]:
                continue
            for dy in rng:
                for dx in rng:
                    ty, tx = oy + y + dy, ox + x + dx
                    if 0 <= ty < len(L) and 0 <= tx < len(L[0]) and (ymax is None or ty <= ymax):
                        if not (0 <= y + dy < h and 0 <= x + dx < w and mask[y + dy][x + dx]):
                            L[ty][tx] = outline
    for y in range(h):
        yy = oy + y
        if yy < 0 or yy >= len(L) or (ymax is not None and yy > ymax):
            continue
        for x in range(w):
            if mask[y][x]:
                L[yy][ox + x] = lut(y / max(1, h - 1))

new_resources = {}
review = []

for idx, ko in SPIRITS.items():
    p = payload(get_sub("arc03", idx))
    grid, ver, w, h = img_to_grid(p)
    L = to_logical(grid)
    big_rows = [y for y in range(0, 18) if any(L[y])]
    big_cols = [x for x in range(64) if any(L[y][x] for y in range(18))]
    ob_top, ob_bot = (min(big_rows), max(big_rows)) if big_rows else (1, 17)
    bx0, bx1 = (min(big_cols), max(big_cols)) if big_cols else (2, 61)
    box_w = bx1 - bx0 + 1
    # erase EVERYTHING including small variant region
    for y in range(32):
        for x in range(64):
            L[y][x] = 0
    # glyph: THIN crisp strokes (no thicken/stretch), largest size fitting bbox
    avail = box_w - 4  # outline(2) + shear margin

    def dotum_mask(text, size, thr=110):
        f2 = ImageFont.truetype(GULIM, size, index=2)
        img2 = Image.new("L", (20 * len(text) + 40, size * 3), 0)
        ImageDraw.Draw(img2).text((10, size), text, font=f2, fill=255)
        img2 = img2.crop(img2.getbbox())
        pp2 = img2.load()
        return [[1 if pp2[xx, yy] >= thr else 0 for xx in range(img2.width)]
                for yy in range(img2.height)]

    m = None
    for size in (16, 15, 14, 13, 12, 11, 10):
        cand = shear_mask(dotum_mask(ko, size, thr=100 if size <= 11 else 110), ratio=10)
        if len(cand[0]) <= avail:
            m = cand
            break
    if m is None:
        cand = shear_mask(glyph_mask(ko, px_h=11), ratio=10)
        if len(cand[0]) > avail:
            img2 = Image.new("L", (len(cand[0]), len(cand)), 0)
            for yy in range(len(cand)):
                for xx in range(len(cand[0])):
                    if cand[yy][xx]:
                        img2.putpixel((xx, yy), 255)
            img2 = img2.resize((avail, len(cand)), Image.NEAREST)
            pp2 = img2.load()
            cand = [[1 if pp2[xx, yy] >= 128 else 0 for xx in range(avail)]
                    for yy in range(len(cand))]
        m = cand
    bh = len(m)
    oy = max(1, min((ob_top + ob_bot) // 2 - bh // 2, 17 - bh))
    ox = max(bx0 + 1, bx0 + (box_w - len(m[0])) // 2)
    stamp(L, m, ox, oy, grad_big, outline=1, outline_r=1, ymax=17)
    new_resources[idx] = grid_to_img(from_logical(L), ver, w, h)
    review.append((idx, [row[:] for row in L]))

for idx, ko in SKILLS.items():
    p = payload(get_sub("arc03", idx))
    grid, ver, w, h = img_to_grid(p)
    L = to_logical(grid)
    rows = [y for y in range(0, 14) if any(L[y])]
    t0, t1 = (min(rows), max(rows)) if rows else (2, 12)
    for y in range(max(0, t0 - 1), min(t1 + 2, 14)):
        for x in range(64):
            L[y][x] = 0
    m = glyph_mask(ko, px_h=11)
    if len(m[0]) > 58:
        img = Image.new("L", (len(m[0]), len(m)), 0)
        for y in range(len(m)):
            for x in range(len(m[0])):
                if m[y][x]:
                    img.putpixel((x, y), 255)
        img = img.resize((58, len(m)), Image.NEAREST)
        pp = img.load()
        m = [[1 if pp[x, y] >= 128 else 0 for x in range(58)] for y in range(len(m))]
    m = shear_mask(m, ratio=6)
    bh = len(m)
    oy = max(0, min((t0 + t1) // 2 - bh // 2, 13 - bh))
    stamp(L, m, 1, oy, grad_skill, outline=1, outline_r=1, ymax=14)
    new_resources[idx] = grid_to_img(from_logical(L), ver, w, h)
    review.append((idx, [row[:] for row in L]))

pickle.dump(new_resources, open(os.path.join(STATE, "newres", "spirits.pkl"), "wb"))
print("resources:", len(new_resources))

# review with BOTH palettes (green 1985 + check 1986/1987 pink variants)
for pi in (1985, 1986, 1987):
    pp = payload(get_sub("arc03", pi))
    if pp[:3] == b"PLT":
        plt = parse_plt(pp)
        print(f"palette {pi}:", plt[:4], "...", plt[12:16])

plt = parse_plt(payload(get_sub("arc03", 1986)))
cols = 8
rows_n = (len(review) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 70, rows_n * 48), (10, 30, 14))
dr = ImageDraw.Draw(sheet)
for n2, (idx, L) in enumerate(review):
    cx, cy = (n2 % cols) * 70 + 3, (n2 // cols) * 48 + 12
    dr.text((cx, cy - 11), str(idx), fill=(255, 220, 80))
    for y in range(32):
        for x in range(64):
            v = L[y][x]
            if v:
                sheet.putpixel((cx + x, cy + y), plt[v])
sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
sheet.save(os.path.join(OUT, "ko_spirits5.png"))
print("review saved")
