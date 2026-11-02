"""Styles 10-13: four more action styles for MegaGammaForce, each a
different take on 80s/90s arcade and home-console shooter music. They share
style 9's arrangement (compose._generate_kit) and harmony helpers, but each
has its own instruments, chord banks, and bass/arp/pad/drum writing:

- **10 "fmrock"**: Mega Drive FM rock (Thunder Force, Gley Lancer).
  Distorted guitar or synth brass lead playing riffs, palm-muted 16th chug
  on root and fifth, picked 8th-note bass, rock organ pad, a rock kit with
  double-kick runs when hot.
- **11 "eurobeat"**: Eurobeat. Synth brass hook with syncopated
  rhythms, a 16th-note broken-chord sequence over two octaves, octave
  "oom-pah" bass on every 8th, polysynth pad, four-on-the-floor kick with
  offbeat hats.
- **12 "chiparcade"**: chiptune arcade. Square leads, a fast every-row chord
  arpeggio, bouncing root/octave bass, and the pad channel turned into an
  echo of the lead three rows behind, the classic one-channel delay trick.
- **13 "fusion"**: Japanese fusion (Gradius, T-Square era). Sax or synth
  lead with syncopated phrases, electric piano comping stabs, slap bass
  with octave pops and ghost notes, string pad, a busy funk kit.

All four are 4/4. A 6/8 mood (the Boss track) plays them 1.5x faster, at
the same eighth-note pulse. MoodPreset.intensity still sets the energy:
0.5 and up gets 16th-note lead runs, 0.75 and up the busiest drums.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .furwriter import NOTE_OFF, RowCell, note_value
from .silvergun import (CRASH, HAT, HIGH_TOM, KICK, LOW_TOM, SNARE, Chord, _chord_tones, _nearest_chord_tone,
                        _scale_for, _step)

OPEN_HAT = HAT  # the kit has one hat; open hats are played louder
RPB, BEAT = 16, 4  # 4/4 on the 16th grid


@dataclass
class Style:
    name: str
    pools: Dict[str, List[int]]  # melodic patches, 00-7F only
    minor_bank: List[Tuple[int, List[Chord]]]
    major_bank: List[Tuple[int, List[Chord]]]
    motifs: List[List[int]]   # lead bar rhythms, in rows
    drive: List[List[int]]    # busier lead rhythms for intensity >= 0.5
    bass: Callable
    arp: Callable
    pad: Callable
    drums: Callable

    # The interface compose._generate_kit expects (silvergun.py has the same).
    def meter_rows(self, meter: str) -> Tuple[int, int]:
        return RPB, BEAT

    def tempo(self, mood) -> float:
        return mood.bpm * 1.5 if mood.meter == "6/8" else mood.bpm

    def pick_instruments(self, rng: random.Random) -> Dict[str, int]:
        ins = {role: rng.choice(pool) for role, pool in self.pools.items()}
        ins["kick"], ins["snare"], ins["hat"] = KICK, SNARE, HAT
        return ins

    def bank(self, major: bool):
        return self.major_bank if major else self.minor_bank

    def pick_progressions(self, rng: random.Random, intensity: float, major: bool,
                          override: Optional[Tuple[int, int]] = None):
        bank = self.bank(major)

        def weight(tier):
            return 1.0 if tier == 1 else max(0.2, intensity * 1.6) if tier == 2 else max(0.0, intensity - 0.4) * 2.5

        idxs = list(range(len(bank)))
        out = []
        for _ in range(2):
            pick = rng.choices(idxs, weights=[weight(bank[i][0]) + 0.02 for i in idxs], k=1)[0]
            out.append(pick)
            idxs.remove(pick)
        if override is not None:
            out = list(override)
        for i in out:
            if not 0 <= i < len(bank):
                raise ValueError(f"progression {i} is not in {self.name}'s {'major' if major else 'minor'} bank "
                                 f"(0-{len(bank) - 1})")
        return bank[out[0]][1], bank[out[1]][1], out[0], out[1]

    def generate_chunk(self, rng, mood, ins, chords, root, base_vol, jitter, bars):
        return _chunk(self, rng, mood, ins, chords, root, base_vol, jitter, bars)


class _Ctx:
    """One chunk being written: the rows, and helpers to put notes in them."""

    def __init__(self, rng, mood, ins, base_vol, jitter):
        self.rng, self.mood, self.ins, self.base_vol, self.jitter = rng, mood, ins, base_vol, jitter
        self.rows: Dict[str, Dict[int, RowCell]] = {r: {} for r in ("lead", "arp", "bass", "pad", "kick", "snare",
                                                                     "hat")}
        self.drive = mood.intensity >= 0.5
        self.hot = mood.intensity >= 0.75
        self.state: Dict[str, object] = {}  # per-chunk choices a role makes once and keeps

    def put(self, role, row, pitch, ins_idx=None, vol_add=0):
        """pitch is an absolute semitone (12 * octave + pitch class)."""
        j = self.jitter.get(role, 3)
        v = self.base_vol[role] + vol_add + self.rng.randint(-j, j)
        self.rows[role][row] = RowCell(note=note_value(pitch // 12, pitch % 12),
                                       ins=self.ins[role] if ins_idx is None else ins_idx, vol=max(0, min(63, v)))

    def drum(self, role, row, ins_idx=None, vol_add=0):
        self.put(role, row, 36, ins_idx, vol_add)

    def off(self, role, row):
        if row not in self.rows[role]:
            self.rows[role][row] = RowCell(note=NOTE_OFF)


def _chunk(style, rng, mood, ins, chords, root, base_vol, jitter, bars):
    c = _Ctx(rng, mood, ins, base_vol, jitter)
    major = mood.scale in ("major", "mixolydian")
    rhythms = style.drive if c.drive else style.motifs
    motif = rng.choice(rhythms)
    motif_steps = [rng.choice([-2, -1, 1, 2, 3, -3, 4]) for _ in motif]
    pitch = _nearest_chord_tone(12 * mood.lead_octave + root, _chord_tones(root, chords[0]))
    for bar in range(bars):
        base = bar * RPB
        chord = chords[bar % len(chords)]
        tones = _chord_tones(root, chord)
        last = bar == bars - 1
        style.bass(c, base, tones, bar, last)
        style.arp(c, base, tones, bar, last)
        style.drums(c, base, tones, bar, last)
        # Lead: a hook, restated over each chord, a variation, a cadence.
        if last:
            rhythm = rng.choice([[16], [12, 4], [4, 12], [8, 8], [6, 10]])
            steps = [rng.choice([-1, 1]) for _ in rhythm]
        elif bar == 2 and rng.random() < 0.6:
            rhythm = rng.choice(rhythms)
            steps = [rng.choice([-1, 1]) * (1 if d < BEAT else 2) for d in rhythm]
        else:
            rhythm, steps = motif, motif_steps
        pitch = _lead_bar(c, base, rhythm, steps, pitch, tones, _scale_for(root, chord, major))
        style.pad(c, base, tones, bar, last)
    if style.pad is _pad_echo:
        _echo(c, bars * RPB)
    return c.rows


def _lead_bar(c, base, rhythm, steps, pitch, tones, pcs):
    pitch = _nearest_chord_tone(pitch, tones)
    lo, hi = 12 * (c.mood.lead_octave - 1) + 5, 12 * (c.mood.lead_octave + 1) + 7
    r = base
    for i, dur in enumerate(rhythm):
        if r >= base + RPB:
            break
        if i > 0:
            pitch = _step(pitch, steps[i], pcs)
            if dur >= BEAT:
                pitch = _nearest_chord_tone(pitch, tones)
        while pitch > hi:
            pitch -= 12
        while pitch < lo:
            pitch += 12
        c.put("lead", r, pitch, vol_add=(3 if r == base else 0))
        if dur >= 4 and r + dur - 1 < base + RPB:
            c.off("lead", r + dur - 1)
        r += dur
    return pitch


# ---- bass ---------------------------------------------------------------

def _bass_picked(c, base, tones, bar, last):
    """Rock: picked 8ths on the root, a fifth or octave on the last pair."""
    lo = 12 * c.mood.bass_octave + tones[0] % 12
    tail = c.state.setdefault("bass_tail", c.rng.choice([[0, 0], [7, 12], [12, 7], [0, 12]]))
    for k, r in enumerate(range(0, RPB, 2)):
        p = lo + (tail[k - 6] if k >= 6 else 0)
        c.put("bass", base + r, p, vol_add=(2 if r % BEAT == 0 else -1))
    if c.hot and last:
        for r in range(9, RPB, 2):
            c.put("bass", base + r, lo, vol_add=-4)


def _bass_octave(c, base, tones, bar, last):
    """Eurobeat: root, octave, root, octave on every 8th."""
    lo = 12 * c.mood.bass_octave + tones[0] % 12
    for r in range(0, RPB, 2):
        c.put("bass", base + r, lo + (12 if r % 4 else 0), vol_add=(2 if r % 4 == 0 else -1))
        c.off("bass", base + r + 1)


def _bass_bounce(c, base, tones, bar, last):
    """Chip: a bouncing 16th figure on root and octave."""
    lo = 12 * c.mood.bass_octave + tones[0] % 12
    fig = c.state.setdefault("bass_fig", c.rng.choice([
        [(0, 0), (2, 12), (3, 0), (4, 0), (6, 12), (8, 0), (10, 12), (11, 0), (12, 0), (14, 12)],
        [(0, 0), (2, 0), (4, 12), (6, 0), (8, 0), (10, 0), (12, 12), (14, 7)],
        [(0, 0), (3, 0), (6, 12), (8, 0), (11, 0), (14, 12)],
    ]))
    for r, iv in fig:
        c.put("bass", base + r, lo + iv, vol_add=(2 if r % BEAT == 0 else -2))
        c.off("bass", base + r + 1)


def _bass_slap(c, base, tones, bar, last):
    """Fusion: thumb on the root, popped octaves, ghosted notes between."""
    lo = 12 * c.mood.bass_octave + tones[0] % 12
    fig = c.state.setdefault("bass_fig", c.rng.choice([
        [(0, 0, 3), (3, 12, 0), (6, 0, 0), (8, 0, 2), (10, 12, 0), (11, 7, -6), (14, 12, 0)],
        [(0, 0, 3), (2, 0, -8), (3, 12, 0), (7, 0, 0), (8, 0, 2), (10, 10, 0), (12, 12, 0), (14, 7, -2)],
        [(0, 0, 3), (4, 12, 0), (6, 0, -6), (7, 0, 0), (10, 12, 0), (12, 0, 2), (13, 12, -4), (15, 7, -2)],
    ]))
    for r, iv, v in fig:
        c.put("bass", base + r, lo + iv, vol_add=v)
        c.off("bass", base + r + 1)


def _bass_airwolf(c, base, tones, bar, last):
    """Airwolf: driving 16th-note galloping synth bass with root-octave pulse."""
    lo = 12 * c.mood.bass_octave + tones[0] % 12
    pat = c.state.setdefault("airwolf_bass", c.rng.choice([
        [(0, 0), (2, 0), (3, 0), (4, 0), (6, 0), (7, 0), (8, 12), (10, 0), (11, 0), (12, 12), (14, 0), (15, 0)],
        [(0, 0), (1, 0), (2, 12), (3, 0), (4, 0), (5, 0), (6, 12), (7, 0), (8, 0), (9, 0), (10, 12), (11, 0), (12, 0), (13, 0), (14, 12), (15, 7)],
        [(0, 0), (2, 0), (3, 0), (4, 0), (6, 12), (8, 0), (10, 0), (11, 0), (12, 12), (14, 7), (15, 0)],
    ]))
    for r, iv in pat:
        c.put("bass", base + r, lo + iv, vol_add=(3 if r % BEAT == 0 else -1 if iv == 12 else -3))
        c.off("bass", base + r + 1)


# ---- arp ----------------------------------------------------------------

def _arp_chug(c, base, tones, bar, last):
    """Rock: palm-muted 16ths on the root, the fifth on accents."""
    lo = 12 * c.mood.arp_octave + tones[0] % 12 - 12
    pat = c.state.setdefault("chug", c.rng.choice([
        "x.xxx.xxx.xxx.x.", "xxx.xxx.xx.xxx.x", "x.x.xxx.x.x.xx.x", "xxxxxxxxxxxxxxxx",
    ]))
    for r, ch in enumerate(pat):
        if ch == "x":
            fifth = r in (6, 14) or (r == 10 and bar % 2)
            c.put("arp", base + r, lo + (7 if fifth else 0), vol_add=(3 if r % BEAT == 0 else -3))
            c.off("arp", base + r + 1)


def _arp_broken(c, base, tones, bar, last):
    """Eurobeat: 16th broken chord, up and down two octaves."""
    a = 12 * c.mood.arp_octave + tones[0] % 12
    t = [a, a + (tones[1] - tones[0]), a + 7]
    shape = c.state.setdefault("shape", c.rng.choice([
        [0, 1, 2, 3, 4, 3, 2, 1], [0, 2, 3, 2, 4, 2, 3, 1], [0, 1, 2, 1, 3, 2, 4, 2],
    ]))
    seq = [t[0], t[1], t[2], t[0] + 12, t[1] + 12]
    for r in range(RPB):
        c.put("arp", base + r, seq[shape[r % len(shape)]], vol_add=(3 if r % BEAT == 0 else -3))


def _arp_chip(c, base, tones, bar, last):
    """Chip: one row per chord tone, the fast arpeggio that fakes a chord."""
    a = 12 * (c.mood.arp_octave + 1) + tones[0] % 12
    t = [a, a + (tones[1] - tones[0]), a + 7]
    shape = c.state.setdefault("shape", c.rng.choice([[0, 1, 2], [0, 1, 2, 1], [0, 2, 1, 2]]))
    for r in range(RPB):
        c.put("arp", base + r, t[shape[(base + r) % len(shape)]], vol_add=-6)


def _arp_comp(c, base, tones, bar, last):
    """Fusion: electric piano stabs on the upper chord tones, syncopated."""
    hits = c.state.setdefault("comp", c.rng.choice([[2, 6, 10, 14], [3, 6, 11, 14], [0, 3, 8, 11, 14], [3, 7, 10]]))
    a = 12 * c.mood.arp_octave
    for k, r in enumerate(hits):
        t = tones[1 + k % 2]
        c.put("arp", base + r, a + t % 12, vol_add=(2 if k == 0 else 0))
        c.off("arp", base + r + 2)


def _arp_airwolf(c, base, tones, bar, last):
    """Airwolf: tight 16th-note analog sequencer ostinato."""
    a = 12 * c.mood.arp_octave + tones[0] % 12
    t = [a, a + (tones[1] - tones[0]), a + 7, a + 12]
    shape = c.state.setdefault("airwolf_arp", c.rng.choice([
        [0, 1, 2, 3, 2, 1, 0, 1, 2, 3, 2, 1, 2, 3, 2, 1],
        [0, 2, 1, 3, 0, 2, 1, 3, 0, 2, 1, 3, 2, 1, 3, 2],
        [3, 2, 1, 0, 3, 2, 1, 0, 3, 2, 1, 0, 1, 2, 3, 2],
    ]))
    for r in range(RPB):
        c.put("arp", base + r, t[shape[r % len(shape)] % len(t)], vol_add=(2 if r % BEAT == 0 else -4))
        c.off("arp", base + r + 1)


# ---- pad ----------------------------------------------------------------

def _pad_hold(c, base, tones, bar, last):
    """Voice-led chord tone held all bar."""
    p = c.state.get("pad", 12 * (c.mood.arp_octave - 1) + tones[1])
    p = _nearest_chord_tone(p, tones[1:])
    c.state["pad"] = p
    c.put("pad", base, p)


def _pad_echo(c, base, tones, bar, last):
    pass  # written after the whole chunk, by _echo


def _echo(c, rows):
    """The pad channel repeats the lead three rows later, quieter."""
    lead = c.rows["lead"]
    for r, cell in lead.items():
        e = r + 3
        if e < rows:
            if cell.note == NOTE_OFF:
                c.rows["pad"][e] = RowCell(note=NOTE_OFF)
            else:
                v = max(0, (cell.vol if cell.vol is not None else c.base_vol["lead"]) - 14)
                c.rows["pad"][e] = RowCell(note=cell.note, ins=c.ins["pad"], vol=v)


# ---- drums --------------------------------------------------------------

def _crash_or_fill(c, base, bar, last):
    if bar == 0:
        c.drum("hat", base, CRASH)
        return False
    if last and c.rng.random() < 0.5:
        for k, rr in enumerate(range(8, RPB, 2)):
            c.drum("hat", base + rr, HIGH_TOM if k < 2 else LOW_TOM)
        return True
    return False


def _snare_roll(c, base, last, chance=0.6):
    if last and c.rng.random() < chance:
        for rr in range(12, RPB):
            c.drum("snare", base + rr, vol_add=-8 + (rr - 12) * 2)
        return True
    return False


def _drums_rock(c, base, tones, bar, last):
    kicks = c.state.setdefault("kicks", c.rng.choice([[0, 8, 10], [0, 6, 8], [0, 3, 8, 11]]))
    for r in kicks:
        c.drum("kick", base + r)
    if c.hot and last:
        for r in range(8, RPB):
            c.drum("kick", base + r, vol_add=-3)  # double-kick run
    if not _snare_roll(c, base, last, 0.4):
        c.drum("snare", base + 4)
        c.drum("snare", base + 12)
    if not _crash_or_fill(c, base, bar, last):
        for r in range(0 if bar else 2, RPB, 2):
            c.drum("hat", base + r, vol_add=(-2 if r % BEAT == 0 else -8))


def _drums_four(c, base, tones, bar, last):
    for r in range(0, RPB, BEAT):
        c.drum("kick", base + r)
    if not _snare_roll(c, base, last):
        c.drum("snare", base + 4)
        c.drum("snare", base + 12)
    if not _crash_or_fill(c, base, bar, last):
        for r in range(0 if bar else 1, RPB):
            if r % BEAT == 2:
                c.drum("hat", base + r, OPEN_HAT if c.hot and r == 14 else HAT, vol_add=0)
            elif c.drive and r % 2 == 0 and r:
                c.drum("hat", base + r, vol_add=-10)


def _drums_chip(c, base, tones, bar, last):
    kicks = c.state.setdefault("kicks", c.rng.choice([[0, 8], [0, 6, 8], [0, 10]]))
    for r in kicks:
        c.drum("kick", base + r)
    if not _snare_roll(c, base, last):
        c.drum("snare", base + 4)
        c.drum("snare", base + 12)
        if c.hot:
            c.drum("snare", base + 15, vol_add=-10)
    if not _crash_or_fill(c, base, bar, last):
        step = 1 if c.hot else 2
        for r in range(0 if bar else 2, RPB, step):
            c.drum("hat", base + r, vol_add=(-4 if r % 2 == 0 else -12))


def _drums_funk(c, base, tones, bar, last):
    kicks = c.state.setdefault("kicks", c.rng.choice([[0, 3, 6, 10], [0, 7, 10], [0, 2, 7, 11]]))
    for r in kicks:
        c.drum("kick", base + r)
    if not _snare_roll(c, base, last, 0.4):
        c.drum("snare", base + 4)
        c.drum("snare", base + 12)
        for r in range(RPB):
            if r not in (4, 12) and c.rng.random() < 0.2:
                c.drum("snare", base + r, vol_add=-18)  # ghost notes
    if not _crash_or_fill(c, base, bar, last):
        for r in range(0 if bar else 1, RPB):
            if r == 14 and c.rng.random() < 0.5:
                c.drum("hat", base + r, OPEN_HAT, vol_add=-4)
            elif r % 2 == 0 or c.drive:
                c.drum("hat", base + r, vol_add=(-3 if r % 4 == 0 else -6 if r % 2 == 0 else -12))


def _drums_airwolf(c, base, tones, bar, last):
    """Airwolf: high-octane 80s action synth-pop drums."""
    kicks = [0, 4, 8, 12] if not c.hot else ([0, 6, 8, 12, 14] if (bar % 2 == 1) else [0, 4, 8, 12])
    for r in kicks:
        c.drum("kick", base + r)
    if not _snare_roll(c, base, last, 0.5):
        c.drum("snare", base + 4)
        c.drum("snare", base + 12)
        if c.hot and bar % 2 == 1:
            c.drum("snare", base + 15, vol_add=-8)
    if not _crash_or_fill(c, base, bar, last):
        for r in range(0 if bar else 1, RPB):
            if r % 4 == 2:
                c.drum("hat", base + r, OPEN_HAT if (c.drive and r == 14) else HAT, vol_add=0)
            else:
                c.drum("hat", base + r, HAT, vol_add=(-3 if r % 4 == 0 else -8))


def M(o):
    return (o, "M")


def m(o):
    return (o, "m")


STYLES: Dict[int, Style] = {
    10: Style(
        name="fmrock",
        pools={"lead": [29, 30, 29, 30, 62], "arp": [28, 28, 29], "bass": [33, 34, 33, 34],
               "pad": [18, 18, 61, 62]},
        minor_bank=[
            (1, [m(0), M(8), M(10), m(0)]),     # i bVI bVII i
            (1, [m(0), M(10), M(8), M(10)]),    # i bVII bVI bVII
            (1, [m(0), M(3), M(10), m(5)]),     # i bIII bVII iv
            (2, [m(0), m(5), M(8), M(7)]),      # i iv bVI V
            (2, [m(0), M(8), m(5), M(10)]),     # i bVI iv bVII
            (3, [m(0), M(1), M(10), M(8)]),     # i bII bVII bVI   (Phrygian metal)
            (3, [m(0), M(6), M(8), M(10)]),     # i bV bVI bVII
        ],
        major_bank=[
            (1, [M(0), M(10), M(5), M(0)]),     # I bVII IV I
            (1, [M(0), M(7), M(10), M(5)]),     # I V bVII IV
            (2, [M(0), M(5), M(10), M(5)]),     # I IV bVII IV
            (2, [m(9), M(5), M(0), M(7)]),      # vi IV I V
            (3, [M(0), M(3), M(5), M(10)]),     # I bIII IV bVII
        ],
        motifs=[[2, 2, 4, 2, 2, 4], [4, 4, 2, 2, 4], [3, 3, 2, 4, 4], [2, 2, 2, 2, 8], [6, 2, 4, 4]],
        drive=[[2, 2, 2, 2, 2, 2, 4], [1, 1, 2, 2, 2, 4, 4], [3, 3, 2, 2, 2, 4], [2, 1, 1, 2, 2, 8]],
        bass=_bass_picked, arp=_arp_chug, pad=_pad_hold, drums=_drums_rock,
    ),
    11: Style(
        name="eurobeat",
        pools={"lead": [62, 63, 81, 86, 61], "arp": [80, 6, 7, 81, 4], "bass": [38, 39, 38, 39],
               "pad": [90, 89, 50, 51]},
        minor_bank=[
            (1, [m(0), M(8), M(10), m(0)]),     # i bVI bVII i
            (1, [M(8), M(10), m(0), m(0)]),     # bVI bVII i i
            (1, [m(0), M(10), M(8), M(10)]),    # i bVII bVI bVII
            (2, [m(5), M(10), M(3), M(8)]),     # iv bVII bIII bVI (circle of fifths)
            (2, [m(0), m(7), M(8), M(10)]),     # i v bVI bVII
            (3, [M(8), M(10), M(3), M(7)]),     # bVI bVII bIII V
        ],
        major_bank=[
            (1, [M(5), M(7), m(4), m(9)]),      # IV V iii vi
            (1, [M(0), M(7), m(9), M(5)]),      # I V vi IV
            (2, [m(9), M(5), M(7), M(0)]),      # vi IV V I
            (2, [M(5), M(7), M(0), m(9)]),      # IV V I vi
            (3, [M(5), M(7), M(8), M(10)]),     # IV V bVI bVII
        ],
        motifs=[[3, 3, 2, 3, 3, 2], [2, 1, 1, 2, 2, 4, 4], [3, 3, 4, 2, 4], [2, 2, 3, 3, 2, 4]],
        drive=[[3, 3, 2, 2, 2, 2, 2], [1, 1, 1, 1, 3, 3, 2, 4], [2, 2, 1, 1, 2, 3, 3, 2], [3, 3, 2, 1, 1, 2, 4]],
        bass=_bass_octave, arp=_arp_broken, pad=_pad_hold, drums=_drums_four,
    ),
    12: Style(
        name="chiparcade",
        pools={"lead": [80, 82, 83, 81], "arp": [80, 82, 8, 11, 13], "bass": [38, 39, 33, 38],
               "pad": [80, 82, 83]},
        minor_bank=[
            (1, [m(0), M(10), M(8), M(10)]),    # i bVII bVI bVII
            (1, [m(0), M(8), M(10), m(0)]),     # i bVI bVII i
            (2, [m(0), m(5), M(10), M(3)]),     # i iv bVII bIII
            (2, [m(0), M(8), M(3), M(10)]),     # i bVI bIII bVII
            (3, [m(0), M(8), M(1), M(7)]),      # i bVI bII V
        ],
        major_bank=[
            (1, [M(0), M(7), m(9), M(5)]),      # I V vi IV
            (1, [M(0), M(5), M(7), M(5)]),      # I IV V IV
            (2, [m(9), M(5), M(0), M(7)]),      # vi IV I V
            (2, [M(0), m(9), M(5), M(7)]),      # I vi IV V
            (3, [M(5), M(7), m(4), m(9)]),      # IV V iii vi
        ],
        motifs=[[2, 2, 2, 2, 4, 4], [4, 2, 2, 4, 4], [2, 2, 4, 2, 2, 4], [6, 2, 4, 2, 2]],
        drive=[[1, 1, 2, 4, 2, 2, 4], [2, 2, 2, 2, 2, 2, 4], [1, 1, 1, 1, 4, 2, 2, 4], [2, 1, 1, 2, 2, 2, 2, 4]],
        bass=_bass_bounce, arp=_arp_chip, pad=_pad_echo, drums=_drums_chip,
    ),
    13: Style(
        name="fusion",
        pools={"lead": [65, 64, 66, 62, 81], "arp": [4, 5, 4, 2, 11], "bass": [36, 37, 36, 37, 35],
               "pad": [48, 89, 50, 16]},
        minor_bank=[
            (1, [m(0), m(5), M(10), M(3)]),     # i iv bVII bIII
            (1, [M(8), M(10), m(0), m(0)]),     # bVI bVII i i
            (2, [m(5), m(7), m(0), m(0)]),      # iv v i i
            (2, [m(0), M(10), M(8), M(7)]),     # i bVII bVI V
            (3, [M(8), M(10), m(0), M(4)]),     # bVI bVII i III
        ],
        major_bank=[
            (1, [M(5), M(7), m(4), m(9)]),      # IV V iii vi ("royal road")
            (1, [m(2), M(7), M(0), m(9)]),      # ii V I vi
            (2, [M(8), M(10), M(0), M(0)]),     # bVI bVII I I
            (2, [M(5), m(4), m(2), M(0)]),      # IV iii ii I
            (3, [M(0), M(4), m(9), M(2)]),      # I III vi II (secondary dominants)
        ],
        motifs=[[3, 3, 2, 2, 2, 4], [1, 2, 1, 4, 2, 2, 4], [4, 3, 3, 2, 4], [2, 1, 1, 4, 8]],
        drive=[[1, 1, 1, 1, 2, 2, 3, 3, 2], [3, 1, 2, 2, 1, 1, 2, 4], [1, 2, 1, 2, 2, 2, 2, 4]],
        bass=_bass_slap, arp=_arp_comp, pad=_pad_hold, drums=_drums_funk,
    ),
    14: Style(
        name="airwolf",
        pools={
            "lead": [62, 63, 81, 84, 56, 61],
            "arp": [80, 81, 89, 4, 5, 82],
            "bass": [38, 39, 38, 39],
            "pad": [89, 90, 48, 50, 51],
        },
        minor_bank=[
            (1, [m(0), M(8), M(10), m(0)]),    # i bVI bVII i
            (1, [m(0), M(10), M(8), M(7)]),     # i bVII bVI V
            (1, [m(0), M(8), M(3), M(10)]),     # i bVI bIII bVII
            (2, [m(0), m(5), M(10), m(0)]),     # i iv bVII i
            (2, [m(0), M(8), m(5), M(7)]),      # i bVI iv V
            (3, [m(0), M(1), M(10), m(0)]),     # i bII bVII i
        ],
        major_bank=[
            (1, [M(0), M(10), M(5), M(0)]),     # I bVII IV I
            (1, [M(0), M(7), m(9), M(5)]),      # I V vi IV
            (2, [m(9), M(5), M(0), M(7)]),      # vi IV I V
            (2, [M(5), M(7), m(4), m(9)]),      # IV V iii vi
            (3, [M(0), M(8), M(10), M(0)]),     # I bVI bVII I
        ],
        motifs=[
            [4, 4, 4, 4],
            [6, 2, 4, 4],
            [4, 2, 2, 4, 4],
            [8, 4, 4],
            [2, 2, 4, 4, 4],
            [3, 3, 2, 4, 4],
        ],
        drive=[
            [2, 2, 2, 2, 4, 4],
            [3, 1, 2, 2, 4, 4],
            [2, 2, 4, 2, 2, 4],
            [1, 1, 2, 2, 2, 2, 6],
            [4, 2, 1, 1, 4, 4],
        ],
        bass=_bass_airwolf,
        arp=_arp_airwolf,
        pad=_pad_hold,
        drums=_drums_airwolf,
    ),
}
