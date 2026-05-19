"""Hex ↔ 像素轉換工具（純數學，無 UI 依賴）。

使用 odd-r offset 座標系：
  - r 為列（偶數列不偏移，奇數列向右偏移半格）
  - 地圖呈矩形排列，視覺上直觀
  - 距離/鄰居/圓盤等算術在內部透過 cube 座標實作，保持精確
"""
from __future__ import annotations
import math

SQRT3 = math.sqrt(3)


# ── Cube ↔ Odd-r offset ───────────────────────────────────────────────────────

def _to_cube(q: int, r: int) -> tuple[int, int, int]:
    x = q - (r - (r & 1)) // 2
    z = r
    y = -x - z
    return x, y, z


def _from_cube(x: int, y: int, z: int) -> tuple[int, int]:
    q = x + (z - (z & 1)) // 2
    r = z
    return q, r


def _cube_round(xf: float, yf: float, zf: float) -> tuple[int, int, int]:
    rx, ry, rz = round(xf), round(yf), round(zf)
    dx, dy, dz = abs(rx - xf), abs(ry - yf), abs(rz - zf)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return rx, ry, rz


# ── Pixel ↔ Hex ───────────────────────────────────────────────────────────────

def hex_to_pixel(
    q: int, r: int,
    size: float,
    ox: float = 0.0,
    oy: float = 0.0,
) -> tuple[float, float]:
    """Odd-r offset hex → 像素中心（偶數列不偏移，奇數列右移半格）。"""
    x = size * SQRT3 * (q + 0.5 * (r & 1)) + ox
    y = size * 1.5 * r + oy
    return x, y


def pixel_to_hex(
    px: float, py: float,
    size: float,
    ox: float = 0.0,
    oy: float = 0.0,
) -> tuple[int, int]:
    """像素 → (q, r) offset 座標，使用 cube rounding 精確處理格邊界。"""
    lx = (px - ox) / size
    ly = (py - oy) / size
    r_f = ly / 1.5
    xf  = lx / SQRT3 - 0.5 * (round(r_f) & 1)
    zf  = r_f
    yf  = -xf - zf
    return _from_cube(*_cube_round(xf, yf, zf))


def hex_corners(cx: float, cy: float, size: float) -> list[tuple[float, float]]:
    """Pointy-top hex 的六個頂點座標（順時針）。"""
    return [
        (cx + size * math.cos(math.radians(60 * i - 30)),
         cy + size * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


# ── Hex arithmetic ────────────────────────────────────────────────────────────

def hex_distance(q1: int, r1: int, q2: int, r2: int) -> int:
    x1, y1, z1 = _to_cube(q1, r1)
    x2, y2, z2 = _to_cube(q2, r2)
    return (abs(x1 - x2) + abs(y1 - y2) + abs(z1 - z2)) // 2


def hex_line(q0: int, r0: int, q1: int, r1: int) -> list[tuple[int, int]]:
    """沿直線的所有 hex 座標（含兩端點）。"""
    n = hex_distance(q0, r0, q1, r1)
    if n == 0:
        return [(q0, r0)]
    x0, y0, z0 = _to_cube(q0, r0)
    x1, y1, z1 = _to_cube(q1, r1)
    return [
        _from_cube(*_cube_round(
            x0 + (x1 - x0) * i / n,
            y0 + (y1 - y0) * i / n,
            z0 + (z1 - z0) * i / n,
        ))
        for i in range(n + 1)
    ]


def hex_disk(cq: int, cr: int, radius: int) -> list[tuple[int, int]]:
    """以 (cq, cr) 為中心、半徑 radius 以內的所有 hex。"""
    cx, cy, cz = _to_cube(cq, cr)
    results = []
    for dx in range(-radius, radius + 1):
        for dy in range(max(-radius, -dx - radius), min(radius, -dx + radius) + 1):
            results.append(_from_cube(cx + dx, cy + dy, -dx - dy))
    return results


def canvas_pixel_size(
    width: int, height: int,
    hex_size: float,
    margin: float = 30.0,
) -> tuple[int, int]:
    """計算包住整張地圖所需的像素畫布尺寸。"""
    max_x = hex_size * SQRT3 * (width - 1 + 0.5) + margin * 2 + hex_size * 2
    max_y = hex_size * 1.5 * (height - 1) + margin * 2 + hex_size * 2
    return int(max_x), int(max_y)
