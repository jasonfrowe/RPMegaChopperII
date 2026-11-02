"""Registry of the game's music slots and the mood each one should evoke.

Mapping confirmed by reading MegaGammaForce's source directly:
  - src/music.c              default/title track
  - src/gameplay.c           track_for_level() -- one distinct track per
                              level 1-7; level 8+ falls back to Level_07
                              (there's no higher-level track, so the last
                              one just keeps playing)
  - src/gameplay.c           gameplay_reset_to_title_scene() -> title track
  - src/gameplay_boss.c      BOSS_STAGE_MUSIC_TRACK (src/constants.h)
  - src/level_bonus.c        bonus round
  - src/gameplay_game_over.c game over (loss) / victory (win)

`resource` is both the ROM asset name game code opens via
"ROM:<resource>.vgm" (see CMakeLists.txt's
rp6502_asset(... <resource>.vgm music/<resource>.vgm) lines)
and this tool's output filename stem (music/<resource>.vgm,
music/fur_levels/<resource>.fur) -- so it doubles as the single source of
truth tying the generator, the build, and the game's `music_set_track()`
calls together. Previously these were opaque "RESOURCE.NNN" ids (a
leftover of an older, smaller track count that reused one track across two
levels, e.g. level 1 & 5 shared RESOURCE.005) -- renamed to these
self-documenting names once every level got its own distinct track.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MoodPreset:
    """Musical parameters for a track's mood. Semitone 0 = C.

    `intensity` (0.0-1.0) places the track on the game's arc and drives
    compose.py's choice of chord progressions (title/early levels stay
    simple and diatonic; boss fights and late levels pull from a pool of
    more harmonically restless progressions) and whether the contrasting
    B-theme/bridge modulates to a different key.
    """

    key_root: int
    scale: str
    bpm: float
    intensity: float
    target_seconds: float = 170.0
    lead_octave: int = 5
    arp_octave: int = 4
    bass_octave: int = 2
    use_drums: bool = True
    meter: str = "4/4"  # "4/4", "6/8" or "3/4"; styles 9 and up read it
    # "song" (intro, themes, bridge, outro; loops) or "jingle": two phrases,
    # the second a cadence home, played once (styles 9 and up)
    form: str = "song"


@dataclass
class TrackSpec:
    resource: str  # e.g. "Level_01" -- ROM asset name and output filename stem
    description: str
    aliases: list
    mood: MoodPreset


TRACKS: list = [
    TrackSpec(
        resource="Title",
        description="Title / attract screen",
        aliases=["title"],
        # Heroic major fanfare.
        mood=MoodPreset(key_root=2, scale="major", bpm=150, intensity=0.55, target_seconds=100.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage1",
        description="Stage 1, Sky Fortress",
        aliases=["stage1", "level1"],
        # 180 bpm: 5 ticks a 16th at 60 Hz (6 ticks would be 150).
        mood=MoodPreset(key_root=9, scale="minor", bpm=180, intensity=0.70, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage2",
        description="Stage 2, Neon Spires",
        aliases=["stage2", "level2"],
        mood=MoodPreset(key_root=4, scale="minor", bpm=150, intensity=0.75, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage3",
        description="Stage 3, Iron Tide",
        aliases=["stage3", "level3"],
        mood=MoodPreset(key_root=2, scale="minor", bpm=150, intensity=0.75, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Boss3",
        description="Boss battle, battleship LEVIATHAN",
        aliases=["boss3"],
        mood=MoodPreset(key_root=0, scale="minor", bpm=180, intensity=0.95, target_seconds=120.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage4",
        description="Stage 4, Scorched Sands",
        aliases=["stage4", "level4"],
        mood=MoodPreset(key_root=4, scale="minor", bpm=150, intensity=0.75, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Boss4",
        description="Boss battle, DUNE WYRM",
        aliases=["boss4"],
        mood=MoodPreset(key_root=1, scale="minor", bpm=180, intensity=0.95, target_seconds=120.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage5",
        description="Stage 5, Frozen Strait",
        aliases=["stage5", "level5"],
        mood=MoodPreset(key_root=11, scale="minor", bpm=160, intensity=0.8, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Boss5",
        description="Boss battle, GLACIER CRAWLER",
        aliases=["boss5"],
        mood=MoodPreset(key_root=6, scale="minor", bpm=172, intensity=0.95, target_seconds=120.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage6",
        description="Stage 6, Ascent",
        aliases=["stage6", "level6"],
        mood=MoodPreset(key_root=2, scale="minor", bpm=156, intensity=0.85, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Boss6",
        description="Boss battle, HALO STATION",
        aliases=["boss6"],
        mood=MoodPreset(key_root=9, scale="minor", bpm=176, intensity=0.95, target_seconds=120.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage7",
        description="Stage 7, Sea of Tranquility",
        aliases=["stage7", "level7"],
        mood=MoodPreset(key_root=7, scale="minor", bpm=148, intensity=0.8, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Boss7",
        description="Boss battle, MASS DRIVER",
        aliases=["boss7"],
        mood=MoodPreset(key_root=4, scale="minor", bpm=184, intensity=1.0, target_seconds=120.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage8",
        description="Stage 8, Deep Field",
        aliases=["stage8", "level8"],
        mood=MoodPreset(key_root=2, scale="minor", bpm=140, intensity=0.8, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Boss8",
        description="Boss battle, HIVE MOTHERSHIP",
        aliases=["boss8"],
        mood=MoodPreset(key_root=11, scale="minor", bpm=174, intensity=1.0, target_seconds=120.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Stage9",
        description="Stage 9, Corona",
        aliases=["stage9", "level9"],
        mood=MoodPreset(key_root=9, scale="minor", bpm=160, intensity=0.9, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Final",
        description="Final boss, GAMMA PRIME",
        aliases=["final"],
        mood=MoodPreset(key_root=2, scale="minor", bpm=188, intensity=1.0, target_seconds=150.0, lead_octave=5),
    ),
    TrackSpec(
        resource="Gameover",
        description="Game over",
        aliases=["gameover"],
        # Slow and dark: a phrase, then a cadence home, once.
        mood=MoodPreset(key_root=9, scale="minor", bpm=84, intensity=0.3, target_seconds=20.0, lead_octave=5,
                        form="jingle"),
    ),
    TrackSpec(
        resource="Victory",
        description="Mission accomplished, victory fanfare",
        aliases=["victory"],
        mood=MoodPreset(key_root=2, scale="major", bpm=150, intensity=0.6, target_seconds=20.0, lead_octave=5,
                        form="jingle"),
    ),
    TrackSpec(
        resource="Boss",
        description="Boss battle, GAMMA CORE",
        aliases=["boss"],
        # Galloping 6/8; bpm counts dotted quarters.
        mood=MoodPreset(key_root=4, scale="minor", bpm=120, intensity=0.95, target_seconds=110.0,
                         lead_octave=5, arp_octave=4, meter="6/8"),
    ),
]

_ALIAS_INDEX = {}
for _t in TRACKS:
    _ALIAS_INDEX[_t.resource] = _t
    for _a in _t.aliases:
        _ALIAS_INDEX[_a] = _t


def resolve(name: str) -> TrackSpec:
    key = name.strip().lower()
    for candidate_key, spec in _ALIAS_INDEX.items():
        if candidate_key.lower() == key:
            return spec
    raise KeyError(f"unknown track '{name}'. Known: {sorted(set(_ALIAS_INDEX.keys()))}")
