#!/usr/bin/env python3
"""Run an emulator script against the built ROM, with symbols filled in.

The emulator's --script language addresses memory by number, and the
numbers move every build. Write {name} in a script instead, and this
fills in the address of that symbol from the ELF. {name+1} works too.

Built-in scripts (pass the name instead of a file):
  flight   take off and fly west, shooting and bombing, with screenshots
  rescue   breach a prison, land, load hostages, unload them at home
  soak     fly about holding fire through a full storm, invulnerable,
           printing dropped frames

test_stats (dumped by the scripts) is: state, cargo, saved, lost, lives,
breached prisons (a bit each), score (2 bytes), storm strength (0-16), hostages still in the prisons. Dump that rather than the
game's own variables, which can be stale in memory.

Usage:
  tools/playtest.py rescue [--out DIR]
  tools/playtest.py my_script.txt [--out DIR]
  tools/playtest.py soak --phi2 4000     # the 6502 at half speed: does it still keep up?
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

def le(v, n=4):
    return " ".join(f"${(v >> (8 * i)) & 0xFF:02X}" for i in range(n))


# World x to land at on the home helipad (see src/gen/assets.h).
HOME_X = 4436


# Put the chopper at world (x, y), hovering, with the camera on it.
def place(x, y):
    return (f"poke {{debug_warp_y}} {le(y, 2)}\n"
            f"poke {{debug_warp_x}} {le(x, 2)}\n")


BUILTIN = {
    # Fly west from the helipad across the map, firing.
    "flight": (
        "run 30\n"
        "shot \"{out}/01_title.png\"\n"
        "press z\nrun 2\nrelease z\n"
        "run 60\n"
        "shot \"{out}/02_home_base.png\"\n"
        "press w\nrun 30\nrelease w\n"
        "press a\n"
        + "".join("run 21\npress w\nrun 9\nrelease w\n" for _ in range(6))
        + "shot \"{out}/03_in_flight.png\"\n"
        "press z\n"
        + "".join("run 21\npress w\nrun 9\nrelease w\n" for _ in range(6))
        + "release z\n"
        "shot \"{out}/04_firing.png\"\n"
        "release a\n"
        "press x\nrun 2\nrelease x\nrun 20\n"
        "press z\nrun 2\nrelease z\nrun 20\n"
        "shot \"{out}/05_bombing.png\"\n"
        "run 60\n"
        "shot \"{out}/06_tundra.png\"\n"
        "dump {lag_frames} 2\n"
        "dump {test_stats} 10\n"
    ),
    # Shoot open the nearest prison, land, load up, fly home and unload.
    "rescue": (
        "run 30\npress z\nrun 2\nrelease z\nrun 30\n"
        "poke {chopper_invulnerable} 1\n"
        + place(3300, 172)
        + "press a\nrun 2\nrelease a\nrun 4\n"
        "press z\nrun 30\nrelease z\nrun 20\n"
        "shot \"{out}/01_breach.png\"\n"
        "dump {test_stats} 10\n"
        + place(3212, 150)
        + "press s\nrun 40\nrelease s\n"
        "run 400\n"
        "shot \"{out}/02_boarding.png\"\n"
        "run 1000\n"
        "shot \"{out}/03_boarded.png\"\n"
        "dump {test_stats} 10\n"
        # Home: climb, then put it over the helipad and set it down.
        "press w\nrun 10\nrelease w\n"
        + place(HOME_X, 150)
        + "press s\nrun 40\nrelease s\nrun 60\n"
        "shot \"{out}/04_unloading.png\"\n"
        "run 700\n"
        "shot \"{out}/05_home.png\"\n"
        "dump {test_stats} 10\n"
        "dump {lag_frames} 2\n"
    ),
    # Empty every prison in turn and fly everyone home: the sector clears.
    "campaign": (
        "run 30\npress z\nrun 2\nrelease z\nrun 30\npoke {chopper_invulnerable} 1\n"
        + "".join(
            place(door + 84, 172)
            + "press a\nrun 2\nrelease a\nrun 4\npress z\nrun 30\nrelease z\nrun 20\n"
            + place(door - 4, 150)
            + "press s\nrun 40\nrelease s\nrun 1500\n"
            f"shot \"{{out}}/c{k}_loaded.png\"\n"
            "dump {test_stats} 10\n"
            "press w\nrun 10\nrelease w\n"
            + place(HOME_X, 150)
            + "press s\nrun 40\nrelease s\nrun 800\n"
            "dump {test_stats} 10\n"
            for k, door in enumerate((3216, 2288, 1280, 368))
        )
        + "run 400\nshot \"{out}/c_clear.png\"\ndump {test_stats} 10\n"
    ),
    # Real danger, no invulnerability: open the first prison, wait on the
    # ground while the tanks roll in, then hover high above their flak,
    # then sit on the ground at the second prison until the bomber comes.
    "ambush": (
        "run 30\npress z\nrun 2\nrelease z\nrun 30\n"
        + place(3300, 172)
        + "press a\nrun 2\nrelease a\nrun 4\npress z\nrun 30\nrelease z\nrun 20\n"
        "press s\nrun 30\nrelease s\nrun 400\n"
        "shot \"{out}/a1_tanks.png\"\ndump {test_stats} 10\n"
        "press w\nrun 100\nrelease w\n"
        + "".join("press w\nrun 2\nrelease w\nrun 5\n" for _ in range(60))
        + "shot \"{out}/a2_high.png\"\ndump {test_stats} 10\n"
        "poke {chopper_invulnerable} 1\n"
        + place(2372, 172)
        + "press a\nrun 2\nrelease a\nrun 4\npress z\nrun 30\nrelease z\n"
        "press s\nrun 30\nrelease s\n"
        + "".join(f"run 60\nshot \"{{out}}/a3_ground_{k}.png\"\n" for k in range(8))
        + "dump {test_stats} 10\n"
    ),
    # Free a prison so the enemy turns up, then keep putting the chopper
    # back among them, unprotected, until the last one is lost.
    "gameover": (
        "run 30\npress z\nrun 2\nrelease z\nrun 30\npoke {chopper_invulnerable} 1\n"
        + place(3300, 172)
        + "press a\nrun 2\nrelease a\nrun 4\npress z\nrun 30\nrelease z\n"
        "press s\nrun 30\nrelease s\nrun 600\npoke {chopper_invulnerable} 0\n"
        + "".join(place(3300, 150) + "run 500\n" for _ in range(8))
        + "shot \"{out}/gameover.png\"\ndump {test_stats} 10\n"
    ),
    "soak": (
        "run 30\npress z\nrun 2\nrelease z\npoke {chopper_invulnerable} 1\npoke {debug_storm} 16\n"
        + "".join(
            f"press {k}\nrun 120\nshot \"{{out}}/soak_{i}.png\"\ndump {{lag_frames}} 2\nrelease {k}\n"
            for i, k in enumerate("wazwazxzdwzs")
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
