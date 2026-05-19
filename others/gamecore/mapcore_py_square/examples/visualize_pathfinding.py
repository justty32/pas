"""A* 尋路視覺化範例 (pygame, 4 鄰居方格版)。

依賴：`pip install pygame`

操作：
    左鍵：設起點 (綠)
    右鍵：設終點 (紅)
    中鍵 / Shift + 左鍵：循環切換目前格的地形
    F：整片填成 OCEAN
    R：整片重設為 PLAINS
    1-7：把目前游標所在格設成指定地形
         1 PLAINS  2 GRASSLAND  3 DESERT  4 FOREST  5 HILL  6 MOUNTAIN  7 OCEAN
    C：清除起終點
    ESC：離開

路徑會在每次操作後自動重算；不可達時顯示「No path」。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.grid import Coord
from mapcore.map import TerrainType, TileMap
from mapcore.pathfinding import astar, path_cost

TILE_SIZE = 40
MAP_W, MAP_H = 22, 15
MARGIN_X, MARGIN_Y = 30, 20
WIDTH = MAP_W * TILE_SIZE + 2 * MARGIN_X
HEIGHT = MAP_H * TILE_SIZE + 2 * MARGIN_Y + 110

BG = (16, 18, 26)
TEXT = (220, 220, 220)
GRID_LINE = (40, 42, 50)
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


def coord_to_pixel(c: Coord) -> tuple[int, int]:
    return MARGIN_X + c.x * TILE_SIZE, MARGIN_Y + c.y * TILE_SIZE


def pixel_to_coord(px: int, py: int) -> Coord:
    return Coord((px - MARGIN_X) // TILE_SIZE, (py - MARGIN_Y) // TILE_SIZE)


def cycle_next(t: TerrainType) -> TerrainType:
    try:
        i = CYCLE.index(t)
    except ValueError:
        return CYCLE[0]
    return CYCLE[(i + 1) % len(CYCLE)]


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py_square — A* demo")
    font = pygame.font.SysFont("monospace", 16)
    clock = pygame.time.Clock()

    tile_map = TileMap(MAP_W, MAP_H, default_terrain=TerrainType.PLAINS)
    start: Coord | None = None
    goal: Coord | None = None
    path: list[Coord] | None = None

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
                    c = pixel_to_coord(mx, my)
                    if tile_map.in_bounds(c):
                        tile_map.set_terrain(c, KEY_TO_TERRAIN[ev.key])
                        recompute()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                c = pixel_to_coord(*ev.pos)
                if not tile_map.in_bounds(c):
                    continue
                shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
                if ev.button == 1 and shift:
                    tile_map.set_terrain(c, cycle_next(tile_map.get(c).terrain))
                elif ev.button == 1:
                    start = c
                elif ev.button == 3:
                    goal = c
                elif ev.button == 2:
                    tile_map.set_terrain(c, cycle_next(tile_map.get(c).terrain))
                recompute()

        screen.fill(BG)
        for c, tile in tile_map:
            px, py = coord_to_pixel(c)
            rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, TERRAIN_COLOR[tile.terrain], rect)
            pygame.draw.rect(screen, GRID_LINE, rect, 1)

        if path is not None:
            # 用粗線連接路徑中心點，比 outline 更能看清楚 4 連通路徑的轉折
            half = TILE_SIZE // 2
            pts = [(coord_to_pixel(c)[0] + half, coord_to_pixel(c)[1] + half) for c in path]
            if len(pts) >= 2:
                pygame.draw.lines(screen, PATH_COLOR, False, pts, 5)
            for c in path:
                px, py = coord_to_pixel(c)
                pygame.draw.rect(screen, PATH_COLOR, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), 2)

        if start is not None:
            px, py = coord_to_pixel(start)
            pygame.draw.rect(screen, START_COLOR, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), 5)
        if goal is not None:
            px, py = coord_to_pixel(goal)
            pygame.draw.rect(screen, GOAL_COLOR, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), 5)

        status = "No path" if (start and goal and path is None) else (
            f"len={len(path) - 1}  cost={path_cost(tile_map, path):.1f}" if path else "—"
        )
        info = [
            f"Map: {MAP_W}x{MAP_H}",
            f"Start: {(start.x, start.y) if start else None}   Goal: {(goal.x, goal.y) if goal else None}",
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
