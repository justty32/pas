"""氣候階段 (Phase 2.5)：rainfall(mm) / temperature(°C) / hilliness。

對齊 projects/rimworld/RimWorld.Planet/WorldGenStep_Terrain.cs:55-198 的設計：

- temperature = AvgTempByLatitudeCurve(lat) − TemperatureReductionAtElevation(elev) + noise_offset
- rainfall    = base_noise × AbsLatitudeCurve(lat) × (1 − elevation_factor) → squash → Power(1.5) → ×4000
- hilliness   = 由 mountain_lines_noise + hills_patches 在 5 級之間判定

跟現有的 biome.py（用 normalized [0, 1] temperature）共存：
biome.py 內部仍用自己的 normalized 算法；climate 算的真實 °C / mm 主要給河流生成等
真正需要物理量的階段用。Tile.hilliness 由本階段填入。
"""

from __future__ import annotations

import math
import random
from typing import Optional

from ..map import Hilliness, TileMap, TerrainType


# 對齊 WorldGenStep_Terrain.cs:55-61 AvgTempByLatitudeCurve
# (lat_normalized, base_temp_celsius)
_AVG_TEMP_BY_LAT = (
    (0.0, 30.0),
    (0.1, 29.0),
    (0.5, 7.0),
    (1.0, -37.0),
)

# 對齊 WorldGenStep_Terrain.cs:139-147 AbsLatitudeCurve（緯度單位 °）
_RAINFALL_LAT_MOD = (
    (0.0,  1.12),
    (25.0, 0.94),
    (45.0, 0.70),
    (70.0, 0.30),
    (80.0, 0.05),
    (90.0, 0.05),
)


