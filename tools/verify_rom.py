# -*- coding: utf-8 -*-
"""Cross-verify: read patched resources back out of the FINAL ROM and render them.

Independent of the build pickles - proves what actually landed in the ROM.
Run after tools/build_all.py; writes a review PNG into the build out/ folder.
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from ecd import ecd_decompress
from PIL import Image, ImageDraw

ROM = _CFG.OUT_ROM
OUT = _CFG.OUT_DIR
data = open(ROM, "rb").read()

fat_off = struct.unpack_from("<I", data, 0x48)[0]
def file_range(fid):
    return struct.unpack_from("<II", data, fat_off + fid * 8)

# arc03 = fileid 99, arc05 = fileid 101 (from original listing: 97=arc01,98=arc02,99=arc03,100=arc04,101=arc05)
def arc_blob(fid):
    st, en = file_range(fid)
    return data[st:en]

def subpay(blob, i):
    first = struct.unpack_from("<I", blob, 0)[0]
    n = first // 4
    offs = list(struct.unpack_from(f"<{n}I", blob, 0)) + [len(blob)]
    raw = blob[offs[i]:offs[i + 1]]
    if raw[:3] == b"ECD":
        return ecd_decompress(raw)
    return bytes(raw)

a03 = arc_blob(99)
a05 = arc_blob(101)

def parse_plt_pay(p):
    n = struct.unpack_from("<I", p, 4)[0]
    cols = []
    for i in range(n):
        v = struct.unpack_from("<H", p, 8 + i * 2)[0]
        cols.append(((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3))
    return cols

def img_tiles_pay(p):
    ver = p[3]
    w, h = struct.unpack_from("<HH", p, 4)
    tsz = 64 if ver == 1 else 32
    tiles = []
    pos = 8
    for _ in range(w * h):
        t = p[pos:pos + tsz]; pos += tsz
        px = []
        for i in range(64):
            if ver == 1:
                px.append(t[i])
            else:
                b = t[i // 2]
                px.append((b & 0xF) if i % 2 == 0 else (b >> 4))
        tiles.append(px)
    return tiles, w, h

def compose_pay(imgp, scrp, plt):
    tiles, _, _ = img_tiles_pay(imgp)
    w, h = scrp[5], scrp[6]
    entries = struct.unpack_from(f"<{w*h}H", scrp, 8)
    im = Image.new("RGB", (w * 8, h * 8), (0, 0, 0))
    px = im.load()
    for ty in range(h):
        for tx in range(w):
            e = entries[ty * w + tx]
            tn, hf, vf, pb = e & 0x3FF, (e >> 10) & 1, (e >> 11) & 1, e >> 12
            if tn >= len(tiles):
                continue
            t = tiles[tn]
            for i in range(64):
                x, y = i % 8, i // 8
                c = t[(7 - y if vf else y) * 8 + (7 - x if hf else x)]
                ci = pb * 16 + c
                if ci < len(plt):
                    px[tx * 8 + x, ty * 8 + y] = plt[ci]
    return im

panels = []
plt_title = parse_plt_pay(subpay(a03, 3395))
for i, scr in ((3287, 3342), (3339, 3394)):
    im = compose_pay(subpay(a03, i), subpay(a03, scr), plt_title)
    panels.append((f"title{i}", im.crop((0, 80, 256, 120))))
plt_tc = parse_plt_pay(subpay(a03, 3008))
panels.append(("tc3006", compose_pay(subpay(a03, 3006), subpay(a03, 3007), plt_tc).crop((0, 80, 256, 110))))
# spirit 1995 (linear 128x16 folded)
def folded_img(p, plt):
    tiles, w, h = img_tiles_pay(p)
    im = Image.new("RGB", (64, 32), (40, 40, 52))
    px = im.load()
    grid = [[0] * 128 for _ in range(16)]
    for ti, t in enumerate(tiles):
        tx, ty = ti % w, ti // w
        for i in range(64):
            grid[ty * 8 + i // 8][tx * 8 + i % 8] = t[i]
    for y in range(16):
        for x in range(64):
            if grid[y][x]:
                px[x, y] = plt[grid[y][x]]
            if grid[y][x + 64]:
                px[x, y + 16] = plt[grid[y][x + 64]]
    return im
plt_sp = parse_plt_pay(subpay(a03, 1985))
panels.append(("spirit1995", folded_img(subpay(a03, 1995), plt_sp)))
panels.append(("spirit1988", folded_img(subpay(a03, 1988), plt_sp)))
# arc05 label 50
def linear_img(p, plt):
    tiles, w, h = img_tiles_pay(p)
    im = Image.new("RGB", (w * 8, h * 8), (40, 40, 52))
    px = im.load()
    for ti, t in enumerate(tiles):
        tx, ty = ti % w, ti // w
        for i in range(64):
            c = t[i]
            if c:
                px[tx * 8 + i % 8, ty * 8 + i // 8] = plt[c]
    return im
plt05 = parse_plt_pay(subpay(a05, 4))
panels.append(("arc05_50", linear_img(subpay(a05, 50), plt05)))
panels.append(("arc05_31", linear_img(subpay(a05, 31), plt05)))

W = 300
total = sum(p[1].height + 16 for p in panels)
sheet = Image.new("RGB", (W, total), (25, 25, 33))
dr = ImageDraw.Draw(sheet)
y = 0
for name, im in panels:
    dr.text((2, y + 2), name, fill=(255, 220, 80))
    sheet.paste(im, (72, y + 2))
    y += im.height + 16
sheet = sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST)
sheet.save(os.path.join(OUT, "final_verify.png"))
print("saved final_verify.png")
