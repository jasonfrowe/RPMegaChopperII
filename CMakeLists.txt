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
chopper_sheet(bomb 8 8 XRAM_IMG_BOMB)
chopper_sheet(bullet 8 4 XRAM_IMG_BULLET)
chopper_sheet(explosion 32 32 XRAM_IMG_EXPLOSION)
chopper_sheet(smallexplosion 16 16 XRAM_IMG_SMALLEXPLOSION)
chopper_sheet(flags 24 16 XRAM_IMG_FLAGS)
chopper_sheet(target 16 16 XRAM_IMG_TARGET)
chopper_sheet(snow 4 4 XRAM_IMG_SNOW)
chopper_sheet(gust 16 8 XRAM_IMG_GUST)
chopper_sheet(logo 64 24 XRAM_IMG_LOGO 1)

# Sound effects
rp6502_asset(RPMegaChopperII XRAM(XRAM_SFX_DATA) music/sfx.bin)

# Each level's own art (enemies, tiles, maps, palettes), packed as
# ROM:level<N>.bin and loaded into XRAM when the level starts.
function(chopper_level n)
    set(out ${CMAKE_CURRENT_BINARY_DIR}/level${n}.bin)
    file(GLOB deps CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/images/level${n}/*)
    add_custom_command(
        OUTPUT ${out}
        COMMAND ${ART_PYTHON} ${CMAKE_CURRENT_SOURCE_DIR}/tools/mklevel.py
            ${CMAKE_CURRENT_SOURCE_DIR}/images/level${n}/level.json ${out}
        DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tools/mklevel.py ${CMAKE_CURRENT_SOURCE_DIR}/tools/png2bin.py ${deps}
        VERBATIM
    )
    rp6502_asset(RPMegaChopperII level${n}.bin ${out})
endfunction()

foreach(n RANGE 1 9)
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/images/level${n}/level.json)
        chopper_level(${n})
    endif()
endforeach()

# Streamed VGM music tracks in ROM
foreach(track Title Stage1 Stage2 Victory Gameover)
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
    src/level.c
    src/music.c
    src/opl.c
    src/player.c
    src/projectiles.c
    src/sfx.c
    src/sprites.c
    src/vgm.c
    src/weather.c
)
