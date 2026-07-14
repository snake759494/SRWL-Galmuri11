# -*- coding: utf-8 -*-
"""Redraw spirit command labels (arc03#1988-2022) + skill activations (v2: AA quantize)."""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(__file__))
from imglib import get_sub, payload, parse_plt
from kredraw import img_to_grid, grid_to_img
from PIL import Image, ImageFont, ImageDraw

SCRATCH = os.path.dirname(__file__)
OUT = os.path.join(SCRATCH, "out")
STATE = os.path.join(SCRATCH, "state")
GALMURI = r"D:\nds\files (1)\Galmuri11.ttf"
DOTUM = r"C:\Windows\Fonts\gulim.ttc"  # gulim collection: Gulim/GulimChe/Dotum/DotumChe

SPIRITS = {
    1988: "열혈", 1989: "혼", 1990: "투지", 1991: "번뜩임", 1992: "불굴",
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

def aa_text(text, size, bold=1, max_w=60):
    """AA coverage image (L), pseudo-bold via stroke."""
    font = ImageFont.truetype(DOTUM, size, index=2)  # index2 = Dotum
    img = Image.new("L", (16 * len(text) + 60, size * 3), 0)
    ImageDraw.Draw(img).text((20, size), text, font=font, fill=255, stroke_width=bold, stroke_fill=255)
    bb = img.getbbox()
    img = img.crop(bb)
    if img.width > max_w:
        img = img.resize((max_w, img.height), Image.LANCZOS)
    return img

def shear_img(img, ratio=9):
    h = img.height
    extra = (h - 1) // ratio + 1
    out = Image.new("L", (img.width + extra, h), 0)
    for y in range(h):
        dx = (h - 1 - y) // ratio
        out.paste(img.crop((0, y, img.width, y + 1)), (dx, y))
    return out

def grad_big(p):
    if p < 0.18: return 12
    if p < 0.30: return 13
    if p < 0.40: return 14
    if p < 0.62: return 15
    if p < 0.72: return 14
    if p < 0.85: return 13
    return 12

def grad_small(p):
    if p < 0.3: return 11
    if p < 0.65: return 10
    return 9

def grad_skill(p):
    if p < 0.25: return 14
    if p < 0.55: return 15
    if p < 0.8: return 13
    return 12

def stamp_aa(L, img, ox, oy, lut, hi=95, mid=45, mid_idx=7, outline=1, ymax=None):
    """Stamp AA image: strong->lut(row), weak->mid_idx, dilate->outline."""
    px = img.load()
    w, h = img.width, img.height
    solid = [[px[x, y] >= hi for x in range(w)] for y in range(h)]
    on = [[px[x, y] >= mid for x in range(w)] for y in range(h)]
    for y in range(h):
        yy = oy + y
        if yy < 0 or yy >= len(L) or (ymax and yy > ymax):
            continue
        for x in range(w):
            if not on[y][x]:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ty, tx = yy + dy, ox + x + dx
                    if 0 <= ty < len(L) and 0 <= tx < len(L[0]) and (ymax is None or ty <= ymax):
                        if not (0 <= y + dy < h and 0 <= x + dx < w and on[y + dy][x + dx]):
                            L[ty][tx] = outline
    for y in range(h):
        yy = oy + y
        if yy < 0 or yy >= len(L) or (ymax and yy > ymax):
            continue
        for x in range(w):
            if solid[y][x]:
                L[yy][ox + x] = lut(y / max(1, h - 1))
            elif on[y][x]:
                L[yy][ox + x] = mid_idx

def crisp_mask_img(text, ppem=12):
    font = ImageFont.truetype(GALMURI, ppem)
    img = Image.new("L", (14 * len(text) + 40, 40), 0)
    ImageDraw.Draw(img).text((8, 8), text, font=font, fill=255)
    return img.crop(img.getbbox())

new_resources = {}
review = []

for idx, ko in SPIRITS.items():
    p = payload(get_sub("arc03", idx))
    grid, ver, w, h = img_to_grid(p)
    L = to_logical(grid)
    big_rows = [y for y in range(0, 18) if any(L[y])]
    small_rows = [y for y in range(18, 32) if any(L[y])]
    ob_top, ob_bot = (min(big_rows), max(big_rows)) if big_rows else (1, 17)
    os_top = min(small_rows) if small_rows else 18
    for y in range(32):
        for x in range(64):
            L[y][x] = 0
    size = 16 if len(ko) <= 3 else 14
    img = aa_text(ko, size, bold=1, max_w=57)
    img = shear_img(img, ratio=9)
    bh = img.height
    oy = max(1, min((ob_top + ob_bot) // 2 - bh // 2, 16 - bh))
    stamp_aa(L, img, 2, oy, grad_big, ymax=17)
    # small variant (crisp galmuri downscaled to 8px)
    ms = crisp_mask_img(ko, 12)
    sc = 8 / ms.height
    ms2 = ms.resize((max(1, int(ms.width * sc)), 8), Image.LANCZOS)
    px2 = ms2.load()
    Lmask = [[1 if px2[x, y] >= 110 else 0 for x in range(ms2.width)] for y in range(8)]
    # direct stamp small: fill via grad_small + outline 1
    oy2 = min(os_top, 22)
    for y in range(8):
        for x in range(ms2.width):
            if Lmask[y][x]:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ty, tx = oy2 + y + dy, 1 + x + dx
                        if 0 <= ty < 32 and 0 <= tx < 64 and not (
                            0 <= y + dy < 8 and 0 <= x + dx < ms2.width and Lmask[y + dy][x + dx]):
                            L[ty][tx] = 1
    for y in range(8):
        for x in range(ms2.width):
            if Lmask[y][x]:
                L[oy2 + y][1 + x] = grad_small(y / 7)
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
    img = crisp_mask_img(ko, 12)
    img = shear_img(img, ratio=6)
    if img.width > 62:
        img = img.resize((62, img.height), Image.LANCZOS)
    px = img.load()
    mask = [[1 if px[x, y] >= 110 else 0 for x in range(img.width)] for y in range(img.height)]
    bh = len(mask)
    oy = max(0, min((t0 + t1) // 2 - bh // 2, 13 - bh))
    for y in range(bh):
        for x in range(img.width):
            if mask[y][x]:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ty, tx = oy + y + dy, 1 + x + dx
                        if 0 <= ty <= 14 and 0 <= tx < 64 and not (
                            0 <= y + dy < bh and 0 <= x + dx < img.width and mask[y + dy][x + dx]):
                            L[ty][tx] = 1
    for y in range(bh):
        for x in range(img.width):
            if mask[y][x]:
                L[oy + y][1 + x] = grad_skill(y / max(1, bh - 1))
    new_resources[idx] = grid_to_img(from_logical(L), ver, w, h)
    review.append((idx, [row[:] for row in L]))

pickle.dump(new_resources, open(os.path.join(STATE, "newres", "spirits.pkl"), "wb"))
print("resources:", len(new_resources))

plt = parse_plt(payload(get_sub("arc03", 1985)))
cols = 8
rows_n = (len(review) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 70, rows_n * 48), (40, 40, 52))
dr = ImageDraw.Draw(sheet)
for n, (idx, L) in enumerate(review):
    cx, cy = (n % cols) * 70 + 3, (n // cols) * 48 + 12
    dr.text((cx, cy - 11), str(idx), fill=(255, 220, 80))
    for y in range(32):
        for x in range(64):
            v = L[y][x]
            if v:
                sheet.putpixel((cx + x, cy + y), plt[v])
sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
sheet.save(os.path.join(OUT, "ko_spirits.png"))
print("review saved")
