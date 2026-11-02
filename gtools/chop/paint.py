"""Small painting helpers shared by the layers."""

from __future__ import annotations

import math

import numpy as np

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
BAYER8 = np.array([
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) / 64.0


def bayer(h, w, n=4):
    m = BAYER4 if n == 4 else BAYER8
    return np.tile(m, (h // n + 1, w // n + 1))[:h, :w]


def wave(width, terms, seed):
    """A curve that repeats every `width` pixels: a sum of sines whose
    frequencies are whole numbers of cycles across the width.
    terms: [(cycles, amplitude), ...]"""
    rng = np.random.default_rng(seed)
    x = np.arange(width)
    y = np.zeros(width)
    for cyc, amp in terms:
        y += amp * np.sin(2 * math.pi * cyc * x / width + rng.uniform(0, 2 * math.pi))
    return y


def torus_noise(h, w, cell, seed):
    """Smooth value noise that wraps in x (and in y if h is a multiple of cell)."""
    rng = np.random.default_rng(seed)
    gw = max(1, w // cell)
    gh = h // cell + 2
    g = rng.random((gh, gw))
    yy, xx = np.mgrid[0:h, 0:w]
    fx, fy = xx / cell, yy / cell
    x0, y0 = fx.astype(int), fy.astype(int)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    x1 = (x0 + 1) % gw
    x0 = x0 % gw
    a = g[y0, x0] * (1 - tx) + g[y0, x1] * tx
    b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x1] * tx
    return a * (1 - ty) + b * ty


def fbm(h, w, cell, seed, octaves=3):
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = max(2, cell >> o)
        out += amp * torus_noise(h, w, c, seed + o * 17)
        tot += amp
        amp *= 0.5
    return out / tot


def ramp_dither(value, ramp, dith):
    """value in 0..1 -> palette index from `ramp`, ordered-dithered."""
    n = len(ramp)
    v = np.clip(value * (n - 1) + (dith - 0.5) * 0.9, 0, n - 1)
    return np.array(ramp)[np.round(v).astype(int)]
