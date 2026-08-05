# -*- coding: utf-8 -*-
"""Central configuration for the SRWL Galmuri11 patch build pipeline.

All build scripts import their paths from here, so the whole pipeline is
relocatable and reproducible on a fresh machine. Only the SOURCE ROM must be
provided by the user (it is never included in this repository).

Override any path with an environment variable:
  SRWL_SRC_ROM   path to your SRW L Korean-patch v0.9.1 ROM (input)
  SRWL_BUILD_DIR where intermediate/output files are written (default ./build)
  SRWL_BATANG    path to a Korean Myeongjo/serif TTF/TTC (default Windows 바탕)
  SRWL_GULIM     path to a Korean Gothic TTF/TTC       (default Windows 굴림)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))     # .../tools
ROOT = os.path.dirname(HERE)                           # repo root

# --- INPUT: source ROM you provide (SRW L + Korean patch v0.9.1 applied) ---
#   Expected: 134,217,728 bytes, CRC32 82804748 (the v0.9.1 patched ROM).
SRC_ROM = os.environ.get(
    "SRWL_SRC_ROM",
    os.path.join(ROOT, "source", "SRWL_K_v0.9.1.nds"),
)

# --- Build outputs (generated) ---
BUILD = os.environ.get("SRWL_BUILD_DIR", os.path.join(ROOT, "build"))
OUT_DIR = os.path.join(BUILD, "out")                   # arm9 bins + review PNGs
STATE = os.path.join(BUILD, "state")                   # resource pickles under state/newres
FONT_ROM = os.path.join(BUILD, "SRWL_Galmuri11.nds")           # font-only ROM (intermediate)
OUT_ROM = os.path.join(BUILD, "SRWL_Galmuri11_IMG.nds")        # final font+image ROM

# --- Fonts ---
GALMURI = os.path.join(ROOT, "fonts", "Galmuri11.ttf")  # bundled (SIL OFL 1.1)
# Windows system fonts used to match the original serif/gothic pixel styles.
# On non-Windows, install/point these to any Korean Myeongjo / Gothic font
# (output differs slightly; the released xdelta was built with Windows fonts).
BATANG = os.environ.get("SRWL_BATANG", r"C:\Windows\Fonts\batang.ttc")  # 바탕 (Myeongjo)
GULIM = os.environ.get("SRWL_GULIM", r"C:\Windows\Fonts\gulim.ttc")     # 굴림/돋움 (Gothic)

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.join(STATE, "newres"), exist_ok=True)
