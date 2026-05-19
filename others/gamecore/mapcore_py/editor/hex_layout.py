"""Hex ↔ 像素轉換工具（純數學，無 UI 依賴）。

使用與 mapcore 範例相同的 pointy-top axial 座標系，確保視覺一致。
"""
from __future__ import annotations
import math

SQRT3 = math.sqrt(3)


def hex_to_pixel(
    q: int, r: int,
    size: float,
    ox: float = 0.0,
    oy: float = 0.0,
) -> tuple[float, float]:
    """Pointy-top hex axial → 像素中心，ox/oy 為畫布偏移。"""
    x = size * (SQRT3 * q + SQRT3 / 2 * r) + ox
    y = size * (1.5 * r) + oy
    return x, y


def pixel_to_hex(
    px: float, py: float,
    size: float,
    ox: float = 0.0,
    oy: float = 0.0,
) -> tuple[int, int]:
    """像素 → (q, r)，附帶 cube rounding。"""
    x = (px - ox) / size
    y = (py - oy) / size
    q_f = SQRT3 / 3 * x - 1 / 3 * y
    r_f = 2 / 3 * y
    return _axial_round(q_f, r_f)


def _axial_round(q_f: float, r_f: float) -> tuple[int, int]:
    s_f = -q_f - r_f
    q, r, s = round(q_f), round(r_f), round(s_f)
    dq, dr, ds = abs(q - q_f), abs(r - r_f), abs(s - s_f)
    if dq > dr and dq > ds:
        q = -r - s
    elif dr > ds:
        r = -q - s
    return int(q), int(r)


def hex_corners(cx: float, cy: float, size: float) -> list[tuple[float, float]]:
    """Pointy-top hex 的六個頂點座標（順時針）。"""
    return [
        (cx + size * math.cos(math.radians(60 * i - 30)),
         cy + size * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


def hex_distance(q1: int, r1: int, q2: int, r2: int) -> int:
    dq, dr = q2 - q1, r2 - r1
    return max(abs(dq), abs(dr), abs(dq + dr))


def hex_line(q0: int, r0: int, q1: int, r1: int) -> list[tuple[int, int]]:
    """沿直線的所有 hex 座標（含兩端點）。"""
    n = hex_distance(q0, r0, q1, r1)
    if n == 0:
        return [(q0, r0)]
    return [
        _axial_round(q0 + (q1 - q0) * i / n, r0 + (r1 - r0) * i / n)
        for i in range(n + 1)
    ]


def hex_disk(cq: int, cr: int, radius: int) -> list[tuple[int, int]]:
    """以 (cq, cr) 為中心、半徑 radius 以內的所有 hex。"""
    results = []
    for dq in range(-radius, radius + 1):
        for dr in range(max(-radius, -dq - radius), min(radius, -dq + radius) + 1):
            results.append((cq + dq, cr + dr))
    return results


def canvas_pixel_size(
    width: int, height: int,
    hex_size: float,
    margin: float = 30.0,
) -> tuple[int, int]:
    """計算包住整張地圖所需的像素畫布尺寸。"""
    max_x = hex_size * (SQRT3 * (width - 1) + SQRT3 / 2 * (height - 1)) + margin * 2 + hex_size * 2
    max_y = hex_size * (1.5 * (height - 1)) + margin * 2 + hex_size * 2
    return int(max_x), int(max_y)
