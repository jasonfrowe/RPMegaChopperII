"""Cut a painted layer into tiles, and fit it to a tile budget.

A layer is painted as one big indexed image. Cutting it gives a map and
the set of distinct tiles. When there are more distinct tiles than the
budget allows, the tile that costs least to lose (how different it is from
its nearest surviving neighbour, times how often it is used) is folded into
that neighbour, until the set fits. Tiles named as protected are never
folded away and nothing is folded into them, so a door the game swaps out
keeps its own ids.
"""

from __future__ import annotations

import numpy as np


def cut(img: np.ndarray, t: int):
    h, w = img.shape
    assert h % t == 0 and w % t == 0, (img.shape, t)
    rows, cols = h // t, w // t
    blocks = img.reshape(rows, t, cols, t).swapaxes(1, 2).reshape(rows * cols, t, t)
    return blocks, rows, cols


def _lum(pal):
    return np.array([0.3 * r + 0.55 * g + 0.15 * b for r, g, b in pal])


def build(img: np.ndarray, t: int, palette, budget: int, extra=(), protect=(), transparent0=True):
    """Tiles and map for `img`.

    extra: more images (multiples of t) whose tiles must exist in the set
        but are not in the map, such as a breached door. Their tiles are
        protected.
    protect: tile images (t x t arrays) that must survive unchanged.
    Returns (tiles: list of t x t arrays, map: rows x cols uint8,
    lookup: function from a t x t array to its id).
    """
    blocks, rows, cols = cut(img, t)
    keys = [b.tobytes() for b in blocks]
    uniq: dict = {}
    count: dict = {}
    order = []
    for k, b in zip(keys, blocks):
        if k not in uniq:
            uniq[k] = b.copy()
            order.append(k)
            count[k] = 0
        count[k] += 1
    prot = {np.asarray(p, dtype=np.uint8).tobytes() for p in protect}
    for e in extra:
        eb, _, _ = cut(e, t)
        for b in eb:
            k = b.tobytes()
            prot.add(k)
            if k not in uniq:
                uniq[k] = b.copy()
                order.append(k)
                count[k] = 0
    # The empty (all zero) tile first, so id 0 is blank where that matters.
    zero = np.zeros((t, t), np.uint8).tobytes()
    if zero in uniq:
        order.remove(zero)
        order.insert(0, zero)

    n = len(order)
    remap = {k: k for k in order}
    if n > budget:
        lum = _lum(palette)
        flat = np.stack([uniq[k].reshape(-1) for k in order]).astype(int)
        L = lum[flat]
        if transparent0:
            L = np.where(flat == 0, -400.0, L)
        # Pairwise cost: summed brightness difference, plus a term for
        # differing indices so same-looking colors still prefer exact matches.
        D = np.zeros((n, n))
        for i in range(n):
            D[i] = np.abs(L - L[i]).sum(axis=1) + 4.0 * (flat != flat[i]).sum(axis=1)
        alive = np.ones(n, bool)
        is_prot = np.array([k in prot for k in order])
        weight = np.array([count[k] for k in order], float)
        alive_n = n
        while alive_n > budget:
            Dm = D.copy()
            Dm[:, ~alive] = np.inf
            Dm[np.arange(n), np.arange(n)] = np.inf
            nearest = Dm.argmin(axis=1)
            cost = Dm[np.arange(n), nearest] * np.maximum(weight, 0.5)
            cost[~alive | is_prot] = np.inf
            cost[0] = np.inf if order[0] == zero else cost[0]
            victim = int(cost.argmin())
            if not np.isfinite(cost[victim]):
                raise ValueError(f"cannot fit {n} tiles into {budget}: all the rest are protected")
            into = int(nearest[victim])
            alive[victim] = False
            weight[into] += weight[victim]
            alive_n -= 1
            remap[order[victim]] = order[into]
        # Follow chains of merges to the survivor.
        for k in order:
            r = remap[k]
            while remap[r] != r:
                r = remap[r]
            remap[k] = r
        order = [k for i, k in enumerate(order) if alive[i]]

    ids = {k: i for i, k in enumerate(order)}
    tiles = [uniq[k] for k in order]
    m = np.array([ids[remap[k]] for k in keys], dtype=np.uint8).reshape(rows, cols)

    def lookup(tile):
        k = np.asarray(tile, dtype=np.uint8).tobytes()
        return ids[remap[k]]

    return tiles, m, lookup


def sheet(tiles, t, per_row=None):
    """Tiles side by side (one row unless told), for the PNG the build converts."""
    n = len(tiles)
    per_row = per_row or n
    rows = (n + per_row - 1) // per_row
    out = np.zeros((rows * t, per_row * t), np.uint8)
    for i, tile in enumerate(tiles):
        r, c = divmod(i, per_row)
        out[r * t:(r + 1) * t, c * t:(c + 1) * t] = tile
    return out


def render(tiles, m, t):
    """The map drawn back out, to check the fit."""
    rows, cols = m.shape
    out = np.zeros((rows * t, cols * t), np.uint8)
    for r in range(rows):
        for c in range(cols):
            out[r * t:(r + 1) * t, c * t:(c + 1) * t] = tiles[m[r, c]]
    return out
