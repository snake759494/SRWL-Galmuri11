"""ECD decompressor ported from SRW K/L arm9 @0x200E8AC (LZSS, 1KB ring)."""

def ecd_decompress(src: bytes) -> bytes:
    assert src[:3] == b"ECD", "not ECD"
    version = src[3]
    nraw = int.from_bytes(src[4:8], "big")
    total = int.from_bytes(src[8:12], "big")
    outsz = int.from_bytes(src[12:16], "big")
    if version == 0:
        return bytes(src[16 : 16 + outsz])
    ring = bytearray(1024)
    pos = 0x3BE
    out = bytearray()
    p = 16
    end = 16 + total
    # raw prefix
    for _ in range(nraw):
        out.append(src[p]); p += 1
    ctrl = 0
    while len(out) < outsz:
        ctrl >>= 1
        if not (ctrl & 0x100):
            if p >= end: break
            ctrl = src[p] | 0xFF00; p += 1
        if ctrl & 1:
            if p >= end: break
            b = src[p]; p += 1
            out.append(b)
            ring[pos] = b; pos = (pos + 1) & 0x3FF
        else:
            if p + 1 >= end: break
            b1, b2 = src[p], src[p + 1]; p += 2
            length = (b2 & 0x3F) + 3
            off = b1 | ((b2 & 0xC0) << 2)
            for i in range(length):
                b = ring[(off + i) & 0x3FF]
                out.append(b)
                ring[pos] = b; pos = (pos + 1) & 0x3FF
    return bytes(out)


if __name__ == "__main__":
    import os
    OUT = os.path.join(os.path.dirname(__file__), "out")
    blob = open(os.path.join(OUT, "srwk_state.bin"), "rb").read()
    RAM = blob[0xC6C0 : 0xC6C0 + 0x400000]
    src = RAM[0x43CF4 : 0x43CF4 + 16 + 436]
    dec = ecd_decompress(src)
    print("decompressed:", len(dec), "expect 2056")
    print("head:", dec[:16].hex(" "))
    # sanity: emitted count vs header
    tail_zeros = dec.count(0)
    print("zeros:", tail_zeros)
