"""Nintendo BLZ (backward LZ) decompressor for arm9 binaries."""
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
    import os
    OUT = os.path.join(os.path.dirname(__file__), "out")
    for tag, path, size in [
        ("L", r"D:\nds\roms\SRWL\Super Robot Wars L K v0.9.1.nds", 351628),
        ("K", r"D:\nds\roms\SRWK\Super Robot Wars K.nds", 613560),
    ]:
        data = open(path, "rb").read()
        arm9 = data[0x4000 : 0x4000 + size]
        try:
            dec = blz_decompress(arm9)
            print(f"{tag}: {size} -> {len(dec)}")
        except ValueError as e:
            dec = arm9
            print(f"{tag}: not BLZ ({e}), keeping raw")
        open(os.path.join(OUT, f"arm9_{tag}.bin"), "wb").write(dec)
