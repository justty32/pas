"""六角格座標核心。

使用 axial 座標 (q, r)，隱含第三軸 s = -q - r。
方向常數對齊 analysis/unciv/tutorial/cpp_hex_library.md 第 31 行。
距離公式對齊 analysis/unciv/tutorial/cpp_hex_map_structure.md 第 39 行。

設計決策：Hex 刻意不可雜湊。未來的 C++ 版會用 2D array 索引地圖，
Python 版也走相同路線，不依賴 hash map / set 來儲存或查詢格子。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(eq=True, slots=True)
class Hex:
    q: int
    r: int

    @property
    def s(self) -> int:
        return -self.q - self.r

    def __add__(self, other: "Hex") -> "Hex":
        return Hex(self.q + other.q, self.r + other.r)

    def __sub__(self, other: "Hex") -> "Hex":
        return Hex(self.q - other.q, self.r - other.r)

    def __mul__(self, scalar: int) -> "Hex":
        return Hex(self.q * scalar, self.r * scalar)

    def neighbor(self, direction_index: int) -> "Hex":
        return self + DIRECTIONS[direction_index % 6]

    def neighbors(self) -> tuple["Hex", "Hex", "Hex", "Hex", "Hex", "Hex"]:
        return tuple(self + d for d in DIRECTIONS)  # type: ignore[return-value]


DIRECTIONS: tuple[Hex, Hex, Hex, Hex, Hex, Hex] = (
    Hex(1, 0),
    Hex(1, -1),
    Hex(0, -1),
    Hex(-1, 0),
    Hex(-1, 1),
    Hex(0, 1),
)


def direction(index: int) -> Hex:
    return DIRECTIONS[index % 6]


def distance(a: Hex, b: Hex) -> int:
    return (abs(a.q - b.q) + abs(a.q + a.r - b.q - b.r) + abs(a.r - b.r)) // 2


def hex_round(qf: float, rf: float) -> Hex:
    """將浮點軸向座標取整到最近的 Hex。

    必須轉成 cube (q, r, s) 後分別四捨五入，再以「誤差最大者由其他兩軸回推」修正，
    否則直線遍歷會在格子邊界跳格。對齊 cpp_hex_library.md 第 94 行 hex_round。
    """
    sf = -qf - rf
    rq = round(qf)
    rr = round(rf)
    rs = round(sf)

    q_diff = abs(rq - qf)
    r_diff = abs(rr - rf)
    s_diff = abs(rs - sf)

    if q_diff > r_diff and q_diff > s_diff:
        rq = -rr - rs
    elif r_diff > s_diff:
        rr = -rq - rs
    return Hex(int(rq), int(rr))


def line(start: Hex, end: Hex) -> list[Hex]:
    """從 start 到 end 的格子序列（含兩端點）。長度 = distance + 1。"""
    n = distance(start, end)
    if n == 0:
        return [start]
    results: list[Hex] = []
    for i in range(n + 1):
        t = i / n
        q = start.q * (1.0 - t) + end.q * t
        r = start.r * (1.0 - t) + end.r * t
        results.append(hex_round(q, r))
    return results


def ring(center: Hex, radius: int) -> list[Hex]:
    """半徑為 radius 的環上所有格子。radius >= 0；radius=0 回傳 [center]。"""
    if radius < 0:
        raise ValueError(f"radius must be >= 0, got {radius}")
    if radius == 0:
        return [center]

    results: list[Hex] = []
    cube = center + DIRECTIONS[4] * radius
    for i in range(6):
        for _ in range(radius):
            results.append(cube)
            cube = cube + DIRECTIONS[i]
    return results


def spiral(center: Hex, max_radius: int) -> Iterator[Hex]:
    """從中心向外，依環序逐格 yield。總數 = 1 + 3N(N+1)。"""
    if max_radius < 0:
        raise ValueError(f"max_radius must be >= 0, got {max_radius}")
    yield center
    for radius in range(1, max_radius + 1):
        yield from ring(center, radius)
