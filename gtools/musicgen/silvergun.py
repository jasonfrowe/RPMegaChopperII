"""Style 9, "silvergun": orchestral-epic action music for MegaGammaForce.

Written to sound unlike RPDemo's electronic styles 1-8, after the
character of Hitoshi Sakimoto's Radiant Silvergun score rather than any of
its actual music:

- Harmony is chromatic, not diatonic degrees: the "epic minor" moves
  (i-bVI-bVII, i-iv-V with a major dominant, Phrygian bII, chromatic
  mediants), or bVI-bVII-I heroics in major.
- The lead is brass or a solo string playing *phrases*: a one-bar motif,
  restated a step along the progression (a sequence), a variation, then
  a long cadence note. Not a repeating hook.
- The arp channel is a string ostinato: repeated notes in gallop and
  pulse rhythms, not an arpeggio cycle.
- The pad is choir or strings, voice-leading to the nearest chord tone.
- Percussion is an orchestra over a rock kit, for drive: the "kick"
  channel mixes a bass drum groove with tuned timpani on the downbeats and
  rolls; the snare is a backbeat with 16th fills; the "hat" channel plays
  8th-note hats, with crashes and orchestra hits on phrase starts.
- Energy comes from MoodPreset.intensity: hot tracks (0.5 and up) get
  octave-jumping 8th bass, 16th ostinatos and 16th-note lead runs.
- Optional 6/8 time (MoodPreset.meter), for galloping themes.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .furwriter import NOTE_OFF, RowCell, note_value

Chord = Tuple[int, str]  # (semitones above the key root, "M" | "m")

MINOR_BANK: List[Tuple[int, List[Chord]]] = [
    (1, [(0, "m"), (8, "M"), (10, "M"), (0, "m")]),   # i  bVI bVII i
    (1, [(0, "m"), (5, "m"), (10, "M"), (3, "M")]),   # i  iv  bVII bIII
    (1, [(0, "m"), (8, "M"), (3, "M"), (10, "M")]),   # i  bVI bIII bVII
    (2, [(0, "m"), (10, "M"), (8, "M"), (7, "M")]),   # i  bVII bVI V   (Andalusian)
    (2, [(0, "m"), (3, "M"), (8, "M"), (7, "M")]),    # i  bIII bVI V
    (2, [(0, "m"), (5, "m"), (7, "M"), (0, "m")]),    # i  iv  V   i
    (3, [(0, "m"), (1, "M"), (0, "m"), (1, "M")]),    # i  bII i   bII  (Phrygian)
    (3, [(0, "m"), (8, "M"), (1, "M"), (7, "M")]),    # i  bVI bII V    (Neapolitan)
    (3, [(0, "m"), (4, "M"), (8, "M"), (7, "M")]),    # i  III bVI V    (chromatic mediant)
    (3, [(0, "m"), (6, "M"), (5, "m"), (7, "M")]),    # i  bV  iv  V    (tritone lurch)
]

MAJOR_BANK: List[Tuple[int, List[Chord]]] = [
    (1, [(0, "M"), (8, "M"), (10, "M"), (0, "M")]),   # I  bVI bVII I   (heroic)
    (1, [(0, "M"), (5, "M"), (7, "M"), (0, "M")]),    # I  IV  V   I
    (1, [(0, "M"), (10, "M"), (5, "M"), (0, "M")]),   # I  bVII IV  I
    (2, [(0, "M"), (9, "m"), (5, "M"), (7, "M")]),    # I  vi  IV  V
    (2, [(0, "M"), (4, "m"), (5, "M"), (7, "M")]),    # I  iii IV  V
    (3, [(0, "M"), (3, "M"), (8, "M"), (7, "M")]),    # I  bIII bVI V
    # Added later; appended so the indices above keep their meaning.
    (2, [(5, "M"), (7, "M"), (4, "m"), (9, "m")]),    # IV V   iii vi  ("royal road", JRPG staple)
    (2, [(9, "m"), (5, "M"), (0, "M"), (7, "M")]),    # vi IV  I   V
    (2, [(0, "M"), (7, "M"), (9, "m"), (5, "M")]),    # I  V   vi  IV
    (3, [(0, "M"), (4, "M"), (9, "m"), (7, "M")]),    # I  III vi  V   (secondary dominant)
    (3, [(5, "M"), (7, "M"), (8, "M"), (10, "M")]),   # IV V   bVI bVII (rising, never lands)
]

# Natural minor, natural major. A major chord built on the 5th raises the 7th.
MINOR = [0, 2, 3, 5, 7, 8, 10]
MAJOR = [0, 2, 4, 5, 7, 9, 11]

# GM programs (indices into RPTracker's bank).
POOLS = {
    "lead": [56, 57, 60, 61, 40, 68, 71],           # trumpet, trombone, horn, brass section, violin, oboe, clarinet
    "arp": [44, 45, 48, 49, 46],                     # tremolo, pizzicato, string ensembles, harp
    "bass": [42, 43, 58, 70],                        # cello, contrabass, tuba, bassoon
    "pad": [52, 53, 48, 49, 50],                     # choir aahs, voice oohs, strings, synth strings
}
KICK = 253        # RPTracker's custom kit, known to sound right on OPL2
HAT = 255
TIMPANI = 47
ORCH_HIT = 55
SNARE = 254       # RPTracker's custom snare, known to sound right on OPL2
CRASH = 183
RIDE = 185
LOW_TOM = 175
HIGH_TOM = 184


def meter_rows(meter: str) -> Tuple[int, int]:
    """(rows per bar, rows per beat) on the 16th-note grid."""
    if meter == "6/8":
        return 12, 6  # two dotted-quarter beats
    if meter == "3/4":
        return 12, 4
    return 16, 4


def pick_progressions(rng: random.Random, intensity: float, major: bool,
                      override: Optional[Tuple[int, int]] = None) -> Tuple[List[Chord], List[Chord], int, int]:
    """Two progressions for the A and B themes, and their bank indices.
    `override` names the indices instead; the picks still draw from `rng`
    so the rest of the seed's composition comes out the same."""
    bank = MAJOR_BANK if major else MINOR_BANK

    def weight(tier):
        if tier == 1:
            return 1.0
        if tier == 2:
            return max(0.2, intensity * 1.6)
        return max(0.0, intensity - 0.4) * 2.5

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
            raise ValueError(f"progression {i} is not in the {'major' if major else 'minor'} bank (0-{len(bank) - 1})")
    return bank[out[0]][1], bank[out[1]][1], out[0], out[1]


