"""A* 尋路視覺化範例 (pygame)。

依賴：`pip install pygame`

操作：
    左鍵：設起點 (綠)
    右鍵：設終點 (紅)
    中鍵 / 拖曳左 Shift + 左鍵：循環切換目前格的地形
    F：整片填成 OCEAN
    R：整片重設為 PLAINS
    1-7：把目前游標所在格設成指定地形
         1 PLAINS  2 GRASSLAND  3 DESERT  4 FOREST  5 HILL  6 MOUNTAIN  7 OCEAN
    C：清除起終點
    ESC：離開

路徑會在每次操作後自動重算；不可達時顯示「No path」。
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex, hex_round
from mapcore.map import TerrainType, TileMap
from mapcore.pathfinding import astar, path_cost

HEX_SIZE = 30
MAP_W, MAP_H = 18, 11
WIDTH, HEIGHT = 1200, 800
MARGIN_X, MARGIN_Y = 50, 30

SQRT3 = math.sqrt(3)

BG = (16, 18, 26)
TEXT = (220, 220, 220)
START_COLOR = (60, 220, 110)
GOAL_COLOR = (230, 70, 80)
PATH_COLOR = (255, 235, 90)

TERRAIN_COLOR = {
    TerrainType.OCEAN: (30, 60, 130),
    TerrainType.COAST: (70, 130, 180),
    TerrainType.PLAINS: (180, 180, 90),
    TerrainType.GRASSLAND: (80, 160, 70),
    TerrainType.DESERT: (220, 200, 120),
    TerrainType.TUNDRA: (180, 200, 210),
    TerrainType.SNOW: (235, 240, 245),
    TerrainType.FOREST: (40, 110, 60),
    TerrainType.HILL: (140, 110, 60),
    TerrainType.MOUNTAIN: (110, 100, 100),
}

CYCLE = [
    TerrainType.PLAINS,
    TerrainType.GRASSLAND,
    TerrainType.FOREST,
    TerrainType.DESERT,
    TerrainType.HILL,
    TerrainType.MOUNTAIN,
    TerrainType.OCEAN,
]

KEY_TO_TERRAIN = {
    pygame.K_1: TerrainType.PLAINS,
    pygame.K_2: TerrainType.GRASSLAND,
    pygame.K_3: TerrainType.DESERT,
    pygame.K_4: TerrainType.FOREST,
    pygame.K_5: TerrainType.HILL,
    pygame.K_6: TerrainType.MOUNTAIN,
    pygame.K_7: TerrainType.OCEAN,
}


def hex_to_pixel(h: Hex) -> tuple[float, float]:
    x = HEX_SIZE * (SQRT3 * h.q + SQRT3 / 2 * h.r) + MARGIN_X
    y = HEX_SIZE * (1.5 * h.r) + MARGIN_Y
    return x, y


def pixel_to_hex(px: float, py: float) -> Hex:
    x = (px - MARGIN_X) / HEX_SIZE
    y = (py - MARGIN_Y) / HEX_SIZE
    q = SQRT3 / 3 * x - 1.0 / 3 * y
    r = 2.0 / 3 * y
    return hex_round(q, r)


def hex_corners(cx: float, cy: float) -> list[tuple[float, float]]:
    return [
        (cx + HEX_SIZE * math.cos(math.radians(60 * i - 30)),
         cy + HEX_SIZE * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


def cycle_next(t: TerrainType) -> TerrainType:
    try:
        i = CYCLE.index(t)
    except ValueError:
        return CYCLE[0]
    return CYCLE[(i + 1) % len(CYCLE)]


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py — A* demo")
    font = pygame.font.SysFont("monospace", 16)
    clock = pygame.time.Clock()

    tile_map = TileMap(MAP_W, MAP_H, default_terrain=TerrainType.PLAINS)
    start: Hex | None = None
    goal: Hex | None = None
    path: list[Hex] | None = None

    def recompute():
        nonlocal path
        if start is None or goal is None:
            path = None
        else:
            path = astar(tile_map, start, goal)

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_f:
                    tile_map.fill(TerrainType.OCEAN)
                    recompute()
                elif ev.key == pygame.K_r:
                    tile_map.fill(TerrainType.PLAINS)
                    recompute()
                elif ev.key == pygame.K_c:
                    start = None
                    goal = None
                    recompute()
                elif ev.key in KEY_TO_TERRAIN:
                    mx, my = pygame.mouse.get_pos()
                    h = pixel_to_hex(mx, my)
                    if tile_map.in_bounds(h):
                        tile_map.set_terrain(h, KEY_TO_TERRAIN[ev.key])
                        recompute()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                h = pixel_to_hex(*ev.pos)
                if not tile_map.in_bounds(h):
                    continue
                shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
                if ev.button == 1 and shift:
                    tile_map.set_terrain(h, cycle_next(tile_map.get(h).terrain))
                elif ev.button == 1:
                    start = h
                elif ev.button == 3:
                    goal = h
                elif ev.button == 2:
                    tile_map.set_terrain(h, cycle_next(tile_map.get(h).terrain))
                recompute()

        screen.fill(BG)
        for h, tile in tile_map:
            cx, cy = hex_to_pixel(h)
            pts = hex_corners(cx, cy)
            pygame.draw.polygon(screen, TERRAIN_COLOR[tile.terrain], pts)
            pygame.draw.polygon(screen, (40, 42, 50), pts, 1)

        if path is not None:
            for h in path:
                pts = hex_corners(*hex_to_pixel(h))
                pygame.draw.polygon(screen, PATH_COLOR, pts, 4)

        if start is not None:
            pygame.draw.polygon(screen, START_COLOR, hex_corners(*hex_to_pixel(start)), 5)
        if goal is not None:
            pygame.draw.polygon(screen, GOAL_COLOR, hex_corners(*hex_to_pixel(goal)), 5)

        status = "No path" if (start and goal and path is None) else (
            f"len={len(path) - 1}  cost={path_cost(tile_map, path):.1f}" if path else "—"
        )
        info = [
            f"Map: {MAP_W}x{MAP_H}",
            f"Start: {(start.q, start.r) if start else None}   Goal: {(goal.q, goal.r) if goal else None}",
            f"Path: {status}",
            "Left=start  Right=goal  Middle/Shift+Left=cycle terrain  1-7=terrain at cursor",
            "F=fill ocean  R=fill plains  C=clear  ESC=quit",
        ]
        for i, txt in enumerate(info):
            screen.blit(font.render(txt, True, TEXT), (10, HEIGHT - 110 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
