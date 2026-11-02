cmake_minimum_required(VERSION 3.21)

include(${CMAKE_CURRENT_LIST_DIR}/tools/rp6502.cmake)

project(RPMegaChopperII C CXX ASM)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(ART_PYTHON ${Python3_EXECUTABLE})

add_executable(RPMegaChopperII)
rp6502_map(RPMegaChopperII src/xram.h "XRAM_.*" "XRAM_IMG_.*|XRAM_SFX_DATA|XRAM_KEYBOARD|XRAM_GAMEPAD|XRAM_HUD|XRAM_MAP_.*|XRAM_TILES_.*")

# Helper function to convert indexed PNGs to 4bpp binary sprites/tiles
function(chopper_sheet name w h xram_dest)
    set(out ${CMAKE_CURRENT_BINARY_DIR}/${name}.bin)
    add_custom_command(
        OUTPUT ${out}
        COMMAND ${ART_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/tools/png2bin.py
            ${CMAKE_CURRENT_SOURCE_DIR}/images/${name}.png ${out} ${w} ${h}
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tools/png2bin.py ${CMAKE_CURRENT_SOURCE_DIR}/images/${name}.png
        VERBATIM
    )
    rp6502_asset(RPMegaChopperII XRAM(${xram_dest}) ${out})
endfunction()

# Sprite sheets
chopper_sheet(chopper 32 16 XRAM_IMG_CHOPPER)
chopper_sheet(hostages 16 16 XRAM_IMG_HOSTAGES)
chopper_sheet(tank 40 16 XRAM_IMG_TANK)
chopper_sheet(jet 32 16 XRAM_IMG_JET)
chopper_sheet(balloon 16 32 XRAM_IMG_BALLOON)
chopper_sheet(bomb 8 8 XRAM_IMG_BOMB)
chopper_sheet(bullet 8 8 XRAM_IMG_BULLET)
chopper_sheet(explosion 32 16 XRAM_IMG_EXPLOSION)
chopper_sheet(smallexplosion 16 16 XRAM_IMG_SMALLEXPLOSION)
chopper_sheet(flags 16 16 XRAM_IMG_FLAGS)
chopper_sheet(target 16 16 XRAM_IMG_TARGET)

# Mode 2 Tile sheets
chopper_sheet(bg_tiles 16 16 XRAM_TILES_BG)
chopper_sheet(fg_tiles 16 16 XRAM_TILES_FG)

# Binary assets (Palettes, World maps, SFX data)
rp6502_asset(RPMegaChopperII XRAM(XRAM_PALETTES) images/palettes.bin)
rp6502_asset(RPMegaChopperII XRAM(XRAM_SFX_DATA) music/sfx.bin)
rp6502_asset(RPMegaChopperII XRAM(XRAM_MAP_BG) images/bg_map.bin)
rp6502_asset(RPMegaChopperII XRAM(XRAM_MAP_FG) images/fg_map.bin)

# Streamed VGM music tracks in ROM
foreach(track Title Stage1 Victory Gameover)
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/music/${track}.vgm)
        rp6502_asset(RPMegaChopperII ${track}.vgm music/${track}.vgm)
    endif()
endforeach()

rp6502_executable(RPMegaChopperII DATA default RESET default)
rp6502_web(RPMegaChopperII)

target_include_directories(RPMegaChopperII PRIVATE src)
target_compile_options(RPMegaChopperII PRIVATE -Oz -Wall)

target_sources(RPMegaChopperII PRIVATE
    src/main.c
    src/bg.c
    src/compounds.c
    src/enemies.c
    src/hostages.c
    src/hud.c
    src/input.c
    src/music.c
    src/opl.c
    src/player.c
    src/projectiles.c
    src/sfx.c
    src/sprites.c
    src/vgm.c
)
