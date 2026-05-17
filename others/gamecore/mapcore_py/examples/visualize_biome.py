"""生物群系視覺化範例 (Phase 3, pygame)。

依賴：`pip install pygame`

操作：
    方向鍵 ←→↑↓：平移視角（持續按住）   Home：相機歸位
    Space：換新 seed
    N / M：seed -1 / +1
    +/-：調 octaves
    [/]：調 persistence
    ,/.：調 base_frequency
    PgUp / PgDn：調 sea_level
    ; / '：調 coast_depth
    1 / 2 / 3 / 4 / 5 / 6：view = terrain / heightmap / moisture / temperature / hilliness / features
    P：切換 post_process    9 / 0：調 island_min_size    O / L：調 lake_max_size
    R：切換 rivers 顯示
    K：循環河流密度預設 (Dense → Medium → Sparse → Rare)
    B：切換河流分支 (on/off)
    ESC：離開
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.climate import compute_temperature_celsius
from mapcore.generation.pipeline import generate_world
from mapcore.generation.postprocess import find_components, is_land
from mapcore.hex import DIRECTIONS, Hex
from mapcore.map import Hilliness, TerrainType
from mapcore.rivers import iter_river_edges

HEX_SIZE = 16
MAP_W, MAP_H = 80, 50
WIDTH, HEIGHT = 1280, 760
MARGIN_X, MARGIN_Y = 30, 20
SCROLL_SPEED = 10
RIVER_COLOR = (110, 200, 250)

SQRT3 = math.sqrt(3)
BG = (12, 14, 20)
TEXT = (220, 220, 220)

TERRAIN_COLOR = {
    TerrainType.OCEAN: (20, 50, 110),
    TerrainType.COAST: (70, 140, 200),
    TerrainType.PLAINS: (200, 200, 110),
    TerrainType.GRASSLAND: (95, 175, 80),
    TerrainType.DESERT: (230, 210, 130),
    TerrainType.TUNDRA: (180, 200, 200),
    TerrainType.SNOW: (240, 245, 250),
    TerrainType.FOREST: (35, 110, 55),
    TerrainType.HILL: (140, 110, 60),
    TerrainType.MOUNTAIN: (110, 100, 100),
}

VIEW_TERRAIN, VIEW_HEIGHT, VIEW_MOISTURE, VIEW_TEMP = "terrain", "height", "moisture", "temp"
VIEW_HILLINESS, VIEW_FEATURES = "hilliness", "features"

# 河流密度預設：(label, spawn_threshold, degrade_threshold, branch_flow_threshold, branch_chance)
# 對齊 RW RiverDef tier 概念：
#   Dense  ≈ 比 RW Creek 更低門檻，溪流到處都是
#   Medium ≈ RW Creek (600)        ← 預設
#   Sparse ≈ RW River (2000)
#   Rare   ≈ RW LargeRiver (4000)，只剩主流
RIVER_DENSITY_PRESETS = [
    ("Dense",  200.0,  50.0,  120.0, 0.5),
    ("Medium", 600.0,  200.0, 400.0, 0.3),
    ("Sparse", 1500.0, 500.0, 1000.0, 0.2),
    ("Rare",   3500.0, 1500.0, 2500.0, 0.1),
]
VIEW_KEYS = {
    pygame.K_1: VIEW_TERRAIN,
    pygame.K_2: VIEW_HEIGHT,
    pygame.K_3: VIEW_MOISTURE,
    pygame.K_4: VIEW_TEMP,
    pygame.K_5: VIEW_HILLINESS,
    pygame.K_6: VIEW_FEATURES,
}

# 5 級灰階：Flat 亮 → Impassable 暗；UNDEFINED 給藍灰
HILLINESS_COLOR = {
    Hilliness.UNDEFINED: (40, 50, 70),
    Hilliness.FLAT: (220, 220, 200),
    Hilliness.SMALL_HILLS: (180, 170, 130),
    Hilliness.LARGE_HILLS: (140, 120, 90),
    Hilliness.MOUNTAINOUS: (100, 90, 80),
    Hilliness.IMPASSABLE: (60, 55, 50),
}


def feature_color(feature_id: int) -> tuple[int, int, int]:
    """穩定哈希到 HSV 中均勻色相，避免相鄰 feature 撞色。"""
    if feature_id < 0:
        return (40, 40, 50)
    # golden-ratio 序列在小整數上分布均勻
    hue = (feature_id * 0.61803398875) % 1.0
    # HSV → RGB，S=0.55 V=0.78
    i = int(hue * 6)
    f = hue * 6 - i
    p = int(255 * 0.78 * (1 - 0.55))
    q = int(255 * 0.78 * (1 - 0.55 * f))
    t = int(255 * 0.78 * (1 - 0.55 * (1 - f)))
    v = int(255 * 0.78)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i % 6]


def hex_to_pixel(h: Hex, cam_x: float = 0.0, cam_y: float = 0.0) -> tuple[float, float]:
    return (
        HEX_SIZE * (SQRT3 * h.q + SQRT3 / 2 * h.r) + MARGIN_X - cam_x,
        HEX_SIZE * (1.5 * h.r) + MARGIN_Y - cam_y,
    )


def hex_corners(cx: float, cy: float) -> list[tuple[float, float]]:
    return [
        (cx + HEX_SIZE * math.cos(math.radians(60 * i - 30)),
         cy + HEX_SIZE * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


def grayscale(v: float) -> tuple[int, int, int]:
    g = max(0, min(255, int(v * 255)))
    return g, g, g


def temperature_norm_at(r: int, q: int, hm: list[list[float]], H: int) -> float:
    """用 climate.compute_temperature_celsius 算真實 °C，再映射到 [0, 1] 給 heatmap_color。

    線性映射：-40°C → 0（冷），30°C → 1（熱）。對齊 RW AvgTempByLatitudeCurve 兩端。
    """
    c = compute_temperature_celsius(r, H, hm[r][q])
    return max(0.0, min(1.0, (c - (-40.0)) / (30.0 - (-40.0))))


def heatmap_color(v: float) -> tuple[int, int, int]:
    """blue (cold) → green → yellow → red (hot); v ∈ [0, 1]"""
    stops = [
        (0.0, (40, 60, 200)),
        (0.4, (80, 200, 200)),
        (0.6, (120, 220, 120)),
        (0.8, (240, 220, 90)),
        (1.0, (230, 80, 60)),
    ]
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]
        v1, c1 = stops[i + 1]
        if v <= v1:
            t = 0.0 if v1 == v0 else (v - v0) / (v1 - v0)
            return tuple(int(c0[k] * (1 - t) + c1[k] * t) for k in range(3))  # type: ignore[return-value]
    return stops[-1][1]


def _load_cjk_font(size: int) -> "pygame.font.Font":
    """嘗試載入支援繁中的字體；找不到才退回 SysFont monospace。

    pygame.font.SysFont 可接逗號分隔的多個候選名稱，會依序嘗試。
    """
    candidates = [
        "notosanscjktc", "notosanscjksc", "notosansmonocjktc",
        "microsoftjhenghei", "msjh", "pingfang", "pingfangtc",
        "simhei", "simsun", "wqyzenhei", "wqymicrohei",
        "monospace",
    ]
    return pygame.font.SysFont(",".join(candidates), size)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("mapcore_py — biome demo")
    font = pygame.font.SysFont("monospace", 16)
    label_font = _load_cjk_font(15)  # feature 名稱用，需要 CJK 支援
    clock = pygame.time.Clock()

    seed = random.randint(0, 99999)
    octaves = 5
    persistence = 0.5
    base_frequency = 4
    sea_level = 0.40
    coast_depth = 1
    view = VIEW_TERRAIN
    do_post = True
    island_min_size = 3
    lake_max_size = 4
    show_rivers = True
    river_preset_idx = 1   # 預設 Medium (對齊 RW Creek)
    river_branches = True
    cam_x, cam_y = 0.0, 0.0

    def regen():
        _, spawn_th, degrade_th, branch_th, branch_ch = RIVER_DENSITY_PRESETS[river_preset_idx]
        return generate_world(
            MAP_W, MAP_H,
            seed=seed, sea_level=sea_level, coast_depth=coast_depth,
            octaves=octaves, persistence=persistence, base_frequency=base_frequency,
            post_process=do_post,
            island_min_size=island_min_size,
            lake_max_size=lake_max_size,
            river_spawn_flow_threshold=spawn_th,
            river_degrade_threshold=degrade_th,
            river_branch_flow_threshold=branch_th,
            river_branch_chance=branch_ch if river_branches else 0.0,
        )

    tile_map, heightmap, moisture = regen()
    dirty = False
    running = True

    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    seed = random.randint(0, 99999); dirty = True
                elif ev.key == pygame.K_n:
                    seed = max(0, seed - 1); dirty = True
                elif ev.key == pygame.K_m:
                    seed += 1; dirty = True
                elif ev.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    octaves = min(8, octaves + 1); dirty = True
                elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    octaves = max(1, octaves - 1); dirty = True
                elif ev.key == pygame.K_LEFTBRACKET:
                    persistence = max(0.1, round(persistence - 0.05, 2)); dirty = True
                elif ev.key == pygame.K_RIGHTBRACKET:
                    persistence = min(1.0, round(persistence + 0.05, 2)); dirty = True
                elif ev.key == pygame.K_COMMA:
                    base_frequency = max(1, base_frequency - 1); dirty = True
                elif ev.key == pygame.K_PERIOD:
                    base_frequency = min(16, base_frequency + 1); dirty = True
                elif ev.key == pygame.K_PAGEUP:
                    sea_level = min(1.0, round(sea_level + 0.02, 2)); dirty = True
                elif ev.key == pygame.K_PAGEDOWN:
                    sea_level = max(0.0, round(sea_level - 0.02, 2)); dirty = True
                elif ev.key == pygame.K_SEMICOLON:
                    coast_depth = max(0, coast_depth - 1); dirty = True
                elif ev.key == pygame.K_QUOTE:
                    coast_depth = min(8, coast_depth + 1); dirty = True
                elif ev.key in VIEW_KEYS:
                    view = VIEW_KEYS[ev.key]
                elif ev.key == pygame.K_p:
                    do_post = not do_post; dirty = True
                elif ev.key == pygame.K_9:
                    island_min_size = max(1, island_min_size - 1); dirty = True
                elif ev.key == pygame.K_0:
                    island_min_size = min(50, island_min_size + 1); dirty = True
                elif ev.key == pygame.K_o:
                    lake_max_size = max(0, lake_max_size - 1); dirty = True
                elif ev.key == pygame.K_l:
                    lake_max_size = min(50, lake_max_size + 1); dirty = True
                elif ev.key == pygame.K_r:
                    show_rivers = not show_rivers
                elif ev.key == pygame.K_k:
                    river_preset_idx = (river_preset_idx + 1) % len(RIVER_DENSITY_PRESETS); dirty = True
                elif ev.key == pygame.K_b:
                    river_branches = not river_branches; dirty = True
                elif ev.key == pygame.K_HOME:
                    cam_x, cam_y = 0.0, 0.0

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  cam_x -= SCROLL_SPEED
        if keys[pygame.K_RIGHT]: cam_x += SCROLL_SPEED
        if keys[pygame.K_UP]:    cam_y -= SCROLL_SPEED
        if keys[pygame.K_DOWN]:  cam_y += SCROLL_SPEED

        if dirty:
            tile_map, heightmap, moisture = regen()
            dirty = False

        screen.fill(BG)
        for r in range(MAP_H):
            for q in range(MAP_W):
                cx, cy = hex_to_pixel(Hex(q, r), cam_x, cam_y)
                # 簡單裁剪：完全離開螢幕的就不畫
                if cx < -HEX_SIZE or cx > WIDTH + HEX_SIZE:
                    continue
                if cy < -HEX_SIZE or cy > HEIGHT + HEX_SIZE:
                    continue
                pts = hex_corners(cx, cy)
                tile = tile_map.get(Hex(q, r))
                if view == VIEW_TERRAIN:
                    color = TERRAIN_COLOR[tile.terrain]
                elif view == VIEW_HEIGHT:
                    color = grayscale(heightmap[r][q])
                elif view == VIEW_MOISTURE:
                    color = grayscale(moisture[r][q])
                elif view == VIEW_TEMP:
                    color = heatmap_color(temperature_norm_at(r, q, heightmap, MAP_H))
                elif view == VIEW_HILLINESS:
                    color = HILLINESS_COLOR.get(tile.hilliness, (50, 50, 60))
                else:  # VIEW_FEATURES
                    color = feature_color(tile.feature_id)
                pygame.draw.polygon(screen, color, pts)

        if show_rivers:
            # RimWorld 風：河流走 tile center → tile center（穿過共享邊）。
            # iter_river_edges 只回 direction 0..2，owner_hex + DIRECTIONS[d] 是另一端 tile。
            # 同一條多段河流會在 tile 中心自然交會，看得到匯流節點。
            for h, d, strength in iter_river_edges(tile_map):
                nb = h + DIRECTIONS[d]
                cx_o, cy_o = hex_to_pixel(h, cam_x, cam_y)
                cx_n, cy_n = hex_to_pixel(nb, cam_x, cam_y)
                width = min(2 + (strength - 1) // 2, 7)
                pygame.draw.line(screen, RIVER_COLOR, (cx_o, cy_o), (cx_n, cy_n), width)

        # features view 時把每個 feature 名字畫在重心位置
        if view == VIEW_FEATURES and tile_map.features is not None:
            for f in tile_map.features:
                cx, cy = hex_to_pixel(f.center, cam_x, cam_y)
                if -50 < cx < WIDTH + 50 and -50 < cy < HEIGHT + 50:
                    label = label_font.render(f.name, True, (250, 250, 250))
                    shadow = label_font.render(f.name, True, (0, 0, 0))
                    screen.blit(shadow, (cx - label.get_width() // 2 + 1, cy - label.get_height() // 2 + 1))
                    screen.blit(label, (cx - label.get_width() // 2, cy - label.get_height() // 2))

        counts: dict[TerrainType, int] = {}
        for _, t in tile_map:
            counts[t.terrain] = counts.get(t.terrain, 0) + 1
        total = sum(counts.values())
        breakdown = "  ".join(
            f"{k.name}={counts.get(k, 0)*100//total}%"
            for k in (
                TerrainType.OCEAN, TerrainType.COAST,
                TerrainType.PLAINS, TerrainType.GRASSLAND, TerrainType.FOREST,
                TerrainType.DESERT, TerrainType.TUNDRA, TerrainType.SNOW,
                TerrainType.HILL, TerrainType.MOUNTAIN,
            )
            if counts.get(k, 0) > 0
        )

        land_components = find_components(tile_map, is_land)
        islands = len(land_components)
        biggest = max((len(c) for c in land_components), default=0)
        feature_count = len(tile_map.features) if tile_map.features is not None else 0

        edge_count = sum(1 for _ in iter_river_edges(tile_map))
        preset_name = RIVER_DENSITY_PRESETS[river_preset_idx][0]
        info = [
            f"seed={seed}  octaves={octaves}  persistence={persistence}  base_freq={base_frequency}  cam=({cam_x:.0f},{cam_y:.0f})",
            f"sea_level={sea_level:.2f} (PgUp/PgDn)   coast_depth={coast_depth} (;/')   view={view} (1-6)   rivers={'ON' if show_rivers else 'OFF'} (R)",
            f"post={'ON' if do_post else 'OFF'} (P)   island_min={island_min_size} (9/0)   lake_max={lake_max_size} (O/L)   islands={islands}   biggest={biggest}   features={feature_count}",
            f"river_density={preset_name} (K)   branches={'ON' if river_branches else 'OFF'} (B)   river_edges={edge_count}",
            breakdown,
            "Arrows=pan  Home=reset cam  Space=random  N/M=seed  +/-=octaves  [/]=persistence  ,/.=base_freq  ESC=quit",
        ]
        for i, txt in enumerate(info):
            screen.blit(font.render(txt, True, TEXT), (10, HEIGHT - 130 + i * 20))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
