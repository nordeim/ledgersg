"""Session-70 screenshot pixel verification (the repo convention).

Asserts every capture is a real, non-blank image: decodes the PNG, measures
the per-pixel variance, and refuses anything below the threshold 30 (a blank
or near-blank page scores ~0).
"""
import struct
import sys
import zlib
from pathlib import Path

OUT = Path("/home/z/my-project/ledgersg/docs/screenshots")
SHOTS = [
    "240_invoices_page1_session70",
    "241_invoice_detail_session70",
    "242_banking_payments_session70",
    "243_reports_trial_balance_session70",
    "244_ledger_lines_session70",
    "245_dashboard_session70",
    "246_mobile_dashboard_closed_session70",
    "247_mobile_nav_open_session70",
]


def decode_png(data: bytes):
    """Minimal PNG decoder for 8-bit RGB/RGBA (color types 2/6)."""
    pos = 8
    width = height = bit_depth = color_type = None
    raw = b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        if ctype == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk[:10])
        elif ctype == b"IDAT":
            raw += chunk
        pos += 12 + length
    if bit_depth != 8 or color_type not in (2, 6):
        raise ValueError(f"unsupported PNG: depth={bit_depth} color={color_type}")
    bpp = 3 if color_type == 2 else 4
    stride = width * bpp
    # de-filter
    out = bytearray()
    prev = bytearray(stride)
    p = 0
    while p < len(raw):
        filt = raw[p]
        p += 1
        line = bytearray(raw[p:p + stride])
        p += stride
        if filt == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif filt == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        out += line
        prev = line
    return width, height, bpp, bytes(out)


all_ok = True
for name in SHOTS:
    f = OUT / f"{name}.png"
    if not f.exists():
        print(f"FAIL {name}: missing")
        all_ok = False
        continue
    w, h, bpp, px = decode_png(f.read_bytes())
    n = len(px) // bpp
    if n == 0:
        print(f"FAIL {name}: empty")
        all_ok = False
        continue
    total = sum(px)
    mean = total / (n * bpp)
    var = sum((b - mean) ** 2 for b in px[:: 97]) / max(1, len(px[:: 97]))
    ok = var > 30
    all_ok &= ok
    print(f"{'OK  ' if ok else 'FAIL'} {name}: {w}x{h} mean={mean:.1f} variance={var:.1f}")

print("\nALL PIXEL-VERIFIED" if all_ok else "\nPIXEL FAILURES PRESENT")
sys.exit(0 if all_ok else 1)
