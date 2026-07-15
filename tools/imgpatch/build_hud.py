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

# ---- arc05#6 critical ----
p = payload(get_sub("arc05", 6))
grid, ver, w, h = img_to_grid(p)
W = w * 8
cols = [x for x in range(W) if any(grid[y][x] for y in range(16))]
# critical = rightmost large run; measured visually starts ~x196
a, z = 196, 255
lut_rows = {}
for y in range(16):
    c = Counter(grid[y][x] for x in range(a, z + 1) if grid[y][x] not in (0, 1))
    if c:
        lut_rows[y] = c.most_common(1)[0][0]
keys = sorted(lut_rows)
t0s, t1s = keys[0], keys[-1]
def lut05(pp):
    yy = t0s + pp * (t1s - t0s)
    best = min(keys, key=lambda k: abs(k - yy))
    return lut_rows[best]
for y in range(0, 16):
    for x in range(max(0, a - 2), min(W, z + 1)):
        grid[y][x] = 0
m = shear(to_mask(crisp("크리티컬", 12)), 6)
m = fit_width(m, z - a - 1)
stamp(grid, m, a, max(0, t0s - 1), lut05)
pickle.dump({6: grid_to_img(grid, ver, w, h)}, open(os.path.join(STATE, "newres", "hud05.pkl"), "wb"))
print("arc05#6 done; crit rows", t0s, t1s)

# ---- arc03#17 save messages ----
MSGS17 = [
    (0, 0, 71, "세이브 중입니다.", "L"),
    (0, 144, 255, "데이터를 읽지 못했습니다.", "L"),
    (1, 0, 127, "전원을 끄지 마세요.", "L"),
    (1, 144, 255, "데이터를 쓰지 못했습니다.", "L"),
    (2, 0, 223, "전원을 끄고 닌텐도 DS 전용 게임 카드를", "L"),
    (3, 40, 223, "다시 꽂아 주세요.", "L"),
]
p = payload(get_sub("arc03", 17))
grid, ver, w, h = img_to_grid(p)
W = w * 8
c = Counter(v for row in grid for v in row if v not in (0, 1))
fill17 = c.most_common(1)[0][0]
for band, a, z, txt, align in MSGS17:
    y0 = band * 16
    for y in range(y0, y0 + 16):
        for x in range(a, min(W, z + 1)):
            grid[y][x] = 0
    m = to_mask(crisp(txt, 12))
    m = fit_width(m, z - a)
    ox = a
    oy = y0 + max(0, (15 - len(m)) // 2)
    stamp(grid, m, ox, oy, lambda pp: fill17, outline=1)
new03[17] = grid_to_img(grid, ver, w, h)
print("arc03#17 done, fill", fill17)

# ---- arc03#3494 terrain chars 空陸海宇 -> 공육해우 (hardcoded cells) ----
p = payload(get_sub("arc03", 3494))
grid, ver, w, h = img_to_grid(p)
W = w * 8
c = Counter(v for row in grid for v in row if v not in (0, 1))
fill94 = c.most_common(1)[0][0]
CELLS = [(48, 61, "공"), (62, 75, "육"), (76, 89, "해"), (90, 103, "우")]
for a, z, txt in CELLS:
    for y in range(16, 32):
        for x in range(a, z + 1):
            grid[y][x] = 0
    m = to_mask(crisp(txt, 12))
    m = fit_width(m, z - a - 1)
    stamp(grid, m, a + 1, 17, lambda pp: fill94, outline=1)
new03[3494] = grid_to_img(grid, ver, w, h)
print("arc03#3494 done, fill", fill94)

res = pickle.load(open(os.path.join(STATE, "newres", "spirits.pkl"), "rb"))
res.update(new03)
pickle.dump(res, open(os.path.join(STATE, "newres", "spirits.pkl"), "wb"))
print("saved into spirits.pkl; total:", len(res))

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
