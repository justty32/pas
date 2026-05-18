"""一站式地圖生成管線。

把 Phase 1~6 串成 generate_world()，回傳 WorldGenResult（對應 C++ 側的 WorldData struct）。
WorldGenResult 包含所有中間產物，可直接傳入後續的 overlay phase。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..features import FeatureWorker, WorldFeatures, apply_features
from ..map import TerrainType, TileMap
from ..rivers import generate_rivers
from ..terrain import DEFAULT_REGISTRY, TerrainRegistry
from .biome import apply_biomes
from .classify import heightmap_to_tilemap
from .climate import apply_climate
from .depressions import fill_depressions
from .heightmap import generate_heightmap
from .postprocess import post_process as run_post_process

MOISTURE_SEED_OFFSET = 99991   # 任意質數，讓 height 與 moisture 的 noise 不相關
RIVERS_SEED_OFFSET   = 314159  # 河流取樣的獨立 seed 偏移
CLIMATE_SEED_OFFSET  = 271828  # 氣候階段 (hilliness 抖動 / 溫度 noise) 的獨立 seed
EXTRA_NOISE_BASE_OFFSET = 500003  # extra_noise 各 channel 的 seed 基底偏移

# 每種形狀建議的 heightmap noise 參數。
# 低 base_frequency → 低頻大塊（盤古/諸大陸）；高 base_frequency → 高頻破碎（群島）。
# heightmap_shape_auto_freq=True（預設）時自動套用；False 時完全由呼叫端的 octaves/base_frequency 決定。
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
    """generate_world() 的完整輸出；對應 C++ 側的 WorldData struct。

    設計原則：
    - 所有中間產物集中在此，overlay phase 只需接收這一個物件
    - 新增欄位不破壞已有呼叫端（dataclass 欄位名稱存取）
    - None 代表對應 phase 未執行（climate=False 時 temperature/rainfall 為 None）
    - extra_noise 是命名 noise 圖集合，供 overlay 條件使用
    """
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
    # noise params (套用至 heightmap 與 moisture)
    octaves: int = 5,
    persistence: float = 0.5,
    base_frequency: int = 4,
    # heightmap 形狀與山脊
    heightmap_ridge_weight: float = 0.0,
    heightmap_ridge_mode: str = "plates",
    heightmap_ridge_direction: float = 0.0,
    heightmap_ridge_direction_variation: float = 90.0,
    heightmap_num_plates: int = 12,
    heightmap_plate_boundary_width: float = 0.08,
    heightmap_shape: Optional[str] = None,
    heightmap_shape_strength: float = 0.85,
    heightmap_shape_params: Optional[dict] = None,
    heightmap_shape_auto_freq: bool = True,
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
    lake_fill: int = TerrainType.PLAINS,
    # 窪地填充 (Phase 4.5)：Priority-Flood 產生內陸湖泊
    lake_depressions: bool = False,
    # climate (Phase 5)：對齊 WorldGenStep_Terrain 的 °C/mm/hilliness
    climate: bool = True,
    climate_temperature_offset_amp: float = 4.0,
    climate_impassable_threshold: float = 0.95,
    climate_rain_shadow_strength: float = 0.0,
    # rivers (RimWorld 風，對齊 WorldGenStep_Rivers.cs)
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
    # features (Phase 6)：命名大區域，對齊 WorldGenStep_Features
    features: bool = True,
    feature_workers: Optional[list[FeatureWorker]] = None,
    # registry：用哪個 TerrainRegistry；None 代表使用 DEFAULT_REGISTRY
    registry: Optional[TerrainRegistry] = None,
    # extra_noise_specs：額外 noise 圖的 (名稱, seed_offset) 清單；供 overlay phase 使用
    extra_noise_specs: Optional[list[tuple[str, int]]] = None,
) -> WorldGenResult:
    """跑完 Phase 1~6，回傳 WorldGenResult。

    WorldGenResult 包含 tile_map、所有中間產物 (heightmap/moisture/climate grids)、
    extra_noise 以及 registry，可直接傳入 apply_terrain_patches()（overlay phase）。
    """
    if registry is None:
        registry = DEFAULT_REGISTRY

    # 形狀自動頻率：依 shape 套用建議的 octaves / base_frequency（可被呼叫端覆蓋）
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

    # Phase 4.5：窪地填充 → 標記 LAKE 格子
    # 在 post_process 之後執行，確保噪點小湖已被清理，這裡建的是真實地形湖泊
    if lake_depressions:
        from ..map import TerrainType as _TT
        lake_tile_set, filled_hm = fill_depressions(heightmap, sea_level=sea_level)
        for r, q in lake_tile_set:
            tile = tile_map._rows[r][q]
            tile.terrain = _TT.LAKE
            # water_depth 代表湖水深度（填充水面 − 湖底高程）
            tile.water_depth = filled_hm[r][q] - heightmap[r][q]

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
            min_sea_size=river_min_sea_size,
            min_seed_spacing=river_min_seed_spacing,
        )

    if features:
        tile_map.features = apply_features(tile_map, workers=feature_workers)

    # 額外 noise 圖（供 overlay phase 使用）
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
