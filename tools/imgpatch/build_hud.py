# -*- coding: utf-8 -*-
"""HUD dictionary sheets + critical + save msgs + terrain chars (final spans)."""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(__file__))
from imglib import get_sub, payload, parse_plt
from kredraw import img_to_grid, grid_to_img
from PIL import Image, ImageFont, ImageDraw
from collections import Counter

SCRATCH = os.path.dirname(__file__)
OUT = os.path.join(SCRATCH, "out")
STATE = os.path.join(SCRATCH, "state")
GALMURI = r"D:\nds\files (1)\Galmuri11.ttf"

def crisp(text, ppem=12):
    img = Image.new("L", (14 * len(text) + 40, 40), 0)
    ImageDraw.Draw(img).text((8, 8), text, font=ImageFont.truetype(GALMURI, ppem), fill=255)
    return img.crop(img.getbbox())

def to_mask(img, thr=110):
    p = img.load()
    return [[1 if p[x, y] >= thr else 0 for x in range(img.width)] for y in range(img.height)]

def shear(mask, ratio=6):
    h, w = len(mask), len(mask[0])
    extra = (h - 1) // ratio + 1
    out = [[0] * (w + extra) for _ in range(h)]
    for y in range(h):
        dx = (h - 1 - y) // ratio
        for x in range(w):
            if mask[y][x]:
                out[y][x + dx] = 1
    return out

def fit_width(mask, maxw):
    if len(mask[0]) <= maxw:
        return mask
    img = Image.new("L", (len(mask[0]), len(mask)), 0)
    for y in range(len(mask)):
        for x in range(len(mask[0])):
            if mask[y][x]:
                img.putpixel((x, y), 255)
    img = img.resize((maxw, len(mask)), Image.NEAREST)
    return to_mask(img, 100)

def grad_skill(p):
    if p < 0.25: return 14
    if p < 0.55: return 15
    if p < 0.8: return 13
    return 12

def stamp(grid, mask, ox, oy, lut, outline=1):
    h, w = len(mask), len(mask[0])
    H, W = len(grid), len(grid[0])
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ty, tx = oy + y + dy, ox + x + dx
                        if 0 <= ty < H and 0 <= tx < W and not (
                            0 <= y + dy < h and 0 <= x + dx < w and mask[y + dy][x + dx]):
                            grid[ty][tx] = outline
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                yy, xx = oy + y, ox + x
                if 0 <= yy < H and 0 <= xx < W:
                    grid[yy][xx] = lut(y / max(1, h - 1))

# span tables: (band, x0, x1, text) — text None = keep original pixels
SHEETS = {
    2033: [
        (0, 1, 62, "카운터"), (0, 67, 116, "합체공격"), (0, 123, 172, "원호공격"), (0, 179, 228, "원호방어"),
        (1, 2, 68, "크리티컬"), (1, 74, 116, "실드"), (1, 123, 196, "안티빔 실드"),
        (2, 3, 77, "빔 실드"),
    ],
    2034: [
        (0, 2, 21, None), (0, 27, 51, "회피"), (0, 58, 100, "베어내기"), (0, 108, 154, "쏘아떨구기"),
        (0, 163, 185, "분신"), (0, 194, 252, "하이퍼 재머"),
        (1, 4, 58, "오버라이드"), (1, 67, 132, "미라주 콜로이드"), (1, 138, 229, "일루전 프로텍트"), (1, 234, 255, "특수"),
        (2, 3, 52, "전자미채"), (2, 58, 108, "공간전이"), (2, 117, 147, "스텔스"), (2, 156, 225, "이매지너리 로드"), (2, 232, 253, "회피"),
    ],
    2035: [
        (0, 0, 63, "드라군 배리어"), (0, 66, 150, "핀포인트 배리어"), (0, 153, 166, None), (0, 169, 246, "라미네이트 장갑"), (0, 249, 254, None),
        (1, 2, 45, "야타노카가미"), (1, 51, 100, "차원단층"), (1, 106, 164, "A.T.필드"), (1, 170, 204, "PS장갑"), (1, 210, 254, None),
        (2, 2, 36, "양전자"), (2, 41, 84, "리플렉터"), (2, 90, 110, "빔"), (2, 115, 149, "무효화"), (2, 155, 213, "배리어 필드"), (2, 217, 222, None), (2, 226, 255, "라플라스"),
        (3, 3, 69, "액티브 클로크"), (3, 74, 141, "엔젤 월"), (3, 148, 203, "구형 배리어"), (3, 208, 243, "월"), (3, 249, 254, None),
        (4, 1, 107, "내빔 코팅 망토"),
    ],
    2036: [
        (0, 2, 37, "조준치"), (0, 43, 76, "운동성"), (0, 82, 117, "장갑치"), (0, 122, 156, "이동력"),
        (0, 163, 196, "공격력"), (0, 204, 228, "사거리"), (0, 234, 244, None),
        (1, 5, 29, "기력"), (1, 34, 45, None), (1, 50, 123, "특수효과무효"), (1, 129, 149, "다운"),
        (1, 155, 180, "흡수"), (1, 184, 255, None),
    ],
}

