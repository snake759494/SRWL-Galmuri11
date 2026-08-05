"""Compose IMG+SCR tilemap screens."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from imglib import get_sub, payload, parse_plt
from PIL import Image

def parse_scr(p):
    assert p[:3] == b"SCR"
    w, h = p[5], p[6]
    entries = list(struct.unpack_from(f"<{w*h}H", p, 8))
    return w, h, entries

def img_tiles(p):
    """IMG payload -> list of 8x8 tiles (each row-major index list)."""
    ver = p[3]
    w, h = struct.unpack_from("<HH", p, 4)
    bpp8 = ver == 1
    tsz = 64 if bpp8 else 32
    tiles = []
    pos = 8
    for _ in range(w * h):
        t = p[pos : pos + tsz]
        pos += tsz
        px = []
        for i in range(64):
            if bpp8:
                px.append(t[i])
            else:
                b = t[i // 2]
                px.append((b & 0xF) if i % 2 == 0 else (b >> 4))
        tiles.append(px)
    return tiles

def compose(img_payload, scr_payload, plt, plt_bank=None):
    tiles = img_tiles(img_payload)
    w, h, entries = parse_scr(scr_payload)
    im = Image.new("RGB", (w * 8, h * 8), (255, 0, 255))
    px = im.load()
    for ty in range(h):
        for tx in range(w):
            e = entries[ty * w + tx]
            tn = e & 0x3FF
            hf = (e >> 10) & 1
            vf = (e >> 11) & 1
            if tn >= len(tiles):
                continue
            t = tiles[tn]
            for i in range(64):
                x, y = i % 8, i // 8
                sx = 7 - x if hf else x
                sy = 7 - y if vf else y
                c = t[sy * 8 + sx]
                if c < len(plt):
                    px[tx * 8 + x, ty * 8 + y] = plt[c]
    return im
