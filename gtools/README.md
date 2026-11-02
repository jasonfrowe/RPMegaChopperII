# Asset Generation Tools (`gtools`)

These scripts procedurally generated the initial graphics, sound effects,
music, and lookup tables for MegaGammaForce. They are kept outside the main
build and ignored by git so that hand-remastered PNG and VGM/Furnace assets
in `images/` and `music/` are never overwritten during normal builds.

## Setup

Regenerating the art requires Pillow and numpy in a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/pip install -r gtools/requirements.txt
```

## Overview

| Tool | Makes |
|---|---|
| `gtools/gen_art.py` | Shared sheets in `images/*.png`; each stage's sheets, maps and palettes in `images/stage<N>/`; `src/gen/assets.h`, `src/gen/stage<N>.h` (bank offsets) and `src/gen/stage<N>_data.h` (enemy type checks) |
| `gtools/art/` | The pixel-art kit: shapes with heights, lit from the top left, outlined. Banking frames are real rolls of the ship. `stages.py` lists what each stage's files hold and places ground units, `waves.py` has every stage's air waves; `tiles.py`, `city.py`, `ocean.py`, `desert.py`, `arctic.py`, `orbit.py`, `luna.py`, `deep.py`, `sun.py` draw the stages, `boss.py`, `boss2.py`, `ship.py`, `wyrm.py`, `crawler.py`, `station.py`, `driver.py`, `hive.py`, `gamma.py` the bosses, `airpath.py` checks the waves against the sky, `hud.py` the HUD graphics. |
| `gtools/gen_sfx.py` | OPL2 sound effects in `music/sfx.bin`, `music/sfx/*.vgm`, `src/gen/sfx_ids.h` |
| `gtools/generate_music.py` | OPL2 music via Furnace (from RPDemo's composer): `music/fur_levels/*.fur` and `music/*.vgm` |
| `gtools/gen_tables.py` | Trig tables in `src/gen/tables.c` |

> **Warning:** Running `gtools/gen_art.py`, `gtools/gen_sfx.py`, or
> `gtools/generate_music.py` (without `--scratch`) will overwrite the
> corresponding static assets in `images/` and `music/`.

## Graphics & Stage Generation (`gtools/gen_art.py`)

```sh
.venv/bin/python gtools/gen_art.py [--preview DIR]
```

The PNG sheets written to `images/*.png` and `images/stage<N>/*.png` are
indexed 16-color images with frames side by side, so they open directly in
Aseprite.

Enemy waves are laid out clear of sky-layer obstacles: the sky scrolls a
fixed amount for every pixel the ground does, so `gtools/art/airpath.py`
flies every wave over the sky when `gen_art.py` runs and stops on any that
would run into one, naming the nearest clear place to move it.

## Music Generation (`gtools/generate_music.py`)

The remastered tracks in `music/fur_levels/*.fur` and `music/*.vgm` no
longer match `gtools/music_manifest.json`. Running `generate_music.py`
without `--scratch` writes over them, so use it only for new material. The
rest of this section describes how the original tracks were generated.

### The generator

The title, stage 1 and stage 1 boss music use style 9, **silvergun**, written for this game in
`gtools/musicgen/silvergun.py`: orchestral-epic instead of RPDemo's
electronic styles, but with a rock kit underneath for drive. That means
brass and string leads playing phrases and 16th-note runs, galloping
string ostinatos, octave-jumping bass, choir pads, timpani, a bass drum and
hi-hat groove, crashes and orchestra hits, chromatic "epic minor" harmony,
and optional 6/8 time. Tempo comes in steps, because a 16th note is a whole
number of 60 Hz ticks: 6 ticks is 150 bpm, 5 is 180.

Four more styles, in `gtools/musicgen/arcade.py`, give you something else
to try with `--style`:

| Style | Sound |
|---|---|
| 10 **fmrock** | Mega Drive FM rock: distorted guitar or synth brass riffs, palm-muted 16th chug, picked bass, rock organ, double-kick runs |
| 11 **eurobeat** | Synth brass hooks, a two-octave 16th broken-chord sequence, octave bass on every 8th, four-on-the-floor kick |
| 12 **chiparcade** | Square leads, a fast one-row-per-note chord arpeggio, bouncing bass, and the pad channel used as an echo of the lead |
| 13 **fusion** | Sax or synth lead, electric piano stabs, slap bass with octave pops and ghost notes, a busy funk kit |

Stage 2 uses eurobeat, stage 3 fusion and the battleship fmrock, stage 4 silvergun with Phrygian chords (`--prog 6,7`) and the wyrm fmrock, stage 5 chiparcade and the crawler eurobeat, stage 6 fusion and the station silvergun, stage 7 eurobeat and the mass driver fmrock, stage 8 trance and the mothership dnb, stage 9 silvergun and GAMMA PRIME fmrock (`Final.vgm`); the stage 2 boss reuses `Boss.vgm`.
`Victory.vgm` (and its `.fur`) comes from RPDemo as it is, and plays once after a boss is destroyed.
`Gameover.vgm` is generated (style 9, `"form": "jingle"` in its mood: one phrase and a cadence home, played once).
All four are in 4/4. On a 6/8 track (the boss), they keep the same eighth-note
pulse, so they play 1.5 times as fast.

The base mix already includes the `--vol -3,3,0,0,0,0,12` balance that
RPDemo's tracks always needed, so `vol` offsets in the manifest start at 0. Track moods
(key, tempo, meter, intensity) are in `gtools/musicgen/tracks.py`.

Every generated track is recorded in `gtools/music_manifest.json`: its
seed, style, per-role volume offsets and patches, mood, and the exact
command. To tweak a track, edit its `vol` or `patch` there (roles in
`lead,arp,bass,pad,kick,snare,hat` order; patches are hex indices into
RPTracker's bank) and rebuild it without re-rolling the composition:

```sh
.venv/bin/python gtools/generate_music.py --track boss --from-manifest --export-vgm
.venv/bin/python gtools/generate_music.py --track all --from-manifest --export-vgm
```

`--vol`/`--patch` on that command line override the recorded values for
one run. A new `--seed` re-rolls the composition. Then rebuild the game.

To change only the chords, pick the two themes' progressions with
`--prog A,B`. `--list-progs` prints the banks, such as the "royal road"
IV-V-iii-vi. The melody, rhythms and instruments of the seed stay the same,
and the choice is recorded in the manifest:

```sh
.venv/bin/python gtools/generate_music.py --list-progs            # every style's banks
.venv/bin/python gtools/generate_music.py --list-progs --style 11 # one style's
.venv/bin/python gtools/generate_music.py --track title --from-manifest --prog 6,0 --export-vgm
```

### Trying out new music

The `.vgm` files in `music/` are what the game plays. The build packs
every track's `music/<Track>.vgm` into the ROM as it is, so nothing else
needs converting. The `.fur` files are only for editing
in Furnace.

Add `--scratch` to try ideas without touching the game's tracks. Takes go
to `music/scratch/` (which is gitignored), are named by track, style and
seed, and are not recorded in the manifest:

```sh
# Each style once at the Stage 1 mood, to hear the differences.
for s in 9 10 11 12 13; do
  .venv/bin/python gtools/generate_music.py --track stage1 --style $s --scratch --export-vgm
done
# Then vary one you like: the same seed with other chords, or another tempo.
.venv/bin/python gtools/generate_music.py --track stage1 --style 11 --seed 42 --prog 2,3 --scratch --export-vgm
.venv/bin/python gtools/generate_music.py --track stage1 --style 11 --seed 42 --bpm 150 --scratch --export-vgm
```

Open a take's `.fur` in Furnace to listen and edit it. To hear it in the
game, either:

- **Keep it:** rerun the take's command without `--scratch`. Every run prints
  its command. That writes `music/Stage1.vgm` and records the take in the
  manifest.
- **Use your Furnace edits:** in Furnace, choose File > Export > VGM and save over
  `music/Stage1.vgm`. The songs this tool writes are already OPL2 only. You can also
  export without the GUI:
  `furnace -subsong 0 -loops 1 -vgmout music/Stage1.vgm music/scratch/<take>.fur`.

Then rebuild. The exported VGM must be plain OPL2 on channels 1-7: the
game's player doesn't understand OPL3, and channels 8-9 are kept for sound
effects.

`--bpm` takes any number, but the speed is a whole number of 60 Hz ticks
per 16th note, so the tempo lands on 900/n: 180, 150, 128.6, 112.5, 100.

See [`gtools/musicgen/README.md`](musicgen/README.md) for more details on
the composer internals and sound effects generator (`gtools/gen_sfx.py`).
