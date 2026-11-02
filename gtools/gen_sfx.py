#!/usr/bin/env python3
"""Generate MegaGammaForce's OPL2 sound effects.

Adapted from RPDemo's tools/generate_sfx.py. Each effect is a short stream
of OPL2 register writes and waits (0x5A reg val, 0x61 wait16, 0x66 end),
on channel 7 (player) or 8 (enemy); music never uses those two channels.
All the streams are packed into one blob that the ROM loads into XRAM.

Writes:
  music/sfx.bin          the blob, loaded at XRAM_SFX_DATA
  music/sfx/<name>.vgm   each effect alone, for auditioning
  src/gen/sfx_ids.h      an id per effect and its offset in the blob

Usage: python3 gtools/gen_sfx.py
"""

import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VGM_RATE = 44100
OPL_RATE = 49716.0
MOD = {7: 0x11, 8: 0x12}
CAR = {7: 0x14, 8: 0x15}


def fnum_block(hz):
    for block in range(8):
        f = round(hz * (2 ** (20 - block)) / OPL_RATE)
        if 0 < f <= 1023:
            return f, block
    return 1023, 7


class Sfx:
    def __init__(self, ch):
        self.ch = ch
        self.ev = []  # (reg, val, wait)

    def w(self, reg, val):
        self.ev.append((reg, val & 0xFF, 0))

    def patch(self, mod_mult=1, mod_tl=0, mod_ar=15, mod_dr=8, mod_sl=0, mod_rr=8, mod_wave=0,
              car_mult=1, car_tl=0, car_ar=15, car_dr=8, car_sl=0, car_rr=8, car_wave=0,
              feedback=0, connection=0, sustain=1):
        m, c = MOD[self.ch], CAR[self.ch]
        self.w(0x20 + m, (sustain << 5) | mod_mult)
        self.w(0x20 + c, (sustain << 5) | car_mult)
        self.w(0x40 + m, mod_tl)
        self.w(0x40 + c, car_tl)
        self.w(0x60 + m, (mod_ar << 4) | mod_dr)
        self.w(0x60 + c, (car_ar << 4) | car_dr)
        self.w(0x80 + m, (mod_sl << 4) | mod_rr)
        self.w(0x80 + c, (car_sl << 4) | car_rr)
        self.w(0xE0 + m, mod_wave)
        self.w(0xE0 + c, car_wave)
        self.w(0xC0 + self.ch, (feedback << 1) | connection)
        return self

    def on(self, hz):
        f, b = fnum_block(hz)
        self.w(0xA0 + self.ch, f & 0xFF)
        self.w(0xB0 + self.ch, 0x20 | (b << 2) | (f >> 8))
        return self

    def off(self):
        self.w(0xB0 + self.ch, 0)
        return self

    def wait(self, ms):
        n = round(ms * VGM_RATE / 1000)
        if n > 0:
            r, v, w = self.ev[-1]
            self.ev[-1] = (r, v, w + n)
        return self

    def sweep(self, a, b, ms, steps=10):
        for i in range(steps + 1):
            self.on(a + (b - a) * i / steps)
            if i < steps:
                self.wait(ms / steps)
        return self

    def tl(self, level):
        self.w(0x40 + CAR[self.ch], level)
        return self

    def modtl(self, level):
        """Modulator level: lower is brighter, higher is darker and purer."""
        self.w(0x40 + MOD[self.ch], level)
        return self

    def boom(self, a, b, ms, steps, tl0, tl1):
        """Pitch drop that also darkens as it falls: the body of an explosion."""
        for i in range(steps + 1):
            t = i / steps
            self.modtl(round(tl0 + (tl1 - tl0) * t))
            self.on(a + (b - a) * t)
            if i < steps:
                self.wait(ms / steps)
        return self

    def stream(self):
        out = bytearray()
        for r, v, w in self.ev:
            out += bytes([0x5A, r, v])
            while w > 0:
                n = min(w, 0xFFFF)
                out += bytes([0x61]) + struct.pack("<H", n)
                w -= n
        out.append(0x66)
        return bytes(out)


# Everything here is tonal, for a full sound under the orchestral music:
# sine carriers, modulator multiples of 1-3 (saw- and square-like
# harmonics), feedback no higher than 5. RPDemo's noise recipe (pulse-sine
# waveforms with feedback 7) comes out as thin scratching on this mix.
# Explosions are low booms whose brightness fades as the pitch falls.

def rotor():
    """Helicopter rotor blade chop: low percussive thump."""
    s = Sfx(7).patch(mod_mult=1, mod_tl=12, mod_dr=4, car_mult=1, car_dr=6, car_sl=2, car_rr=6, feedback=5)
    return s.sweep(90, 45, 45, 3).off()


def vulcan():
    """Chopper machine gun: crisp punchy burst."""
    return Sfx(7).patch(mod_tl=16, mod_dr=6, car_dr=7, car_sl=4, car_rr=9, feedback=4).sweep(780, 240, 50, 5).off()


def bomb_drop():
    """Bomb falling whistle: descending high tone."""
    s = Sfx(7).patch(mod_mult=1, mod_tl=28, car_mult=1, car_dr=2, car_sl=1, car_rr=4, feedback=2)
    return s.sweep(1400, 320, 280, 14).off()


def hostage_board():
    """Hostage boards chopper: bright rising double blip."""
    s = Sfx(7).patch(mod_mult=2, mod_tl=18, car_mult=2, car_dr=6, car_sl=3, car_rr=8, feedback=2, connection=1)
    return s.on(987.8).wait(25).off().wait(8).on(1318.5).wait(35).off()


