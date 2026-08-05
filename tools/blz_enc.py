"""Backward-LZ (BLZ) encoder for NDS arm9, mirroring the game's decoder at footer semantics.

Decoder semantics (from blz.py):
  reads backward from end-hdr_len; flag byte then 8 tokens (MSB first);
  flag bit 1 -> backref: pair (high<<8|low), len=(pair>>12)+3 (3..18),
  disp=(pair&0xFFF)+3 (3..4098); copy out[dst-1] = out[dst-1+disp] descending.
  flag bit 0 -> literal byte.
  stops when dst reaches cstart (all output written).
"""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as _CFG
from collections import defaultdict

MINLEN, MAXLEN = 3, 18
MINDISP, MAXDISP = 3, 0x1002


def blz_encode_stream(data: bytes, verbose=False) -> bytes:
    """Encode `data` (the tail after the raw head) for backward decoding.
    Returns the stream bytes as they appear in the file (low addresses first),
    i.e. the decoder reads them from the END of this block backwards."""
    R = data[::-1]
    n = len(R)
    # hash chains on 3-byte keys
    heads = defaultdict(list)
    tokens = []  # decode-order tokens: ('lit', b) or ('ref', len, disp)
    i = 0
    CAND = 96

    def find(i):
        if i + MINLEN > n:
            return 0, 0
        key = R[i : i + 3]
        best_l, best_d = 0, 0
        lim = min(MAXLEN, n - i)
        for j in reversed(heads[key]):
            d = i - j
            if d > MAXDISP:
                break
            if d < MINDISP:
                continue
            # extend
            l = 3
            while l < lim and R[j + l] == R[i + l]:
                l += 1
            if l > best_l:
                best_l, best_d = l, d
                if l == lim:
                    break
        return best_l, best_d

    def push(i):
        if i + 3 <= n:
            key = R[i : i + 3]
            h = heads[key]
            h.append(i)
            if len(h) > CAND:
                del h[: len(h) - CAND]

    while i < n:
        l, d = find(i)
        if l >= MINLEN:
            # lazy: check i+1
            l2, d2 = find(i + 1) if i + 1 < n else (0, 0)
            if l2 > l + 1:
                tokens.append(("lit", R[i]))
                push(i)
                i += 1
                continue
            tokens.append(("ref", l, d))
            for k in range(l):
                push(i + k)
            i += l
        else:
            tokens.append(("lit", R[i]))
            push(i)
            i += 1

    # serialize in decode order: groups of 8 tokens, flag byte first
    out = bytearray()  # decode-order byte sequence
    for g in range(0, len(tokens), 8):
        grp = tokens[g : g + 8]
        flag = 0
        for bi, t in enumerate(grp):
            if t[0] == "ref":
                flag |= 0x80 >> bi
        out.append(flag)
        for t in grp:
            if t[0] == "lit":
                out.append(t[1])
            else:
                _, l, d = t
                pair = ((l - 3) << 12) | (d - 3)
                out.append(pair >> 8)   # decoder reads high byte first
                out.append(pair & 0xFF)
    # file order = reverse of decode order
    return bytes(out[::-1])


def build_arm9(patched: bytes, orig_comp_len_total: int, total_size: int, cstart: int, hdr_len=8):
    """Assemble arm9 file of exactly total_size bytes."""
    raw_head = patched[:cstart]
    stream = blz_encode_stream(patched[cstart:])
    budget = total_size - cstart - hdr_len
    print(f"stream={len(stream)} budget={budget} margin={budget-len(stream)}")
    if len(stream) > budget:
        return None, len(stream), budget
    pad = bytes(budget - len(stream))
    extra = len(patched) - total_size
    info = (hdr_len << 24) | (total_size - cstart)  # comp region incl footer
    footer = struct.pack("<II", info, extra)
    arm9 = raw_head + pad + stream + footer
    assert len(arm9) == total_size
    return bytes(arm9), len(stream), budget


if __name__ == "__main__":
    OUT = _CFG.OUT_DIR
    patched = open(os.path.join(OUT, "arm9_L_galmuri.bin"), "rb").read()
    TOTAL = 351628
    CSTART = 0x4001
    arm9, sl, budget = build_arm9(patched, None, TOTAL, CSTART)
    if arm9 is None:
        print("OVER BUDGET")
    else:
        open(os.path.join(OUT, "arm9_L_galmuri_blz.bin"), "wb").write(arm9)
        # roundtrip verify with our decoder
        from blz import blz_decompress
        dec = blz_decompress(arm9)
        print("roundtrip equal:", dec == patched)
