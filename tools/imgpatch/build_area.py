# -*- coding: utf-8 -*-
"""Redraw area name labels arc03#1783 (keep underlines)."""
import os, sys, pickle
sys.path.insert(0, os.path.dirname(__file__))
from imglib import get_sub, payload, parse_plt
from kredraw import img_to_grid, grid_to_img
from PIL import Image, ImageFont, ImageDraw

SCRATCH = os.path.dirname(__file__)
OUT = os.path.join(SCRATCH, "out")
STATE = os.path.join(SCRATCH, "state")
GALMURI = r"D:\nds\files (1)\Galmuri11.ttf"

p = payload(get_sub("arc03", 1783))
grid, ver, w, h = img_to_grid(p)
H, W = len(grid), len(grid[0])
print("size", W, H)

# underline rows: rows containing a horizontal run >= 40
def underline_spans(row):
    spans = []
    x = 0
    while x < W:
        if grid[row][x]:
            x0 = x
            while x < W and grid[row][x]:
                x += 1
            if x - x0 >= 40:
                spans.append((x0, x))
        else:
            x += 1
    return spans

ul_rows = {}
for y in range(H):
    s = underline_spans(y)
    if s:
        ul_rows[y] = s
print("underline rows:", ul_rows)

# sample text style from original: interior dark? text = teal(?) with light outline
from collections import Counter
plt = None
for j in (1784, 1785, 1786, 1782):
    pp = payload(get_sub("arc03", j))
    if pp and pp[:3] == b"PLT":
        plt = parse_plt(pp)
        break
hist = Counter()
for y in range(H):
    if y in ul_rows:
        continue
    for x in range(W):
        if grid[y][x]:
            hist[grid[y][x]] += 1
print("text idx hist:", hist.most_common(8))
