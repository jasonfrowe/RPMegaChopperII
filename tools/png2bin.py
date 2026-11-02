#!/usr/bin/env python3
"""Convert an indexed PNG sheet into packed sprite/tile frames for the VGA.

Frames are FRAME_W x FRAME_H, read left to right then top to bottom.
Each frame is written row by row, 4bpp with the left pixel in the high
nibble, which is the Mode 2 tile and Mode 5 sprite image format.

Standard library only, so the build needs no packages: it decodes
non-interlaced indexed (palette) PNGs, as Aseprite and Pillow write them.

Usage: png2bin.py in.png out.bin FRAME_W FRAME_H [BPP]
"""

import struct
import sys
import zlib


def read_indexed_png(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"{path}: not a PNG")
    pos = 8
    idat = b""
    w = h = depth = ctype = interlace = None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            break
    if ctype not in (0, 3):
        sys.exit(f"{path}: must be an indexed (palette) PNG, color type {ctype}")
    if interlace:
        sys.exit(f"{path}: interlaced PNGs are not supported")
    raw = zlib.decompress(idat)
    stride = (w * depth + 7) // 8
    bpp = max(1, depth // 8)
    rows = []
    prev = bytearray(stride)
    p = 0
    for _ in range(h):
        f = raw[p]
        line = bytearray(raw[p + 1:p + 1 + stride])
        p += 1 + stride
        for i in range(stride):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            if f == 1:
                line[i] = (line[i] + a) & 0xFF
            elif f == 2:
                line[i] = (line[i] + b) & 0xFF
            elif f == 3:
                line[i] = (line[i] + ((a + b) >> 1)) & 0xFF
            elif f == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        prev = line
        px = []
        per = 8 // depth if depth < 8 else 1
        mask = (1 << depth) - 1 if depth < 8 else 0xFF
        for x in range(w):
            if depth == 8:
                px.append(line[x])
            else:
                byte = line[x // per]
                shift = 8 - depth * (x % per + 1)
                px.append((byte >> shift) & mask)
        rows.append(px)
    return w, h, rows


def convert(src, fw, fh, bpp=4):
    """The frames of an indexed PNG sheet, packed."""
    w, h, px = read_indexed_png(src)
    if w % fw or h % fh:
        sys.exit(f"{src}: {w}x{h} is not a whole number of {fw}x{fh} frames")
    per = 8 // bpp
    out = bytearray()
    for fy in range(0, h, fh):
        for fx in range(0, w, fw):
            for y in range(fy, fy + fh):
                for x in range(fx, fx + fw, per):
                    b = 0
                    for k in range(per):
                        v = px[y][x + k]
                        if v >= (1 << bpp):
                            sys.exit(f"{src}: index {v} at {x + k},{y} needs more than {bpp} bits")
                        b = (b << bpp) | v
                    out.append(b)
    return bytes(out)


def main():
    src, dst, fw, fh = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    bpp = int(sys.argv[5]) if len(sys.argv) > 5 else 4
    with open(dst, "wb") as f:
        f.write(convert(src, fw, fh, bpp))


if __name__ == "__main__":
    main()
