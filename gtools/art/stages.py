"""What each stage's bank holds, for gen_art.py.

A stage is a dict:
  n          stage number, 1 up
  palettes   {slot: palette} for palettes.STAGE_SLOTS (missing ones are blank)
  items      contents in order: {"name", "frames", "pal", "idx"} for a
             sheet, or {"name", "data"} for raw bytes (a tile map); with
             "boss": True it goes in the boss file instead of the stage file
  waves      the air waves (waves.py)
  ground     ground units: (map y from the bottom, x, type, color, param)
  defines    extra #defines for src/gen/stage<N>.h, prefixed S<N>_
  sky_check  (sky map, solid tile ids, sky speed) for a sky with towers:
             gen_art.py flies the waves over it (airpath.py)
  previews   {name: (image, palette)} written with --preview
"""

import numpy as np

import arctic
import boss
import boss2
import city
import crawler
import deep
import desert
import driver
import gamma
import hive
import hud
import logo
import luna
import orbit
import ocean
import palettes
import ship
import station
import sun
import tiles
import waves
import wyrm

COLOR = ["COL_RED", "COL_BLUE", "COL_YELLOW", "COL_GRAY"]


def sky_clear(smap, solid):
    """The towers again, as the game reads them: for each sky row (top row
    first, as the map), 16 bits with bit c set if column c is clear."""
    solid = set(solid)
    rows = [sum(1 << c for c, t in enumerate(row) if int(t) not in solid) for row in smap]
    return np.array(rows, dtype="<u2").tobytes()


def sky_fine(tiles, ids):
    """What the ship crashes into, finer than whole tiles, so it can graze
    a tower as it can a bullet: for each tile id 16 bits, a 4 x 4 grid of
    4-pixel cells, bit row * 4 + column set where a solid tile is filled
    in (12 of the cell's 16 pixels). ids: the tiles to look in."""
    out = []
    for i, t in enumerate(tiles):
        bits = 0
        if i in ids:
            for r in range(4):
                for c in range(4):
                    if (t[r * 4:r * 4 + 4, c * 4:c * 4 + 4] != 0).sum() >= 12:
                        bits |= 1 << (r * 4 + c)
        out.append(bits)
    return np.array(out, dtype="<u2").tobytes()


def solid_sky(smap, solid, sky_speed, tiles, fine_ids=None):
    """A sky with towers: its masks for the bank, and what gen_art.py needs
    to fly the waves over it (airpath.py). The ship crashes on the art of
    fine_ids' tiles, the solid ones unless given."""
    solid = set(solid)
    return ([{"name": "sky_clear", "data": sky_clear(smap, solid)},
             {"name": "sky_fine", "data": sky_fine(tiles, set(fine_ids) if fine_ids else solid)}],
            (smap, solid, sky_speed))


def map_defines(prefix, m, loop_rows=0):
    return {f"{prefix}_ROWS": m.shape[0], f"{prefix}_COLS": m.shape[1], f"{prefix}_LOOP_ROWS": loop_rows}


def stage1():
    tl, ids, stage_map, hatches = tiles.stage1()
    pal = palettes.STAGE1
    # Ground turrets sit on the hatches. Y is the turret center measured up from
    # the bottom of the map; the stage spawns it as Y scrolls onto the screen.
    g = sorted(((r + 1) * 16, (c + 1) * 16) for r, c in hatches)
    units = [(y, x, "ET_TURRET", COLOR[i % 3], 0) for i, (y, x) in enumerate(g)]
    defines = map_defines("MAP", stage_map, tiles.LOOP_ROWS)
    defines.update({"TILES_N": len(tl), "SKY_ROWS": 0})
    return {
        "n": 1,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": tl, "pal": pal["TILES"]},
            {"name": "map", "data": stage_map.astype(np.uint8).tobytes()},
            {"name": "logo", "frames": logo.logo(), "pal": pal["BOSS"]},
            {"name": "boss_core", "boss": True, "frames": boss.core()},
            {"name": "portrait", "boss": True, "frames": boss.portrait()},
            {"name": "boss_wing", "boss": True, "frames": boss.wing()},
            {"name": "boss_cannon", "boss": True, "frames": boss.cannon()},
            {"name": "boss_turret", "boss": True, "frames": boss.turret()},
        ],
        "defines": defines,
        "waves": waves.S1_WAVES,
        "ground": units,
    }