ROMAN = {0: "I", 1: "bII", 2: "II", 3: "bIII", 4: "III", 5: "IV", 6: "bV", 7: "V", 8: "bVI", 9: "VI", 10: "bVII",
         11: "VII"}


def describe(prog: List[Chord]) -> str:
    return " ".join(ROMAN[o] if q == "M" else ROMAN[o].lower() for o, q in prog)


def pick_instruments(rng: random.Random) -> Dict[str, int]:
    ins = {role: rng.choice(pool) for role, pool in POOLS.items()}
    # Percussion roles: --patch can swap these too.
    ins["kick"], ins["snare"], ins["hat"] = TIMPANI, SNARE, ORCH_HIT
    return ins


def _n(octave: int, semis: int) -> int:
    return note_value(octave + semis // 12, semis % 12)


def _chord_tones(root: int, chord: Chord) -> List[int]:
    off, q = chord
    r = root + off
    return [r, r + (4 if q == "M" else 3), r + 7]


def _scale_for(root: int, chord: Chord, major: bool) -> List[int]:
    """Pitch classes for melody over this chord."""
    base = MAJOR if major else MINOR
    pcs = {(root + s) % 12 for s in base}
    off, q = chord
    if not major and off == 7 and q == "M":
        pcs.discard((root + 10) % 12)
        pcs.add((root + 11) % 12)  # harmonic minor over V
    if off == 1:
        pcs.discard((root + 2) % 12)
        pcs.add((root + 1) % 12)   # Phrygian bII
    for t in _chord_tones(root, chord):
        pcs.add(t % 12)
    return sorted(pcs)


def _step(pitch: int, steps: int, pcs: List[int]) -> int:
    """Move a MIDI-style absolute semitone pitch by scale steps."""
    p = pitch
    d = 1 if steps > 0 else -1
    for _ in range(abs(steps)):
        p += d
        while p % 12 not in pcs:
            p += d
    return p


def _nearest_chord_tone(pitch: int, tones: List[int]) -> int:
    best = None
    for t in tones:
        for o in range(-3, 4):
            c = (t % 12) + 12 * ((pitch // 12) + o)
            if best is None or abs(c - pitch) < abs(best - pitch):
                best = c
    return best


# Busier phrases for energetic tracks: 16th-note runs into held notes.
DRIVE_44 = [[2, 2, 2, 2, 4, 4], [3, 3, 2, 2, 2, 4], [4, 2, 2, 2, 2, 4], [2, 2, 4, 2, 2, 4], [6, 2, 4, 4],
            [2, 2, 2, 2, 2, 2, 4]]
DRIVE_68 = [[2, 2, 2, 2, 2, 2], [3, 1, 2, 6], [2, 2, 2, 6], [4, 2, 2, 2, 2], [6, 2, 2, 2]]
RHYTHMS_44 = [[8, 4, 4], [12, 2, 2], [6, 2, 8], [4, 4, 8], [16], [3, 1, 4, 8], [8, 8], [4, 2, 2, 8], [2, 2, 4, 8]]
RHYTHMS_68 = [[6, 6], [4, 2, 6], [12], [6, 4, 2], [3, 3, 6], [2, 2, 2, 6], [6, 2, 2, 2]]
CADENCE_44 = [[16], [12, 4], [4, 12]]
CADENCE_68 = [[12], [6, 6], [2, 2, 2, 6]]


def generate_chunk(rng: random.Random, mood, ins: Dict[str, int], chords: List[Chord], root: int,
                   base_vol: Dict[str, int], jitter: Dict[str, int], bars: int) -> Dict[str, Dict[int, RowCell]]:
    rpb, beat = meter_rows(mood.meter)
    six8 = mood.meter == "6/8"
    major = mood.scale in ("major", "mixolydian")
    rows: Dict[str, Dict[int, RowCell]] = {r: {} for r in ("lead", "arp", "bass", "pad", "kick", "snare", "hat")}
    hot = mood.intensity >= 0.75
    drive = mood.intensity >= 0.5

    def put(role, row, note, ins_idx=None, vol_add=0):
        j = jitter.get(role, 3)
        v = base_vol[role] + vol_add + rng.randint(-j, j)
        rows[role][row] = RowCell(note=note, ins=ins[role] if ins_idx is None else ins_idx, vol=max(0, min(63, v)))

    def off(role, row):
        if row not in rows[role]:
            rows[role][row] = RowCell(note=NOTE_OFF)

    # String ostinato rhythm for the whole chunk: steps within a bar, and
    # which of them leave the root (index into [root, fifth, octave]).
    if six8:
        ost = rng.choice([[0, 2, 3, 6, 8, 9], [0, 2, 4, 6, 8, 10], [0, 3, 6, 9], [0, 1, 2, 6, 7, 8]])
    else:
        ost = rng.choice([
            [0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15],   # gallop
            list(range(16)),                              # driving 16ths
        ] + ([] if drive else [
            [0, 3, 6, 8, 11, 14],                         # 3+3+2
            [0, 2, 4, 6, 8, 10, 12, 14],                  # 8ths
        ]))
    ost_shape = rng.choice([[0] * 7 + [1], [0, 0, 2, 0, 0, 1, 0, 2], [0, 1, 0, 2]])

    # Lead motif: rhythm and contour picked once, then sequenced.
    rhythms = (DRIVE_68 if six8 else DRIVE_44) if drive else (RHYTHMS_68 if six8 else RHYTHMS_44)
    motif_rhythm = rng.choice(rhythms)
    motif_steps = [rng.choice([-2, -1, 1, 2, 3, -3, 4]) for _ in motif_rhythm]
    lead_oct = mood.lead_octave
    pitch = _nearest_chord_tone(12 * lead_oct + root, _chord_tones(root, chords[0]))
    pad_pitch = 12 * (mood.arp_octave - 1) + root + rng.choice([3, 4, 7])

    for bar in range(bars):
        base = bar * rpb
        chord = chords[bar % len(chords)]
        tones = _chord_tones(root, chord)
        pcs = _scale_for(root, chord, major)
        last = bar == bars - 1

        # Bass: root held, a fifth or octave leap mid-bar; pedalling 8ths when hot.
        broot = tones[0] % 12
        if drive:
            # Octave-jumping 8ths: the engine of the track.
            for r in range(0, rpb, 2):
                put("bass", base + r, _n(mood.bass_octave + ((r // 2) & 1), broot), vol_add=(2 if r % beat == 0 else -2))
        else:
            put("bass", base, _n(mood.bass_octave, broot))
            half = rpb // 2
            put("bass", base + half, _n(mood.bass_octave, broot + rng.choice([7, 12, 0, -5 + 12])))

        # Pad: voice-lead to the nearest chord tone, held all bar.
        pad_pitch = _nearest_chord_tone(pad_pitch, tones[1:])
        put("pad", base, note_value(pad_pitch // 12, pad_pitch % 12))

        # String ostinato.
        aroot = 12 * mood.arp_octave + tones[0] % 12
        choices = [aroot, aroot + 7, aroot + 12]
        for k, r in enumerate(ost):
            if r >= rpb:
                continue
            p = choices[ost_shape[k % len(ost_shape)]]
            put("arp", base + r, note_value(p // 12, p % 12), vol_add=(4 if r % beat == 0 else -3))

        # Lead phrase: motif, sequence, variation, cadence.
        if last:
            rhythm = rng.choice(CADENCE_68 if six8 else CADENCE_44)
            steps = [rng.choice([-1, 1]) for _ in rhythm]
        elif bar == 2 and rng.random() < 0.6:
            rhythm = rng.choice(rhythms)
            steps = [rng.choice([-2, -1, 1, 2]) for _ in rhythm]
            if drive:
                steps = [rng.choice([-1, 1]) * (1 if d < beat else 2) for d in rhythm]  # scalar runs
        else:
            rhythm, steps = motif_rhythm, motif_steps
        # Each bar starts on a chord tone near where the line is.
        pitch = _nearest_chord_tone(pitch, tones)
        lo, hi = 12 * (lead_oct - 1) + 5, 12 * (lead_oct + 1) + 7
        r = base
        for i, dur in enumerate(rhythm):
            if r >= base + rpb:
                break
            if i > 0:
                pitch = _step(pitch, steps[i], pcs)
                if dur >= beat:  # long notes land on chord tones
                    pitch = _nearest_chord_tone(pitch, tones)
            while pitch > hi:
                pitch -= 12
            while pitch < lo:
                pitch += 12
            put("lead", r, note_value(pitch // 12, pitch % 12), vol_add=(3 if r == base else 0))
            if dur >= 6 and r + dur - 1 < base + rpb:
                off("lead", r + dur - 1)  # breathe before the next note
            r += dur
        if last:
            pitch = _nearest_chord_tone(pitch, [tones[0]])

        troot = tones[0] % 12
        # "kick" channel: timpani on the downbeat, a bass drum groove when driving.
        put("kick", base, _n(2, troot), ins_idx=ins["kick"])
        if drive:
            if six8:
                kicks = [3, 6, 9]  # gallop pushes
            else:
                kicks = [6, 8, 10] if rng.random() < 0.5 else [8, 11, 14]  # rock / syncopated
            for rr in kicks:
                if rr < rpb and not (last and rr >= rpb // 2):
                    put("kick", base + rr, _n(3, 0), ins_idx=KICK)
        else:
            put("kick", base + rpb // 2, _n(2, (troot + 7) % 12), ins_idx=ins["kick"], vol_add=-6)
        if last:
            for rr in range(rpb // 2, rpb):
                put("kick", base + rr, _n(2, troot), ins_idx=ins["kick"], vol_add=-12 + (rr - rpb // 2))

        # Snare: backbeat, ghost notes, a roll into the next chunk.
        backs = [beat] if six8 else [beat, 3 * beat]
        if last and rng.random() < 0.7:
            for rr in range(rpb // 2, rpb):
                put("snare", base + rr, _n(3, 0), vol_add=-14 + (rr - rpb // 2) * 2)
        else:
            for b in backs:
                put("snare", base + b, _n(3, 0))
            for rr in range(rpb):
                if rr not in backs and rng.random() < (0.25 if drive else 0.1):
                    put("snare", base + rr, _n(3, 0), vol_add=-18)

        # "hat" channel: crash or orchestra hit on the phrase, tom fills, hats.
        if bar == 0:
            if rng.random() < 0.6:
                put("hat", base, _n(4, troot), ins_idx=ins["hat"], vol_add=4)
            else:
                put("hat", base, _n(3, 0), ins_idx=CRASH)
        if last and rng.random() < 0.5:
            for k, rr in enumerate(range(rpb // 2, rpb, 2)):
                put("hat", base + rr, _n(3, 0), ins_idx=HIGH_TOM if k % 2 == 0 else LOW_TOM)
        elif drive:
            for rr in range(0 if bar else 2, rpb, 2):
                if rng.random() < 0.95:
                    put("hat", base + rr, _n(3, 0), ins_idx=HAT, vol_add=(0 if rr % beat else 4) - 6)
        elif hot:
            for rr in range(0, rpb, 3):
                put("hat", base + rr, _n(3, 0), ins_idx=RIDE, vol_add=-14)
    return rows
