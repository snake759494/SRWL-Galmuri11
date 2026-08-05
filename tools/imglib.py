"""SRWL archive/IMG/PLT decoding library."""
import struct, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from ecd import ecd_decompress
from PIL import Image

ROM = _CFG.SRC_ROM
_data = open(ROM, "rb").read()

ARCS = {
    "arc02": (0x00186638, 1929084),
    "arc03": (0x0035D5B4, 13577156),
    "arc04": (0x01050178, 1332570),
    "arc05": (0x011956D4, 23324532),
    "arc06": (0x027D3E48, 57921192),
    "arc07": (0x05F10CF0, 1204087),
}

def rom_data():
    return _data

def subfiles(name):
    base, size = ARCS[name]
    first = struct.unpack_from("<I", _data, base)[0]
    n = first // 4
    offs = list(struct.unpack_from(f"<{n}I", _data, base)) + [size]
    return [(i, base + offs[i], offs[i + 1] - offs[i]) for i in range(n)]

def get_sub(name, i):
    subs = subfiles(name)
    _, off, sz = subs[i]
    return _data[off : off + sz]

def payload(raw):
    """Return decompressed resource payload (follow ECD)."""
    if raw[:3] == b"ECD" and len(raw) >= 16:
        try:
            return ecd_decompress(raw)
        except Exception:
            return None
    return bytes(raw)

def parse_plt(p):
    if p is None or p[:3] != b"PLT":
        return None
    n = struct.unpack_from("<I", p, 4)[0]
    cols = []
    for i in range(min(n, (len(p) - 8) // 2)):
        v = struct.unpack_from("<H", p, 8 + i * 2)[0]
        r = (v & 31) << 3
        g = ((v >> 5) & 31) << 3
        b = ((v >> 10) & 31) << 3
        cols.append((r | r >> 5, g | g >> 5, b | b >> 5))
    return cols

DEFAULT16 = [(i * 17, i * 17, i * 17) for i in range(16)]

def parse_img(p, plt=None):
    """Decode IMG payload -> PIL RGB image (tiles laid w x h)."""
    if p is None or p[:3] != b"IMG":
        return None
    ver = p[3]
    w, h = struct.unpack_from("<HH", p, 4)
    if w == 0 or h == 0 or w > 128 or h > 128:
        return None
    bpp8 = ver == 1
    tsz = 64 if bpp8 else 32
    need = 8 + w * h * tsz
    if len(p) < need:
        return None
    if plt is None:
        plt = [(i, i, i) for i in range(256)] if bpp8 else DEFAULT16
    img = Image.new("RGB", (w * 8, h * 8), (0, 0, 0))
    px = img.load()
    pos = 8
    for ty in range(h):
        for tx in range(w):
            tile = p[pos : pos + tsz]
            pos += tsz
            for i in range(64):
                if bpp8:
                    c = tile[i]
                else:
                    b = tile[i // 2]
                    c = (b & 0xF) if (i % 2 == 0) else (b >> 4)
                x = tx * 8 + i % 8
                y = ty * 8 + i // 8
                if c < len(plt):
                    px[x, y] = plt[c]
    return img
