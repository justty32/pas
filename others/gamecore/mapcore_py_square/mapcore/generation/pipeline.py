"""一站式地圖生成管線（方格 4 鄰居版）。

對齊 mapcore_py 的 hex 版 generation/pipeline.py：把 Phase 1~7 串成 generate_world()，
回傳 WorldGenResult。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..features import FeatureWorker, apply_features
from ..map import TerrainType, TileMap
from ..rivers import generate_rivers
from ..terrain import DEFAULT_REGISTRY, TerrainRegistry
from .biome import apply_biomes
from .classify import heightmap_to_tilemap
from .climate import apply_climate
from .depressions import fill_depressions
from .heightmap import generate_heightmap
from .postprocess import post_process as run_post_process

MOISTURE_SEED_OFFSET = 99991
RIVERS_SEED_OFFSET   = 314159
CLIMATE_SEED_OFFSET  = 271828
EXTRA_NOISE_BASE_OFFSET = 500003

SHAPE_NOISE_DEFAULTS: dict[str, dict] = {
    "pangaea":                {"octaves": 4, "base_frequency": 3},
    "continents":             {"octaves": 4, "base_frequency": 4},
    "ring_sea":               {"octaves": 4, "base_frequency": 4},
    "island":                 {"octaves": 4, "base_frequency": 4},
    "archipelago":            {"octaves": 5, "base_frequency": 5},
    "shattered_archipelago":  {"octaves": 6, "base_frequency": 7},
}


@dataclass
class WorldGenResult:
    """generate_world() 的完整輸出。對應 C++ 側未來的 WorldData struct。"""
    tile_map: TileMap
    heightmap: list[list[float]]
    moisture: list[list[float]]
    temperature_celsius: Optional[list[list[float]]]
    rainfall_mm: Optional[list[list[float]]]
    extra_noise: dict[str, list[list[float]]]
    registry: TerrainRegistry
    seed: Optional[int]


def generate_world(
    width: int,
    height: int,
    seed: Optional[int] = None,
    sea_level: float = 0.4,
    coast_depth: int = 1,
    octaves: int = 5,
    persistence: float = 0.5,
    base_frequency: int = 4,
    heightmap_ridge_weight: float = 0.0,
    heightmap_ridge_mode: str = "plates",
    heightmap_ridge_direction: float = 0.0,
    heightmap_ridge_direction_variation: float = 90.0,
    heightmap_ridge_power: float = 2.0,
    heightmap_ridge_multifractal_gain: float = 2.0,
    heightmap_num_plates: int = 20,
    heightmap_plate_boundary_width: float = 0.05,
    heightmap_shape: Optional[str] = None,
    heightmap_shape_strength: float = 0.85,
    heightmap_shape_params: Optional[dict] = None,
    heightmap_shape_auto_freq: bool = True,
    mountain_threshold: float = 0.85,
    hill_threshold: float = 0.70,
    snow_temp: float = 0.15,
    tundra_temp: float = 0.30,
    hot_temp: float = 0.65,
    dry_moisture: float = 0.30,
    wet_moisture: float = 0.65,
    elevation_temp_factor: float = 0.5,
    post_process: bool = True,
    island_min_size: int = 3,
    lake_max_size: int = 4,
    lake_fill: int = TerrainType.PLAINS,
    lake_depressions: bool = False,
    climate: bool = True,
    climate_temperature_offset_amp: float = 4.0,
    climate_impassable_threshold: float = 0.95,
    climate_rain_shadow_strength: float = 0.0,
    rivers: bool = True,
    river_rainfall_scale: float = 1.0,
    river_spawn_flow_threshold: float = 600.0,
    river_degrade_threshold: float = 200.0,
    river_branch_flow_threshold: float = 400.0,
    river_branch_chance: float = 0.3,
    river_flow_strength_scale: float = 0.05,
    river_evaporation_scale: float = 1.0,
    river_min_sea_size: int = 5,
    river_min_seed_spacing: int = 1,
    features: bool = True,
    feature_workers: Optional[list[FeatureWorker]] = None,
    registry: Optional[TerrainRegistry] = None,
    extra_noise_specs: Optional[list[tuple[str, int]]] = None,
) -> WorldGenResult:
    """跑完 Phase 1~7，回傳 WorldGenResult。"""
    if registry is None:
        registry = DEFAULT_REGISTRY

    _oct   = octaves
    _bfreq = base_frequency
    if heightmap_shape is not None and heightmap_shape_auto_freq:
        _shape_noise = SHAPE_NOISE_DEFAULTS.get(heightmap_shape, {})
        _oct   = _shape_noise.get("octaves",        octaves)
        _bfreq = _shape_noise.get("base_frequency", base_frequency)

    heightmap = generate_heightmap(
        width, height,
        seed=seed,
        octaves=_oct,
        persistence=persistence,
        base_frequency=_bfreq,
        ridge_weight=heightmap_ridge_weight,
        ridge_mode=heightmap_ridge_mode,
        ridge_direction=heightmap_ridge_direction,
        ridge_direction_variation=heightmap_ridge_direction_variation,
        ridge_power=heightmap_ridge_power,
        ridge_multifractal_gain=heightmap_ridge_multifractal_gain,
        num_plates=heightmap_num_plates,
        plate_boundary_width=heightmap_plate_boundary_width,
        shape=heightmap_shape,
        shape_strength=heightmap_shape_strength,
        shape_params=heightmap_shape_params,
        shape_sea_level=sea_level,
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

    if lake_depressions:
        lake_tile_set, filled_hm = fill_depressions(heightmap, sea_level=sea_level)
        for y, x in lake_tile_set:
            tile = tile_map._rows[y][x]
            tile.terrain = TerrainType.LAKE
            tile.water_depth = filled_hm[y][x] - heightmap[y][x]

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
            rain_shadow_strength=climate_rain_shadow_strength,
        )

    if rivers:
        river_seed = None if seed is None else seed + RIVERS_SEED_OFFSET
        if rainfall_mm is not None:
            rainfall_for_rivers = rainfall_mm
            rainfall_scale_for_rivers = river_rainfall_scale
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
            min_sea_size=river_min_sea_size,
            min_seed_spacing=river_min_seed_spacing,
        )

    if features:
        tile_map.features = apply_features(tile_map, workers=feature_workers)

    extra_noise: dict[str, list[list[float]]] = {}
    if extra_noise_specs:
        for name, offset in extra_noise_specs:
            noise_seed = None if seed is None else seed + EXTRA_NOISE_BASE_OFFSET + offset
            extra_noise[name] = generate_heightmap(
                width, height,
                seed=noise_seed,
                octaves=octaves,
                persistence=persistence,
                base_frequency=base_frequency,
            )

    return WorldGenResult(
        tile_map=tile_map,
        heightmap=heightmap,
        moisture=moisture,
        temperature_celsius=temperature_celsius,
        rainfall_mm=rainfall_mm,
        extra_noise=extra_noise,
        registry=registry,
        seed=seed,
    )