new03 = {}
for idx, entries in SHEETS.items():
    p = payload(get_sub("arc03", idx))
    grid, ver, w, h = img_to_grid(p)
    orig = [row[:] for row in grid]
    W = w * 8
    bands = sorted(set(b for b, *_ in entries))
    for b in bands:
        for y in range(b * 16, b * 16 + 16):
            for x in range(W):
                grid[y][x] = 0
    for b, a, z, txt in entries:
        y0 = b * 16
        if txt is None:
            for y in range(y0, y0 + 16):
                for x in range(max(0, a - 1), min(W, z + 2)):
                    grid[y][x] = orig[y][x]
            continue
        m = shear(to_mask(crisp(txt, 12)), 6)
        m = fit_width(m, z - a + 1)
        oy = y0 + max(0, (15 - len(m)) // 2)
        stamp(grid, m, a, oy, grad_skill)
    new03[idx] = grid_to_img(grid, ver, w, h)

# ---- arc05#6 critical: green fill + light(2) outline, tall like original ----
p = payload(get_sub("arc05", 6))
grid, ver, w, h = img_to_grid(p)
W = w * 8
# original クリティカル katakana occupies x193..255 (band0), icon at 169-190 kept
a, z = 193, 255
CRIT_OUTLINE = 2  # light lavender, matches original border

def crit_fill(pp):
    if pp < 0.30: return 14     # bright green (thick body)
    if pp < 0.62: return 12
    if pp < 0.85: return 11
    return 10

def thicken2(mask, dx=1, dy=1):
    h2, w2 = len(mask), len(mask[0])
    out = [[0] * (w2 + dx) for _ in range(h2 + dy)]
    for y in range(h2):
        for x in range(w2):
            if mask[y][x]:
                for ddy in range(dy + 1):
                    for ddx in range(dx + 1):
                        out[y + ddy][x + ddx] = 1
    return out

def scale_mask(mask, tw, th):
    im = Image.new("L", (len(mask[0]), len(mask)), 0)
    for y in range(len(mask)):
        for x in range(len(mask[0])):
            if mask[y][x]:
                im.putpixel((x, y), 255)
    im = im.resize((tw, th), Image.NEAREST)
    pp = im.load()
    return [[1 if pp[x, y] >= 128 else 0 for x in range(tw)] for y in range(th)]

# erase the full katakana region only (keep icon at <=190)
for y in range(0, 16):
    for x in range(a, min(W, z + 1)):
        grid[y][x] = 0
# fill the FULL span x193..255 like the original (a hardware sprite shows wrapped
# tiles right after x255, so the text must reach the edge like original ル did)
mk = thicken2(to_mask(crisp("크리티컬", 12)), 1, 1)
mk = scale_mask(mk, z - a - 2, 14)   # ~60px wide, ends flush at x255
mk = shear(mk, 8)
if len(mk[0]) > z - a:
    mk = [row[: z - a] for row in mk]
oy = max(0, (16 - len(mk)) // 2)
ox = a + 1
stamp(grid, mk, ox, oy, crit_fill, outline=CRIT_OUTLINE)
pickle.dump({6: grid_to_img(grid, ver, w, h)}, open(os.path.join(STATE, "newres", "hud05.pkl"), "wb"))
print(f"arc05#6 critical done: span {a}-{z}, glyph {len(mk[0])}x{len(mk)} at x{ox} y{oy}")

# ---- arc03#17 save messages: NOT patched ----
# IMG#17 is a shared tile atlas composed by SCR#18/19/20 (3 different save screens),
# NOT a linear image. A linear pixel overwrite corrupts the tilemap (screen breaks).
# Regenerating all 3 screens needs 296 unique tiles > 256 budget, so leave original.
print("arc03#17 save messages: kept original (tilemap atlas, cannot fit Korean)")

# ---- arc03#3494 terrain chars: NOT patched (kept original 空陸海宇 per request) ----
print("arc03#3494 terrain chars: kept original (reverted per user request)")

res = pickle.load(open(os.path.join(STATE, "newres", "spirits.pkl"), "rb"))
res.pop(17, None)    # remove old (broken) save-screen patch
res.pop(3494, None)  # remove terrain-char patch (revert to original)
res.update(new03)
pickle.dump(res, open(os.path.join(STATE, "newres", "spirits.pkl"), "wb"))
print("saved into spirits.pkl; total:", len(res), "(17 present:", 17 in res, ")")

# review renders
plt = parse_plt(payload(get_sub("arc03", 1985)))
panels = []
for idx, pay in new03.items():
    grid, ver, w, h = img_to_grid(pay)
    im = Image.new("RGB", (w * 8, h * 8), (25, 25, 33))
    for y in range(h * 8):
        for x in range(w * 8):
            v = grid[y][x]
            if v:
                im.putpixel((x, y), plt[min(v, 15)])
    panels.append((idx, im))
grid, ver, w, h = img_to_grid(pickle.load(open(os.path.join(STATE, "newres", "hud05.pkl"), "rb"))[6])
plt5 = parse_plt(payload(get_sub("arc05", 4)))
im = Image.new("RGB", (w * 8, h * 8), (25, 25, 33))
for y in range(h * 8):
    for x in range(w * 8):
        v = grid[y][x]
        if v:
            im.putpixel((x, y), plt5[v])
panels.append(("a05_6", im))
total = sum(p2.height + 16 for _, p2 in panels)
sheet = Image.new("RGB", (300, total), (18, 18, 24))
dr = ImageDraw.Draw(sheet)
y = 0
for name, im in panels:
    dr.text((2, y + 2), str(name), fill=(255, 220, 80))
    sheet.paste(im, (40, y + 2))
    y += im.height + 16
sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
sheet.save(os.path.join(OUT, "hud_ko_review.png"))
print("review saved")