def hostage_saved():
    """Hostage rescued at home base: cheerful major arpeggio."""
    s = Sfx(7).patch(mod_mult=1, mod_tl=8, mod_dr=5, car_mult=2, car_dr=4, car_sl=4, car_rr=6, feedback=3, connection=1)
    for f in (523.25, 659.25, 783.99, 1046.5):
        s.on(f).wait(35).off().wait(6)
    s.on(1318.5).wait(100)
    return s.off()


def player_die():
    """Chopper explosion and crash."""
    s = Sfx(7).patch(mod_tl=4, mod_dr=2, car_dr=2, car_sl=2, car_rr=3, feedback=5)
    s.boom(180, 140, 35, 3, 2, 8)
    s.boom(140, 35, 450, 18, 6, 32)
    s.boom(90, 25, 550, 20, 10, 44)
    return s.off()


def tank_fire():
    """Heavy tank shell fired."""
    s = Sfx(8).patch(mod_mult=1, mod_tl=10, car_dr=5, car_sl=3, car_rr=6, feedback=5)
    return s.sweep(280, 70, 90, 6).off()


def jet_flyby():
    """Jet interceptor rushing past."""
    s = Sfx(8).patch(mod_mult=3, mod_tl=14, car_dr=3, car_sl=2, car_rr=5, feedback=4)
    return s.sweep(400, 1100, 160, 8).sweep(1100, 300, 220, 10).off()


def explode():
    """Standard ground explosion."""
    s = Sfx(8).patch(mod_tl=6, mod_dr=3, car_dr=4, car_sl=3, car_rr=5, feedback=5)
    s.boom(160, 130, 25, 2, 4, 8)
    return s.boom(130, 40, 260, 12, 10, 36).off()


def big_explode():
    """Bunker breach / building detonation."""
    s = Sfx(8).patch(mod_tl=4, mod_dr=2, car_dr=2, car_sl=2, car_rr=3, feedback=5)
    s.boom(170, 130, 35, 3, 2, 6)
    s.boom(130, 38, 380, 16, 6, 28)
    s.boom(100, 25, 500, 18, 10, 44)
    return s.off()


def hostage_wave():
    """Hostage whistling / shouting for help."""
    s = Sfx(8).patch(mod_mult=1, mod_tl=22, car_mult=1, car_dr=4, car_sl=2, car_rr=7, feedback=2)
    return s.sweep(1200, 1600, 60, 4).wait(20).sweep(1600, 1300, 60, 4).off()


def hostage_die():
    """Hostage killed: sad low buzz."""
    s = Sfx(8).patch(mod_mult=3, mod_tl=18, car_dr=4, car_sl=3, car_rr=6, feedback=4)
    return s.sweep(320, 120, 140, 6).off()


def warning():
    """Air raid / enemy incoming siren."""
    s = Sfx(8).patch(mod_tl=16, car_dr=2, car_sl=1, car_rr=8, feedback=4)
    for _ in range(2):
        s.sweep(440, 880, 200, 8).sweep(880, 440, 200, 8)
    return s.off()


def extend():
    """1-UP extra chopper awarded."""
    s = Sfx(7).patch(mod_mult=1, mod_tl=10, mod_dr=4, car_mult=2, car_dr=3, car_sl=3, car_rr=5, feedback=4, connection=0)
    for f, ms in ((783.99, 60), (1046.5, 60), (1318.5, 60), (1568.0, 60), (2093.0, 120)):
        s.on(f).wait(ms).off().wait(8)
    return s.off()


SFX = [
    ("ROTOR", rotor),
    ("VULCAN", vulcan),
    ("BOMB_DROP", bomb_drop),
    ("HOSTAGE_BOARD", hostage_board),
    ("HOSTAGE_SAVED", hostage_saved),
    ("PLAYER_DIE", player_die),
    ("TANK_FIRE", tank_fire),
    ("JET_FLYBY", jet_flyby),
    ("EXPLODE", explode),
    ("BIG_EXPLODE", big_explode),
    ("HOSTAGE_WAVE", hostage_wave),
    ("HOSTAGE_DIE", hostage_die),
    ("WARNING", warning),
    ("EXTEND", extend),
]


def main():
    blob = bytearray()
    offsets = []
    (ROOT / "music" / "sfx").mkdir(parents=True, exist_ok=True)
    for name, fn in SFX:
        data = fn().stream()
        offsets.append(len(blob))
        blob += data
        hdr = bytearray(0x40)
        hdr[0:4] = b"Vgm "
        (ROOT / "music" / "sfx" / f"{name.lower()}.vgm").write_bytes(bytes(hdr) + data)
    if len(blob) & 1:
        blob.append(0)
    (ROOT / "music" / "sfx.bin").write_bytes(bytes(blob))
    h = ["/* Generated by gtools/gen_sfx.py. Do not edit; regenerate instead. */",
         "#ifndef GEN_SFX_IDS_H", "#define GEN_SFX_IDS_H", "", "enum", "{"]
    h += [f"    SFX_{name}," for name, _ in SFX]
    h += ["    SFX_COUNT,", "};", "", f"#define SFX_BLOB_SIZE {len(blob)}", "",
          "#ifdef SFX_OFFSETS", "static const uint16_t sfx_offsets[SFX_COUNT] = {"]
    h += [f"    {o}, /* {name} */" for o, (name, _) in zip(offsets, SFX)]
    h += ["};", "#endif", "", "#endif", ""]
    (ROOT / "src" / "gen" / "sfx_ids.h").write_text("\n".join(h))
    print(f"{len(SFX)} sfx, {len(blob)} bytes")


if __name__ == "__main__":
    main()
