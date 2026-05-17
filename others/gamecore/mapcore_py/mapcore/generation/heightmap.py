"""高程 noise (Phase 1)。

純 stdlib 的多層 value noise (fBm-like)：
1. 每個 octave 各自產生一張低解析度隨機網格 (值 ∈ [0,1])。
2. 用 smoothstep + 雙線性插值 (bilinear) 放大到 width×height。
3. 用 persistence^octave 當權重加總，最後除以權重和，輸出仍在 [0,1]。

頻率倍增 (lacunarity=2)。要换 Perlin/Simplex 之後再說，先求架構與決定性。
對齊 analysis/wesnoth/details/encyclopedia_vol1_heightmap.md 的分層概念。
"""

from __future__ import annotations

import random
from typing import Optional


def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _bilinear(coarse: list[list[float]], x: float, y: float) -> float:
    """在 coarse 網格上做 smoothstep + bilinear 取樣；x、y 為 coarse 座標系。"""
    gh = len(coarse)
    gw = len(coarse[0])
    x0 = int(x)
    y0 = int(y)
    x1 = min(x0 + 1, gw - 1)
    y1 = min(y0 + 1, gh - 1)
    fx = _smoothstep(x - x0)
    fy = _smoothstep(y - y0)
    top = coarse[y0][x0] * (1.0 - fx) + coarse[y0][x1] * fx
    bot = coarse[y1][x0] * (1.0 - fx) + coarse[y1][x1] * fx
    return top * (1.0 - fy) + bot * fy


def generate_heightmap(
    width: int,
    height: int,
    seed: Optional[int] = None,
    octaves: int = 4,
    persistence: float = 0.5,
    base_frequency: int = 4,
) -> list[list[float]]:
    """產生 height × width 的高程陣列，值 ∈ [0, 1]。

    - width / height：地圖尺寸，需 > 0。
    - seed：隨機種子；同 seed 同參數可完全重現。
    - octaves：疊加層數；越多越細緻、越貴。
    - persistence：每往細一層振幅乘以多少 (0~1)。0.5 是常用值。
    - base_frequency：最粗那層的網格邊長 (cells)；2 表示 3×3 的 coarse grid。
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be > 0, got ({width}, {height})")
    if octaves <= 0:
        raise ValueError(f"octaves must be > 0, got {octaves}")
    if not 0.0 < persistence <= 1.0:
        raise ValueError(f"persistence must be in (0, 1], got {persistence}")
    if base_frequency < 1:
        raise ValueError(f"base_frequency must be >= 1, got {base_frequency}")

    rng = random.Random(seed)
    grid: list[list[float]] = [[0.0] * width for _ in range(height)]
    total_weight = 0.0

    for octave in range(octaves):
        freq = base_frequency * (2 ** octave)
        weight = persistence ** octave
        total_weight += weight

        gw = freq + 1
        gh = freq + 1
        coarse = [[rng.random() for _ in range(gw)] for _ in range(gh)]

        # 把 (q, r) 線性對應到 coarse 的 [0, freq] 範圍。
        x_scale = freq / max(width - 1, 1)
        y_scale = freq / max(height - 1, 1)
        for r in range(height):
            cy = r * y_scale
            for q in range(width):
                cx = q * x_scale
                grid[r][q] += weight * _bilinear(coarse, cx, cy)

    inv = 1.0 / total_weight
    for r in range(height):
        for q in range(width):
            grid[r][q] *= inv
    return grid
