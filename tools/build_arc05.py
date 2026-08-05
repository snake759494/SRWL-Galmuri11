# -*- coding: utf-8 -*-
"""Redraw arc05 battle labels #14-81 (in-place, style sampled from originals)."""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from imglib import get_sub, payload, parse_plt
from kredraw import img_to_grid, grid_to_img
from PIL import Image, ImageFont, ImageDraw
from collections import Counter

SCRATCH = os.path.dirname(__file__)
OUT = _CFG.OUT_DIR
STATE = _CFG.STATE
GALMURI = _CFG.GALMURI
F12 = ImageFont.truetype(GALMURI, 12)

LABELS = {
    14: "MAP병기", 15: "합체 공격", 16: "어택 콤보",
    17: "베어내기", 18: "쏘아떨구기", 19: "하이퍼 재머", 20: "분신",
    21: "미라주 콜로이드", 22: "오버라이드", 23: "전자 미채", 24: "공간 전이",
    25: "일루전 프로텍트", 26: "스텔스", 27: "이매지너리 로드", 28: "특수 회피",
    29: "드라군 배리어", 30: "양전자 리플렉터", 31: "핀포인트 배리어", 32: "차원 단층",
    33: "A.T.필드", 34: "빔 무효화", 35: "구형 배리어", 36: "엔젤 월",
    37: "라플라스 월", 38: "배리어 필드", 39: "액티브 클로크", 40: "라미네이트 장갑",
    41: "야타노카가미", 42: "PS장갑", 43: "VPS장갑", 44: "내빔 코팅 망토",
    45: "실드 방어", 46: "AB실드 방어", 47: "빔 실드 방어", 48: "베어내기 공격",
    49: "베어내기 방어", 50: "카운터",
    51: "조준치 다운 L1", 52: "조준치 다운 L2", 53: "조준치 다운 L3",
    54: "운동성 다운 L1", 55: "운동성 다운 L2", 56: "운동성 다운 L3",
    57: "장갑치 다운 L1", 58: "장갑치 다운 L2", 59: "장갑치 다운 L3",
    60: "이동력 다운 L1", 61: "이동력 다운 L2", 62: "이동력 다운 L3",
    63: "공격력 다운 L1", 64: "공격력 다운 L2", 65: "공격력 다운 L3",
    66: "사거리 다운 L1", 67: "사거리 다운 L2", 68: "사거리 다운 L3",
    69: "SP 다운 L1", 70: "SP 다운 L2", 71: "SP 다운 L3",
    72: "EN 다운 L1", 73: "EN 다운 L2", 74: "EN 다운 L3",
    75: "EN 흡수 L1", 76: "EN 흡수 L2", 77: "EN 흡수 L3",
    81: "특수효과 무효",
}

# ---- sample style from #50 (カウンター) ----
grid50, ver, w50, h50 = img_to_grid(payload(get_sub("arc05", 50)))
H = len(grid50)
W = len(grid50[0])
# interior vs border classification
def classify(grid):
    Hh, Ww = len(grid), len(grid[0])
    interior_rows = {}
    border = Counter()
    for y in range(Hh):
        for x in range(Ww):
            v = grid[y][x]
            if not v:
                continue
            nb = [grid[yy][xx] for yy, xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1))
                  if 0 <= yy < Hh and 0 <= xx < Ww]
            if all(n != 0 for n in nb):
                interior_rows.setdefault(y, Counter())[v] += 1
            else:
                border[v] += 1
    return interior_rows, border

irows, border = classify(grid50)
plt50 = parse_plt(payload(get_sub('arc05', 4)))
def lum(i):
    c = plt50[i]
    return 0.299*c[0]+0.587*c[1]+0.114*c[2]
OUTLINE = 3
dark_rows = {}
for y, cnt in irows.items():
    darks = Counter({i: n for i, n in cnt.items() if lum(i) < 100})
    if darks:
        dark_rows[y] = darks.most_common(1)[0][0]
text_rows = sorted(dark_rows)
t0, t1 = min(text_rows), max(text_rows)
LUT_ROWS = {(y - t0) / max(1, t1 - t0): dark_rows[y] for y in text_rows}
lut_keys = sorted(LUT_ROWS)
def fill_lut(p):
    best = min(lut_keys, key=lambda k: abs(k - p))
    return LUT_ROWS[best]
print('outline idx:', OUTLINE, 'text rows:', t0, t1, 'LUT:', {round(k,2): v for k, v in LUT_ROWS.items()})

def crisp(text, ppem=12):
    img = Image.new("L", (14 * len(text) + 40, 40), 0)
    ImageDraw.Draw(img).text((8, 8), text, font=ImageFont.truetype(GALMURI, ppem), fill=255)
    return img.crop(img.getbbox())

def shear_img(img, ratio=8):
    h = img.height
    extra = (h - 1) // ratio + 1
    out = Image.new("L", (img.width + extra, h), 0)
    for y in range(h):
        out.paste(img.crop((0, y, img.width, y + 1)), ((h - 1 - y) // ratio, y))
    return out

new_resources = {}
review = []
plt = parse_plt(payload(get_sub("arc05", 4)))

for idx, ko in LABELS.items():
    p = payload(get_sub("arc05", idx))
    grid, ver, w, h = img_to_grid(p)
    Wpx = w * 8
    # erase all
    for y in range(len(grid)):
        for x in range(Wpx):
            grid[y][x] = 0
    img = crisp(ko, 12)
    img = shear_img(img, 8)
    maxw = Wpx - 4
    if img.width > maxw:
        img = img.resize((maxw, img.height), Image.LANCZOS)
    px = img.load()
    mask = [[1 if px[x, y] >= 110 else 0 for x in range(img.width)] for y in range(img.height)]
    bh = len(mask)
    ox = (Wpx - img.width) // 2
    oy = max(1, (t0 + t1) // 2 - bh // 2 + 0)
    if oy + bh > 15:
        oy = max(0, 15 - bh)
    # outline
    for y in range(bh):
        for x in range(img.width):
            if mask[y][x]:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ty, tx = oy + y + dy, ox + x + dx
                        if 0 <= ty < len(grid) and 0 <= tx < Wpx and not (
                            0 <= y + dy < bh and 0 <= x + dx < img.width and mask[y + dy][x + dx]):
                            grid[ty][tx] = OUTLINE
    for y in range(bh):
        for x in range(img.width):
            if mask[y][x]:
                grid[oy + y][ox + x] = fill_lut(y / max(1, bh - 1))
    new_resources[idx] = grid_to_img(grid, ver, w, h)
    review.append((idx, [row[:] for row in grid]))

pickle.dump(new_resources, open(os.path.join(STATE, "newres", "arc05.pkl"), "wb"))
print("resources:", len(new_resources))

rows_out = []
sheet = Image.new("RGB", (170, len(review) * 20), (30, 30, 40))
dr = ImageDraw.Draw(sheet)
y = 0
for idx, grid in review:
    dr.text((0, y + 2), str(idx), fill=(255, 220, 80))
    for yy in range(min(16, len(grid))):
        for xx in range(len(grid[0])):
            v = grid[yy][xx]
            if v:
                sheet.putpixel((34 + xx, y + 2 + yy), plt[v])
    y += 20
sheet = sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST)
half = sheet.height // 2
sheet.crop((0, 0, sheet.width, half)).save(os.path.join(OUT, "ko_arc05_0.png"))
sheet.crop((0, half, sheet.width, sheet.height)).save(os.path.join(OUT, "ko_arc05_1.png"))
print("review saved")
