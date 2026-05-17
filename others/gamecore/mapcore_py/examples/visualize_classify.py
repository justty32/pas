"""海平面切割視覺化範例 (Phase 2, pygame)。

依賴：`pip install pygame`

操作：
    Space：換新 seed
    N / M：seed -1 / +1
    +/-：調 octaves
    [/]：調 persistence
    ,/.：調 base_frequency
    方向鍵 ←→↑↓：平移視角   Home：相機歸位
    PgUp / PgDn：調 sea_level (0.00 ~ 1.00, 0.02 為一格)
    ; / '：調 coast_depth (0 ~ 8)
    H：切顯示模式 (terrain / heightmap)
    ESC：離開
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.classify import heightmap_to_tilemap
from mapcore.generation.heightmap import generate_heightmap
from mapcore.hex import Hex
from mapcore.map import TerrainType

HEX_SIZE = 16
MAP_W, MAP_H = 80, 50
WIDTH, HEIGHT = 1280, 760
MARGIN_X, MARGIN_Y = 30, 20
SCROLL_SPEED = 10

SQRT3 = math.sqrt(3)
BG = (12, 14, 20)
TEXT = (220, 220, 220)

TERRAIN_COLOR = {
    TerrainType.OCEAN: (20, 50, 110),
    TerrainType.COAST: (70, 140, 200),
    TerrainType.PLAINS: (140, 170, 90),
    TerrainType.GRASSLAND: (80, 160, 70),
    TerrainType.DESERT: (220, 200, 120),
    TerrainType.TUNDRA: (180, 200, 210),
    TerrainType.SNOW: (235, 240, 245),
    TerrainType.FOREST: (40, 110, 60),
    TerrainType.HILL: (140, 110, 60),
    TerrainType.MOUNTAIN: (110, 100, 100),
}


def hex_to_pixel(h: Hex, cam_x: float = 0.0, cam_y: float = 0.0) -> tuple[float, float]:
    x = HEX_SIZE * (SQRT3 * h.q + SQRT3 / 2 * h.r) + MARGIN_X - cam_x
    y = HEX_SIZE * (1.5 * h.r) + MARGIN_Y - cam_y
    return x, y


def hex_corners(cx: float, cy: float) -> list[tuple[float, float]]:
    return [
        (cx + HEX_SIZE * math.cos(math.radians(60 * i - 30)),
         cy + HEX_SIZE * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


def grayscale(v: float) -> tuple[int, int, int]:
    g = max(0, min(255, int(v * 255)))
    return g, g, g


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py — classify demo")
    font = pygame.font.SysFont("monospace", 16)
    clock = pygame.time.Clock()

    seed = random.randint(0, 99999)
    octaves = 5
    persistence = 0.5
    base_frequency = 4
    sea_level = 0.40
    coast_depth = 1
    show_heightmap = False
    cam_x, cam_y = 0.0, 0.0

    def regen_heightmap():
        return generate_heightmap(
            MAP_W, MAP_H,
            seed=seed, octaves=octaves,
            persistence=persistence, base_frequency=base_frequency,
        )

    heightmap = regen_heightmap()
    tile_map = heightmap_to_tilemap(heightmap, sea_level=sea_level, coast_depth=coast_depth)
    dirty_height = False
    dirty_class = False
    running = True

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    seed = random.randint(0, 99999); dirty_height = True
                elif ev.key == pygame.K_n:
                    seed = max(0, seed - 1); dirty_height = True
                elif ev.key == pygame.K_m:
                    seed += 1; dirty_height = True
                elif ev.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    octaves = min(8, octaves + 1); dirty_height = True
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    octaves = max(1, octaves - 1); dirty_height = True
                elif ev.key == pygame.K_LEFTBRACKET:
                    persistence = max(0.1, round(persistence - 0.05, 2)); dirty_height = True
                elif ev.key == pygame.K_RIGHTBRACKET:
                    persistence = min(1.0, round(persistence + 0.05, 2)); dirty_height = True
                elif ev.key == pygame.K_COMMA:
                    base_frequency = max(1, base_frequency - 1); dirty_height = True
                elif ev.key == pygame.K_PERIOD:
                    base_frequency = min(16, base_frequency + 1); dirty_height = True
                elif ev.key == pygame.K_PAGEUP:
                    sea_level = min(1.0, round(sea_level + 0.02, 2)); dirty_class = True
                elif ev.key == pygame.K_PAGEDOWN:
                    sea_level = max(0.0, round(sea_level - 0.02, 2)); dirty_class = True
                elif ev.key == pygame.K_HOME:
                    cam_x, cam_y = 0.0, 0.0
                elif ev.key == pygame.K_SEMICOLON:
                    coast_depth = max(0, coast_depth - 1); dirty_class = True
                elif ev.key == pygame.K_QUOTE:
                    coast_depth = min(8, coast_depth + 1); dirty_class = True
                elif ev.key == pygame.K_h:
                    show_heightmap = not show_heightmap

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  cam_x -= SCROLL_SPEED
        if keys[pygame.K_RIGHT]: cam_x += SCROLL_SPEED
        if keys[pygame.K_UP]:    cam_y -= SCROLL_SPEED
        if keys[pygame.K_DOWN]:  cam_y += SCROLL_SPEED

        if dirty_height:
            heightmap = regen_heightmap()
            dirty_height = False
            dirty_class = True
        if dirty_class:
            tile_map = heightmap_to_tilemap(heightmap, sea_level=sea_level, coast_depth=coast_depth)
            dirty_class = False

        screen.fill(BG)
        if show_heightmap:
            for r in range(MAP_H):
                for q in range(MAP_W):
                    cx, cy = hex_to_pixel(Hex(q, r), cam_x, cam_y)
                    if cx < -HEX_SIZE or cx > WIDTH + HEX_SIZE: continue
                    if cy < -HEX_SIZE or cy > HEIGHT + HEX_SIZE: continue
                    pygame.draw.polygon(screen, grayscale(heightmap[r][q]), hex_corners(cx, cy))
        else:
            for h, tile in tile_map:
                cx, cy = hex_to_pixel(h, cam_x, cam_y)
                if cx < -HEX_SIZE or cx > WIDTH + HEX_SIZE: continue
                if cy < -HEX_SIZE or cy > HEIGHT + HEX_SIZE: continue
                pygame.draw.polygon(screen, TERRAIN_COLOR[tile.terrain], hex_corners(cx, cy))

        ocean = coast = plains = 0
        for _, t in tile_map:
            if t.terrain == TerrainType.OCEAN:
                ocean += 1
            elif t.terrain == TerrainType.COAST:
                coast += 1
            else:
                plains += 1
        total = ocean + coast + plains

        info = [
            f"seed={seed}  octaves={octaves}  persistence={persistence}  base_freq={base_frequency}  cam=({cam_x:.0f},{cam_y:.0f})",
            f"sea_level={sea_level:.2f} (PgUp/PgDn)   coast_depth={coast_depth} (;/')   view: {'heightmap' if show_heightmap else 'terrain'} (H)",
            f"ocean={ocean} ({ocean*100/total:.0f}%)  coast={coast} ({coast*100/total:.0f}%)  land={plains} ({plains*100/total:.0f}%)",
            "Arrows=pan  Home=reset cam  Space=random  N/M=seed  +/-=octaves  [/]=persistence  ,/.=base_freq  ESC=quit",
        ]
        for i, txt in enumerate(info):
            screen.blit(font.render(txt, True, TEXT), (10, HEIGHT - 90 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
