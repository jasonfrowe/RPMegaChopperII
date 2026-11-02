#!/usr/bin/env python3
"""Run an emulator script against the built ROM, with symbols filled in.

The emulator's --script language addresses memory by number, and the
numbers move every build. Write {name} in a script instead, and this
fills in the address of that symbol from the ELF. {name+1} works too.

Built-in scripts (pass the name instead of a file):
  boss     warp to the end of the stage, fight the boss invulnerable,
           print dropped frames and save screenshots
  soak     play the whole stage holding fire, invulnerable, printing
           dropped frames as it goes

Usage:
  tools/playtest.py boss [--out DIR] [--stage N]
  tools/playtest.py my_script.txt [--out DIR]
  tools/playtest.py boss --phi2 4000     # the 6502 at half speed: does it still keep up?
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "llvm-mos" / "release"
ROM = BUILD / "RPMegaChopperII.rp6502"
ELF = BUILD / "RPMegaChopperII.elf"
NM = Path.home() / ".rp6502" / "llvm-mos" / "bin" / "llvm-nm"
EMU = ROOT / "tools" / "rp6502-emu"

BUILTIN = {
    "flight": (
        "run 30\n"
        "shot \"{out}/01_title.png\"\n"
        "press z\nrun 2\nrelease z\n"
        "run 60\n"
        "shot \"{out}/02_home_base.png\"\n"
        "# Fly left and climb\n"
        "press a\npress w\n"
        "run 80\n"
        "release w\n"
        "shot \"{out}/03_in_flight.png\"\n"
        "# Fire vulcan machine guns\n"
        "press z\nrun 20\nrelease z\n"
        "run 40\n"
        "shot \"{out}/04_firing.png\"\n"
        "# Turn to face front and drop bombs\n"
        "press x\nrun 2\nrelease x\n"
        "run 20\n"
        "press z\nrun 2\nrelease z\n"
        "run 40\n"
        "shot \"{out}/05_bombing.png\"\n"
        "release a\n"
        "run 60\n"
        "shot \"{out}/06_tundra.png\"\n"
        "dump {lag_frames} 2\n"
        "dump {gstate} 1\n"
        "dump {score} 4\n"
    ),
    "soak": (
        "run 30\npress z\nrun 2\nrelease z\n"
        + "".join(
            f"press {k}\nrun 120\nshot \"{{out}}/soak_{i}.png\"\ndump {{lag_frames}} 2\nrelease {k}\n"
            for i, k in enumerate("adwzszaxd")
        )
    ),
}


def symbols():
    out = subprocess.run([str(NM), str(ELF)], capture_output=True, text=True, check=True).stdout
    syms = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    return syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", default=tempfile.gettempdir())
    ap.add_argument("--seed", default="3")
    ap.add_argument("--stage", type=int, default=1, help="the stage a built-in script plays (1 up)")
    ap.add_argument("--phi2", help="6502 clock in kHz (default 8000); lower it to measure CPU headroom")
    args = ap.parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    text = BUILTIN.get(args.script)
    if text is None:
        text = Path(args.script).read_text()
    syms = symbols()

    def sub(m):
        name, plus = m.group(1), m.group(2)
        if name == "out":
            return args.out
        if name == "stage":
            return str(args.stage - 1)
        if name not in syms:
            sys.exit(f"unknown symbol {name}")
        return hex(syms[name] + (int(plus) if plus else 0))

    text = re.sub(r"\{(\w+)(?:\+(\d+))?\}", sub, text)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(text)
    cmd = [str(EMU), str(ROM), "--memseed", args.seed, "--mute", "--script", f.name]
    if args.phi2:
        cmd += ["--phi2", args.phi2]
    r = subprocess.run(cmd)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
