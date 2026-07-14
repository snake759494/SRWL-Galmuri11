"""Replace SRWL hangul glyphs (2350) with Galmuri11, patch arm9."""
import os
from PIL import Image, ImageFont, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "out")
FONT = r"D:\nds\files (1)\Galmuri11.ttf"
HG_CELL0 = 0x61EA0       # first hangul cell (code halfword at +0, pixels at +2)
N_HG = 2350

arm9 = bytearray(open(os.path.join(OUT, "arm9_L.bin"), "rb").read())

# KS X 1001 hangul syllables in order
hangul = []
for row in range(0x30, 0x49):
    for cell in range(0x21, 0x7F):
        try:
            hangul.append(bytes([0x80 | row, 0x80 | cell]).decode("euc-kr"))
        except UnicodeDecodeError:
            pass
assert len(hangul) == 2350, len(hangul)

font = ImageFont.truetype(FONT, 12)

def render_glyph(ch):
    """Return 12 rows of (b0, b1) engine-format bytes; box 16x12, ink cols0-10 rows1-11."""
    img = Image.new("L", (24, 20), 0)
    ImageDraw.Draw(img).text((4, 4), ch, font=font, fill=255)
    px = img.load()
    bb = img.getbbox()
    assert bb, f"empty glyph {ch}"
    assert bb[0] >= 4 and bb[2] <= 15 + 1 and bb[1] >= 5 and bb[3] <= 16, f"{ch} bbox {bb}"
    rows = []
    for r in range(12):
        y = 4 + r
        b0 = b1 = 0
        for x in range(16):
            v = px[4 + x, y]
            assert v in (0, 255), f"antialiased pixel in {ch}"
            if v:
                if x < 8:
                    b0 |= 0x80 >> x
                else:
                    b1 |= 0x80 >> (x - 8)
        rows.append((b0, b1))
    return rows

# patch
stats_maxcol = 0
for k, ch in enumerate(hangul):
    off = HG_CELL0 + k * 26
    rows = render_glyph(ch)
    for r, (b0, b1) in enumerate(rows):
        arm9[off + 2 + r * 2] = b0
        arm9[off + 3 + r * 2] = b1

open(os.path.join(OUT, "arm9_L_galmuri.bin"), "wb").write(arm9)
print("patched arm9 written:", len(arm9))

# ---- verification: re-extract every hangul cell and compare to fresh render ----
bad = 0
for k, ch in enumerate(hangul):
    off = HG_CELL0 + k * 26
    want = render_glyph(ch)
    got = [(arm9[off + 2 + r * 2], arm9[off + 3 + r * 2]) for r in range(12)]
    if want != got:
        bad += 1
print("verify mismatches:", bad)

# code halfwords untouched?
orig = open(os.path.join(OUT, "arm9_L.bin"), "rb").read()
diffs_outside = 0
for i in range(len(arm9)):
    if arm9[i] != orig[i]:
        rel = i - HG_CELL0
        if not (0 <= rel < N_HG * 26 and rel % 26 >= 2):
            diffs_outside += 1
print("modified bytes outside allowed pixel areas:", diffs_outside)
