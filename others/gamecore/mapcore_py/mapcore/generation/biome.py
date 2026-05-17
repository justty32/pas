"""生物群系分類 (Phase 3)。

把 TileMap 上的陸地（非 OCEAN/COAST）細分為：
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

對齊 Whittaker biome chart 的精神（簡化版）；參考
analysis/wesnoth/details/tech_encyclopedia_vol3_terrain_engine.md 的地形分類。
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
    """In-place 細分 tile_map 上的陸地。OCEAN/COAST 不會被改動。"""
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

    # 緯度分母：把 r=0 與 r=H-1 算作緯度 1，中央列算 0。
    half = max((h_map - 1) / 2.0, 1e-9)
    span = max(1.0 - sea_level, 1e-9)

    for h, tile in tile_map:
        if tile.terrain in (TerrainType.OCEAN, TerrainType.COAST):
            continue
        elev = heightmap[h.r][h.q]

        # 高程主導：高 elev 直接是 MOUNTAIN/HILL，不需要看溫度/濕度
        # （Whittaker 圖在現實裡也是這樣，赤道的高山一樣可以是冰原）
        if elev > mountain_threshold:
            tile.terrain = TerrainType.MOUNTAIN
            continue
        if elev > hill_threshold:
            tile.terrain = TerrainType.HILL
            continue

        # 溫度（normalized 0~1）= 1 − latitude − 高程拉低值；不是真實 °C
        # 真實 °C 在 climate.py 算，但 biome 故意維持簡化版本以保持自包含
        latitude = abs(h.r - (h_map - 1) / 2.0) / half
        elev_above_sea = max(0.0, elev - sea_level) / span
        temp = 1.0 - latitude - elevation_temp_factor * elev_above_sea
        if temp < 0.0:
            temp = 0.0
        elif temp > 1.0:
            temp = 1.0
        moist = moisture[h.r][h.q]

        # 寒區優先（無論濕度都是 SNOW/TUNDRA），熱區跟溫帶才看濕度三分
        if temp < snow_temp:
            tile.terrain = TerrainType.SNOW
        elif temp < tundra_temp:
            tile.terrain = TerrainType.TUNDRA
        elif temp >= hot_temp:
            # 熱帶：濕度從乾到濕 → DESERT / PLAINS / FOREST（熱帶雨林）
            if moist < dry_moisture:
                tile.terrain = TerrainType.DESERT
            elif moist > wet_moisture:
                tile.terrain = TerrainType.FOREST
            else:
                tile.terrain = TerrainType.PLAINS
        else:
            # 溫帶：濕度從乾到濕 → PLAINS / GRASSLAND / FOREST
            # 跟熱帶差別在「乾」是 PLAINS（半乾草原）而非 DESERT
            if moist < dry_moisture:
                tile.terrain = TerrainType.PLAINS
            elif moist > wet_moisture:
                tile.terrain = TerrainType.FOREST
            else:
                tile.terrain = TerrainType.GRASSLAND
