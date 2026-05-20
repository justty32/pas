"""地形雕刻工具：筆刷、山脊、裂谷（方格版）。

對應 mapcore_py/editor/tools.py；主要差異：
- 使用 Chebyshev disk（正方形搜尋範圍）取代 hex_disk
- 使用 Euclidean 距離做 Gaussian 衰減（圓形筆刷感）
- 放射線計算直接用 (dx, dy)，不需 hex → 直角轉換
"""
from __future__ import annotations
import math
import random as _random

from .state import EditorState
from .grid_layout import tile_disk, tile_distance


def apply_brush(state: EditorState, x: int, y: int, delta: float) -> None:
    """高斯衰減筆刷：中心 delta 最強，邊緣趨近 0。"""
    for nx, ny in tile_disk(x, y, state.brush_size):
        if not state.in_bounds(nx, ny):
            continue
        dist   = tile_distance(x, y, nx, ny)
        weight = _gaussian(dist, state.brush_size)
        state.set_h(nx, ny, state.get_h(nx, ny) + delta * weight)


def apply_ridge_stamp(state: EditorState, x: int, y: int) -> None:
    """以滑鼠為中心的徑向山脊筆刷。"""
    _apply_radial_stamp(state, x, y, +1)


def apply_rift_stamp(state: EditorState, x: int, y: int) -> None:
    """以滑鼠為中心的徑向裂谷筆刷。"""
    _apply_radial_stamp(state, x, y, -1)


def toggle_water_source(state: EditorState, x: int, y: int) -> None:
    pt = (x, y)
    if pt in state.water_sources:
        state.water_sources.remove(pt)
    else:
        state.water_sources.append(pt)


# ── 內部工具 ──────────────────────────────────────────────────────────────────

def _tile_hash(x: int, y: int) -> float:
    """每格穩定的偽隨機值 0..1。"""
    v = (x * 1664525 + y * 1013904223) & 0xFFFFFFFF
    v ^= v >> 16
    v  = (v * 0x45d9f3b) & 0xFFFFFFFF
    v ^= v >> 16
    return (v & 0xFFFF) / 65535.0


def _apply_radial_stamp(state: EditorState, x: int, y: int, sign: float) -> None:
    radius   = max(1, state.brush_size)
    strength = state.brush_strength * 2.5
    chaos    = state.brush_chaos
    falloff  = state.brush_falloff
    invert   = state.brush_spokes_invert

    # Step 1：決定 spoke 數量
    if state.brush_spokes_rand:
        lo = min(state.brush_spokes_min, state.brush_spokes_max)
        hi = max(state.brush_spokes_min, state.brush_spokes_max)
        n_spokes = _random.randint(lo, hi)
    else:
        n_spokes = state.brush_spokes

    # Step 2：決定輪盤基底角度（wheel rotation）
    if state.brush_wheel_rand:
        lo = min(state.brush_wheel_min, state.brush_wheel_max)
        hi = max(state.brush_wheel_min, state.brush_wheel_max)
        wheel_rad = math.radians(_random.uniform(lo, hi))
    else:
        wheel_rad = math.radians(max(0.0, state.brush_wheel_angle))

    # Step 3：為每個 spoke 加上個別隨機偏移，建立 spoke 角度列表
    spoke_angles: list[float] = []
    if n_spokes > 0:
        jitter_rad = math.radians(state.brush_spoke_jitter)
        inc        = math.pi * 2.0 / n_spokes
        for i in range(n_spokes):
            base = i * inc + wheel_rad
            if jitter_rad > 0.0:
                base += _random.uniform(-jitter_rad, jitter_rad)
            spoke_angles.append(base)

    half_w = (math.pi * 2.0 / n_spokes * 0.35) if n_spokes > 0 else 0.0

    max_reach = radius * (1.0 + 0.6 * chaos)
    if spoke_angles:
        max_reach = max(max_reach, radius * 2.0)
    search_r = int(math.ceil(max_reach)) + 1

    for nx, ny in tile_disk(x, y, search_r):
        if not state.in_bounds(nx, ny):
            continue
        dist = tile_distance(x, y, nx, ny)

        if chaos > 0.0:
            noise_val  = _tile_hash(nx, ny)
            eff_radius = radius * (1.0 + chaos * (noise_val * 2.0 - 1.0) * 0.55)
            eff_radius = max(0.5, eff_radius)
        else:
            eff_radius = float(radius)
        t           = max(0.0, 1.0 - dist / eff_radius)
        base_weight = t ** falloff if t > 0.0 else 0.0

        spoke_w = 0.0
        if spoke_angles and dist > 0:
            # 方格座標已是直角，直接用 dx/dy
            tile_angle = math.atan2(float(ny - y), float(nx - x))
            min_diff   = min(
                abs(((tile_angle - sa) + math.pi) % (math.pi * 2.0) - math.pi)
                for sa in spoke_angles
            )
            if min_diff < half_w:
                spoke_cos = math.cos(min_diff / half_w * math.pi * 0.5)
                spoke_rad = max(0.0, 1.0 - dist / (radius * 2.0))
                spoke_w   = spoke_cos ** 2 * spoke_rad

        effective = base_weight - spoke_w if invert else max(base_weight, spoke_w)
        if abs(effective) < 1e-6:
            continue
        state.set_h(nx, ny, state.get_h(nx, ny) + sign * strength * effective)


def _gaussian(dist: float, radius: float) -> float:
    if radius <= 0:
        return 1.0
    sigma = radius / 2.2
    return math.exp(-0.5 * (dist / sigma) ** 2)
