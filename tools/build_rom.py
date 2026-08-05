import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from blz import blz_decompress

OUT = _CFG.OUT_DIR
SRC_ROM = _CFG.SRC_ROM
DST_ROM = _CFG.FONT_ROM

rom = bytearray(open(SRC_ROM, "rb").read())
arm9_new = open(os.path.join(OUT, "arm9_L_galmuri_blz.bin"), "rb").read()
patched_plain = open(os.path.join(OUT, "arm9_L_galmuri.bin"), "rb").read()

A9_OFF, A9_SZ = 0x4000, 351628
assert len(arm9_new) == A9_SZ

orig_arm9 = bytes(rom[A9_OFF : A9_OFF + A9_SZ])
rom[A9_OFF : A9_OFF + A9_SZ] = arm9_new

# verification 1: diff confined to arm9 stream region
first = last = None
for i in range(len(rom)):
    if rom[i] != open(SRC_ROM, "rb").read()[i:i+1][0] if False else False:
        pass  # too slow; do block compare below
orig = open(SRC_ROM, "rb").read()
assert orig[:A9_OFF] == bytes(rom[:A9_OFF]), "header changed!"
assert orig[A9_OFF + A9_SZ :] == bytes(rom[A9_OFF + A9_SZ :]), "data after arm9 changed!"
# secure area (first 0x4001 bytes of arm9) unchanged
assert orig[A9_OFF : A9_OFF + 0x4001] == bytes(rom[A9_OFF : A9_OFF + 0x4001]), "secure area changed!"
# footer unchanged
assert orig[A9_OFF + A9_SZ - 8 : A9_OFF + A9_SZ] == bytes(rom[A9_OFF + A9_SZ - 8 : A9_OFF + A9_SZ]), "footer changed!"
print("ROM diff confined to arm9 compressed stream ✓")

# verification 2: end-to-end: extract arm9 from new ROM, decompress, compare
dec = blz_decompress(bytes(rom[A9_OFF : A9_OFF + A9_SZ]))
assert dec == patched_plain, "end-to-end decompress mismatch!"
print("end-to-end arm9 decompress == patched plaintext ✓")

# verification 3: hangul glyphs in decompressed == Galmuri renders (spot re-verify all)
from PIL import Image, ImageFont, ImageDraw
FONT = _CFG.GALMURI
font = ImageFont.truetype(FONT, 12)
hangul = []
for row in range(0x30, 0x49):
    for cell in range(0x21, 0x7F):
        try:
            hangul.append(bytes([0x80 | row, 0x80 | cell]).decode("euc-kr"))
        except UnicodeDecodeError:
            pass
HG_CELL0 = 0x61EA0
bad = 0
for k, ch in enumerate(hangul):
    img = Image.new("L", (24, 20), 0)
    ImageDraw.Draw(img).text((4, 4), ch, font=font, fill=255)
    px = img.load()
    off = HG_CELL0 + k * 26 + 2
    for r in range(12):
        b0 = b1 = 0
        for x in range(16):
            if px[4 + x, 4 + r]:
                if x < 8: b0 |= 0x80 >> x
                else: b1 |= 0x80 >> (x - 8)
        if dec[off + r * 2] != b0 or dec[off + r * 2 + 1] != b1:
            bad += 1
print(f"glyph bitmap verification: {bad} mismatched rows (expect 0)")
assert bad == 0

open(DST_ROM, "wb").write(rom)
print("written:", DST_ROM, len(rom))
