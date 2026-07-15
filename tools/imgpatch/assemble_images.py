# -*- coding: utf-8 -*-
"""Assemble image-patched ROM from generated resources."""
import os, sys, pickle, struct
sys.path.insert(0, os.path.dirname(__file__))
from imglib import get_sub, payload, ARCS, subfiles, rom_data
from rebuild import rebuild_rom, wrap_ecd0
from ecd import ecd_decompress

SCRATCH = os.path.dirname(__file__)
STATE = os.path.join(SCRATCH, "state")
OUT_ROM = r"D:\nds\roms\SRWL\Super Robot Wars L K v0.9.1 - Galmuri11-IMG.nds"

titles = pickle.load(open(os.path.join(STATE, "newres", "titles_tc.pkl"), "rb"))
spirits = pickle.load(open(os.path.join(STATE, "newres", "spirits.pkl"), "rb"))
arc05_new = pickle.load(open(os.path.join(STATE, "newres", "arc05.pkl"), "rb"))
hud05_path = os.path.join(STATE, "newres", "hud05.pkl")
if os.path.exists(hud05_path):
    arc05_new.update(pickle.load(open(hud05_path, "rb")))

def make_replacement(arc, idx, new_payload):
    raw = get_sub(arc, idx)
    if raw[:3] == b"ECD":
        return wrap_ecd0(new_payload)
    return new_payload

repl = {"arc03": {}, "arc05": {}}
for idx, pay in {**titles, **spirits}.items():
    repl["arc03"][idx] = make_replacement("arc03", idx, pay)
for idx, pay in arc05_new.items():
    repl["arc05"][idx] = make_replacement("arc05", idx, pay)

print("arc03 replacements:", len(repl["arc03"]), "arc05:", len(repl["arc05"]))
total, moved = rebuild_rom(repl, OUT_ROM)
print("ROM written:", total)

# ---- verification: re-extract and compare ----
import importlib
import imglib
rom2 = open(OUT_ROM, "rb").read()

def subfiles2(name):
    base = None
    fat_off = struct.unpack_from("<I", rom2, 0x48)[0]
    fat_size = struct.unpack_from("<I", rom2, 0x4C)[0]
    # find arc file by matching name via original order: use path-independent trick:
    # original ARCS order by base offset; new FAT entries in same file-id order.
    # file ids: arc02..arc07 = consecutive; find by size ordering instead:
    return None

# simpler: locate new arc bases via FAT (file order preserved: match by original fat index)
orig = rom_data()
fat_off = struct.unpack_from("<I", orig, 0x48)[0]
nfiles = struct.unpack_from("<I", orig, 0x4C)[0] // 8
name_by_fid = {}
for fid in range(nfiles):
    st, en = struct.unpack_from("<II", orig, fat_off + fid * 8)
    for nm, (b, s) in ARCS.items():
        if st == b:
            name_by_fid[fid] = nm
bad = 0
for fid, nm in name_by_fid.items():
    if nm not in repl or not repl[nm]:
        continue
    st2, en2 = struct.unpack_from("<II", rom2, fat_off + fid * 8)
    blob = rom2[st2:en2]
    first = struct.unpack_from("<I", blob, 0)[0]
    n = first // 4
    offs = list(struct.unpack_from(f"<{n}I", blob, 0)) + [len(blob)]
    for idx, want in repl[nm].items():
        got = blob[offs[idx] : offs[idx] + len(want)]
        if bytes(got) != bytes(want):
            bad += 1
            print("MISMATCH", nm, idx)
        # decode check for ECD-wrapped
        if want[:3] == b"ECD":
            dec = ecd_decompress(bytes(want))
            assert dec[:3] in (b"IMG", b"SCR"), (nm, idx, dec[:4])
print("verify mismatches:", bad)
