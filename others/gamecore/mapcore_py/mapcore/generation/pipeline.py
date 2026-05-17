"""一站式地圖生成管線。

把 Phase 1 (heightmap)、Phase 2 (海平面切割)、Phase 3 (生物群系) 串成一個函式。
"""

from __future__ import annotations

from typing import Optional

from ..map import TerrainType, TileMap
from ..rivers import generate_rivers
from .biome import apply_biomes
from .classify import heightmap_to_tilemap
from .heightmap import generate_heightmap
from .postprocess import post_process as run_post_process

MOISTURE_SEED_OFFSET = 99991  # 任意質數，讓 height 與 moisture 的 noise 不相關
RIVERS_SEED_OFFSET = 314159   # 河流取樣的獨立 seed 偏移


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
    # rivers
    rivers: bool = True,
    river_source_threshold: float = 0.6,
    river_source_density: float = 0.15,
    river_min_length: int = 2,
) -> tuple[TileMap, list[list[float]], list[list[float]]]:
    """跑完 Phase 1 → 2 → 3 → 4 → rivers，回傳 (tile_map, heightmap, moisture)。

    post_process=False 時跳過 Phase 4；rivers=False 時跳過河流。
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
    if rivers:
        river_seed = None if seed is None else seed + RIVERS_SEED_OFFSET
        generate_rivers(
            tile_map, heightmap,
            seed=river_seed,
            source_threshold=river_source_threshold,
            source_density=river_source_density,
            min_river_length=river_min_length,
        )
    return tile_map, heightmap, moisture
