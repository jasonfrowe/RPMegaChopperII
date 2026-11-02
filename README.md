# RP Mega Chopper II: Operation Northern Lights

[![Picocomputer 6502](https://img.shields.io/badge/Platform-Picocomputer%206502-blue.svg)](https://picocomputer.github.io/)
[![Compiler](https://img.shields.io/badge/Compiler-llvm--mos-green.svg)](https://llvm-mos.org/)
[![Sound](https://img.shields.io/badge/Audio-Yamaha%20OPL2%20(YM3812)-orange.svg)](https://picocomputer.github.io/)

A fast-paced tactical helicopter rescue game for the **Picocomputer 6502**, sequel to *RPMegaChopper*.

Built from the ground up utilizing the modern RP6502 SDK, **RP Mega Chopper II** takes full advantage of the Picocomputer's hardware capabilities:
* **Mode 5 Custom 4bpp Sprites**: Multi-frame animated sprites with native custom dimensions (32×16 SuperChopper, 40×16 patrolling Heavy Tanks, 32×16 Supersonic Jets, 16×32 Drone Balloons, 16×16 Hostages, Canadian Maple Leaf flags, weakpoint target reticles, and particle explosions).
* **Mode 2 Parallax Scrolling**: Dual-layer 4bpp tilemaps spanning a 4,096-pixel world. Plane 0 scrolls distant snowy peaks and aurora skies at 3/8 speed; Plane 1 renders the snowbanks, pine forests, medical camps, and enemy compounds with horizontal wrap-around.
* **Top Status HUD**: Plane 2 overlay featuring real-time Score, Saved Hostages, Cargo count (`00/16`), Casualties Lost, Spare Choppers, and a dynamic 22-character tactical Radar / Compass.
* **Yamaha OPL2 Sound & Music**: True 9-channel FM synthesis audio engine powered by the `xreg_ria_opl` soundcard. Features custom VGM streaming (with an iconic driving 16th-note **Airwolf** galloping synth bass and brass lead) plus prioritized polyphonic sound effects (rotor engine, vulcan fire, falling bombs, tank shells, jet flybys, compound breaches, and hostage rescue chimes).

---

## Story & Mission: Operation Northern Lights

Deep in the frozen Northern Arctic frontier, hostile forces have captured allied researchers and soldiers across heavily fortified compound bunkers. 

As pilot of the experimental **SuperChopper**, your mission is to:
1. Infiltrate enemy territory across a 4,096-pixel hostile corridor.
2. Bomb the reinforced blast doors of enemy bunkers to free hostages trapped inside.
3. Land safely on the snowbanks so freed hostages can reach and board your transport hold.
4. Ferry hostages back to the Canadian Home Base medical station at the western perimeter.
5. Evacuate every hostage without letting enemy armor, jet fighters, or anti-air flak destroy your aircraft or slaughter the fleeing survivors!

---

## Controls

| Action | Keyboard | Gamepad |
| :--- | :--- | :--- |
| **Move / Altitude** | Arrow Keys / `W`, `A`, `S`, `D` | D-Pad / Left Analog Stick |
| **Fire Vulcan / Drop Bomb** | `Z`, `J`, or `Space` | Button **A** / **R1** |
| **Rotate Facing (L / Front / R)** | `X`, `K`, or `C` | Button **B** / **C** / **X** / **L1** |
| **Start / Pause** | `Enter` / `P` | **Start** / **Select** |

### Flight & Combat Tactics
* **Vulcan Cannon**: When facing **Left** or **Right**, primary fire shoots high-velocity auto-cannon rounds horizontally to neutralize aerial drones, incoming jets, and enemy tanks.
* **Precision Bombing**: Press **Rotate** to orient your chopper facing **Front** toward the screen. Primary fire now drops free-fall aerial bombs inheriting the chopper's horizontal velocity. Bombs detonate on ground contact, destroying tanks and breaching reinforced compound blast doors.
* **Hostage Boarding**: Come to a full landing on ground snow (`chopper_y >= GROUND_Y` with horizontal velocity = 0). Waving hostages will immediately sprint toward your chopper and climb aboard.
* **Cargo Capacity**: Your cargo bay holds up to **16 hostages**. If full, you must fly back to Home Base to disembark survivors before rescuing more.
* **Home Base Disembarkation**: Land near the Canadian flag and medical tents at the western end of the sector ($X < 360$). Hostages will exit the helicopter and run inside the medical shelter, earning rescue bonus points.

---

## Tactical Radar Display

The top status bar incorporates a horizontal real-time radar strip:
```text
SCORE:000000 SAVED:00 CARGO:00/16 LOST:00 [H  .  .  .  ^  .  .  ] x3
```
* `H`: Canadian Home Base / Medical Outposts
* `.`: Compound Bunkers (blinks when breached)
* `^`: SuperChopper position and flight vector
* `*`: Hostages running on foot in the snow

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

## Headless Testing & Emulation

The repository includes test tools and the `rp6502-emu` emulator:

```bash
# Run 60 frames headlessly and capture screenshot
tools/rp6502-emu build/llvm-mos/release/RPMegaChopperII.rp6502 --frames 60 --screenshot /tmp/screen.png --mute

# Run automated flight playtest script verifying 60 Hz frame synchronization:
python3 tools/playtest.py flight --out /tmp/flight_test
```

---

## Project Structure

```
RPMegaChopperII/
├── CMakeLists.txt              # Build configuration & asset conversion rules
├── CMakePresets.json           # llvm-mos and toolchain presets
├── README.md                   # This documentation
├── gtools/                     # Generation tools (musicgen, gen_art, gen_sfx)
│   ├── gen_art.py              # Pure Python 4bpp sprite & Mode-2 tilemap generator
│   ├── gen_sfx.py              # OPL2 FM sound effect bank synthesizer
│   └── musicgen/               # Airwolf & arcade style VGM generator
├── images/                     # Generated 4bpp sprite PNGs, maps, and palettes
│   ├── chopper.png             # 32x16 SuperChopper sprite sheet (22 frames)
│   ├── tank.png                # 40x16 Heavy Tank sprite sheet (6 frames)
│   ├── jet.png                 # 32x16 Fighter Jet sprite sheet (2 frames)
│   ├── balloon.png             # 16x32 Drone Balloon sheet (3 frames)
│   ├── hostages.png            # 16x16 Hostage sprites (10 frames)
│   ├── bg_tiles.png            # Parallax background tiles
│   ├── fg_tiles.png            # Foreground terrain & compound tiles
│   ├── bg_map.bin / fg_map.bin # 256x15 Mode-2 world maps
│   └── palettes.bin            # 16 RGB555 4bpp palettes
├── music/                      # OPL2 VGM streaming tracks & sfx.bin
│   ├── Stage1.vgm              # Airwolf style stage music
│   ├── Title.vgm               # Title theme
│   ├── Victory.vgm             # Sector clear theme
│   ├── Gameover.vgm            # Game over theme
│   └── sfx.bin                 # OPL2 synthesized sound effects
├── src/                        # 6502 C Game Source Code
│   ├── main.c                  # Main game loop, states & vsync timing
│   ├── xram.h                  # RIA XRAM memory map and hardware registers
│   ├── game.h                  # Physics constants and world metrics
│   ├── player.c / .h           # Chopper flight mechanics, bombing & landing
│   ├── compounds.c / .h        # Compound bunkers, targeting reticles & breach
│   ├── hostages.c / .h         # Hostage AI, panic, boarding & rescue states
│   ├── enemies.c / .h          # Tanks, Jets, Drone balloons & flag animation
│   ├── projectiles.c / .h      # Bullets, bombs, flak shells & explosions
│   ├── sprites.c / .h          # Mode 5 custom 4bpp sprite manager
│   ├── bg.c / .h               # Mode 2 parallax scrolling and blast door destruction
│   ├── hud.c / .h              # Plane 2 status bar and tactical radar
│   ├── input.c / .h            # Keyboard and USB gamepad polling
│   ├── opl.c / .h              # Low-level Yamaha OPL2 hardware register I/O
│   ├── vgm.c / .h              # ROM streaming VGM background music player
│   └── sfx.c / .h              # Polyphonic OPL2 FM sound effect player
└── tools/                      # RP6502 toolchain, emulator & conversion utilities
```

---

## License

Picocomputer 6502 software and SDK are licensed under open-source terms. See individual source files for copyright details.
