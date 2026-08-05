"""Korean text redrawing toolkit for 4bpp indexed game images.

Works on index grids (list of rows of palette indices) decoded from IMG tiles.
Renders Galmuri text pixel-perfect with optional outline, using existing
palette indices so no palette changes are needed.
"""
import os, struct, sys
from PIL import Image, ImageFont, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG

GALMURI11 = _CFG.GALMURI
_fonts = {}

def get_font(px):
    """Galmuri11 is pixel-perfect at ppem 12. For other sizes we scale."""
    key = px
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(GALMURI11, px)
    return _fonts[key]

def render_text_mask(text, ppem=12):
    """Render text -> binary mask (list of rows of 0/1) tightly cropped."""
    img = Image.new("L", (16 * len(text) + 32, ppem * 3), 0)
    ImageDraw.Draw(img).text((8, 8), text, font=get_font(ppem), fill=255)
    bb = img.getbbox()
    if bb is None:
        return [[0]]
    img = img.crop(bb)
    w, h = img.size
    px = img.load()
    return [[1 if px[x, y] >= 128 else 0 for x in range(w)] for y in range(h)]

def img_to_grid(payload):
    """IMG payload -> (grid, ver, w_tiles, h_tiles). grid[y][x] = palette index."""
    assert payload[:3] == b"IMG"
    ver = payload[3]
    w, h = struct.unpack_from("<HH", payload, 4)
    bpp8 = ver == 1
    tsz = 64 if bpp8 else 32
    grid = [[0] * (w * 8) for _ in range(h * 8)]
    pos = 8
    for ty in range(h):
        for tx in range(w):
            tile = payload[pos : pos + tsz]
            pos += tsz
            for i in range(64):
                if bpp8:
                    c = tile[i]
                else:
                    b = tile[i // 2]
                    c = (b & 0xF) if (i % 2 == 0) else (b >> 4)
                grid[ty * 8 + i // 8][tx * 8 + i % 8] = c
    return grid, ver, w, h

def grid_to_img(grid, ver, w, h):
    """grid -> IMG payload bytes."""
    bpp8 = ver == 1
    out = bytearray(b"IMG" + bytes([ver]) + struct.pack("<HH", w, h))
    for ty in range(h):
        for tx in range(w):
            if bpp8:
                for i in range(64):
                    out.append(grid[ty * 8 + i // 8][tx * 8 + i % 8])
            else:
                for i in range(0, 64, 2):
                    lo = grid[ty * 8 + i // 8][tx * 8 + i % 8] & 0xF
                    hi = grid[ty * 8 + (i + 1) // 8][tx * 8 + (i + 1) % 8] & 0xF
                    out.append(lo | (hi << 4))
    return bytes(out)

def erase_rect(grid, x0, y0, x1, y1, bg):
    for y in range(y0, y1):
        for x in range(x0, x1):
            grid[y][x] = bg

def draw_mask(grid, mask, ox, oy, fg, outline=None, bg_protect=None):
    """Stamp mask at (ox,oy) with palette index fg; optional 1px outline index."""
    h = len(mask); w = len(mask[0])
    if outline is not None:
        for y in range(h):
            for x in range(w):
                if mask[y][x]:
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            yy, xx = oy + y + dy, ox + x + dx
                            if 0 <= yy < len(grid) and 0 <= xx < len(grid[0]):
                                if grid[yy][xx] != fg:
                                    grid[yy][xx] = outline
    for y in range(h):
        for x in range(w):
            if mask[y][x]:
                yy, xx = oy + y, ox + x
                if 0 <= yy < len(grid) and 0 <= xx < len(grid[0]):
                    grid[yy][xx] = fg
