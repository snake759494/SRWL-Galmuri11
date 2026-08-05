"""Nintendo BLZ (backward LZ) decompressor for arm9 binaries."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
import struct

def blz_decompress(comp: bytes) -> bytes:
    if len(comp) < 8:
        raise ValueError("too small")
    # strip nitrocode footer if present (dEC00621 marker)
    tail = comp
    while len(tail) >= 12 and struct.unpack_from("<I", tail, len(tail) - 12)[0] == 0xDEC00621:
        tail = tail[: len(tail) - 12]
    info, extra = struct.unpack_from("<II", tail, len(tail) - 8)
    hdr_len = info >> 24
    comp_len = info & 0xFFFFFF
    if hdr_len < 8 or hdr_len > 0x20 or comp_len > len(tail) or comp_len < hdr_len:
        raise ValueError("not BLZ")
    out_size = len(tail) + extra
    cstart = len(tail) - comp_len  # start of compressed region
    obuf = bytearray(out_size)
    obuf[: len(tail)] = tail
    src = len(tail) - hdr_len
    dst = out_size
    end = cstart
    while src > end and dst > end:
        src -= 1
        flags = obuf[src]
        for _ in range(8):
            if src <= end or dst <= end:
                break
            if flags & 0x80:
                src -= 2
                pair = (obuf[src + 1] << 8) | obuf[src]
                length = (pair >> 12) + 3
                disp = (pair & 0xFFF) + 3
                for _ in range(length):
                    dst -= 1
                    obuf[dst] = obuf[dst + disp]
            else:
                src -= 1
                dst -= 1
                obuf[dst] = obuf[src]
            flags = (flags << 1) & 0xFF
    return bytes(obuf)


if __name__ == "__main__":
    # Extract + BLZ-decompress the SRW L arm9 from the source ROM.
    A9_OFF, A9_SZ = 0x4000, 351628
    data = open(_CFG.SRC_ROM, "rb").read()
    arm9 = data[A9_OFF : A9_OFF + A9_SZ]
    try:
        dec = blz_decompress(arm9)
        print(f"L arm9: {A9_SZ} -> {len(dec)}")
    except ValueError as e:
        dec = arm9
        print(f"L arm9: not BLZ ({e}), keeping raw")
    open(os.path.join(_CFG.OUT_DIR, "arm9_L.bin"), "wb").write(dec)
    print("wrote", os.path.join(_CFG.OUT_DIR, "arm9_L.bin"))