def tilemap_image(tiles_list, m):
    """The whole map as one image, for previews."""
    rows = [np.concatenate([tiles_list[t] for t in row], axis=1) for row in m]
    return np.concatenate(rows, axis=0)


# Where the waves end on stages 2 and 3 (stage.c), in ground pixels: the
# sky must have reached its empty top rows by then.
WAVES_END = 2950


def stage2():
    gt, gmap, pads, roads, body_rows = city.stage2_ground()
    sky_speed = 6  # quarters: the sky scrolls 1.5 times as fast as the ground
    sky_rows = (WAVES_END * sky_speed // 4 + 240) // 16 + 1
    st, smap, solid, towers = city.stage2_sky(sky_rows)
    clear, check = solid_sky(smap, solid, sky_speed, st)
    pal = {"TILES": city.CITY, "SKY": city.SKY, "BOSS": palettes.BOSS2, "BOSS_WRECK": palettes.BOSS2_WRECK}
    units = []
    # Guns on three pads in four; the rest stay empty.
    for i, (r, c) in enumerate(p for k, p in enumerate(sorted(pads)) if k % 4 != 3):
        y = (r + 1) * 16
        if 300 < y < WAVES_END:
            units.append((y, (c + 1) * 16, "ET_TURRET", COLOR[i % 3], 0))
    # Tanks on three roads in eight, alternating directions, colors in threes.
    k = 0
    for r in roads:
        y = r * 16 + 8
        if y < 500 or y > WAVES_END - 100 or (r // city.BLOCK) % 8 not in (0, 3, 5):
            continue
        left = k % 2 == 1
        units.append((y, 200 if left else 0, "ET_TANK", COLOR[(k // 3) % 3], (0x80 if left else 0) | 10))
        k += 1
    defines = map_defines("MAP", gmap, city.LOOP_ROWS)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": smap.shape[0], "SKY_SPEED": sky_speed, "SKY_TILES_N": len(st)})
    return {
        "n": 2,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": city.CITY},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "sky_tiles", "frames": st, "pal": city.SKY},
            {"name": "sky_map", "data": smap.astype(np.uint8).tobytes()},
            *clear,
            {"name": "boss_core", "boss": True, "frames": boss2.core(), "pal": palettes.BOSS2},
            {"name": "portrait", "boss": True, "frames": boss2.portrait(), "pal": palettes.BOSS2},
            {"name": "boss_pod", "boss": True, "frames": boss2.pod(), "pal": palettes.BOSS2},
            {"name": "boss_cannon", "boss": True, "frames": boss2.cannon(), "pal": palettes.BOSS2},
            {"name": "boss_turret", "boss": True, "frames": boss.turret(), "pal": palettes.BOSS2},
        ],
        "defines": defines,
        "waves": waves.S2_WAVES,
        "ground": units,
        "sky_check": check,
        "previews": {"ground": (tilemap_image(gt, gmap), city.CITY), "sky": (tilemap_image(st, smap), city.SKY)},
    }


def stage3():
    gt, gmap, bunkers, water = ocean.stage3_ground()
    sky_speed = 6
    sky_rows = (WAVES_END * sky_speed // 4 + 240) // 16 + 1
    st, smap = ocean.stage3_sky(sky_rows)
    ht, hids = ship.hull_tileset()
    hmap = ship.hull_map(hids)
    pal = {"TILES": ocean.OCEAN, "SKY": ocean.SKY, "LAYER": ship.HULL, "BOSS": ship.BOSS3,
           "BOSS_WRECK": ship.BOSS3_WRECK}
    units = []
    for i, (r, c) in enumerate(sorted(bunkers)):
        y = (r + 1) * 16
        if 300 < y < WAVES_END:
            units.append((y, (c + 1) * 16, "ET_TURRET", COLOR[i % 3], 0))
    boats = [(r, c) for r, c in sorted(water) if 600 < r * 16 < WAVES_END - 200][::2]
    for k, (r, c) in enumerate(boats):
        units.append((r * 16 + 8, c * 16 + 8, "ET_GUNBOAT", COLOR[(k // 3) % 3], 0))
    defines = map_defines("MAP", gmap, ocean.LOOP_ROWS)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": smap.shape[0], "SKY_SPEED": sky_speed, "SKY_TILES_N": len(st),
                    "HULL_W": ship.W, "HULL_H": ship.H, "HULL_TILES_N": len(ht)})
    # Each part's place on the hull: tile column/row of its top left, and
    # its center relative to the hull's center, in pixels.
    for name, (c, r, w, h) in ship.PARTS.items():
        defines[f"{name}_COL"] = c
        defines[f"{name}_ROW"] = r
        defines[f"{name}_OX"] = c * 16 + w * 8 - ship.W * 8
        defines[f"{name}_OY"] = r * 16 + h * 8 - ship.H * 8
    for name in ("crater", "crater_big0", "crater_big1", "crater_big2", "crater_big3", "bay0", "bay1", "bayo0", "bayo1",
                 "crater_bay0", "crater_bay1"):
        defines[f"T_{name.upper()}"] = hids[name]
    assert len(ht) <= 256
    return {
        "n": 3,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": ocean.OCEAN},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "sky_tiles", "frames": st, "pal": ocean.SKY},
            {"name": "sky_map", "data": smap.astype(np.uint8).tobytes()},
            {"name": "hull_tiles", "boss": True, "frames": ht, "pal": ship.HULL},
            {"name": "hull_map", "boss": True, "data": hmap.astype(np.uint8).tobytes()},
            {"name": "boss_bridge", "boss": True, "frames": ship.bridge(), "pal": ship.BOSS3},
            {"name": "portrait", "boss": True, "frames": ship.portrait(), "pal": ship.BOSS3},
            {"name": "boss_reactor", "boss": True, "frames": ship.reactor(), "pal": ship.BOSS3},
            {"name": "boss_gun", "boss": True, "frames": ship.main_gun(), "pal": ship.BOSS3},
            {"name": "boss_turret", "boss": True, "frames": boss.turret(), "pal": ship.BOSS3},
        ],
        "defines": defines,
        "waves": waves.S3_WAVES,
        "ground": units,
        "previews": {"ground": (tilemap_image(gt, gmap), ocean.OCEAN), "sky": (tilemap_image(st, smap), ocean.SKY),
                     "hull": (tilemap_image(ht, hmap), ship.HULL)},
    }


def sky_stage_rows(sky_speed):
    return (WAVES_END * sky_speed // 4 + 240) // 16 + 1


def stage4():
    gt, gmap, bunkers = desert.stage4_ground()
    sky_speed = 6
    st, smap = desert.stage4_sky(sky_stage_rows(sky_speed))
    pal = {"TILES": desert.SAND, "SKY": desert.DUST, "BOSS": wyrm.BOSS4, "BOSS_WRECK": wyrm.BOSS4_WRECK}
    units = []
    for i, (r, c) in enumerate(sorted(bunkers)):
        y = (r + 1) * 16
        if 300 < y < WAVES_END:
            units.append((y, (c + 1) * 16, "ET_TURRET", COLOR[i % 3], 0))
    # Armoured trains: five cars, one color each, a locomotive in front
    # (param 0), heading up the track. The rail's middle is RAIL * 16 + 16.
    x = desert.RAIL * 16 + 16
    for k, y0 in enumerate((700, 1500, 2300)):
        for car in range(5):
            units.append((y0 - car * 30, x, "ET_TRAIN", COLOR[k % 3], car))
    defines = map_defines("MAP", gmap, LOOP_ROWS_DEFAULT)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": smap.shape[0], "SKY_SPEED": sky_speed})
    return {
        "n": 4,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": desert.SAND},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "sky_tiles", "frames": st, "pal": desert.DUST},
            {"name": "sky_map", "data": smap.astype(np.uint8).tobytes()},
            {"name": "train", "frames": desert.train(), "pal": palettes.ENEMY_RED},
            {"name": "boss_head", "boss": True, "frames": wyrm.head(), "pal": wyrm.BOSS4},
            {"name": "boss_seg", "boss": True, "frames": wyrm.segment(), "pal": wyrm.BOSS4},
            {"name": "boss_tail", "boss": True, "frames": wyrm.tail(), "pal": wyrm.BOSS4},
            {"name": "portrait", "boss": True, "frames": wyrm.portrait(), "pal": wyrm.BOSS4},
        ],
        "defines": defines,
        "waves": waves.S4_WAVES,
        "ground": units,
        "previews": {"ground": (tilemap_image(gt, gmap), desert.SAND), "sky": (tilemap_image(st, smap), desert.DUST)},
    }


LOOP_ROWS_DEFAULT = 16


def hull_defines(defines, mod, hids, craters):
    """A tile-built boss's hull: its size, each part's socket (tile column
    and row of its top left) and center offset from the hull's center in
    pixels, and the tile ids the game writes."""
    defines.update({"HULL_W": mod.W, "HULL_H": mod.H})
    for name, (c, r, w, h) in mod.PARTS.items():
        defines[f"{name}_COL"] = c
        defines[f"{name}_ROW"] = r
        defines[f"{name}_OX"] = c * 16 + w * 8 - mod.W * 8
        defines[f"{name}_OY"] = r * 16 + h * 8 - mod.H * 8
    for name in craters:
        defines[f"T_{name.upper()}"] = hids[name]


def stage5():
    gt, gmap, bunkers, roads, water = arctic.stage5_ground()
    sky_speed = 6
    st, smap, solid = arctic.stage5_sky(sky_stage_rows(sky_speed))
    clear, check = solid_sky(smap, solid, sky_speed, st)
    ht, hids = crawler.hull_tileset()
    hmap = crawler.hull_map(hids)
    pal = {"TILES": arctic.ICE, "SKY": arctic.FROST, "LAYER": crawler.HULL5, "BOSS": crawler.BOSS5,
           "BOSS_WRECK": crawler.BOSS5_WRECK}
    units = []
    for i, (r, c) in enumerate(sorted(bunkers)[::2]):
        y = (r + 1) * 16
        if 300 < y < WAVES_END:
            units.append((y, (c + 1) * 16, "ET_TURRET", COLOR[i % 3], 0))
    # Snow tanks on the roads, alternating directions.
    for k, r in enumerate(roads):
        y = r * 16 + 8
        if 400 < y < WAVES_END - 100:
            left = k % 2 == 1
            units.append((y, 200 if left else 0, "ET_TANK", COLOR[(k // 3) % 3], (0x80 if left else 0) | 9))
    boats = [(r, c) for r, c in sorted(water) if 500 < r * 16 < WAVES_END - 200][1::3]
    for k, (r, c) in enumerate(boats):
        units.append((r * 16 + 8, c * 16 + 8, "ET_GUNBOAT", COLOR[k % 3], 0))
    defines = map_defines("MAP", gmap, LOOP_ROWS_DEFAULT)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": smap.shape[0], "SKY_SPEED": sky_speed, "SKY_TILES_N": len(st),
                    "HULL_TILES_N": len(ht)})
    hull_defines(defines, crawler, hids, ("crater", "crater_big0"))
    assert all(hids[f"crater_big{k}"] == hids["crater_big0"] + k for k in range(4))
    return {
        "n": 5,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": arctic.ICE},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "sky_tiles", "frames": st, "pal": arctic.FROST},
            {"name": "sky_map", "data": smap.astype(np.uint8).tobytes()},
            *clear,
            {"name": "hull_tiles", "boss": True, "frames": ht, "pal": crawler.HULL5},
            {"name": "hull_map", "boss": True, "data": hmap.astype(np.uint8).tobytes()},
            {"name": "boss_reactor", "boss": True, "frames": crawler.reactor(), "pal": crawler.BOSS5},
            {"name": "portrait", "boss": True, "frames": crawler.portrait(), "pal": crawler.BOSS5},
            {"name": "boss_drill", "boss": True, "frames": crawler.drill(), "pal": crawler.BOSS5},
            {"name": "boss_gun", "boss": True, "frames": ship.main_gun(), "pal": crawler.BOSS5},
            {"name": "boss_turret", "boss": True, "frames": boss.turret(), "pal": crawler.BOSS5},
        ],
        "defines": defines,
        "waves": waves.S5_WAVES,
        "ground": units,
        "sky_check": check,
        "previews": {"ground": (tilemap_image(gt, gmap), arctic.ICE), "sky": (tilemap_image(st, smap), arctic.FROST),
                     "hull": (tilemap_image(ht, hmap), crawler.HULL5)},
    }


def stage6():
    gt, gmap = orbit.stage6_ground()
    sky_speed = 6
    # Satellites from where the ground's limb is about to come into view.
    sat_from = (1300 * sky_speed // 4) // 16
    st, smap, solid = orbit.stage6_sky(sky_stage_rows(sky_speed), sat_from)
    clear, check = solid_sky(smap, solid, sky_speed, st)
    ht, hids, hmap = station.hull()
    pal = {"TILES": orbit.ORBIT, "SKY": orbit.ORBIT_SKY, "LAYER": station.STATION, "BOSS": station.BOSS6,
           "BOSS_WRECK": station.BOSS6_WRECK}
    defines = map_defines("MAP", gmap, LOOP_ROWS_DEFAULT)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": smap.shape[0], "SKY_SPEED": sky_speed, "SKY_TILES_N": len(st),
                    "HULL_TILES_N": len(ht), "FADE_FIRST": orbit.FADE_FIRST, "FADE_N": orbit.FADE_N})
    hull_defines(defines, station, hids, ("crater", "crater_big0"))
    return {
        "n": 6,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": orbit.ORBIT},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "sky_tiles", "frames": st, "pal": orbit.ORBIT_SKY},
            {"name": "sky_map", "data": smap.astype(np.uint8).tobytes()},
            *clear,
            {"name": "hull_tiles", "boss": True, "frames": ht, "pal": station.STATION},
            {"name": "hull_map", "boss": True, "data": hmap.astype(np.uint8).tobytes()},
            {"name": "boss_core", "boss": True, "frames": station.core(), "pal": station.BOSS6},
            {"name": "boss_sat", "boss": True, "frames": station.satellite(), "pal": station.BOSS6},
            {"name": "boss_turret", "boss": True, "frames": boss.turret(), "pal": station.BOSS6},
            {"name": "portrait", "boss": True, "frames": station.portrait(), "pal": station.BOSS6},
        ],
        "defines": defines,
        "waves": waves.S6_WAVES,
        "ground": [],
        "sky_check": check,
        "previews": {"ground": (tilemap_image(gt, gmap), orbit.ORBIT), "sky": (tilemap_image(st, smap), orbit.ORBIT_SKY),
                     "hull": (tilemap_image(ht, hmap), station.STATION)},
    }


def stage7():
    gt, gmap, bunkers, roads = luna.stage7_ground()
    ht, hids, hmap = driver.hull()
    pal = {"TILES": luna.LUNA, "LAYER": driver.DRIVER, "BOSS": driver.BOSS7, "BOSS_WRECK": driver.BOSS7_WRECK}
    units = []
    for i, (r, c) in enumerate(sorted(bunkers)):
        y = (r + 1) * 16
        if 300 < y < WAVES_END:
            units.append((y, (c + 1) * 16, "ET_TURRET", COLOR[i % 3], 0))
    # A rover on every road, alternating ways, colors in threes.
    for k, r in enumerate(sorted(roads)):
        y = r * 16 + 8
        if 300 < y < WAVES_END - 100:
            left = k % 2 == 1
            units.append((y, 200 if left else 0, "ET_TANK", COLOR[(k // 3) % 3], (0x80 if left else 0) | 10))
    defines = map_defines("MAP", gmap, LOOP_ROWS_DEFAULT)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": 0, "HULL_TILES_N": len(ht)})
    hull_defines(defines, driver, hids, ("crater", "crater_big0"))
    return {
        "n": 7,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": luna.LUNA},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "hull_tiles", "boss": True, "frames": ht, "pal": driver.DRIVER},
            {"name": "hull_map", "boss": True, "data": hmap.astype(np.uint8).tobytes()},
            {"name": "boss_breech", "boss": True, "frames": driver.breech(), "pal": driver.BOSS7},
            {"name": "boss_cap", "boss": True, "frames": driver.capacitor(), "pal": driver.BOSS7},
            {"name": "boss_muzzle", "boss": True, "frames": driver.muzzle(), "pal": driver.BOSS7},
            {"name": "boss_turret", "boss": True, "frames": boss.turret(), "pal": driver.BOSS7},
            {"name": "portrait", "boss": True, "frames": driver.portrait(), "pal": driver.BOSS7},
        ],
        "defines": defines,
        "waves": waves.S7_WAVES,
        "ground": units,
        "previews": {"ground": (tilemap_image(gt, gmap), luna.LUNA), "hull": (tilemap_image(ht, hmap), driver.DRIVER)},
    }


def stage8():
    gt, gmap = deep.stage8_ground()
    sky_speed = 6
    st, smap, solid, rock = deep.stage8_sky(sky_stage_rows(sky_speed))
    clear, check = solid_sky(smap, solid, sky_speed, st, rock)
    ht, hids, hmap = hive.hull()
    pal = {"TILES": deep.DEEP, "SKY": deep.DEEP_SKY, "LAYER": hive.HIVE, "BOSS": hive.BOSS8,
           "BOSS_WRECK": hive.BOSS8_WRECK}
    defines = map_defines("MAP", gmap, LOOP_ROWS_DEFAULT)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": smap.shape[0], "SKY_SPEED": sky_speed, "SKY_TILES_N": len(st),
                    "HULL_TILES_N": len(ht)})
    hull_defines(defines, hive, hids, ("crater", "crater_big0"))
    return {
        "n": 8,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": deep.DEEP},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "sky_tiles", "frames": st, "pal": deep.DEEP_SKY},
            {"name": "sky_map", "data": smap.astype(np.uint8).tobytes()},
            *clear,
            {"name": "hull_tiles", "boss": True, "frames": ht, "pal": hive.HIVE},
            {"name": "hull_map", "boss": True, "data": hmap.astype(np.uint8).tobytes()},
            {"name": "boss_eye", "boss": True, "frames": hive.eye(), "pal": hive.BOSS8},
            {"name": "boss_pod", "boss": True, "frames": hive.pod(), "pal": hive.BOSS8},
            {"name": "boss_claw", "boss": True, "frames": hive.claw(), "pal": hive.BOSS8},
            {"name": "boss_turret", "boss": True, "frames": boss.turret(), "pal": hive.BOSS8},
            {"name": "portrait", "boss": True, "frames": hive.portrait(), "pal": hive.BOSS8},
        ],
        "defines": defines,
        "waves": waves.S8_WAVES,
        "ground": [],
        "sky_check": check,
        "previews": {"ground": (tilemap_image(gt, gmap), deep.DEEP), "sky": (tilemap_image(st, smap), deep.DEEP_SKY),
                     "hull": (tilemap_image(ht, hmap), hive.HIVE)},
    }


def stage9():
    gt, gmap = sun.stage9_ground()
    sky_speed = 6
    st, smap, flare_a, flare_b = sun.stage9_sky(sky_stage_rows(sky_speed))
    ht, hids, hmap = gamma.hull()
    pal = {"TILES": sun.SUN, "SKY": sun.FLARE, "LAYER": gamma.GAMMA, "BOSS": gamma.BOSS9,
           "BOSS_WRECK": gamma.BOSS9_WRECK}
    defines = map_defines("MAP", gmap, LOOP_ROWS_DEFAULT)
    defines.update({"TILES_N": len(gt), "SKY_ROWS": smap.shape[0], "SKY_SPEED": sky_speed, "SKY_TILES_N": len(st),
                    "FLARE_A": flare_a, "FLARE_B": flare_b, "HULL_TILES_N": len(ht)})
    hull_defines(defines, gamma, hids, ("crater", "crater_big0"))
    return {
        "n": 9,
        "palettes": pal,
        "items": [
            {"name": "tiles", "frames": gt, "pal": sun.SUN},
            {"name": "map", "data": gmap.astype(np.uint8).tobytes()},
            {"name": "sky_tiles", "frames": st, "pal": sun.FLARE_VIEW},
            {"name": "sky_map", "data": smap.astype(np.uint8).tobytes()},
            {"name": "hull_tiles", "boss": True, "frames": ht, "pal": gamma.GAMMA},
            {"name": "hull_map", "boss": True, "data": hmap.astype(np.uint8).tobytes()},
            {"name": "boss_core", "boss": True, "frames": gamma.core(), "pal": gamma.BOSS9},
            {"name": "boss_prism", "boss": True, "frames": gamma.prism(), "pal": gamma.BOSS9},
            {"name": "boss_cannon", "boss": True, "frames": ship.main_gun(), "pal": gamma.BOSS9},
            {"name": "boss_emitter", "boss": True, "frames": driver.muzzle(), "pal": gamma.BOSS9},
            {"name": "boss_turret", "boss": True, "frames": boss.turret(), "pal": gamma.BOSS9},
            {"name": "portrait", "boss": True, "frames": gamma.portrait(), "pal": gamma.BOSS9},
        ],
        "defines": defines,
        "waves": waves.S9_WAVES,
        "ground": [],
        "previews": {"ground": (tilemap_image(gt, gmap), sun.SUN), "sky": (tilemap_image(st, smap), sun.FLARE_VIEW),
                     "hull": (tilemap_image(ht, hmap), gamma.GAMMA)},
    }


def all_stages():
    return [stage1(), stage2(), stage3(), stage4(), stage5(), stage6(), stage7(), stage8(), stage9()]
