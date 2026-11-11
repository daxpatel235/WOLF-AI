"""
Draws the Wolf AI app icon (the mascot's face on the app's indigo gradient) and writes:
  packaging/icons/wolfai.png      512x512
  packaging/icons/wolfai-256.png  256x256 (Linux .desktop / AppImage)
  packaging/icons/wolfai.ico      Windows (16-256 px)
  packaging/icons/wolfai.icns     macOS (128-512 px)

Pure Python, no dependencies. Run once after changing the design: python scripts/make_icons.py
"""
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "packaging" / "icons"


def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


# Shapes in unit coordinates (0..1), drawn bottom to top.
def in_rounded_rect(x, y, r=0.22, pad=0.03):
    x0, y0, x1, y1 = pad, pad, 1 - pad, 1 - pad
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def in_triangle(x, y, a, b, c):
    def side(p, q):
        return (x - q[0]) * (p[1] - q[1]) - (p[0] - q[0]) * (y - q[1])
    d1, d2, d3 = side(a, b), side(b, c), side(c, a)
    neg = d1 < 0 or d2 < 0 or d3 < 0
    pos = d1 > 0 or d2 > 0 or d3 > 0
    return not (neg and pos)


def in_ellipse(x, y, cx, cy, rx, ry):
    return ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1


BG_TOP, BG_BOTTOM = hex_rgb("#6366f1"), hex_rgb("#8b5cf6")
EAR, EAR_INNER = hex_rgb("#3a3a4a"), hex_rgb("#5a5a6e")
HEAD, SNOUT = hex_rgb("#4a4a5c"), hex_rgb("#6e6e84")
EYE, PUPIL, NOSE = hex_rgb("#ffffff"), hex_rgb("#14141c"), hex_rgb("#14141c")

LAYERS = [
    (lambda x, y: in_triangle(x, y, (0.20, 0.47), (0.27, 0.12), (0.47, 0.32)), EAR),
    (lambda x, y: in_triangle(x, y, (0.80, 0.47), (0.73, 0.12), (0.53, 0.32)), EAR),
    (lambda x, y: in_triangle(x, y, (0.26, 0.40), (0.29, 0.21), (0.40, 0.33)), EAR_INNER),
    (lambda x, y: in_triangle(x, y, (0.74, 0.40), (0.71, 0.21), (0.60, 0.33)), EAR_INNER),
    (lambda x, y: in_ellipse(x, y, 0.50, 0.57, 0.30, 0.29), HEAD),
    (lambda x, y: in_ellipse(x, y, 0.50, 0.70, 0.15, 0.11), SNOUT),
    (lambda x, y: in_ellipse(x, y, 0.385, 0.52, 0.065, 0.065), EYE),
    (lambda x, y: in_ellipse(x, y, 0.615, 0.52, 0.065, 0.065), EYE),
    (lambda x, y: in_ellipse(x, y, 0.395, 0.53, 0.032, 0.032), PUPIL),
    (lambda x, y: in_ellipse(x, y, 0.625, 0.53, 0.032, 0.032), PUPIL),
    (lambda x, y: in_ellipse(x, y, 0.50, 0.645, 0.05, 0.034), NOSE),
]


def sample(x, y):
    """RGBA of the top-most shape at (x, y)."""
    if not in_rounded_rect(x, y):
        return (0, 0, 0, 0)
    color = lerp(BG_TOP, BG_BOTTOM, (x + y) / 2)
    for test, layer_color in LAYERS:
        if test(x, y):
            color = layer_color
    return (*color, 255)


def render(size, ss=3):
    """Supersampled render; returns rows of RGBA bytes."""
    rows = []
    n = ss * ss
    for py in range(size):
        row = bytearray()
        for px in range(size):
            r = g = b = a = 0
            for sy in range(ss):
                for sx in range(ss):
                    cr, cg, cb, ca = sample((px + (sx + 0.5) / ss) / size, (py + (sy + 0.5) / ss) / size)
                    r += cr * ca
                    g += cg * ca
                    b += cb * ca
                    a += ca
            if a:
                row += bytes((round(r / a), round(g / a), round(b / a), round(a / n)))
            else:
                row += b"\0\0\0\0"
        rows.append(bytes(row))
    return rows


def png_bytes(rows):
    size = len(rows)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\0" + row for row in rows)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def ico_bytes(pngs):
    """ICO with PNG-compressed entries (supported since Windows Vista)."""
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, data = b"", b""
    for size, png in pngs:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    return header + entries + data


def icns_bytes(pngs):
    """ICNS with PNG entries: ic07=128, ic08=256, ic09=512."""
    types = {128: b"ic07", 256: b"ic08", 512: b"ic09"}
    body = b"".join(types[s] + struct.pack(">I", len(p) + 8) + p for s, p in pngs if s in types)
    return b"icns" + struct.pack(">I", len(body) + 8) + body


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sizes = [512, 256, 128, 64, 48, 32, 24, 16]
    pngs = {}
    for size in sizes:
        pngs[size] = png_bytes(render(size, ss=3 if size >= 128 else 4))
        print(f"rendered {size}px")
    (OUT / "wolfai.png").write_bytes(pngs[512])
    (OUT / "wolfai-256.png").write_bytes(pngs[256])
    (OUT / "wolfai.ico").write_bytes(ico_bytes([(s, pngs[s]) for s in (256, 128, 64, 48, 32, 24, 16)]))
    (OUT / "wolfai.icns").write_bytes(icns_bytes([(s, pngs[s]) for s in (128, 256, 512)]))
    print(f"icons written to {OUT}")


if __name__ == "__main__":
    main()
