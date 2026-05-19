"""方格座標核心 (4-directional von Neumann)。

對應 mapcore_py/mapcore/hex.py 的方格版本：
- 軸向 (q, r) → 直角 (x, y)，x = column、y = row（y 向下，符合 screen-space 與 [y][x] 儲存順序）
- 6 鄰居 → 4 鄰居 (E / N / W / S)，對應 JRPG 風格的 N/S/E/W 移動
- hex distance → Manhattan distance
- hex ring → diamond ring（|dx|+|dy|=radius）
- hex line → 4-connected supercover line

設計決策：Coord 刻意不可雜湊（dataclass(eq=True) 預設行為），對齊未來 C++ 版用 2D array
索引地圖、不依賴 hash map 的記憶體佈局。要用座標查格子請走 `TileMap.get(coord)`。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


# dataclass(eq=True) 預設會把 __hash__ 設為 None，所以 Coord 是 unhashable。
# 刻意：對齊 mapcore_py/mapcore/hex.py 的設計，地圖儲存走 2D array。
@dataclass(eq=True, slots=True)
class Coord:
    x: int
    y: int

    def __add__(self, other: "Coord") -> "Coord":
        return Coord(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Coord") -> "Coord":
        return Coord(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: int) -> "Coord":
        return Coord(self.x * scalar, self.y * scalar)

    def neighbor(self, direction_index: int) -> "Coord":
        return self + DIRECTIONS[direction_index % 4]

    def neighbors(self) -> tuple["Coord", "Coord", "Coord", "Coord"]:
        return tuple(self + d for d in DIRECTIONS)  # type: ignore[return-value]


# 4 方向順序鎖死：0=E, 1=N, 2=W, 3=S。對立方向 i ↔ (i+2)%4。
# 與 hex.py 同樣使「對立 = i + len/2」的模式，方便對齊。
# 注意 y 向下，所以 N = (0, -1)、S = (0, +1)。
DIRECTIONS: tuple[Coord, Coord, Coord, Coord] = (
    Coord(1, 0),    # 0: E
    Coord(0, -1),   # 1: N
    Coord(-1, 0),   # 2: W
    Coord(0, 1),    # 3: S
)


def direction(index: int) -> Coord:
    return DIRECTIONS[index % 4]


def distance(a: Coord, b: Coord) -> int:
    """Manhattan distance = |dx| + |dy|；對應 4 鄰居的最短步數。"""
    return abs(a.x - b.x) + abs(a.y - b.y)


def line(start: Coord, end: Coord) -> list[Coord]:
    """4-connected supercover line：從 start 到 end 的格子序列（含兩端點）。

    長度 = Manhattan distance + 1；相鄰格子總是 4-鄰接（不會出現對角跳格）。
    對應 hex.py 的 line()，但因為 4 連通沒有對角，這裡用 Bresenham 變形：
    每步只動 x 或 y 其中一軸，由累積誤差決定。
    """
    x0, y0 = start.x, start.y
    x1, y1 = end.x, end.y
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    if dx == 0 and dy == 0:
        return [Coord(x0, y0)]

    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1

    # 標準「supercover」Bresenham：誤差 error 控制下一步走 x 還是 y，
    # 不允許同時動兩軸（對齊 4 鄰居拓樸）。總步數 = dx + dy。
    error = dx - dy
    x, y = x0, y0
    result: list[Coord] = [Coord(x, y)]
    for _ in range(dx + dy):
        e2 = 2 * error
        if e2 > -dy:
            error -= dy
            x += sx
        else:
            error += dx
            y += sy
        result.append(Coord(x, y))
    return result


def ring(center: Coord, radius: int) -> list[Coord]:
    """Manhattan 距離恰為 radius 的菱形環。radius >= 0；radius=0 回傳 [center]。

    radius>=1 時共 4*radius 格。順序從西邊頂點 (cx-radius, cy) 開始順時針一圈：
    先走 NE 對角線到北頂點 → SE 到東頂點 → SW 到南頂點 → NW 回到西頂點。
    """
    if radius < 0:
        raise ValueError(f"radius must be >= 0, got {radius}")
    if radius == 0:
        return [center]

    result: list[Coord] = []
    x = center.x - radius
    y = center.y
    # 4 條斜邊，每邊 radius 步；每步座標差 (±1, ±1) 在菱形周上移動
    sides = ((1, -1), (1, 1), (-1, 1), (-1, -1))
    for sx, sy in sides:
        for _ in range(radius):
            result.append(Coord(x, y))
            x += sx
            y += sy
    return result


def spiral(center: Coord, max_radius: int) -> Iterator[Coord]:
    """從中心向外，依菱形環序逐格 yield。總數 = 1 + 2N(N+1)。"""
    if max_radius < 0:
        raise ValueError(f"max_radius must be >= 0, got {max_radius}")
    yield center
    for radius in range(1, max_radius + 1):
        yield from ring(center, radius)
