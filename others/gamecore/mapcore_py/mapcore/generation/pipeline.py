"""一站式地圖生成管線。

把 Phase 1 (heightmap)、Phase 2 (海平面切割)、Phase 3 (生物群系) 串成一個函式。
"""

from __future__ import annotations

from typing import Optional

from ..features import FeatureWorker, WorldFeatures, apply_features
from ..map import TerrainType, TileMap
from ..rivers import generate_rivers
from .biome import apply_biomes
from .classify import heightmap_to_tilemap
from .climate import apply_climate
from .heightmap import generate_heightmap
from .postprocess import post_process as run_post_process

MOISTURE_SEED_OFFSET = 99991  # 任意質數，讓 height 與 moisture 的 noise 不相關
RIVERS_SEED_OFFSET = 314159   # 河流取樣的獨立 seed 偏移
CLIMATE_SEED_OFFSET = 271828  # 氣候階段 (hilliness 抖動 / 溫度 noise) 的獨立 seed


def generate_world(
    width: int,
    height: int,
    seed: Optional[int] = None,
    sea_level: float = 0.4,
    coast_depth: int = 1,
    # noise params (套用至 heightmap 與 moisture)
    octaves: int = 5,
    persistence: float = 0.5,
    base_frequency: int = 4,
    # biome params (透傳)
    mountain_threshold: float = 0.85,
    hill_threshold: float = 0.70,
    snow_temp: float = 0.15,
    tundra_temp: float = 0.30,
    hot_temp: float = 0.65,
    dry_moisture: float = 0.30,
    wet_moisture: float = 0.65,
    elevation_temp_factor: float = 0.5,
    # post-process params (Phase 4)
    post_process: bool = True,
    island_min_size: int = 3,
    lake_max_size: int = 4,
    lake_fill: TerrainType = TerrainType.PLAINS,
    # climate (Phase 5)：對齊 WorldGenStep_Terrain 的 °C/mm/hilliness
    climate: bool = True,
    climate_temperature_offset_amp: float = 4.0,
    climate_impassable_threshold: float = 0.95,
    # rivers (RimWorld 風，對齊 WorldGenStep_Rivers.cs)
    # 預設門檻對齊 RW Creek tier (spawnFlowThreshold=600)，避免大地圖密度過高
    rivers: bool = True,
    river_rainfall_scale: float = 1.0,   # climate 給的已是 mm，預設不再 scale
    river_spawn_flow_threshold: float = 600.0,
    river_degrade_threshold: float = 200.0,
    river_branch_flow_threshold: float = 400.0,
    river_branch_chance: float = 0.3,
    river_flow_strength_scale: float = 0.05,
    river_evaporation_scale: float = 1.0,
    # features (Phase 6)：命名大區域，對齊 WorldGenStep_Features
    features: bool = True,
    feature_workers: Optional[list[FeatureWorker]] = None,
) -> tuple[TileMap, list[list[float]], list[list[float]]]:
    """跑完 Phase 1 → 2 → 3 → 4 → rivers，回傳 (tile_map, heightmap, moisture)。

    post_process=False 時跳過 Phase 4；rivers=False 時跳過河流。
    河流生成風格對齊 RimWorld WorldGenStep_Rivers：moisture 當作 rainfall 餵入。
    """
    heightmap = generate_heightmap(
        width, height,
        seed=seed,
        octaves=octaves,
        persistence=persistence,
        base_frequency=base_frequency,
    )
    moisture_seed = None if seed is None else seed + MOISTURE_SEED_OFFSET
    moisture = generate_heightmap(
        width, height,
        seed=moisture_seed,
        octaves=octaves,
        persistence=persistence,
        base_frequency=base_frequency,
    )
    tile_map = heightmap_to_tilemap(heightmap, sea_level=sea_level, coast_depth=coast_depth)
    apply_biomes(
        tile_map, heightmap, moisture,
        sea_level=sea_level,
        mountain_threshold=mountain_threshold,
        hill_threshold=hill_threshold,
        snow_temp=snow_temp,
        tundra_temp=tundra_temp,
        hot_temp=hot_temp,
        dry_moisture=dry_moisture,
        wet_moisture=wet_moisture,
        elevation_temp_factor=elevation_temp_factor,
    )
    if post_process:
        run_post_process(
            tile_map,
            island_min_size=island_min_size,
            lake_max_size=lake_max_size,
            coast_depth=coast_depth,
            lake_fill=lake_fill,
        )

    temperature_celsius: list[list[float]] | None = None
    rainfall_mm: list[list[float]] | None = None
    if climate:
        climate_seed = None if seed is None else seed + CLIMATE_SEED_OFFSET
        temperature_celsius, rainfall_mm = apply_climate(
            tile_map, heightmap, moisture,
            seed=climate_seed,
            sea_level=sea_level,
            temperature_offset_amp=climate_temperature_offset_amp,
            hill_threshold=hill_threshold,
            mountain_threshold=mountain_threshold,
            impassable_threshold=climate_impassable_threshold,
        )

    if rivers:
        river_seed = None if seed is None else seed + RIVERS_SEED_OFFSET
        # 有 climate 時餵真實 mm rainfall + °C temperature；沒有 climate 時退回 moisture(0~1) × scale
        if rainfall_mm is not None:
            rainfall_for_rivers = rainfall_mm
            rainfall_scale_for_rivers = river_rainfall_scale  # 已是 mm，預設 1.0
        else:
            rainfall_for_rivers = moisture
            rainfall_scale_for_rivers = max(river_rainfall_scale, 1000.0)
        generate_rivers(
            tile_map,
            heightmap,
            rainfall_for_rivers,
            temperature=temperature_celsius,
            seed=river_seed,
            rainfall_scale=rainfall_scale_for_rivers,
            spawn_flow_threshold=river_spawn_flow_threshold,
            degrade_threshold=river_degrade_threshold,
            branch_flow_threshold=river_branch_flow_threshold,
            branch_chance=river_branch_chance,
            flow_strength_scale=river_flow_strength_scale,
            evaporation_scale=river_evaporation_scale,
        )

    if features:
        tile_map.features = apply_features(tile_map, workers=feature_workers)

    return tile_map, heightmap, moisture
