"""TileMap 視覺化範例 (pygame)。

依賴：`pip install pygame`

操作：
    左鍵：循環切換目前格的地形 (PLAINS → GRASSLAND → DESERT → FOREST → HILL → MOUNTAIN → OCEAN → COAST → ...)
    右鍵：把目前格設回 PLAINS
    F：整片填成 OCEAN
    R：整片重設為 PLAINS
    Tab：切換顯示「鄰居」(白框) 或「可通行鄰居」(綠框)
    ESC：離開

繪製採平行四邊形地圖；C++ 版同樣的 2D array 在 hex_to_pixel 後也是這個外觀。
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import Hex, hex_round
from mapcore.map import TerrainType, TileMap

HEX_SIZE = 30
MAP_W, MAP_H = 16, 10
WIDTH, HEIGHT = 1100, 760
MARGIN_X, MARGIN_Y = 60, 40

SQRT3 = math.sqrt(3)

BG = (18, 20, 28)
TEXT = (220, 220, 220)
NEIGHBOR_OUTLINE = (240, 240, 240)
PASSABLE_OUTLINE = (90, 230, 130)

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

# 左鍵點擊循環的地形順序
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
    pts = []
    for i in range(6):
        a = math.radians(60 * i - 30)
        pts.append((cx + HEX_SIZE * math.cos(a), cy + HEX_SIZE * math.sin(a)))
    return pts


def cycle_next(t: TerrainType) -> TerrainType:
    try:
        i = CYCLE.index(t)
    except ValueError:
        return CYCLE[0]
    return CYCLE[(i + 1) % len(CYCLE)]


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py — map demo")
    font = pygame.font.SysFont("monospace", 16)
    clock = pygame.time.Clock()

    game_map = TileMap(MAP_W, MAP_H, default_terrain=TerrainType.PLAINS)
    show_passable = False
    hovered: Hex | None = None

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
                h = pixel_to_hex(*ev.pos)
                if game_map.in_bounds(h):
                    if ev.button == 1:
                        cur = game_map.get(h).terrain
                        game_map.set_terrain(h, cycle_next(cur))
                    elif ev.button == 3:
                        game_map.set_terrain(h, TerrainType.PLAINS)
            elif ev.type == pygame.MOUSEMOTION:
                h = pixel_to_hex(*ev.pos)
                hovered = h if game_map.in_bounds(h) else None

        screen.fill(BG)
        for h, tile in game_map:
            cx, cy = hex_to_pixel(h)
            pts = hex_corners(cx, cy)
            pygame.draw.polygon(screen, TERRAIN_COLOR[tile.terrain], pts)
            pygame.draw.polygon(screen, (40, 42, 50), pts, 1)

        if hovered is not None:
            neighbors = (
                game_map.passable_neighbors(hovered) if show_passable else game_map.neighbors(hovered)
            )
            outline = PASSABLE_OUTLINE if show_passable else NEIGHBOR_OUTLINE
            for n in neighbors:
                pts = hex_corners(*hex_to_pixel(n))
                pygame.draw.polygon(screen, outline, pts, 3)
            pts = hex_corners(*hex_to_pixel(hovered))
            pygame.draw.polygon(screen, (255, 220, 90), pts, 3)

        info = [
            f"Map: {MAP_W}x{MAP_H}  ({len(game_map)} tiles)",
            f"Neighbor mode: {'passable' if show_passable else 'all'}  (Tab to toggle)",
            "Left: cycle terrain  Right: reset to plains  F: fill ocean  R: fill plains  ESC: quit",
        ]
        if hovered is not None:
            t = game_map.get(hovered).terrain
            info.append(f"Hovered: ({hovered.q}, {hovered.r}) = {t.name}")
        for i, txt in enumerate(info):
            screen.blit(font.render(txt, True, TEXT), (10, HEIGHT - 90 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
