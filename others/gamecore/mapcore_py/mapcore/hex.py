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


# dataclass(eq=True) 預設會自動把 __hash__ 設為 None，所以 Hex 是 unhashable。
# 這是刻意的：地圖儲存用 2D array 不用 hash map，跟 C++ 版的記憶體佈局對齊。
@dataclass(eq=True, slots=True)
class Hex:
    q: int
    r: int

    @property
    def s(self) -> int:
        # cube 座標的第三軸由 q + r + s = 0 推回；用 property 而非欄位是為了避免一致性問題
        return -self.q - self.r

    def __add__(self, other: "Hex") -> "Hex":
        return Hex(self.q + other.q, self.r + other.r)

    def __sub__(self, other: "Hex") -> "Hex":
        return Hex(self.q - other.q, self.r - other.r)

    def __mul__(self, scalar: int) -> "Hex":
        return Hex(self.q * scalar, self.r * scalar)

    def neighbor(self, direction_index: int) -> "Hex":
        # % 6 讓 ±方向 / 大於 6 的索引都能 wrap 回合法範圍
        return self + DIRECTIONS[direction_index % 6]

    def neighbors(self) -> tuple["Hex", "Hex", "Hex", "Hex", "Hex", "Hex"]:
        return tuple(self + d for d in DIRECTIONS)  # type: ignore[return-value]


# pointy-top 軸向方向向量，順序鎖死：0=E, 1=NE, 2=NW, 3=W, 4=SW, 5=SE
# rivers.EDGE_CORNERS 跟 edge ownership（0..2 自擁、3..5 鄰居擁）都依賴這個順序，不可變動
DIRECTIONS: tuple[Hex, Hex, Hex, Hex, Hex, Hex] = (
    Hex(1, 0),    # 0: E
    Hex(1, -1),   # 1: NE
    Hex(0, -1),   # 2: NW
    Hex(-1, 0),   # 3: W
    Hex(-1, 1),   # 4: SW
    Hex(0, 1),    # 5: SE
)


def direction(index: int) -> Hex:
    return DIRECTIONS[index % 6]


def distance(a: Hex, b: Hex) -> int:
    # cube distance = (|dq| + |dr| + |ds|) / 2，其中 ds = -(dq + dr)
    # 展開 |ds| = |dq + dr|，所以可以只用 q/r 兩軸計算，省一個 property 取值
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
    # 在 q/r 浮點空間做線性插值再 hex_round；hex_round 的最大誤差軸修正會
    # 確保結果是合法的 hex 序列、不會在邊界跳格
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
    # 標準環形遍歷：從 SW 邊（DIRECTIONS[4]）的角落出發，沿 6 個方向各走 radius 步繞一圈
    # 起點方向選 4 是為了讓輸出順序固定（從西南角開始順時針），測試可重現
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
