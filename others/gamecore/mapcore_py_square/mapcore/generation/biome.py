"""生物群系分類 (Phase 3)。

把 TileMap 上的陸地（非 OCEAN/COAST/LAKE）細分為：
    MOUNTAIN / HILL / SNOW / TUNDRA / DESERT / FOREST / GRASSLAND / PLAINS

決策樹：
1. elev > mountain_threshold → MOUNTAIN
2. elev > hill_threshold     → HILL
3. 否則由 (溫度, 濕度) 決定：
       溫度極低 → SNOW
       溫度低   → TUNDRA
       溫度高   → DESERT / PLAINS / FOREST（依濕度）
       溫帶     → PLAINS / GRASSLAND / FOREST（依濕度）

溫度 = 1 − latitude − elevation_temp_factor × (elev 高於海平面比例)
        clamp 到 [0, 1]
latitude 0 = 赤道（地圖中央列），1 = 兩極（最上 / 最下列）。

對齊 mapcore_py 的 hex 版 generation/biome.py；本檔僅把 h.r/h.q 換成 h.y/h.x，
其餘決策樹完全一致。
"""

from __future__ import annotations

from ..map import TerrainType, TileMap


def apply_biomes(
    tile_map: TileMap,
    heightmap: list[list[float]],
    moisture: list[list[float]],
    sea_level: float = 0.4,
    mountain_threshold: float = 0.85,
    hill_threshold: float = 0.70,
    snow_temp: float = 0.15,
    tundra_temp: float = 0.30,
    hot_temp: float = 0.65,
    dry_moisture: float = 0.30,
    wet_moisture: float = 0.65,
    elevation_temp_factor: float = 0.5,
) -> None:
    """In-place 細分 tile_map 上的陸地。OCEAN/COAST/LAKE 不會被改動。"""
    h_map = tile_map.height
    w_map = tile_map.width
    if len(heightmap) != h_map or len(moisture) != h_map:
        raise ValueError("heightmap and moisture must match tile_map height")
    for row in heightmap:
        if len(row) != w_map:
            raise ValueError("heightmap row width must match tile_map width")
    for row in moisture:
        if len(row) != w_map:
            raise ValueError("moisture row width must match tile_map width")

    half = max((h_map - 1) / 2.0, 1e-9)
    span = max(1.0 - sea_level, 1e-9)

    for c, tile in tile_map:
        if tile.terrain in (TerrainType.OCEAN, TerrainType.COAST, TerrainType.LAKE):
            continue
        elev = heightmap[c.y][c.x]

        # 高程主導：高 elev 直接是 MOUNTAIN/HILL，不需要看溫度/濕度
        if elev > mountain_threshold:
            tile.terrain = TerrainType.MOUNTAIN
            continue
        if elev > hill_threshold:
            tile.terrain = TerrainType.HILL
            continue

        # 溫度（normalized 0~1）= 1 − latitude − 高程拉低值；不是真實 °C
        # 真實 °C 在 climate.py 算，biome 保留簡化版本以保持自包含
        latitude = abs(c.y - (h_map - 1) / 2.0) / half
        elev_above_sea = max(0.0, elev - sea_level) / span
        temp = 1.0 - latitude - elevation_temp_factor * elev_above_sea
        if temp < 0.0:
            temp = 0.0
        elif temp > 1.0:
            temp = 1.0
        moist = moisture[c.y][c.x]

        if temp < snow_temp:
            tile.terrain = TerrainType.SNOW
        elif temp < tundra_temp:
            tile.terrain = TerrainType.TUNDRA
        elif temp >= hot_temp:
            if moist < dry_moisture:
                tile.terrain = TerrainType.DESERT
            elif moist > wet_moisture:
                tile.terrain = TerrainType.FOREST
            else:
                tile.terrain = TerrainType.PLAINS
        else:
            if moist < dry_moisture:
                tile.terrain = TerrainType.PLAINS
            elif moist > wet_moisture:
                tile.terrain = TerrainType.FOREST
            else:
                tile.terrain = TerrainType.GRASSLAND
