#!/usr/bin/env python3
"""Pack one of a stage's ROM files from its JSON manifest.

stage<N>.bin is the stage's TILES and SKY palettes, then its script,
ground and sky; boss<N>.bin is the LAYER, BOSS and BOSS_WRECK palettes,
then the boss. Contents sit at the offsets in src/gen/stage<N>.h. The
game reads the palettes into the stage palette slots and the rest into
XRAM_BANK or XRAM_BOSS. Sheets are read from their PNGs, so edits made in
Aseprite go into the next build; they must keep their frame size and count.

Standard library only, so the build needs no packages.

Usage: mkbank.py images/stage<N>/{stage,boss}.json out.bin
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
    out = bytearray((ROOT / spec["palettes"]).read_bytes())
    start = len(out)
    for it in spec["items"]:
        if len(out) - start != it["offset"]:
            sys.exit(f"{spec_path}: offsets are out of step at {it}")
        if "png" in it:
            data = convert(str(ROOT / it["png"]), it["w"], it["h"])
            label = it["png"]
        else:
            data = (ROOT / it["bin"]).read_bytes()
            label = it["bin"]
        if len(data) != it["size"]:
            sys.exit(f"{label}: {len(data)} bytes, but the game expects {it['size']} "
                     f"(an edited sheet must keep its frame size and count)")
        out += data
    with open(dst, "wb") as f:
        f.write(out)


if __name__ == "__main__":
    main()
