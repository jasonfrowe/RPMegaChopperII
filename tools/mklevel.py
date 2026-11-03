#!/usr/bin/env python3
"""Pack a level's ROM file from its manifest, images/level<N>/level.json
(written by gtools/gen_art.py).

ROM:level<N>.bin holds, in order, the level's enemy sprite sheets (padded
to the shared enemy region), its three tile sheets (each padded to its
layer's tile budget), its three tile maps and every palette, laid out as
xram.h has them, so the game reads it straight into XRAM in three runs:
enemies, tiles and maps, palettes. Sheets are read from their PNGs, so
edits made in Aseprite go into the next build; enemy sheets must keep
their frame size and count, and a tile sheet must stay within its budget.

Standard library only, so the build needs no packages.

Usage: mklevel.py images/level<N>/level.json out.bin
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png2bin import convert  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def main():
    spec_path, dst = Path(sys.argv[1]), sys.argv[2]
    spec = json.loads(spec_path.read_text())
    out = bytearray()
    for it in spec["items"]:
        if "pad" in it:
            out += bytes(it["pad"])
            continue
        if "png" in it:
            data = convert(str(ROOT / it["png"]), it["w"], it["h"])
            label = it["png"]
        else:
            data = (ROOT / it["bin"]).read_bytes()
            label = it["bin"]
        if "max" in it:
            if len(data) > it["max"]:
                sys.exit(f"{label}: {len(data)} bytes, but there is room for {it['max']}")
            data += bytes(it["size"] - len(data))
        elif len(data) != it["size"]:
            sys.exit(f"{label}: {len(data)} bytes, but the game expects {it['size']} "
                     f"(an edited sheet must keep its frame size and count)")
        out += data
    with open(dst, "wb") as f:
        f.write(out)


if __name__ == "__main__":
    main()
