# RP Mega Chopper II: Operation Northern Lights

[![Picocomputer 6502](https://img.shields.io/badge/Platform-Picocomputer%206502-blue.svg)](https://picocomputer.github.io/)
[![Compiler](https://img.shields.io/badge/Compiler-llvm--mos-green.svg)](https://llvm-mos.org/)
[![Sound](https://img.shields.io/badge/Audio-Yamaha%20OPL2%20(YM3812)-orange.svg)](https://picocomputer.github.io/)

<!-- rp6502
preset: llvm-mos/Release
publish: RPMegaChopperII.zip
frames: 120
-->
[![RPMegaChopperII](https://jasonfrowe.github.io/RPMegaChopperII/RPMegaChopperII/screenshot.png)](https://jasonfrowe.github.io/RPMegaChopperII/RPMegaChopperII/)

A fast-paced tactical helicopter rescue game for the **Picocomputer 6502**, sequel to *RPMegaChopper*.

Built from the ground up on the modern RP6502 SDK, using all three VGA planes:
* **Three-depth parallax**: a night sky with a shimmering, palette-cycled **aurora** and a snowy mountain range (plane 0, 8x8 tiles, quarter speed), rolling hills, pine forests, lit cabins and blinking radio masts (plane 1, half speed), and the 4,608-pixel battlefield itself (plane 2, 16x16 tiles).
* **Mode 5 sprites** drawn with lighting and outlines: a 40x20 rescue chopper that pitches nose-down to accelerate and turns to face the screen to bomb, winter-camo tanks, interceptor jets, tethered mine balloons, running and waving hostages, a rippling maple-leaf flag, fireball explosions and falling snow. Right-facing frames are hardware flips.
* **Blizzards**: now and then a storm blows in. The mountains and hills fade into a whiteout (the palettes blend toward a haze), driven snow streams across the screen, and gusting wind pushes the chopper about. They are milder in the first sectors.
* **Title logo** in 1-bit sprites, drawn three times (shadow, rim, face) for a bevel.
* **Status bar and message box** in Mode 1 text, sharing plane 2 with the ground on their own scanlines: score, rescued and lost counts, spare choppers, a 16-seat cargo gauge and a radar of the whole sector.
* **Yamaha OPL2 music and sound**: VGM streaming of the Airwolf-style soundtrack on channels 1-7, sound effects on 8-9.

---

## Story & Mission: Operation Northern Lights

Deep in the frozen Northern Arctic frontier, hostile forces have captured allied researchers and soldiers across heavily fortified compound bunkers. 

As pilot of the experimental **SuperChopper**, your mission is to:
1. Infiltrate enemy territory across a 4,608-pixel hostile corridor.
2. Bomb the reinforced blast doors of enemy bunkers to free hostages trapped inside.
3. Land safely on the snowbanks so freed hostages can reach and board your transport hold.
4. Ferry hostages back to the Canadian Home Base medical station at the eastern end of the sector.
5. Evacuate every hostage without letting enemy armor, jet fighters, or anti-air flak destroy your aircraft or slaughter the fleeing survivors!

---

## Controls

| Action | Keyboard | Gamepad |
| :--- | :--- | :--- |
| **Fly** | Arrow keys / `W` `A` `S` `D` | D-pad / left stick |
| **Fire cannon / drop bomb** | `Z`, `J` or `Space` | **A** / **R1** |
| **Turn (left / front / right)** | `X`, `K` or `C` | **B** / **C** / **X** / **L1** |
| **Start / pause** | `Enter` / `P` | **Start** / **Select** |

### How to play
* **Pick a sector** on the title screen with left and right; the title flies over it. Press fire to start there.
* **Open the prisons.** Each of the four compounds has a blast door marked with a red target. Shoot it, or turn to face the screen and drop a bomb on it. Bombs fall straight down, one at a time.
* **The cannon aims with the nose.** Speeding up tips the nose down and the tracers go down with it, which is how you hit doors and tanks; braking tips it up.
* **Pick them up.** Freed hostages spread out in front of their prison. Come in low and they run for the chopper; land and they climb aboard, 16 at most. Don't come down on top of them.
* **Bring them home.** Land on the helipad by the medical station at the east end. They get off one at a time and run inside. Each one saved is 250 points.
* **Watch out.** The enemy follows the original game's rules (written up in [`docs/ORIGINAL_GAMEPLAY.md`](docs/ORIGINAL_GAMEPLAY.md)):
  * **Tanks** turn up once 4 hostages are aboard or saved, two at a time from the prison you are nearest, and keep coming: a destroyed tank goes back to its prison's garage. Your cannon can't hurt them. **Only a bomb dropped from high enough** (more than 60 px up) reaches them; dropped lower it bursts on the ground short of them. Their shells arc up and fall back, so they can't reach you up high, but a shell coming down can hit a hostage.
  * A **mine blimp** drifts after you once 24 hostages are out. Shoot it down. It won't cross the border.
  * **Jets** come once the third prison is open. Sit on the ground more than 2 seconds and a bomber may come; stay up high more than 4 seconds and a fighter may. You get a warning: "JET INBOUND!" and a red reticle at the edge of the screen it will come from, at the height it will fly.
  * Nothing attacks near the **home base**, east of the border flag.
  * **Blizzards** blow in from time to time: it gets hard to see, and the wind pushes you sideways, up to about a third of your top speed in the gusts. They pass in 20 seconds or so.
  * If the chopper goes down, everyone aboard is lost.
* **Sector 2, the lakes**: boreal forest and frozen lakes under the aurora, with different enemies:
  * **Jeeps** in place of tanks: the same zones and patrols, but twice as fast, and they fire machine-gun bursts straight at you. Their rounds don't carry far, so climb. Strafe them with the cannon (nose down) or bomb them from high up.
  * **Rocket turrets** in place of the blimp: one east of each prison, manned once it is open. When its red light blinks it is about to fire a rocket that steers toward you for about a second, then flies straight: turn hard. Shoot or bomb the turret; it is rebuilt in 15 seconds. The cannon can also shoot rockets down.
  * **Worms** in place of jets, once two prisons are open: sit on the ground too long and a ridge of earth tunnels toward you. Lift off before it gets there, or bomb the ridge.
* After the last sector the game goes round again, harder: sooner tanks and jeeps, earlier jets and worms, stronger storms.
* **Sector clear** when every hostage is home or lost, with a 200-point bonus for each one saved. An extra chopper every 20,000 points.

### Radar
The bottom row of the status bar shows the whole sector: prisons in red while still shut (orange while hostages are still inside, grey once empty), hostages on foot as `*`, home base at the right, and you as the flashing arrow.

---

## Building from Source

### Prerequisites
* **CMake** 3.28 or newer
* **Python** 3.8+
* **llvm-mos** compiler installed (default: `~/.rp6502/llvm-mos/bin`)
* **Furnace tracker CLI** (optional, for regenerating VGM sound tracks)

### Compiling
Configure and build with CMake using the provided presets:

```bash
# Configure Release build
cmake --preset llvm-mos/Release

# Build executable ROM and Web package
cmake --build --preset llvm-mos/Release
```

Output files will be generated in `build/llvm-mos/release/`:
* `RPMegaChopperII.rp6502`: Executable ROM image for real Picocomputer 6502 hardware or SD card.
* `RPMegaChopperII.elf`: Debug ELF binary with symbols.
* `web/RPMegaChopperII.zip`: Web player package ready for browser deployment via GitHub Pages.

---

## Graphics

All the art is generated by `gtools/gen_art.py` (needs Pillow and numpy, see
[`gtools/README.md`](gtools/README.md)); the PNGs it writes in `images/` can be touched up by
hand. Each background layer is painted as one image and then cut into tiles; where it
needs more tiles than its share of XRAM, the most similar tiles are merged until it fits.

Each level's own art (its enemies, three tile layers, maps and palettes) lives in
`images/level<N>/`. The build packs it into `ROM:level<N>.bin` (`tools/mklevel.py`), and the
game reads it into XRAM when the level starts, as MegaGammaForce does with its stages.

```bash
.venv/bin/python gtools/gen_art.py --preview /tmp/preview   # also writes mock screens
```

## Headless Testing & Emulation

```bash
# Run 100 frames headlessly and capture a screenshot
tools/rp6502-emu build/llvm-mos/release/RPMegaChopperII.rp6502 --frames 100 --screenshot /tmp/screen.png --mute

# Scripted playtests, with screenshots and the game's numbers:
python3 tools/playtest.py rescue --out /tmp/rescue      # open a prison, load up, unload at home
python3 tools/playtest.py campaign --out /tmp/campaign  # all 64 hostages, to the sector clear
python3 tools/playtest.py gameover --out /tmp/gameover
python3 tools/playtest.py soak --phi2 4000              # dropped frames with the 6502 at half speed
python3 tools/playtest.py ambush --stage 2              # any of them on another level
```

---

## Project Structure

```
RPMegaChopperII/
├── gtools/                  # Generators (not part of the build)
│   ├── gen_art.py           # Every graphic: sprites, tiles, maps, palettes, src/gen/assets.h
│   ├── chop/                # The art: far.py, mid.py, fg.py (level 1's layers), boreal.py
│   │                        #   (level 2's), sprites.py, boreal_sprites.py, logo.py,
│   │                        #   pal.py (palettes), tilemap.py (cutting and fitting tiles)
│   ├── art/kit.py           # Lit, outlined pixel-art shapes (from MegaGammaForce)
│   ├── gen_sfx.py           # OPL2 sound effects
│   └── generate_music.py    # OPL2 music via Furnace
├── images/                  # Generated PNG sheets; level<N>/: each level's bank
├── music/                   # VGM tracks and sfx.bin
├── src/
│   ├── main.c               # Main loop and game states
│   ├── xram.h               # XRAM layout and sprite slots
│   ├── game.h               # World and flight constants
│   ├── bg.c                 # The three tile layers, door tiles, palette animation
│   ├── hud.c                # Status bar and message box
│   ├── player.c             # Flight, cannon and bombs
│   ├── compounds.c          # Prisons and their doors
│   ├── hostages.c           # Hostages: waiting, boarding, running home
│   ├── level.c              # The levels: settings, and loading each one's bank
│   ├── enemies.c            # Tanks or jeeps, jets, balloon, turrets, worms, the flags
│   ├── projectiles.c        # Shots, bombs, flak and explosions
│   ├── fx.c                 # Falling and blowing snow
│   ├── weather.c            # Storms: when they come, how strong, the wind
│   └── sprites.c, input.c, opl.c, vgm.c, music.c, sfx.c
└── tools/                   # Toolchain, emulator, png2bin.py, mklevel.py, playtest.py
```

---

## License

Picocomputer 6502 software and SDK are licensed under open-source terms. See individual source files for copyright details.
