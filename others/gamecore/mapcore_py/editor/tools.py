"""地形雕刻工具：筆刷、山脊、裂谷。"""
from __future__ import annotations
import math
from .state import EditorState
from .hex_layout import hex_disk, hex_line, hex_distance


def apply_brush(state: EditorState, q: int, r: int, delta: float) -> None:
    """高斯衰減筆刷：中心 delta 最強，邊緣趨近 0。"""
    for nq, nr in hex_disk(q, r, state.brush_size):
        if not state.in_bounds(nq, nr):
            continue
        dist = hex_distance(q, r, nq, nr)
        weight = _gaussian(dist, state.brush_size)
        state.set_h(nq, nr, state.get_h(nq, nr) + delta * weight)


def apply_ridge(
    state: EditorState,
    q0: int, r0: int,
    q1: int, r1: int,
) -> None:
    """沿直線堆起尖銳山脊（垂直方向快速衰減）。"""
    _apply_line_profile(state, q0, r0, q1, r1, sign=+1)


def apply_rift(
    state: EditorState,
    q0: int, r0: int,
    q1: int, r1: int,
) -> None:
    """沿直線挖出裂谷（垂直方向快速衰減）。"""
    _apply_line_profile(state, q0, r0, q1, r1, sign=-1)


def _apply_line_profile(
    state: EditorState,
    q0: int, r0: int,
    q1: int, r1: int,
    sign: float,
) -> None:
    line = hex_line(q0, r0, q1, r1)
    width = max(1, state.brush_size)
    strength = state.brush_strength * 2.5
    for (lq, lr) in line:
        for nq, nr in hex_disk(lq, lr, width):
            if not state.in_bounds(nq, nr):
                continue
            dist = hex_distance(lq, lr, nq, nr)
            weight = math.exp(-2.5 * (dist / width) ** 2)
            state.set_h(nq, nr, state.get_h(nq, nr) + sign * strength * weight)


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
