"""氣候階段 (Phase 5)：rainfall(mm) / temperature(°C) / hilliness。

對齊 mapcore_py 的 hex 版 generation/climate.py（同樣參考 RimWorld 的
WorldGenStep_Terrain.cs）；本檔僅把 h.q/h.r 換成 c.x/c.y，
其餘 latitude curve / rainfall squash / hilliness 判定完全一致。

雨影 (_apply_rain_shadow) 是西→東逐列掃描，4 鄰居/6 鄰居在這個 phase 都不影響
（只用行內順序）。

Tile.hilliness 由本階段填入。
"""

from __future__ import annotations

import math
import random
from typing import Optional

from ..map import Hilliness, TileMap, TerrainType


# 對齊 RW WorldGenStep_Terrain.cs:55-61 AvgTempByLatitudeCurve
_AVG_TEMP_BY_LAT = (
    (0.0, 30.0),
    (0.1, 29.0),
    (0.5, 7.0),
    (1.0, -37.0),
)

# 對齊 RW WorldGenStep_Terrain.cs:139-147 AbsLatitudeCurve（緯度單位 °）
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


def latitude_normalized(y: int, total_h: int) -> float:
    """中央列 (y = (H−1)/2) 為赤道 (0)，邊緣為極 (1)。"""
    half = max((total_h - 1) / 2.0, 1e-9)
    return abs(y - (total_h - 1) / 2.0) / half


def base_temperature_celsius(lat_norm: float) -> float:
    """對齊 RW WorldGenStep_Terrain.cs:309-313 BaseTemperatureAtLatitude。"""
    return _piecewise_linear(_AVG_TEMP_BY_LAT, lat_norm)


def temperature_reduction_at_elevation(
    elev: float, start: float = 0.05, end: float = 1.0, max_reduction: float = 40.0
) -> float:
    """對齊 RW WorldGenStep_Terrain.cs:315-323。

    RW 原本 elev<250m → 0、elev 250→5000m 線性 0→40°C reduction；
    我們 elev ∈ [0,1] → 預設 start=0.05、end=1.0 → 0→40°C。
    """
    if elev < start:
        return 0.0
    if end <= start:
        return max_reduction
    t = min(1.0, (elev - start) / (end - start))
    return max_reduction * t


def compute_temperature_celsius(
    y: int,
    total_h: int,
    elev: float,
    noise_offset: float = 0.0,
) -> float:
    """單格的真實 °C 溫度。noise_offset 通常從 ±4°C 範圍的 noise 取值。"""
    lat_norm = latitude_normalized(y, total_h)
    base = base_temperature_celsius(lat_norm)
    reduction = temperature_reduction_at_elevation(elev)
    return base - reduction + noise_offset


def _rainfall_lat_mod(lat_norm: float) -> float:
    return _piecewise_linear(_RAINFALL_LAT_MOD, lat_norm * 90.0)


def _rainfall_squash(val: float) -> float:
    """對齊 RW WorldGenStep_Terrain.cs:157-172 Arbitrary processor。

    把低端值往上推：避免「整片乾旱」變成完全沒雨的死區。
    """
    if val < 0.0:
        val = 0.0
    if val < 0.12:
        val = (val + 0.12) / 2.0
        if val < 0.03:
            val = (val + 0.03) / 2.0
    return val


def compute_rainfall_mm(
    y: int,
    total_h: int,
    elev: float,
    base_noise: float,
    rainfall_factor: float = 4000.0,
    elev_dry_start: float = 0.1,
    elev_dry_end: float = 1.0,
) -> float:
    """對齊 RW WorldGenStep_Terrain.cs:133-183。

    base_noise: 0~1 的 Perlin-like value
    rainfall_factor: 預設 4000mm 對齊 RW 上限
    """
    lat_norm = latitude_normalized(y, total_h)
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
    """5 級判定。對齊 mapcore_py hex 版 climate.compute_hilliness。"""
    if elev <= sea_level:
        return Hilliness.FLAT
    if elev < hill_threshold:
        if rng is not None and rng.random() < 0.15:
            return Hilliness.SMALL_HILLS
        return Hilliness.FLAT
    if elev < mountain_threshold:
        if rng is not None and rng.random() < 0.5:
            return Hilliness.LARGE_HILLS
        return Hilliness.SMALL_HILLS
    if elev < impassable_threshold:
        return Hilliness.MOUNTAINOUS
    return Hilliness.IMPASSABLE


def _apply_rain_shadow(
    rainfall_mm: list[list[float]],
    heightmap: list[list[float]],
    hill_threshold: float,
    strength: float,
    shadow_decay: float = 0.88,
) -> None:
    """西→東掃線雨影效果（in-place 修改 rainfall_mm）。

    迎風面（山脈西側）：高程越高，地形雨加成越大（最多 +40%）。
    背風面（山脈東側）：shadow 累積值造成降雨衰減。
    """
    H = len(rainfall_mm)
    W = len(rainfall_mm[0])
    for y in range(H):
        shadow = 0.0
        for x in range(W):
            elev = heightmap[y][x]
            if elev > hill_threshold:
                barrier = (elev - hill_threshold) / max(1.0 - hill_threshold, 1e-9)
                rainfall_mm[y][x] = min(
                    4000.0, rainfall_mm[y][x] * (1.0 + 0.4 * barrier * strength)
                )
                shadow = min(shadow + barrier * strength, 2.5)
            elif shadow > 0.005:
                factor = max(0.2, 1.0 - shadow * 0.45 * strength)
                rainfall_mm[y][x] = max(0.0, rainfall_mm[y][x] * factor)
            shadow *= shadow_decay


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
    rain_shadow_strength: float = 0.0,
) -> tuple[list[list[float]], list[list[float]]]:
    """對 tile_map 算 temperature(°C) / rainfall(mm) / hilliness。

    回傳：(temperature_celsius, rainfall_mm) — shape == (H, W)
    in-place 寫入 Tile.hilliness。
    """
    W, H = tile_map.width, tile_map.height
    if len(heightmap) != H or any(len(row) != W for row in heightmap):
        raise ValueError("heightmap shape must match tile_map (height, width)")
    if len(rainfall_noise) != H or any(len(row) != W for row in rainfall_noise):
        raise ValueError("rainfall_noise shape must match tile_map (height, width)")

    rng = random.Random(seed)
    temperature: list[list[float]] = [[0.0] * W for _ in range(H)]
    rainfall_mm: list[list[float]] = [[0.0] * W for _ in range(H)]

    for c, tile in tile_map:
        x, y = c.x, c.y
        elev = heightmap[y][x]
        offset = (rng.random() * 2.0 - 1.0) * temperature_offset_amp
        temperature[y][x] = compute_temperature_celsius(y, H, elev, noise_offset=offset)
        rainfall_mm[y][x] = compute_rainfall_mm(y, H, elev, rainfall_noise[y][x])
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
    if rain_shadow_strength > 0.0:
        _apply_rain_shadow(
            rainfall_mm, heightmap,
            hill_threshold=hill_threshold,
            strength=rain_shadow_strength,
        )
    return temperature, rainfall_mm
