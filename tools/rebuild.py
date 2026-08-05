"""Rebuild arc archives and ROM with replaced subfiles."""
import struct, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from imglib import ARCS, subfiles

ROM = _CFG.FONT_ROM  # base = galmuri ROM

def wrap_ecd0(payload: bytes) -> bytes:
    n = len(payload)
    hdr = b"ECD\x00" + struct.pack(">I", 0) + struct.pack(">I", n) + struct.pack(">I", n)
    return hdr + payload

def rebuild_arc(arc_name, replacements, data):
    """replacements: {sub_idx: new_subfile_bytes}. Returns new arc bytes."""
    subs = subfiles(arc_name)
    n = len(subs)
    parts = []
    for i, off, sz in subs:
        if i in replacements:
            parts.append(replacements[i])
        else:
            parts.append(data[off : off + sz])
    # offset table: n entries, first = n*4
    offs = []
    pos = n * 4
    for p in parts:
        offs.append(pos)
        pos += len(p)
        pos = (pos + 3) & ~3  # 4-align like original (offsets all 4-aligned)
    blob = bytearray(struct.pack(f"<{n}I", *offs))
    for p, o in zip(parts, offs):
        blob.extend(b"\x00" * (o - len(blob)))
        blob.extend(p)
    return bytes(blob)

def crc16(buf):
    crc = 0xFFFF
    for b in buf:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc

def rebuild_rom(arc_replacements, out_path):
    """arc_replacements: {arc_name: {sub_idx: bytes}}"""
    data = open(ROM, "rb").read()
    fat_off = struct.unpack_from("<I", data, 0x48)[0]
    fat_size = struct.unpack_from("<I", data, 0x4C)[0]
    nfiles = fat_size // 8
    fat = [struct.unpack_from("<II", data, fat_off + i * 8) for i in range(nfiles)]

    # new content per file id (only arc files change)
    arc_fileid = {}
    for name, (base, size) in ARCS.items():
        for fid, (st, en) in enumerate(fat):
            if st == base:
                arc_fileid[fid] = name
    new_content = {}
    for fid, name in arc_fileid.items():
        if name in arc_replacements and arc_replacements[name]:
            new_content[fid] = rebuild_arc(name, arc_replacements[name], data)

    # layout: keep everything before first file intact; rewrite files in original order
    order = sorted(range(nfiles), key=lambda f: fat[f][0])
    first_start = fat[order[0]][0]
    out = bytearray(data[:first_start])
    new_fat = list(fat)
    for fid in order:
        st, en = fat[fid]
        content = new_content.get(fid, data[st:en])
        # keep original start alignment style: align 4 (original files 4-aligned)
        while len(out) % 4:
            out.append(0)
        ns = len(out)
        out.extend(content)
        new_fat[fid] = (ns, ns + len(content))
    # write FAT
    for i, (st, en) in enumerate(new_fat):
        struct.pack_into("<II", out, fat_off + i * 8, st, en)
    # header: total used size @0x80, header crc @0x15E
    struct.pack_into("<I", out, 0x80, len(out))
    struct.pack_into("<H", out, 0x15E, crc16(out[:0x15E]))
    open(out_path, "wb").write(out)
    return len(out), {f: (fat[f], new_fat[f]) for f in new_content}

if __name__ == "__main__":
    # smoke test: rebuild with no replacements -> FAT/layout identical?
    total, moved = rebuild_rom({}, os.path.join(_CFG.OUT_DIR, "rebuild_noop.nds"))
    orig = open(ROM, "rb").read()
    new = open(os.path.join(_CFG.OUT_DIR, "rebuild_noop.nds"), "rb").read()
    print("sizes:", len(orig), len(new), "identical:", orig == new)
