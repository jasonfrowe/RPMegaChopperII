#!/usr/bin/env python3
"""Generate Furnace (.fur) tracker projects for MegaGammaForce's OPL2 music.

Procedurally composes OPL2 tracks for each of the game's music slots, in
one of fourteen styles (--style, see musicgen/compose.py's STYLE_NAMES and
module docstring for the full rundown of each: 0 silpheed/orchestral,
1 kraftwerk/motorik electronic (default), 2 daftpunk/house-funk, 3 trance,
4 bigroom/electro-house, 5 dubstep/halftime, 6 techno/minimal-progressive,
7 synthwave, 8 dnb/jungle; MegaGammaForce's own: 9 silvergun/orchestral-epic
(musicgen/silvergun.py), 10 fmrock, 11 eurobeat, 12 chiparcade, 13 fusion
(musicgen/arcade.py)), and writes them as Furnace 0.6.8.1-compatible .fur
files, using RPTracker's 256-patch instrument bank. Open the result in
Furnace to audition and tweak by hand; pass --export-vgm to also render
straight to music/<resource>.vgm (e.g. music/Boss.vgm) using Furnace's own
headless exporter (equivalent to File > Export > VGM in the GUI). Without
that flag, this tool never touches music/*.vgm or CMakeLists.txt.

IMPORTANT: exported VGM must be plain OPL2 (YM3812), never OPL3/dual-chip.
RPDemo's VGM player (src/vgm.c) only understands a minimal opcode set and
will desync on OPL3 port-1 writes (0x5E/0x5F) or other commands outside that
set. Every .fur this tool writes is plain OPL2, so this only matters if you
hand-edit a file to add a second chip or switch to OPL3.

Usage:
  python gtools/generate_music.py --list
  python gtools/generate_music.py --track all
  python gtools/generate_music.py --track boss
  python gtools/generate_music.py --track boss --seed 1234
  python gtools/generate_music.py --track boss --export-vgm

Every run prints a "regenerate:" command with the exact --seed/--vol/--patch
needed to reproduce that roll (instrument picks resolved to their actual
hex values even if you didn't pass --patch) -- copy it and edit one number
to hand-tune a roll you like without re-rolling the rest of the song:
  python gtools/generate_music.py --track boss --seed 1234 \\
      --vol 0,0,1,2,-3,-1,2 --patch 52,53,27,FD,FE,FF,5E
--vol/--patch take 7 comma-separated values in lead,arp,bass,pad,kick,
snare,hat order (musicgen/compose.py's ROLE_TO_CHANNEL). --vol values are
integer offsets from each role's base volume
(can be negative; final volume is still clamped into OPL2's 0-63 range).
--patch values are 2-digit hex instrument indices (00-FF) into RPTracker's
256-patch bank, overriding whichever instrument that role would otherwise
have picked. Both only make sense with a single --track, not --track all.

To try ideas without touching the game's tracks, add --scratch: the .fur
(and the .vgm, with --export-vgm) go to music/scratch/ and the manifest is
left alone:
  python gtools/generate_music.py --track stage1 --style 11 --scratch --export-vgm
  python gtools/generate_music.py --track stage1 --style 11 --seed 77 --bpm 160 --prog 1,3 --scratch

Every run also records the track in gtools/music_manifest.json (seed, style,
vol, patch, mood, the exact command). To rebuild from that record -- after
editing its vol/patch, say -- without re-rolling the composition:
  python gtools/generate_music.py --track boss --from-manifest --export-vgm
  python gtools/generate_music.py --track all --from-manifest --export-vgm
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import random
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from musicgen import compose, tracks  # noqa: E402
from musicgen.furwriter import write_fur  # noqa: E402
from musicgen.instruments import load_bank  # noqa: E402

FURNACE_BIN = "/Applications/Furnace.app/Contents/MacOS/furnace"
MUSIC_DIR = Path(__file__).resolve().parent.parent / "music"
# fur_levels/ is the tracked, canonical editable-.fur location (matches the
# ROM asset/output names in CMakeLists.txt and tracks.py's `resource`
# field). --scratch writes to music/scratch/ instead, which is gitignored.
DEFAULT_OUT_DIR = MUSIC_DIR / "fur_levels"
DEFAULT_VGM_OUT_DIR = MUSIC_DIR
SCRATCH_DIR = MUSIC_DIR / "scratch"  # gitignored; never loaded by the build

# lead, arp, bass, pad, kick, snare, hat -- the canonical order --vol/--patch
# values are given/printed in, taken directly from compose.py's role->channel
# mapping so it can never drift out of sync with the actual role set.
ROLE_ORDER = list(compose.ROLE_TO_CHANNEL.keys())
MANIFEST = Path(__file__).resolve().parent / "music_manifest.json"


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def _record(spec, seed: int, style: int, vol_overrides: dict, ins: dict, exported: bool) -> None:
    bpm = spec.mood.bpm if spec.mood.bpm != tracks.resolve(spec.resource).mood.bpm else None
    prog = ins.get("_prog")
    prog_str = f"{prog[0]},{prog[1]}" if prog else None
    """Remember exactly how a track was made, so it can be rebuilt or tweaked
    later: see --from-manifest."""
    vol_str = ",".join(str(vol_overrides.get(role, 0)) for role in ROLE_ORDER)
    patch_str = ",".join(f"{ins[role]:02X}" for role in ROLE_ORDER)
    m = _load_manifest()
    m[spec.resource] = {
        "seed": seed,
        "style": style,
        "style_name": compose.STYLE_NAMES[style],
        "vol": vol_str,
        "patch": patch_str,
        "roles": ",".join(ROLE_ORDER),
        "mood": {k: v for k, v in vars(spec.mood).items()},
        "prog": prog_str,
        "bpm": bpm,
        "exported_vgm": exported,
        "date": datetime.date.today().isoformat(),
        "command": (f".venv/bin/python gtools/generate_music.py --track {spec.aliases[0]} --seed {seed} "
                    f"--style {style} --vol {vol_str} --patch {patch_str}"
                    + (f" --prog {prog_str}" if prog_str else "") + (f" --bpm {bpm:g}" if bpm else "")
                    + " --export-vgm"),
    }
    MANIFEST.write_text(json.dumps(m, indent=2) + "\n")
    print(f"  recorded in {MANIFEST}")


def _parse_vol(spec: str) -> dict:
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) != len(ROLE_ORDER):
        raise ValueError(f"--vol needs {len(ROLE_ORDER)} comma-separated values ({','.join(ROLE_ORDER)}), got {len(parts)}")
    try:
        values = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"--vol values must be integers, got {spec!r}")
    return dict(zip(ROLE_ORDER, values))


def _parse_patch(spec: str) -> dict:
    parts = [p.strip() for p in spec.split(",")]
    if len(parts) != len(ROLE_ORDER):
        raise ValueError(f"--patch needs {len(ROLE_ORDER)} comma-separated hex values ({','.join(ROLE_ORDER)}), got {len(parts)}")
    try:
        values = [int(p, 16) for p in parts]
    except ValueError:
        raise ValueError(f"--patch values must be 2-digit hex bytes (e.g. FD), got {spec!r}")
    for role, v in zip(ROLE_ORDER, values):
        if role in compose.DRUM_ROLES:
            if v not in compose.DRUM_PATCHES:
                raise ValueError(f"--patch {role} must be a drum patch (FD, FE or FF), got {v:02X}")
        elif not (0 <= v <= compose.MELODIC_MAX):
            raise ValueError(f"--patch {role} must be a melodic patch 00-7F, got {v:02X}")
    return dict(zip(ROLE_ORDER, values))


def _validate_with_furnace(path: Path) -> None:
    if not Path(FURNACE_BIN).exists():
        print(f"  (skipping validation: Furnace not found at {FURNACE_BIN})")
        return
    result = subprocess.run(
        [FURNACE_BIN, "-loglevel", "error", "-info", str(path)],
        capture_output=True, text=True, timeout=30,
    )
    text = result.stdout + result.stderr
    real_errors = [
        line for line in text.splitlines()
        if "ERROR" in line and "could not bind text domain" not in line
    ]
    if real_errors or "SONG INFORMATION" not in text:
        print(f"  WARNING: Furnace validation of {path.name} looked wrong:")
        for line in text.splitlines():
            if line.strip():
                print(f"    {line}")
    else:
        print("  validated OK (furnace -info)")


def _export_vgm(fur_path: Path, vgm_path: Path) -> None:
    if not Path(FURNACE_BIN).exists():
        print(f"  WARNING: can't export VGM, Furnace not found at {FURNACE_BIN}")
        return
    vgm_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [FURNACE_BIN, "-loglevel", "error", "-subsong", "0", "-loops", "1", "-vgmout", str(vgm_path), str(fur_path)],
        capture_output=True, text=True, timeout=60,
    )
    text = result.stdout + result.stderr
    real_errors = [
        line for line in text.splitlines()
        if "ERROR" in line and "could not bind text domain" not in line
    ]
    if real_errors or not vgm_path.exists() or vgm_path.stat().st_size == 0:
        print(f"  WARNING: VGM export of {fur_path.name} failed:")
        for line in text.splitlines():
            if line.strip():
                print(f"    {line}")
        return
    size = vgm_path.stat().st_size
    print(f"  exported VGM -> {vgm_path} ({size} bytes)")


def generate_one(spec: "tracks.TrackSpec", seed: int, bank, out_dir: Path,
                  export_vgm: bool = False, vgm_out_dir: Path = DEFAULT_VGM_OUT_DIR,
                  vol_overrides: dict = None, patch_overrides: dict = None, style: int = compose.STYLE_KRAFTWERK,
                  record: bool = True, prog: tuple = None) -> Path:
    # Scratch takes (record=False) are named for what made them, so several sit side by side.
    stem = spec.resource if record else f"{spec.resource}-{compose.STYLE_NAMES[style]}-{seed}"
    song, ins = compose.generate_track(
        name=f"{spec.resource} - {spec.description}", mood=spec.mood, seed=seed, bank=bank,
        vol_overrides=vol_overrides, patch_overrides=patch_overrides, style=style, prog_override=prog,
    )
    compose.check_patches(song)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{stem}.fur"
    write_fur(str(out_path), song)
    print(f"{spec.resource} ({', '.join(spec.aliases)}) -> {out_path}  [seed={seed}, style={style} ({compose.STYLE_NAMES[style]})]  {spec.description}")
    _validate_with_furnace(out_path)
    if export_vgm:
        _export_vgm(out_path, vgm_out_dir / f"{stem}.vgm")

    vol_overrides = vol_overrides or {}
    vol_str = ",".join(str(vol_overrides.get(role, 0)) for role in ROLE_ORDER)
    patch_str = ",".join(f"{ins[role]:02X}" for role in ROLE_ORDER)
    prog_ab = ins.get("_prog")
    extra = (f" --prog {prog_ab[0]},{prog_ab[1]}" if prog_ab else "")
    if spec.mood.bpm != tracks.resolve(spec.resource).mood.bpm:
        extra += f" --bpm {spec.mood.bpm:g}"
    print(f"  regenerate: python3 gtools/generate_music.py --track {spec.aliases[0]} --seed {seed} --style {style} "
          f"--vol {vol_str} --patch {patch_str}{extra}" + ("" if record else " --scratch"))
    if record:
        _record(spec, seed, style, vol_overrides, ins, export_vgm)
    return out_path


def _with_bpm(spec, bpm):
    """The track with its tempo replaced, or unchanged when bpm is None."""
    if not bpm:
        return spec
    return dataclasses.replace(spec, mood=dataclasses.replace(spec.mood, bpm=float(bpm)))


def cmd_list() -> None:
    for spec in tracks.TRACKS:
        aliases = ", ".join(spec.aliases)
        print(f"{spec.resource}  ({aliases:<20}) {spec.description}")


def _fuse_negative_values(argv: list[str]) -> list[str]:
    """`--vol -4,2,...` (space form) reads as `--vol` with no value to argparse,
    since it only recognizes a following token as a value when it doesn't look
    like another option -- and a leading '-' makes it look like one. None of
    this parser's flags start with a digit, so `--vol`/`--patch` followed by a
    token matching -digit... is unambiguously that flag's value; fuse it into
    the `--vol=...` form argparse already handles correctly.
    """
    fused = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok in ("--vol", "--patch") and i + 1 < len(argv) and re.match(r"^-\d", argv[i + 1]):
            fused.append(f"{tok}={argv[i + 1]}")
            i += 2
            continue
        fused.append(tok)
        i += 1
    return fused


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--track", help="track alias/resource id, or 'all' (e.g. boss, level1, Level_01)")
    parser.add_argument("--seed", type=int, help="RNG seed, for reproducing a specific roll (only valid with a single --track)")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help=f"output directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--export-vgm", action="store_true",
                         help="also render straight to VGM via Furnace's headless exporter "
                              f"(default destination: {DEFAULT_VGM_OUT_DIR}/<resource>.vgm, e.g. Boss.vgm, "
                              "overwriting the existing file)")
    parser.add_argument("--vgm-out-dir", default=str(DEFAULT_VGM_OUT_DIR),
                         help=f"VGM output directory, only used with --export-vgm (default: {DEFAULT_VGM_OUT_DIR})")
    parser.add_argument("--vol", help=f"{len(ROLE_ORDER)} comma-separated integer volume offsets, "
                                       f"{','.join(ROLE_ORDER)} order (only valid with a single --track)")
    parser.add_argument("--patch", help=f"{len(ROLE_ORDER)} comma-separated hex instrument indices (00-FF), "
                                         f"{','.join(ROLE_ORDER)} order (only valid with a single --track)")
    style_choices = ", ".join(f"{k}={v}" for k, v in sorted(compose.STYLE_NAMES.items()))
    parser.add_argument("--style", type=int, default=compose.STYLE_KRAFTWERK,
                         help=f"composition style: {style_choices} (default: {compose.STYLE_KRAFTWERK})")
    parser.add_argument("--list", action="store_true", help="list all tracks and exit")
    parser.add_argument("--prog", help="styles 9 and up: A,B chord progression indices for the two themes "
                                        "(see --list-progs); the rest of the seed's composition is unchanged")
    parser.add_argument("--list-progs", action="store_true",
                        help="list the chord progression banks of --style (or of every style 9 and up) and exit")
    parser.add_argument("--bpm", type=float, help="override the track's tempo (ticks per row are whole numbers at "
                                                  "60 Hz, so 4/4 lands on 900/n: 180, 150, 128.6, 112.5, 100 ...)")
    parser.add_argument("--scratch", action="store_true",
                        help=f"write to {SCRATCH_DIR} instead (both .fur and .vgm) and leave the manifest alone, "
                             "for trying things out")
    parser.add_argument("--from-manifest", action="store_true",
                         help=f"rebuild --track (or 'all') from the seed/style/vol/patch recorded in {MANIFEST.name}; "
                              "--vol/--patch given here still override the recorded ones")
    args = parser.parse_args(_fuse_negative_values(sys.argv[1:]))

    if args.list:
        cmd_list()
        return 0
    if args.list_progs:
        from musicgen import silvergun
        given = "--style" in sys.argv or any(a.startswith("--style=") for a in sys.argv)
        styles = [args.style] if given else [k for k in sorted(compose.STYLE_NAMES) if compose.style_kit(k)]
        for st in styles:
            kit = compose.style_kit(st)
            if kit is None:
                parser.error(f"style {st} has no progression bank (only styles 9 and up do)")
            majb, minb = (kit.MAJOR_BANK, kit.MINOR_BANK) if kit is silvergun else (kit.major_bank, kit.minor_bank)
            print(f"style {st} ({compose.STYLE_NAMES[st]})")
            for label, bank in (("major", majb), ("minor", minb)):
                print(f"  {label} (tracks whose scale is {label}):")
                for i, (tier, p) in enumerate(bank):
                    print(f"    {i:2d}  tier {tier}  {silvergun.describe(p)}")
        return 0
    if args.scratch:
        args.out_dir = args.vgm_out_dir = str(SCRATCH_DIR)
    prog = None
    if args.prog:
        prog = tuple(int(x) for x in args.prog.split(","))
        if len(prog) != 2:
            parser.error("--prog takes two indices, A,B")

    if args.from_manifest:
        manifest = _load_manifest()
        names = [s.resource for s in tracks.TRACKS] if (args.track or "").lower() == "all" else [tracks.resolve(args.track).resource]
        bank = load_bank()
        for name in names:
            if name not in manifest:
                parser.error(f"{name} is not in {MANIFEST}")
            e = manifest[name]
            vol = _parse_vol(args.vol) if args.vol else _parse_vol(e["vol"])
            patch = _parse_patch(args.patch) if args.patch else _parse_patch(e["patch"])
            p = prog or (tuple(int(x) for x in e["prog"].split(",")) if e.get("prog") else None)
            generate_one(_with_bpm(tracks.resolve(name), args.bpm or e.get("bpm")), e["seed"], bank,
                         Path(args.out_dir), export_vgm=args.export_vgm, vgm_out_dir=Path(args.vgm_out_dir),
                         vol_overrides=vol, patch_overrides=patch, style=e["style"], prog=p, record=not args.scratch)
        return 0

    if args.style not in compose.STYLE_NAMES:
        parser.error(f"--style must be one of {style_choices}, got {args.style}")

    if not args.track:
        parser.error("--track is required (or use --list)")

    out_dir = Path(args.out_dir)
    vgm_out_dir = Path(args.vgm_out_dir)

    if args.track.lower() == "all":
        if args.seed is not None:
            parser.error("--seed only makes sense with a single --track, not --track all")
        if args.vol or args.patch:
            parser.error("--vol/--patch only make sense with a single --track, not --track all")
        bank = load_bank()
        for spec in tracks.TRACKS:
            generate_one(_with_bpm(spec, args.bpm), random.randrange(2**31), bank, out_dir,
                         export_vgm=args.export_vgm, vgm_out_dir=vgm_out_dir, style=args.style,
                         record=not args.scratch)
        return 0

    try:
        spec = tracks.resolve(args.track)
    except KeyError as e:
        parser.error(str(e))
        return 2

    try:
        vol_overrides = _parse_vol(args.vol) if args.vol else None
        patch_overrides = _parse_patch(args.patch) if args.patch else None
    except ValueError as e:
        parser.error(str(e))
        return 2

    seed = args.seed if args.seed is not None else random.randrange(2**31)
    bank = load_bank()
    generate_one(_with_bpm(spec, args.bpm), seed, bank, out_dir, export_vgm=args.export_vgm, vgm_out_dir=vgm_out_dir,
                 vol_overrides=vol_overrides, patch_overrides=patch_overrides, style=args.style, prog=prog,
                 record=not args.scratch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
