"""Write an enlarged RGB preview of indexed frames for eyeballing art."""

import sys

import numpy as np
from PIL import Image


def preview(path, frames, palette, scale=8, bg=(40, 40, 48), gap=2):
    h = max(f.shape[0] for f in frames)
    w = sum(f.shape[1] for f in frames) + gap * (len(frames) + 1)
    out = np.zeros((h + gap * 2, w, 3), dtype=np.uint8)
    out[:] = bg
    x = gap
    for f in frames:
        for idx in range(1, 16):
            c = palette[idx] if idx < len(palette) else None
            if c is None:
                continue
            ys, xs = np.nonzero(f == idx)
            out[ys + gap, xs + x] = c
        x += f.shape[1] + gap
    Image.fromarray(out).resize((out.shape[1] * scale, out.shape[0] * scale), Image.NEAREST).save(path)


if __name__ == "__main__":
    print("import me", file=sys.stderr)
