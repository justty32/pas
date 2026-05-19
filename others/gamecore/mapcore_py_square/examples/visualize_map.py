"""方格地圖視覺化範例 (pygame)。

依賴：`pip install pygame`

操作：
    左鍵：循環切換目前格的地形
    右鍵：把目前格設回 PLAINS
    F：整片填成 OCEAN
    R：整片重設為 PLAINS
    Tab：切換顯示「鄰居」(白框) 或「可通行鄰居」(綠框)
    ESC：離開
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.grid import Coord
from mapcore.map import TerrainType, TileMap

TILE_SIZE = 40
MAP_W, MAP_H = 20, 14
MARGIN_X, MARGIN_Y = 40, 30
WIDTH = MAP_W * TILE_SIZE + 2 * MARGIN_X
HEIGHT = MAP_H * TILE_SIZE + 2 * MARGIN_Y + 80

BG = (18, 20, 28)
TEXT = (220, 220, 220)
GRID_LINE = (40, 42, 50)
NEIGHBOR_OUTLINE = (240, 240, 240)
PASSABLE_OUTLINE = (90, 230, 130)
HOVER_OUTLINE = (255, 220, 90)

TERRAIN_COLOR: dict[TerrainType, tuple[int, int, int]] = {
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
    TerrainType.DESERT,
    TerrainType.FOREST,
    TerrainType.HILL,
    TerrainType.MOUNTAIN,
    TerrainType.OCEAN,
    TerrainType.COAST,
    TerrainType.TUNDRA,
    TerrainType.SNOW,
]


def coord_to_pixel(c: Coord) -> tuple[int, int]:
    """格子左上角的螢幕座標。"""
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
    pygame.display.set_caption("mapcore_py_square — map demo")
    font = pygame.font.SysFont("monospace", 16)
    clock = pygame.time.Clock()

    game_map = TileMap(MAP_W, MAP_H, default_terrain=TerrainType.PLAINS)
    show_passable = False
    hovered: Coord | None = None

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_TAB:
                    show_passable = not show_passable
                elif ev.key == pygame.K_f:
                    game_map.fill(TerrainType.OCEAN)
                elif ev.key == pygame.K_r:
                    game_map.fill(TerrainType.PLAINS)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                c = pixel_to_coord(*ev.pos)
                if game_map.in_bounds(c):
                    if ev.button == 1:
                        cur = game_map.get(c).terrain
                        game_map.set_terrain(c, cycle_next(cur))
                    elif ev.button == 3:
                        game_map.set_terrain(c, TerrainType.PLAINS)
            elif ev.type == pygame.MOUSEMOTION:
                c = pixel_to_coord(*ev.pos)
                hovered = c if game_map.in_bounds(c) else None

        screen.fill(BG)
        for c, tile in game_map:
            px, py = coord_to_pixel(c)
            rect = pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, TERRAIN_COLOR[tile.terrain], rect)
            pygame.draw.rect(screen, GRID_LINE, rect, 1)

        if hovered is not None:
            neighbors = (
                game_map.passable_neighbors(hovered)
                if show_passable
                else game_map.neighbors(hovered)
            )
            outline = PASSABLE_OUTLINE if show_passable else NEIGHBOR_OUTLINE
            for n in neighbors:
                px, py = coord_to_pixel(n)
                pygame.draw.rect(screen, outline, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), 3)
            px, py = coord_to_pixel(hovered)
            pygame.draw.rect(screen, HOVER_OUTLINE, pygame.Rect(px, py, TILE_SIZE, TILE_SIZE), 3)

        info = [
            f"Map: {MAP_W}x{MAP_H}  ({len(game_map)} tiles)",
            f"Neighbor mode: {'passable' if show_passable else 'all'}  (Tab to toggle)",
            "Left: cycle terrain  Right: reset to plains  F: fill ocean  R: fill plains  ESC: quit",
        ]
        if hovered is not None:
            t = game_map.get(hovered).terrain
            info.append(f"Hovered: ({hovered.x}, {hovered.y}) = {TerrainType(t).name}")
        for i, txt in enumerate(info):
            screen.blit(font.render(txt, True, TEXT), (10, HEIGHT - 90 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
