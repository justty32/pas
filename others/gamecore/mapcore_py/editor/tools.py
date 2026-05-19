"""地形雕刻工具：筆刷、山脊、裂谷。"""
from __future__ import annotations
import math
import random as _random
from .state import EditorState
from .hex_layout import hex_disk, hex_distance


def apply_brush(state: EditorState, q: int, r: int, delta: float) -> None:
    """高斯衰減筆刷：中心 delta 最強，邊緣趨近 0。"""
    for nq, nr in hex_disk(q, r, state.brush_size):
        if not state.in_bounds(nq, nr):
            continue
        dist = hex_distance(q, r, nq, nr)
        weight = _gaussian(dist, state.brush_size)
        state.set_h(nq, nr, state.get_h(nq, nr) + delta * weight)


# ── Radial stamp brush (editor interactive) ──────────────────────────────────

def apply_ridge_stamp(state: EditorState, q: int, r: int) -> None:
    """以滑鼠為中心的徑向山脊筆刷（非線性衰減，可加雜亂度與放射線）。"""
    _apply_radial_stamp(state, q, r, +1)


def apply_rift_stamp(state: EditorState, q: int, r: int) -> None:
    """以滑鼠為中心的徑向裂谷筆刷（非線性衰減，可加雜亂度與放射線）。"""
    _apply_radial_stamp(state, q, r, -1)


def _tile_hash(q: int, r: int) -> float:
    """每格穩定的偽隨機值 0..1，不依賴 random 模組。"""
    v = (q * 1664525 + r * 1013904223) & 0xFFFFFFFF
    v ^= v >> 16
    v  = (v * 0x45d9f3b) & 0xFFFFFFFF
    v ^= v >> 16
    return (v & 0xFFFF) / 65535.0


def _apply_radial_stamp(state: EditorState, q: int, r: int, sign: float) -> None:
    radius   = max(1, state.brush_size)
    strength = state.brush_strength * 2.5
    chaos    = state.brush_chaos
    falloff  = state.brush_falloff
    invert   = state.brush_spokes_invert

    # ── 決定本次 stamp 的放射線數量與旋轉偏移 ────────────────────
    if state.brush_spokes_rand:
        lo = min(state.brush_spokes_min, state.brush_spokes_max)
        hi = max(state.brush_spokes_min, state.brush_spokes_max)
        n_spokes     = _random.randint(lo, hi)
        spoke_offset = _random.uniform(0.0, math.pi * 2.0) if n_spokes > 0 else 0.0
    else:
        n_spokes     = state.brush_spokes
        spoke_offset = 0.0

    # 搜尋半徑：chaos 會擴展邊界；spokes 延伸到 2× 基礎半徑
    max_reach = radius * (1.0 + 0.6 * chaos)
    if n_spokes > 0:
        max_reach = max(max_reach, radius * 2.0)
    search_r = int(math.ceil(max_reach)) + 1

    for nq, nr in hex_disk(q, r, search_r):
        if not state.in_bounds(nq, nr):
            continue
        dist = hex_distance(q, r, nq, nr)

        # ── 徑向分量（非線性衰減 + 雜亂度）───────────────────────
        if chaos > 0.0:
            noise_val  = _tile_hash(nq, nr)
            eff_radius = radius * (1.0 + chaos * (noise_val * 2.0 - 1.0) * 0.55)
            eff_radius = max(0.5, eff_radius)
        else:
            eff_radius = float(radius)
        t           = max(0.0, 1.0 - dist / eff_radius)
        base_weight = t ** falloff if t > 0.0 else 0.0

        # ── 放射線分量（可反轉方向）──────────────────────────────
        spoke_w = 0.0
        if n_spokes > 0 and dist > 0:
            dq    = nq - q
            dr    = nr - r
            # axial 偏移 → 近似笛卡爾
            cx_f  = dq + 0.5 * dr
            cy_f  = dr * 0.8660254
            angle     = math.atan2(cy_f, cx_f) - spoke_offset
            spoke_inc = math.pi * 2.0 / n_spokes
            idx       = round(angle / spoke_inc)
            nearest   = idx * spoke_inc
            diff      = abs(((angle - nearest) + math.pi) % (math.pi * 2.0) - math.pi)
            half_w    = spoke_inc * 0.35
            if diff < half_w:
                spoke_cos = math.cos(diff / half_w * math.pi * 0.5)
                spoke_rad = max(0.0, 1.0 - dist / (radius * 2.0))
                spoke_w   = spoke_cos ** 2 * spoke_rad

        # ── 合併：同向取 max，反向做差值 ─────────────────────────
        if invert:
            # 放射線和主工具方向相反：基礎推高、放射線壓低（或反之）
            effective = base_weight - spoke_w
        else:
            effective = max(base_weight, spoke_w)

        if abs(effective) < 1e-6:
            continue
        state.set_h(nq, nr, state.get_h(nq, nr) + sign * strength * effective)


def toggle_water_source(state: EditorState, q: int, r: int) -> None:
    pt = (q, r)
    if pt in state.water_sources:
        state.water_sources.remove(pt)
    else:
        state.water_sources.append(pt)


def _gaussian(dist: float, radius: float) -> float:
    if radius <= 0:
        return 1.0
    sigma = radius / 2.2
    return math.exp(-0.5 * (dist / sigma) ** 2)
