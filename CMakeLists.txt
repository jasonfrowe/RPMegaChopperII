cmake_minimum_required(VERSION 3.21)

include(${CMAKE_CURRENT_LIST_DIR}/tools/rp6502.cmake)

project(RPMegaChopperII C CXX ASM)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
set(ART_PYTHON ${Python3_EXECUTABLE})

add_executable(RPMegaChopperII)
rp6502_map(RPMegaChopperII src/xram.h "XRAM_.*" "XRAM_IMG_.*|XRAM_SFX_DATA|XRAM_KEYBOARD|XRAM_GAMEPAD|XRAM_HUD|XRAM_MSG|XRAM_MAP_.*|XRAM_TILES_.*")

# Helper function to convert indexed PNGs to 4bpp binary sprites/tiles
# (an optional fifth argument is the bits per pixel, 4 if left out)
function(chopper_sheet name w h xram_dest)
    set(bpp 4)
    if(ARGC GREATER 4)
        set(bpp ${ARGV4})
    endif()
    set(out ${CMAKE_CURRENT_BINARY_DIR}/${name}.bin)
    add_custom_command(
        OUTPUT ${out}
        COMMAND ${ART_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/tools/png2bin.py
            ${CMAKE_CURRENT_SOURCE_DIR}/images/${name}.png ${out} ${w} ${h} ${bpp}
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tools/png2bin.py ${CMAKE_CURRENT_SOURCE_DIR}/images/${name}.png
        VERBATIM
    )
    rp6502_asset(RPMegaChopperII XRAM(${xram_dest}) ${out})
endfunction()

# Sprite sheets (frame width, height)
chopper_sheet(chopper 40 20 XRAM_IMG_CHOPPER)
chopper_sheet(hostages 16 16 XRAM_IMG_HOSTAGES)
chopper_sheet(tank 40 20 XRAM_IMG_TANK)
chopper_sheet(jet 40 16 XRAM_IMG_JET)
chopper_sheet(balloon 16 32 XRAM_IMG_BALLOON)
chopper_sheet(bomb 8 8 XRAM_IMG_BOMB)
chopper_sheet(bullet 8 4 XRAM_IMG_BULLET)
chopper_sheet(explosion 32 32 XRAM_IMG_EXPLOSION)
chopper_sheet(smallexplosion 16 16 XRAM_IMG_SMALLEXPLOSION)
chopper_sheet(flags 24 16 XRAM_IMG_FLAGS)
chopper_sheet(target 16 16 XRAM_IMG_TARGET)
chopper_sheet(snow 4 4 XRAM_IMG_SNOW)
chopper_sheet(logo 64 24 XRAM_IMG_LOGO 1)

# Mode 2 tile sheets: far sky and hills in 8x8 tiles, the ground in 16x16
chopper_sheet(far_tiles 8 8 XRAM_TILES_FAR)
chopper_sheet(mid_tiles 8 8 XRAM_TILES_MID)
chopper_sheet(fg_tiles 16 16 XRAM_TILES_FG)

# Binary assets (palettes, tile maps, sound effects)
rp6502_asset(RPMegaChopperII XRAM(XRAM_PALETTES) images/palettes.bin)
rp6502_asset(RPMegaChopperII XRAM(XRAM_SFX_DATA) music/sfx.bin)
rp6502_asset(RPMegaChopperII XRAM(XRAM_MAP_FAR) images/far_map.bin)
rp6502_asset(RPMegaChopperII XRAM(XRAM_MAP_MID) images/mid_map.bin)
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
    src/fx.c
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
