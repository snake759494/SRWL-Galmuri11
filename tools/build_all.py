# -*- coding: utf-8 -*-
"""One-shot build: source ROM -> font+image patched ROM -> xdelta.

Usage (from anywhere):
    set SRWL_SRC_ROM=C:\\path\\to\\SRWL_K_v0.9.1.nds     (Windows)
    export SRWL_SRC_ROM=/path/to/SRWL_K_v0.9.1.nds       (macOS/Linux)
    python tools/build_all.py

Outputs (under build/, override with SRWL_BUILD_DIR):
    build/SRWL_Galmuri11.nds        font-only ROM (intermediate)
    build/SRWL_Galmuri11_IMG.nds    final font+image ROM
    build/SRWL_K_v0.9.1_Galmuri11_IMG.xdelta   patch (if xdelta3 available)

Requires: Python 3, Pillow (pip install pillow). xdelta3 optional (for the .xdelta).
Korean serif/gothic pixel styles use Windows 바탕/굴림; on other OSes set
SRWL_BATANG / SRWL_GULIM to any Korean Myeongjo/Gothic font (output differs slightly).
"""
import os, sys, subprocess, hashlib, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config as _CFG

# ordered pipeline; each is a standalone script run as a subprocess
STEPS = [
    ("extract arm9 (BLZ decompress)", "blz.py"),
    ("patch hangul font into arm9", "build_font.py"),
    ("recompress arm9 (tight-fit BLZ)", "blz_fit.py"),
    ("assemble font-only ROM", "build_rom.py"),
    ("build scenario titles + time cards + intro + credits", "build_credits.py"),
    ("build spirit-command cut-ins", "build_spirits4.py"),
    ("build HUD dictionary sheets + critical + revert save/terrain", "build_hud.py"),
    ("build world-map area names", "add_area.py"),
    ("build battle labels (arc05)", "build_arc05.py"),
    ("blank critical banner leftover tile (SCR#10 remap)", "fix_crit_scr.py"),
    ("assemble final font+image ROM", "assemble_images.py"),
]

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()

def main():
    if not os.path.isfile(_CFG.SRC_ROM):
        sys.exit(f"[!] source ROM not found: {_CFG.SRC_ROM}\n"
                 f"    Set SRWL_SRC_ROM to your SRW L Korean-patch v0.9.1 ROM.")
    if not os.path.isfile(_CFG.GALMURI):
        sys.exit(f"[!] Galmuri11 font not found: {_CFG.GALMURI}")
    print(f"source ROM : {_CFG.SRC_ROM}  (md5 {md5(_CFG.SRC_ROM)})")
    print(f"build dir  : {_CFG.BUILD}\n")
    for i, (desc, script) in enumerate(STEPS, 1):
        print(f"[{i}/{len(STEPS)}] {desc}  ({script})")
        r = subprocess.run([sys.executable, os.path.join(HERE, script)], cwd=HERE)
        if r.returncode != 0:
            sys.exit(f"[!] step failed: {script}")
    print(f"\nfont ROM   : {_CFG.FONT_ROM}  (md5 {md5(_CFG.FONT_ROM)})")
    print(f"final ROM  : {_CFG.OUT_ROM}  (md5 {md5(_CFG.OUT_ROM)})")

    # optional: produce xdelta patches if xdelta3 is on PATH
    xd = shutil.which("xdelta3") or shutil.which("xdelta")
    if xd:
        for base, out, name in (
            (_CFG.SRC_ROM, _CFG.FONT_ROM, "SRWL_K_v0.9.1_Galmuri11.xdelta"),
            (_CFG.SRC_ROM, _CFG.OUT_ROM, "SRWL_K_v0.9.1_Galmuri11_IMG.xdelta"),
        ):
            dst = os.path.join(_CFG.BUILD, name)
            subprocess.run([xd, "-e", "-f", "-s", base, out, dst])
            print(f"xdelta     : {dst}")
    else:
        print("\n(xdelta3 not found on PATH; skipping .xdelta generation)")
        print(" install xdelta3 and run:")
        print(f'   xdelta3 -e -f -s "{_CFG.SRC_ROM}" "{_CFG.OUT_ROM}" "{os.path.join(_CFG.BUILD, "SRWL_K_v0.9.1_Galmuri11_IMG.xdelta")}"')

if __name__ == "__main__":
    main()
