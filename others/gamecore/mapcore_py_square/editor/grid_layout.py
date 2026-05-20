"""方格 ↔ 像素轉換工具（純數學，無 UI 依賴）。

座標慣例：
  - (tx, ty) = tile 座標，tx 為欄（x 向右）、ty 為列（y 向下）
  - (ox, oy) = 攝影機偏移（畫布原點到 tile (0,0) 左上角的像素偏移）
  - size     = 每格邊長（像素）
"""
from __future__ import annotations
import math


def tile_to_pixel(tx: int, ty: int, size: float, ox: float = 0.0, oy: float = 0.0) -> tuple[float, float]:
    """tile 左上角的像素座標。"""
    return tx * size + ox, ty * size + oy


def tile_center(tx: int, ty: int, size: float, ox: float = 0.0, oy: float = 0.0) -> tuple[float, float]:
    """tile 中心的像素座標。"""
    return tx * size + size * 0.5 + ox, ty * size + size * 0.5 + oy


def pixel_to_tile(px: float, py: float, size: float, ox: float = 0.0, oy: float = 0.0) -> tuple[int, int]:
    """像素 → tile 座標（floor division）。"""
    return int(math.floor((px - ox) / size)), int(math.floor((py - oy) / size))


def tile_disk(cx: int, cy: int, radius: int) -> list[tuple[int, int]]:
    """Chebyshev 半徑 radius 內的所有 tile（正方形區域，最大邊長 = 2*radius+1）。"""
    return [
        (x, y)
        for x in range(cx - radius, cx + radius + 1)
        for y in range(cy - radius, cy + radius + 1)
    ]


def tile_distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """Euclidean 距離（用於筆刷 Gaussian 衰減，給出圓形感）。"""
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
