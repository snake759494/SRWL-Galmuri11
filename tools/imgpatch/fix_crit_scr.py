# -*- coding: utf-8 -*-
"""Blank the 9th column of SCR#10 (the ル-tail fragment) by remapping to a blank tile.
   Verify a blank tile exists and that no icon/digit is harmed."""
import os, sys, struct, pickle
sys.path.insert(0, os.path.dirname(__file__))
from imglib import get_sub, payload
from compose import img_tiles, parse_scr

STATE = os.path.join(os.path.dirname(__file__), "state")

# find a fully-blank tile index in arc05#6
p6 = payload(get_sub("arc05", 6))
tiles = img_tiles(p6)
blank = None
for i, t in enumerate(tiles):
    if not any(t):
        blank = i
        break
print("blank tile index:", blank)

# read SCR#10, remap cells (8,0) and (8,1) -> blank tile, keep pal/flip = 0
scrp = bytearray(payload(get_sub("arc05", 10)))
w, h = scrp[5], scrp[6]
print("SCR#10", w, "x", h)
def cell_off(tx, ty):
    return 8 + (ty * w + tx) * 2
for (tx, ty) in ((8, 0), (8, 1)):
    old = struct.unpack_from("<H", scrp, cell_off(tx, ty))[0]
    struct.pack_into("<H", scrp, cell_off(tx, ty), blank & 0x3FF)
    print(f"  cell({tx},{ty}): 0x{old:04X} -> tile {blank}")

# save into hud05.pkl alongside the IMG#6 replacement
hud = pickle.load(open(os.path.join(STATE, "newres", "hud05.pkl"), "rb"))
# hud is {6: img_payload}; store SCR under key 10
hud[10] = bytes(scrp)
pickle.dump(hud, open(os.path.join(STATE, "newres", "hud05.pkl"), "wb"))
print("hud05.pkl keys:", sorted(hud.keys()))