def _piecewise_linear(points: tuple[tuple[float, float], ...], x: float) -> float:
    if x <= points[0][0]:
        return points[0][1]
    if x >= points[-1][0]:
        return points[-1][1]
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if x1 <= x <= x2:
            if x2 == x1:
                return y2
            t = (x - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    return points[-1][1]


def latitude_normalized(r: int, total_h: int) -> float:
    """中央列 (r = (H−1)/2) 為赤道 (0)，邊緣為極 (1)。"""
    half = max((total_h - 1) / 2.0, 1e-9)
    return abs(r - (total_h - 1) / 2.0) / half


def base_temperature_celsius(lat_norm: float) -> float:
    """對齊 WorldGenStep_Terrain.cs:309-313 BaseTemperatureAtLatitude。"""
    return _piecewise_linear(_AVG_TEMP_BY_LAT, lat_norm)


def temperature_reduction_at_elevation(elev: float, start: float = 0.05, end: float = 1.0, max_reduction: float = 40.0) -> float:
    """對齊 WorldGenStep_Terrain.cs:315-323 TemperatureReductionAtElevation。

    RW 原本：elev < 250m → 0；elev 250→5000m 線性 → 0→40°C reduction。
    我們 elev ∈ [0, 1]：預設 start=0.05 (≈250m/5000m * 1.0) → end=1.0 → 0→40°C。
    """
    if elev < start:
        return 0.0
    if end <= start:
        return max_reduction
    t = min(1.0, (elev - start) / (end - start))
    return max_reduction * t


def compute_temperature_celsius(
    r: int,
    total_h: int,
    elev: float,
    noise_offset: float = 0.0,
) -> float:
    """單格的真實 °C 溫度。noise_offset 通常從 ±4°C 範圍的 noise 取值。"""
    lat_norm = latitude_normalized(r, total_h)
    base = base_temperature_celsius(lat_norm)
    reduction = temperature_reduction_at_elevation(elev)
    return base - reduction + noise_offset


def _rainfall_lat_mod(lat_norm: float) -> float:
    return _piecewise_linear(_RAINFALL_LAT_MOD, lat_norm * 90.0)


def _rainfall_squash(val: float) -> float:
    """對齊 WorldGenStep_Terrain.cs:157-172 Arbitrary processor。

    把低端值往上推：避免「整片乾旱」變成完全沒雨的死區，給乾燥地形仍保留一點 baseline 雨量
    （沙漠也是有少量降雨的）。具體：< 0.12 區段往 0.12 收斂、< 0.03 再往 0.03 收斂。
    """
    if val < 0.0:
        val = 0.0
    if val < 0.12:
        val = (val + 0.12) / 2.0
        if val < 0.03:
            val = (val + 0.03) / 2.0
    return val


def compute_rainfall_mm(
    r: int,
    total_h: int,
    elev: float,
    base_noise: float,
    rainfall_factor: float = 4000.0,
    elev_dry_start: float = 0.1,
    elev_dry_end: float = 1.0,
) -> float:
    """對齊 WorldGenStep_Terrain.cs:133-183 的 noiseRainfall 構造。

    base_noise: 0~1 的 Perlin-like value
    rainfall_factor: 預設 4000mm 對齊 RW 上限
    elev_dry_*: 高程降水減少的起終點（normalized elev）
    """
    lat_norm = latitude_normalized(r, total_h)
    val = base_noise * _rainfall_lat_mod(lat_norm)
    if elev > elev_dry_start and elev_dry_end > elev_dry_start:
        t = min(1.0, (elev - elev_dry_start) / (elev_dry_end - elev_dry_start))
        val *= max(0.0, 1.0 - t)
    val = _rainfall_squash(val)
    val = max(0.0, val) ** 1.5
    val = min(val, 0.999)
    return val * rainfall_factor


def compute_hilliness(
    elev: float,
    sea_level: float = 0.4,
    mountain_threshold: float = 0.85,
    hill_threshold: float = 0.70,
    impassable_threshold: float = 0.95,
    rng: Optional[random.Random] = None,
) -> Hilliness:
    """5 級判定。對齊精神而非實作（RW 用 RidgedMultifractal mountain lines，
    我們先用 elevation 為主 + 隨機抖動）。

    呼叫前提：tile 是陸地（apply_climate 已經先判過水→FLAT，呼叫到這裡的都是陸地 terrain）。
    elev <= sea_level 的情形包含「postprocess 把小湖填回 PLAINS 後遺下的低海拔陸地」。

    elev <= sea_level                    → FLAT（陸地化的低地）
    elev < hill_threshold                → FLAT (有機率 SMALL_HILLS)
    elev < mountain_threshold            → SMALL_HILLS / LARGE_HILLS
    elev < impassable_threshold          → MOUNTAINOUS
    else                                 → IMPASSABLE
    """
    if elev <= sea_level:
        return Hilliness.FLAT
    if elev < hill_threshold:
        # 平地為主，少量小丘
        if rng is not None and rng.random() < 0.15:
            return Hilliness.SMALL_HILLS
        return Hilliness.FLAT
    if elev < mountain_threshold:
        # 丘陵帶
        if rng is not None and rng.random() < 0.5:
            return Hilliness.LARGE_HILLS
        return Hilliness.SMALL_HILLS
    if elev < impassable_threshold:
        return Hilliness.MOUNTAINOUS
    return Hilliness.IMPASSABLE


def apply_climate(
    tile_map: TileMap,
    heightmap: list[list[float]],
    rainfall_noise: list[list[float]],
    seed: Optional[int] = None,
    sea_level: float = 0.4,
    temperature_offset_amp: float = 4.0,
    hill_threshold: float = 0.70,
    mountain_threshold: float = 0.85,
    impassable_threshold: float = 0.95,
) -> tuple[list[list[float]], list[list[float]]]:
    """對 tile_map 算 temperature(°C) / rainfall(mm) / hilliness。

    回傳：(temperature_celsius, rainfall_mm) — shape == tile_map (H, W)
    in-place 寫入 Tile.hilliness。

    rainfall_noise：0~1 的 base noise（建議直接傳 pipeline 的 moisture）。
    """
    W, H = tile_map.width, tile_map.height
    if len(heightmap) != H or any(len(row) != W for row in heightmap):
        raise ValueError("heightmap shape must match tile_map (height, width)")
    if len(rainfall_noise) != H or any(len(row) != W for row in rainfall_noise):
        raise ValueError("rainfall_noise shape must match tile_map (height, width)")

    rng = random.Random(seed)
    temperature: list[list[float]] = [[0.0] * W for _ in range(H)]
    rainfall_mm: list[list[float]] = [[0.0] * W for _ in range(H)]

    for h, tile in tile_map:
        q, r = h.q, h.r
        elev = heightmap[r][q]
        # ±amp°C noise offset — 用 rng 而非額外 noise grid，省一張 grid
        offset = (rng.random() * 2.0 - 1.0) * temperature_offset_amp
        temperature[r][q] = compute_temperature_celsius(r, H, elev, noise_offset=offset)
        rainfall_mm[r][q] = compute_rainfall_mm(r, H, elev, rainfall_noise[r][q])
        if tile.terrain in (TerrainType.OCEAN, TerrainType.COAST):
            tile.hilliness = Hilliness.FLAT
        else:
            tile.hilliness = compute_hilliness(
                elev,
                sea_level=sea_level,
                hill_threshold=hill_threshold,
                mountain_threshold=mountain_threshold,
                impassable_threshold=impassable_threshold,
                rng=rng,
            )
    return temperature, rainfall_mm
