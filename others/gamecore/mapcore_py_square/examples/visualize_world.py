"""完整世界生成視覺化 (pygame, 4 鄰居方格版)。

跑完整 Phase 1~7 pipeline 並把結果畫出來：地形色塊、河流邊、feature 標籤。

依賴：`pip install pygame`

操作：
    1-5：切換顯示模式（biome / heightmap / rainfall / temperature / hilliness）
    L：切換 feature 標籤顯示
    R：切換河流顯示
    [ / ]：減少/增加 seed 重新生成
    SPACE：用當前 seed 重新生成
    P：切換大陸形狀預設（pangaea / continents / archipelago / island / None）
    ESC：離開

預設地圖 80x50，種子 42，continents shape，板塊山脊。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation import generate_world
from mapcore.grid import DIRECTIONS, Coord
from mapcore.map import Hilliness, TerrainType
from mapcore.rivers import iter_river_edges, classify_river_strength, RiverClass

TILE_SIZE = 12
MAP_W, MAP_H = 80, 50
MARGIN_X, MARGIN_Y = 20, 20
INFO_HEIGHT = 100
WIDTH = MAP_W * TILE_SIZE + 2 * MARGIN_X
HEIGHT = MAP_H * TILE_SIZE + 2 * MARGIN_Y + INFO_HEIGHT

BG = (12, 14, 22)
TEXT = (220, 220, 220)
GRID_LINE = (0, 0, 0, 0)  # 不畫格線（地圖太密）

TERRAIN_COLOR = {
    TerrainType.OCEAN: (24, 50, 110),
    TerrainType.COAST: (70, 130, 180),
    TerrainType.LAKE: (60, 110, 200),
    TerrainType.PLAINS: (180, 180, 90),
    TerrainType.GRASSLAND: (80, 160, 70),
    TerrainType.DESERT: (220, 200, 120),
    TerrainType.TUNDRA: (180, 200, 210),
    TerrainType.SNOW: (235, 240, 245),
    TerrainType.FOREST: (40, 110, 60),
    TerrainType.HILL: (140, 110, 60),
    TerrainType.MOUNTAIN: (110, 100, 100),
}

RIVER_COLORS = {
    RiverClass.CREEK: (100, 170, 230),
    RiverClass.RIVER: (60, 130, 220),
    RiverClass.LARGE_RIVER: (40, 90, 200),
}

RIVER_WIDTHS = {
    RiverClass.CREEK: 1,
    RiverClass.RIVER: 2,
    RiverClass.LARGE_RIVER: 3,
}

VIEW_MODES = ("biome", "heightmap", "rainfall", "temperature", "hilliness")
SHAPES = (None, "continents", "pangaea", "archipelago", "island", "ring_sea", "shattered_archipelago")


def coord_to_pixel(c: Coord) -> tuple[int, int]:
    return MARGIN_X + c.x * TILE_SIZE, MARGIN_Y + c.y * TILE_SIZE


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def color_for_view(view_mode, x, y, tile, result):
    if view_mode == "biome":
        return TERRAIN_COLOR.get(tile.terrain, (200, 0, 200))
    if view_mode == "heightmap":
        v = result.heightmap[y][x]
        return lerp_color((30, 30, 100), (240, 230, 180), v)
    if view_mode == "rainfall":
        if result.rainfall_mm is None:
            return (60, 60, 60)
        v = min(result.rainfall_mm[y][x] / 4000.0, 1.0)
        return lerp_color((230, 200, 130), (40, 80, 200), v)
    if view_mode == "temperature":
        if result.temperature_celsius is None:
            return (60, 60, 60)
        t = (result.temperature_celsius[y][x] + 40.0) / 80.0
        t = max(0.0, min(1.0, t))
        return lerp_color((30, 60, 180), (220, 80, 50), t)
    if view_mode == "hilliness":
        hilliness_colors = {
            Hilliness.UNDEFINED: (40, 40, 40),
            Hilliness.FLAT: (130, 170, 130),
            Hilliness.SMALL_HILLS: (180, 170, 110),
            Hilliness.LARGE_HILLS: (170, 130, 80),
            Hilliness.MOUNTAINOUS: (130, 110, 100),
            Hilliness.IMPASSABLE: (90, 80, 80),
        }
        return hilliness_colors.get(tile.hilliness, (60, 60, 60))
    return (60, 60, 60)


def draw_rivers(screen, result):
    """畫河流邊。河流邊 (c, direction, strength)：
    - direction 0 (E) → 從 (x+1, y) 到 (x+1, y+1) 的垂直邊
    - direction 1 (N) → 從 (x, y) 到 (x+1, y) 的水平邊
    （direction 永遠是 owner 視角的 0 或 1，由 iter_river_edges 保證）
    """
    for c, d, s in iter_river_edges(result.tile_map):
        cls = classify_river_strength(s)
        color = RIVER_COLORS[cls]
        width = RIVER_WIDTHS[cls]
        px, py = coord_to_pixel(c)
        if d == 0:  # E
            # 右邊 = (x+TILE, y) → (x+TILE, y+TILE)
            pygame.draw.line(
                screen, color,
                (px + TILE_SIZE, py),
                (px + TILE_SIZE, py + TILE_SIZE),
                width,
            )
        elif d == 1:  # N
            # 上邊 = (x, y) → (x+TILE, y)
            pygame.draw.line(
                screen, color,
                (px, py),
                (px + TILE_SIZE, py),
                width,
            )


def draw_labels(screen, result, font):
    for f in result.tile_map.features:
        # 過小不畫
        if f.size < 15:
            continue
        # Continent 用較淡色標籤
        alpha = 200 if f.feature_type != "Continent" else 140
        text_color = (255, 255, 255)
        cx, cy = coord_to_pixel(f.center)
        cx += TILE_SIZE // 2
        cy += TILE_SIZE // 2
        surf = font.render(f.name, True, text_color)
        surf.set_alpha(alpha)
        rect = surf.get_rect(center=(cx, cy))
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        bg.fill((0, 0, 0, 90))
        screen.blit(bg, rect)
        screen.blit(surf, rect)


def generate(seed, shape):
    return generate_world(
        MAP_W, MAP_H,
        seed=seed,
        heightmap_shape=shape,
        heightmap_ridge_weight=0.6,
        heightmap_num_plates=15,
        climate_rain_shadow_strength=0.3,
        lake_depressions=True,
        river_min_sea_size=8,
        river_min_seed_spacing=3,
    )


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py_square — world demo")
    font_label = pygame.font.SysFont("monospace", 11)
    font_info = pygame.font.SysFont("monospace", 14)
    clock = pygame.time.Clock()

    seed = 42
    shape = "continents"
    view_mode = "biome"
    show_labels = True
    show_rivers = True

    result = generate(seed, shape)

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_1:
                    view_mode = "biome"
                elif ev.key == pygame.K_2:
                    view_mode = "heightmap"
                elif ev.key == pygame.K_3:
                    view_mode = "rainfall"
                elif ev.key == pygame.K_4:
                    view_mode = "temperature"
                elif ev.key == pygame.K_5:
                    view_mode = "hilliness"
                elif ev.key == pygame.K_l:
                    show_labels = not show_labels
                elif ev.key == pygame.K_r:
                    show_rivers = not show_rivers
                elif ev.key == pygame.K_LEFTBRACKET:
                    seed -= 1
                    result = generate(seed, shape)
                elif ev.key == pygame.K_RIGHTBRACKET:
                    seed += 1
                    result = generate(seed, shape)
                elif ev.key == pygame.K_SPACE:
                    result = generate(seed, shape)
                elif ev.key == pygame.K_p:
                    i = SHAPES.index(shape) if shape in SHAPES else 0
                    shape = SHAPES[(i + 1) % len(SHAPES)]
                    result = generate(seed, shape)

        screen.fill(BG)

        # 地圖本體
        for y in range(MAP_H):
            for x in range(MAP_W):
                tile = result.tile_map._rows[y][x]
                color = color_for_view(view_mode, x, y, tile, result)
                px = MARGIN_X + x * TILE_SIZE
                py = MARGIN_Y + y * TILE_SIZE
                pygame.draw.rect(screen, color, (px, py, TILE_SIZE, TILE_SIZE))

        # 河流（畫在地圖之上、標籤之下）
        if show_rivers and view_mode in ("biome", "heightmap"):
            draw_rivers(screen, result)

        # Feature 標籤
        if show_labels and view_mode == "biome":
            draw_labels(screen, result, font_label)

        # 資訊列
        rivers_count = sum(1 for _ in iter_river_edges(result.tile_map))
        info = [
            f"Map {MAP_W}x{MAP_H}  seed={seed}  shape={shape}  view={view_mode}",
            f"Features: {len(result.tile_map.features)}  River edges: {rivers_count}",
            "1-5=view  L=labels  R=rivers  [ ]=seed-/+  SPACE=regen  P=shape  ESC=quit",
        ]
        for i, txt in enumerate(info):
            screen.blit(font_info.render(txt, True, TEXT), (10, HEIGHT - INFO_HEIGHT + i * 22))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
