# -*- coding: utf-8 -*-
import os, sys, pickle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from imglib import get_sub, payload
from kredraw import img_to_grid, grid_to_img
from PIL import Image, ImageFont, ImageDraw

SCRATCH = os.path.dirname(__file__)
STATE = _CFG.STATE
GALMURI = _CFG.GALMURI

p = payload(get_sub("arc03", 1783))
grid, ver, w, h = img_to_grid(p)
W = 256
for y in list(range(0, 15)) + list(range(19, 39)):
    for x in range(W):
        grid[y][x] = 0

def crisp(text, ppem=12):
    img = Image.new("L", (14 * len(text) + 40, 40), 0)
    ImageDraw.Draw(img).text((8, 8), text, font=ImageFont.truetype(GALMURI, ppem), fill=255)
    return img.crop(img.getbbox())

def stamp(grid, img, ox, oy, fill=2, outline=1):
    px = img.load()
    m = [[1 if px[x, y] >= 110 else 0 for x in range(img.width)] for y in range(img.height)]
    for y in range(img.height):
        for x in range(img.width):
            if m[y][x]:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ty, tx = oy + y + dy, ox + x + dx
                        if 0 <= ty < len(grid) and 0 <= tx < W and not (
                            0 <= y + dy < img.height and 0 <= x + dx < img.width and m[y + dy][x + dx]):
                            grid[ty][tx] = outline
    for y in range(img.height):
        for x in range(img.width):
            if m[y][x]:
                grid[oy + y][ox + x] = fill

# original: fill = teal (idx 8-15 all teal), outline = bright gray (idx 1)
items = [((9, 84), 1, "일본 에리어"), ((89, 175), 1, "지구권 에리어"),
         ((1, 111), 25, "다리우스계 에리어"), ((113, 199), 25, "은하계 에리어")]
for (x0, x1), ytop, txt in items:
    img = crisp(txt, 12)
    cx = x0 + (x1 - x0 - img.width) // 2
    stamp(grid, img, max(1, cx), ytop, fill=12, outline=1)

res = pickle.load(open(os.path.join(STATE, "newres", "spirits.pkl"), "rb"))
res[1783] = grid_to_img(grid, ver, w, h)
pickle.dump(res, open(os.path.join(STATE, "newres", "spirits.pkl"), "wb"))
print("1783 added; total:", len(res))
