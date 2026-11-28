#!/usr/bin/env python3
"""Non-blank pixel verification for the session-55 captures (the repo
convention: per-image grayscale variance must exceed 30 — a blank/near-
blank capture fails)."""
import sys
import glob
import struct
import zlib

def png_grayscale_variance(path):
    with open(path, "rb") as f:
        data = f.read()
    # minimal PNG parse: IHDR + first IDAT (RGB8 assumed)
    pos = 8
    w = h = None
    idat = b""
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos+4])[0]
        ctype = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+length]
        if ctype == b"IHDR":
            w, h, depth, color = struct.unpack(">IIBB", chunk[:10])
            if depth != 8 or color != 2:
                return None
        elif ctype == b"IDAT":
            idat += chunk
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = w * 3
    px = []
    step = max(1, (h // 200))  # sample rows
    for y in range(0, h, step):
        row = raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
        for x in range(0, stride, 9):
            r, g, b = row[x:x+3]
            px.append(0.299 * r + 0.587 * g + 0.114 * b)
    n = len(px)
    mean = sum(px) / n
    var = sum((p - mean) ** 2 for p in px) / n
    return var

ok = True
for f in sorted(glob.glob("docs/screenshots/*_session55.png")):
    v = png_grayscale_variance(f)
    status = "PASS" if (v is not None and v > 30) else "FAIL"
    if status == "FAIL":
        ok = False
    print(f"{status} {f} variance={v and round(v, 1)}")
sys.exit(0 if ok else 1)
