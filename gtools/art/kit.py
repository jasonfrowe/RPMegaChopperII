"""Tiny procedural pixel-art kit.

A Sprite is built from shapes. Each shape writes a material id and a
height into two arrays. Rendering lights the height field from the top
left, picks a shade from the material's ramp of palette indices, and
outlines the silhouette. Shapes are given in sprite pixel coordinates,
with an optional z (height) so a whole sprite can be rolled about its
vertical axis (x' = x cos + z sin) for banking and spin frames.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw

Point = Tuple[float, float]

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5


@dataclass
class Material:
    ramp: Sequence[int]  # palette indices, dark to light
    shaded: bool = True
    dither: float = 0.12  # how much ordered dither blends adjacent shades
    rim: bool = False  # darkest shade on the material's own border


@dataclass
class Shape:
    kind: str
    pts: List[Point]
    mat: str
    z: float = 0.0
    amp: float = 2.0
    bevel: float = 2.0
    width: float = 1.0
    profile: str = "bevel"  # bevel | dome | flat
    data: Optional[np.ndarray] = None  # for kind "mask"


class Sprite:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.shapes: List[Shape] = []

    # --- shape builders ----------------------------------------------------
    def poly(self, pts, mat, z=0.0, amp=2.0, bevel=2.0, profile="bevel", sym=False):
        self.shapes.append(Shape("poly", list(pts), mat, z, amp, bevel, profile=profile))
        if sym:
            self.shapes.append(Shape("poly", [(self.w - x, y) for x, y in pts], mat, z, amp, bevel, profile=profile))
        return self

    def ellipse(self, box, mat, z=0.0, amp=2.0, profile="dome", sym=False):
        x0, y0, x1, y1 = box
        self.shapes.append(Shape("ellipse", [(x0, y0), (x1, y1)], mat, z, amp, profile=profile))
        if sym:
            self.shapes.append(Shape("ellipse", [(self.w - x1, y0), (self.w - x0, y1)], mat, z, amp, profile=profile))
        return self

    def rect(self, box, mat, z=0.0, amp=1.0, bevel=1.0, profile="bevel", sym=False):
        x0, y0, x1, y1 = box
        return self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], mat, z, amp, bevel, profile, sym)

    def line(self, p0, p1, mat, width=1.0, z=0.0, amp=0.5, sym=False):
        self.shapes.append(Shape("line", [p0, p1], mat, z, amp, width=width, profile="flat"))
        if sym:
            self.shapes.append(Shape("line", [(self.w - p0[0], p0[1]), (self.w - p1[0], p1[1])], mat, z, amp,
                                     width=width, profile="flat"))
        return self

    def mask(self, m, mat, z=0.0, amp=2.0, bevel=2.0, profile="bevel"):
        """A shape from a boolean array the size of the sprite (not rolled)."""
        self.shapes.append(Shape("mask", [], mat, z, amp, bevel, profile=profile, data=np.asarray(m, dtype=bool)))
        return self

    def dot(self, x, y, mat, z=0.0, sym=False):
        return self.rect((x, y, x + 1, y + 1), mat, z, amp=0.3, bevel=1.0, profile="flat", sym=sym)

    # --- rasterising -------------------------------------------------------
    def _mask(self, s: Shape, roll: float, scale: float) -> np.ndarray:
        if s.kind == "mask":
            return s.data
        cx = self.w / 2.0
        c, sn = math.cos(roll), math.sin(roll)

        def tx(p):
            x, y = p
            return (cx + ((x - cx) * c + s.z * sn) * scale, self.h / 2.0 + (y - self.h / 2.0) * scale)

        img = Image.new("L", (self.w, self.h), 0)
        d = ImageDraw.Draw(img)
        pts = [tx(p) for p in s.pts]
        if s.kind == "poly":
            # PIL fills inclusive of the right/bottom edge; shrink by a hair.
            d.polygon([(x - 0.5, y - 0.5) for x, y in pts], fill=255)
        elif s.kind == "ellipse":
            (x0, y0), (x1, y1) = pts
            if x1 < x0:
                x0, x1 = x1, x0
            d.ellipse([x0, y0, x1 - 1, y1 - 1], fill=255)
        elif s.kind == "line":
            d.line([(x - 0.5, y - 0.5) for x, y in pts], fill=255, width=max(1, int(round(s.width))))
        return np.array(img) > 127

    @staticmethod
    def _inner_distance(mask: np.ndarray) -> np.ndarray:
        """Distance from each inside pixel to the nearest outside pixel."""
        h, w = mask.shape
        pad = np.pad(mask, 1, constant_values=False)
        out_y, out_x = np.nonzero(~pad)
        in_y, in_x = np.nonzero(pad)
        dist = np.zeros(pad.shape)
        if len(in_y) == 0:
            return dist[1:-1, 1:-1]
        for i in range(0, len(in_y), 512):
            yy = in_y[i:i + 512, None]
            xx = in_x[i:i + 512, None]
            d2 = (yy - out_y[None, :]) ** 2 + (xx - out_x[None, :]) ** 2
            dist[in_y[i:i + 512], in_x[i:i + 512]] = np.sqrt(d2.min(axis=1)) - 0.5
        return dist[1:-1, 1:-1]

    def render(self, materials: Dict[str, Material], roll=0.0, scale=1.0, light=(-0.55, -0.75, 0.9),
               outline: Optional[int] = 1, ambient=0.18, gloss=0.0) -> np.ndarray:
        w, h = self.w, self.h
        mat_id = np.full((h, w), -1, dtype=int)
        height = np.zeros((h, w))
        names = list(materials.keys())
        for s in self.shapes:
            m = self._mask(s, roll, scale)
            if not m.any():
                continue
            if s.profile == "flat":
                prof = np.ones((h, w)) * s.amp
            elif s.profile == "dome":
                ys, xs = np.nonzero(m)
                cy, cx = ys.mean(), xs.mean()
                ry = max(1.0, (ys.max() - ys.min() + 1) / 2.0)
                rx = max(1.0, (xs.max() - xs.min() + 1) / 2.0)
                yy, xx = np.mgrid[0:h, 0:w]
                r2 = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2
                prof = np.sqrt(np.clip(1.0 - r2, 0, 1)) * s.amp * max(rx, ry) * 0.5
            else:
                prof = np.minimum(self._inner_distance(m), s.bevel) / max(s.bevel, 0.01) * s.amp
            mat_id[m] = names.index(s.mat)
            height[m] = s.z + prof[m]

        # Surface normals from the height field, rotated by the roll.
        gy, gx = np.gradient(height)
        nx, ny, nz = -gx, -gy, np.ones_like(height)
        c, sn = math.cos(roll), math.sin(roll)
        nx, nz = nx * c + nz * sn, -nx * sn + nz * c
        ln = np.array(light) / np.linalg.norm(light)
        nl = np.sqrt(nx * nx + ny * ny + nz * nz)
        lam = np.clip((nx * ln[0] + ny * ln[1] + nz * ln[2]) / nl, 0, 1)
        if gloss:
            lam = lam + gloss * lam ** 12
        inten = np.clip(ambient + (1 - ambient) * lam, 0, 1)

        out = np.zeros((h, w), dtype=np.uint8)
        yy, xx = np.mgrid[0:h, 0:w]
        bay = BAYER4[yy % 4, xx % 4]
        for i, name in enumerate(names):
            sel = mat_id == i
            if not sel.any():
                continue
            mat = materials[name]
            ramp = list(mat.ramp)
            n = len(ramp)
            if not mat.shaded or n == 1:
                level = np.full((h, w), n - 1)
            else:
                v = inten * (n - 1) + bay * mat.dither
                level = np.clip(np.round(v), 0, n - 1).astype(int)
            if mat.rim and n > 1:
                edge = sel & ~(np.roll(sel, 1, 0) & np.roll(sel, -1, 0) & np.roll(sel, 1, 1) & np.roll(sel, -1, 1))
                level[edge] = 0
            out[sel] = np.array(ramp)[level[sel]]

        if outline is not None:
            filled = mat_id >= 0
            pad = np.pad(filled, 1)
            nb = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
            out[(~filled) & nb] = outline
        return out


def sheet(frames: List[np.ndarray]) -> np.ndarray:
    """Frames side by side, left to right."""
    return np.concatenate(frames, axis=1)


def save_indexed(path, pixels: np.ndarray, palette_rgb: Sequence[Tuple[int, int, int]]):
    img = Image.fromarray(pixels.astype(np.uint8), mode="P")
    flat = []
    for r, g, b in palette_rgb:
        flat += [r, g, b]
    flat += [0] * (768 - len(flat))
    img.putpalette(flat)
    img.info["transparency"] = 0
    img.save(path, transparency=0)


def value_noise(w, h, cell, seed):
    rng = np.random.default_rng(seed)
    gw, gh = w // cell + 2, h // cell + 2
    g = rng.random((gh, gw))
    yy, xx = np.mgrid[0:h, 0:w] / cell
    x0, y0 = xx.astype(int), yy.astype(int)
    fx, fy = xx - x0, yy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a = g[y0, x0] * (1 - fx) + g[y0, x0 + 1] * fx
    b = g[y0 + 1, x0] * (1 - fx) + g[y0 + 1, x0 + 1] * fx
    return a * (1 - fy) + b * fy
