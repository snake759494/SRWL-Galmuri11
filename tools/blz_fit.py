"""Tight-fit BLZ builder: raw head grows until stream ends exactly at cstart."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(__file__))
from blz_enc import blz_encode_stream, MINLEN
from blz import blz_decompress

OUT = os.path.join(os.path.dirname(__file__), "out")
TOTAL = 351628
HDR = 8

def tokenize(data):
    """Same as blz_encode_stream but returns token list (decode order)."""
    from collections import defaultdict
    R = data[::-1]
    n = len(R)
    heads = defaultdict(list)
    tokens = []
    CAND = 96
    MAXLEN, MAXDISP, MINDISP = 18, 0x1002, 3

    def find(i):
        if i + 3 > n:
            return 0, 0
        best_l, best_d = 0, 0
        lim = min(MAXLEN, n - i)
        for j in reversed(heads[R[i:i+3]]):
            d = i - j
            if d > MAXDISP:
                break
            if d < MINDISP:
                continue
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
            h = heads[R[i:i+3]]
            h.append(i)
            if len(h) > CAND:
                del h[: len(h) - CAND]

    i = 0
    while i < n:
        l, d = find(i)
        if l >= 3:
            l2, d2 = find(i + 1) if i + 1 < n else (0, 0)
            if l2 > l + 1:
                tokens.append(("lit", R[i])); push(i); i += 1
                continue
            tokens.append(("ref", l, d, i))  # keep i for de-opt
            for k in range(l):
                push(i + k)
            i += l
        else:
            tokens.append(("lit", R[i])); push(i); i += 1
    return tokens, R

def serialized_len(tokens):
    n = 0
    for g in range(0, len(tokens), 8):
        n += 1
        for t in tokens[g : g + 8]:
            n += 1 if t[0] == "lit" else 2
    return n

def serialize(tokens):
    out = bytearray()
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
                pair = ((t[1] - 3) << 12) | (t[2] - 3)
                out.append(pair >> 8); out.append(pair & 0xFF)
    return bytes(out[::-1])

def deopt_to_size(tokens, R, target):
    """Inflate stream to exactly target bytes by converting early refs to literals.
    Early tokens = decode-order first = written at output TOP where gap is huge."""
    cur = serialized_len(tokens)
    idx = 0
    while cur < target and idx < len(tokens):
        t = tokens[idx]
        if t[0] == "ref":
            _, l, d, i = t
            lits = [("lit", R[i + k]) for k in range(l)]
            cand = tokens[:idx] + lits + tokens[idx + 1 :]
            newlen = serialized_len(cand)
            if newlen <= target:
                tokens = cand
                cur = newlen
                idx += l
                continue
        idx += 1
    return tokens, cur

patched = open(os.path.join(OUT, "arm9_L_galmuri.bin"), "rb").read()

c = 0x4001
for it in range(12):
    data = patched[c:]
    tokens, R = tokenize(data)
    slen = serialized_len(tokens)
    budget = TOTAL - HDR - c
    print(f"iter{it}: c=0x{c:X} stream={slen} budget={budget} diff={budget-slen}")
    if slen > budget:
        c = TOTAL - HDR - slen  # need larger raw head
        continue
    if slen == budget:
        break
    # slack: try to consume by de-optimization
    tokens, newlen = deopt_to_size(tokens, R, budget)
    print(f"   deopt -> {newlen} (target {budget})")
    if newlen == budget:
        break
    # couldn't hit exactly (rare): shift c up by remaining slack and retry
    c += budget - newlen
else:
    raise SystemExit("did not converge")

stream = serialize(tokens)
assert len(stream) == TOTAL - HDR - c
info = (HDR << 24) | (TOTAL - c)
extra = len(patched) - TOTAL
arm9 = patched[:c] + stream + struct.pack("<II", info, extra)
assert len(arm9) == TOTAL

# verify: full in-place simulation
obuf = bytearray(len(patched))
obuf[:TOTAL] = arm9
src = TOTAL - HDR
dst = len(patched)
end = c
min_gap = 1 << 30
ok = True
while src > end and dst > end:
    src -= 1
    flags = obuf[src]
    for _ in range(8):
        if src <= end or dst <= end:
            break
        if flags & 0x80:
            src -= 2
            if dst - src < 0:
                ok = False
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
        min_gap = min(min_gap, dst - src)
        flags = (flags << 1) & 0xFF
print(f"sim: end src=0x{src:X} dst=0x{dst:X} (end=0x{end:X}) min_gap={min_gap}")
print("sim output equals patched:", bytes(obuf) == patched)
dec = blz_decompress(arm9)
print("decoder roundtrip:", dec == patched)
open(os.path.join(OUT, "arm9_L_galmuri_blz.bin"), "wb").write(arm9)
print("written, size", len(arm9))
