"""河流：拓撲、流量與生成（RimWorld 風 / 方格 4 鄰居版）。

河流走 tile 之間的邊，不走 tile 中心。每條邊只被「兩個共享 tile 中的一個」儲存：
- DIRECTIONS[0,1] (E / N) 由 tile 本身儲存 (Tile.rivers slot 0 / 1)
- DIRECTIONS[2,3] (W / S) 由鄰居儲存（鄰居的 E / N 邊就是本格的 W / S 邊）

每條邊存「流量」(0~255)：0 = 無河，>0 = 流量值。多源頭匯入同條主流時，
generate_rivers 會用 add_river_flow 在共用邊上累加，讓主流流量自然變大。

存儲對外 API：
- has_river_edge(map, c, d) -> bool
- get_river_strength(map, c, d) -> int
- set_river_strength(map, c, d, n) / set_river_edge(map, c, d, bool)
- add_river_flow(map, c, d, amount=1)
- iter_river_edges(map) -> yields (Coord, direction, strength)

生成對齊 RimWorld WorldGenStep_Rivers.cs（同 mapcore_py hex 版的 rivers.py）：
  1) 找所有 coastal water tiles 作為 seeds
  2) 反向 Dijkstra：cost = ElevationChangeCost(elev(st) − elev(ed)) × factor
  3) 對每個 seed 累加 rainfall + 蒸發
  4) 從 seed 開始走樹，按 flow 門檻畫 river edge
"""

from __future__ import annotations

import enum
import heapq
import math
import random
from typing import Iterator, Optional

from .grid import DIRECTIONS, Coord
from .map import TileMap
from .terrain import DEFAULT_REGISTRY

RIVER_BITS = 8
RIVER_MASK = (1 << RIVER_BITS) - 1  # 0xFF
RIVER_MAX_STRENGTH = RIVER_MASK     # 255

# log scale 常數：strength = log(1 + flow*scale) * _LOG_STRENGTH_SCALE
_LOG_STRENGTH_SCALE: float = 45.0

_CREEK_THRESHOLD       = 80   # strength < 80  → CREEK
_LARGE_RIVER_THRESHOLD = 160  # strength >= 160 → LARGE_RIVER


class RiverClass(enum.IntEnum):
    """河流分類，由 classify_river_strength() 依 strength 值決定。"""
    CREEK       = 1
    RIVER       = 2
    LARGE_RIVER = 3


def classify_river_strength(strength: int) -> RiverClass:
    if strength < _CREEK_THRESHOLD:
        return RiverClass.CREEK
    if strength < _LARGE_RIVER_THRESHOLD:
        return RiverClass.RIVER
    return RiverClass.LARGE_RIVER


# ---------------------------------------------------------------------------
# 存儲層
# ---------------------------------------------------------------------------

def _edge_owner(c: Coord, direction: int) -> tuple[Coord, int]:
    """回傳 (owner_coord, slot_index)；direction < 2 自己擁有，其餘由鄰居擁有。

    direction 0 (E) → 自己 slot 0
    direction 1 (N) → 自己 slot 1
    direction 2 (W) → 西邊鄰居 slot 0（鄰居的 E 邊 == 本格的 W 邊）
    direction 3 (S) → 南邊鄰居 slot 1（鄰居的 N 邊 == 本格的 S 邊）
    """
    if 0 <= direction < 2:
        return c, direction
    if 2 <= direction < 4:
        return c + DIRECTIONS[direction], direction - 2
    raise ValueError(f"direction must be in [0, 4), got {direction}")


def _read_slot(rivers: int, slot: int) -> int:
    return (rivers >> (slot * RIVER_BITS)) & RIVER_MASK


def _write_slot(rivers: int, slot: int, value: int) -> int:
    value = max(0, min(RIVER_MAX_STRENGTH, value))
    clear = ~(RIVER_MASK << (slot * RIVER_BITS))
    return (rivers & clear) | (value << (slot * RIVER_BITS))


def get_river_strength(tile_map: TileMap, c: Coord, direction: int) -> int:
    owner, slot = _edge_owner(c, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return 0
    return _read_slot(tile.rivers, slot)


def set_river_strength(tile_map: TileMap, c: Coord, direction: int, strength: int) -> None:
    owner, slot = _edge_owner(c, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return
    tile.rivers = _write_slot(tile.rivers, slot, strength)


def add_river_flow(tile_map: TileMap, c: Coord, direction: int, amount: int = 1) -> None:
    """在指定邊上累加流量；上限 RIVER_MAX_STRENGTH (255)。"""
    owner, slot = _edge_owner(c, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return
    cur = _read_slot(tile.rivers, slot)
    tile.rivers = _write_slot(tile.rivers, slot, cur + amount)


def has_river_edge(tile_map: TileMap, c: Coord, direction: int) -> bool:
    return get_river_strength(tile_map, c, direction) > 0


def set_river_edge(tile_map: TileMap, c: Coord, direction: int, value: bool = True) -> None:
    set_river_strength(tile_map, c, direction, 1 if value else 0)


def iter_river_edges(tile_map: TileMap) -> Iterator[tuple[Coord, int, int]]:
    """yield 所有有河流的 (origin_coord, direction, strength)。direction ∈ {0, 1}。"""
    for c, tile in tile_map:
        if not tile.rivers:
            continue
        for slot in range(2):
            s = _read_slot(tile.rivers, slot)
            if s > 0:
                yield c, slot, s


def _is_water(terrain_id: int) -> bool:
    return DEFAULT_REGISTRY.is_water(terrain_id)


def _manhattan(a: Coord, b: Coord) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


def _downsample_seeds(
    seeds: list[Coord],
    tile_map: TileMap,
    heightmap: list[list[float]],
    min_dist: int,
) -> list[Coord]:
    """貪心過濾：保留彼此距離 >= min_dist 的 seed。

    優先保留「鄰接陸地最低高程」最小的 seed（最低窪出海口），
    讓較高位置的 seed 流域被合併到附近低窪 seed。
    """
    if min_dist <= 1 or not seeds:
        return seeds

    def _min_adj_elev(c: Coord) -> float:
        vals = [
            heightmap[nb.y][nb.x]
            for nb in c.neighbors()
            if tile_map.in_bounds(nb) and not _is_water(tile_map.get(nb).terrain)
        ]
        return min(vals) if vals else 1.0

    ordered = sorted(seeds, key=_min_adj_elev)
    kept: list[Coord] = []
    for s in ordered:
        if all(_manhattan(s, k) >= min_dist for k in kept):
            kept.append(s)
    return kept


def _compute_water_component_sizes(tile_map: TileMap) -> dict[tuple[int, int], int]:
    """BFS 找所有水體連通分量，回傳 {(x, y): 分量格數}（僅水格）。"""
    visited: set[tuple[int, int]] = set()
    result: dict[tuple[int, int], int] = {}
    for c, tile in tile_map:
        key = (c.x, c.y)
        if key in visited or not _is_water(tile.terrain):
            continue
        comp: list[tuple[int, int]] = []
        stack = [key]
        while stack:
            xy = stack.pop()
            if xy in visited:
                continue
            visited.add(xy)
            comp.append(xy)
            for nb in Coord(xy[0], xy[1]).neighbors():
                if not tile_map.in_bounds(nb):
                    continue
                nb_key = (nb.x, nb.y)
                if nb_key not in visited:
                    nb_tile = tile_map.get(nb)
                    if nb_tile is not None and _is_water(nb_tile.terrain):
                        stack.append(nb_key)
        size = len(comp)
        for xy in comp:
            result[xy] = size
    return result


# ---------------------------------------------------------------------------
# RimWorld 風生成
# ---------------------------------------------------------------------------

def _elevation_change_cost(delta: float) -> float:
    """對齊 RW WorldGenStep_Rivers.cs:22-30 ElevationChangeCost SimpleCurve。

    我們 heightmap ∈ [0,1]，把 RW 原本以 -1000~1000m 為單位的 curve 縮 1000 倍：
    delta < 0 → 下游較低，便宜（50~400）；delta ≥ 0 → 逆流/平地，昂貴（5000~50000）。
    """
    if delta < -1.0:
        return 50.0
    if delta < -0.1:
        t = (delta + 1.0) / 0.9
        return 50.0 + t * 50.0
    if delta < 0.0:
        t = (delta + 0.1) / 0.1
        return 100.0 + t * 300.0
    if delta < 0.1:
        t = delta / 0.1
        return 5000.0 + t * 45000.0
    return 50000.0


def _get_coastal_water_tiles(tile_map: TileMap) -> list[Coord]:
    """找所有鄰接陸地的水格（4 鄰居）。"""
    result: list[Coord] = []
    for c, tile in tile_map:
        if not _is_water(tile.terrain):
            continue
        for nb in c.neighbors():
            nb_tile = tile_map.get(nb)
            if nb_tile is not None and not _is_water(nb_tile.terrain):
                result.append(c)
                break
    return result


def _flood_paths_with_cost_for_tree(
    tile_map: TileMap,
    heightmap: list[list[float]],
    seeds: list[Coord],
) -> list[list[Optional[Coord]]]:
    """對齊 RW WorldGenStep_Rivers.cs:48-67 FloodPathsWithCostForTree。

    從多個 seed 同時 Dijkstra 反向擴張，產出每格的 parent（指向下游一格）。
    cost: factor × ElevationChangeCost(elev(st) − elev(ed))
          factor = 1 若 ed 的最低鄰居就是 st，否則 2。
    """
    W, H = tile_map.width, tile_map.height
    inf = math.inf
    g_score: list[list[float]] = [[inf] * W for _ in range(H)]
    parent: list[list[Optional[Coord]]] = [[None] * W for _ in range(H)]
    seed_set = {(s.x, s.y) for s in seeds}

    pq: list[tuple[float, int, int, int]] = []
    counter = 0
    for s in seeds:
        g_score[s.y][s.x] = 0.0
        heapq.heappush(pq, (0.0, counter, s.x, s.y))
        counter += 1

    while pq:
        g, _, x, y = heapq.heappop(pq)
        if g > g_score[y][x]:
            continue
        cur = Coord(x, y)
        # 非起點水格不再擴張；river 只往陸地延伸
        if (x, y) not in seed_set and _is_water(tile_map.get(cur).terrain):
            continue

        cur_elev = heightmap[y][x]
        for nb in cur.neighbors():
            if not tile_map.in_bounds(nb):
                continue
            nb_elev = heightmap[nb.y][nb.x]
            # 找 nb 的最低鄰居：若 cur 剛好是 nb 的自然下游 → factor=1，否則 factor=2
            lowest_elev = inf
            lowest_x = -1
            lowest_y = -1
            for nbnb in nb.neighbors():
                if not tile_map.in_bounds(nbnb):
                    continue
                ee = heightmap[nbnb.y][nbnb.x]
                if ee < lowest_elev:
                    lowest_elev = ee
                    lowest_x, lowest_y = nbnb.x, nbnb.y
            factor = 1.0 if (lowest_x == x and lowest_y == y) else 2.0
            delta = cur_elev - nb_elev
            edge_cost = factor * _elevation_change_cost(delta)
            new_g = g + edge_cost
            if new_g < g_score[nb.y][nb.x]:
                g_score[nb.y][nb.x] = new_g
                parent[nb.y][nb.x] = cur
                counter += 1
                heapq.heappush(pq, (new_g, counter, nb.x, nb.y))

    return parent


def _build_children(
    tile_map: TileMap, parent: list[list[Optional[Coord]]]
) -> list[list[list[Coord]]]:
    """把 parent map 翻成 children list（per tile，list of 上游 tiles）。"""
    W, H = tile_map.width, tile_map.height
    children: list[list[list[Coord]]] = [[[] for _ in range(W)] for _ in range(H)]
    for y in range(H):
        for x in range(W):
            par = parent[y][x]
            if par is not None:
                children[par.y][par.x].append(Coord(x, y))
    return children


def _approximate_temperature(y: int, total_h: int) -> float:
    """近似 °C：中央列（赤道）25°C，邊緣（極地）-30°C。"""
    half = max((total_h - 1) / 2.0, 1e-9)
    lat_abs = abs(y - (total_h - 1) / 2.0) / half
    return 25.0 - 55.0 * lat_abs


def _evaporation_constant(temp_c: float) -> float:
    """對齊 RW WorldGenStep_Rivers.cs:192-195 CalculateEvaporationConstant。"""
    return (
        0.61121
        * math.exp((18.678 - temp_c / 234.5) * (temp_c / (257.14 + temp_c)))
        / (temp_c + 273.0)
    )


def _total_evaporation(flow: float, temp_c: float, scale: float) -> float:
    if flow <= 0:
        return 0.0
    return _evaporation_constant(temp_c) * math.sqrt(flow) * 250.0 * scale


def _accumulate_flow_from(
    flow: list[list[float]],
    children: list[list[list[Coord]]],
    root: Coord,
    rainfall: list[list[float]],
    temperature: list[list[float]],
    evap_scale: float,
) -> None:
    """Post-order iterative DFS：每格 flow = rainfall + Σ child.flow - evap(self_flow, temp)。"""
    stack: list[tuple[Coord, bool]] = [(root, False)]
    while stack:
        cur, processed = stack.pop()
        x, y = cur.x, cur.y
        if not processed:
            stack.append((cur, True))
            for child in children[y][x]:
                stack.append((child, False))
            continue
        flow[y][x] += rainfall[y][x]
        for child in children[y][x]:
            flow[y][x] += flow[child.y][child.x]
        evap = _total_evaporation(flow[y][x], temperature[y][x], evap_scale)
        flow[y][x] = max(0.0, flow[y][x] - evap)


def _coord_direction(a: Coord, b: Coord) -> Optional[int]:
    """a 與 b 鄰接時回傳 a → b 的方向（0..3），否則 None。"""
    delta = b - a
    for d, dh in enumerate(DIRECTIONS):
        if dh == delta:
            return d
    return None


def _paint_edge(
    tile_map: TileMap, cur: Coord, direction: int, flow_value: float, scale: float
) -> None:
    ref = flow_value * scale
    strength = max(1, min(RIVER_MAX_STRENGTH, int(math.log1p(ref) * _LOG_STRENGTH_SCALE)))
    add_river_flow(tile_map, cur, direction, strength)


def _create_rivers_from_seed(
    tile_map: TileMap,
    flow: list[list[float]],
    children: list[list[list[Coord]]],
    seed: Coord,
    spawn_flow_threshold: float,
    degrade_threshold: float,
    branch_flow_threshold: float,
    branch_chance: float,
    flow_strength_scale: float,
    rng: random.Random,
) -> int:
    """對齊 RW WorldGenStep_Rivers.cs:143-190 CreateRivers + ExtendRiver。"""
    painted = 0
    for first_child in children[seed.y][seed.x]:
        cf = flow[first_child.y][first_child.x]
        if cf < spawn_flow_threshold:
            continue
        d = _coord_direction(seed, first_child)
        if d is None:
            continue
        _paint_edge(tile_map, seed, d, cf, flow_strength_scale)
        painted += 1

        stack: list[Coord] = [first_child]
        while stack:
            cur = stack.pop()
            kids = children[cur.y][cur.x]
            if not kids:
                continue
            kids_sorted = sorted(kids, key=lambda k: flow[k.y][k.x], reverse=True)
            best = kids_sorted[0]
            best_flow = flow[best.y][best.x]
            if best_flow >= degrade_threshold:
                bd = _coord_direction(cur, best)
                if bd is not None:
                    _paint_edge(tile_map, cur, bd, best_flow, flow_strength_scale)
                    painted += 1
                stack.append(best)
            for alt in kids_sorted[1:]:
                af = flow[alt.y][alt.x]
                if af < branch_flow_threshold:
                    continue
                if rng.random() >= branch_chance:
                    continue
                ad = _coord_direction(cur, alt)
                if ad is not None:
                    _paint_edge(tile_map, cur, ad, af, flow_strength_scale)
                    painted += 1
                stack.append(alt)
    return painted


def generate_rivers(
    tile_map: TileMap,
    heightmap: list[list[float]],
    rainfall: list[list[float]],
    temperature: Optional[list[list[float]]] = None,
    seed: Optional[int] = None,
    *,
    rainfall_scale: float = 1000.0,
    spawn_flow_threshold: float = 600.0,
    degrade_threshold: float = 200.0,
    branch_flow_threshold: float = 400.0,
    branch_chance: float = 0.3,
    flow_strength_scale: float = 0.05,
    evaporation_scale: float = 1.0,
    min_sea_size: int = 1,
    min_seed_spacing: int = 1,
) -> int:
    """RimWorld 風河流生成（對齊 mapcore_py hex 版的 generate_rivers）。

    流程：
      1. 找 coastal water tiles 當作 seeds
      2. 反向 Dijkstra 建下游樹
      3. DFS 累加 rainfall − evaporation 得到每格 flow
      4. 從每個 seed 走樹：主流走最大 flow child（≥ degrade_threshold），
         其餘 children 中 flow ≥ branch_flow_threshold 者按 branch_chance 分支

    回傳：標記的河流邊數量（不去重，多源匯流時同條邊會被多次 add_river_flow 累加）。
    """
    if rainfall_scale < 0:
        raise ValueError(f"rainfall_scale must be >= 0, got {rainfall_scale}")
    if spawn_flow_threshold < 0:
        raise ValueError(f"spawn_flow_threshold must be >= 0, got {spawn_flow_threshold}")
    if flow_strength_scale <= 0:
        raise ValueError(f"flow_strength_scale must be > 0, got {flow_strength_scale}")
    if not 0.0 <= branch_chance <= 1.0:
        raise ValueError(f"branch_chance must be in [0, 1], got {branch_chance}")

    W, H = tile_map.width, tile_map.height
    if len(heightmap) != H or any(len(row) != W for row in heightmap):
        raise ValueError("heightmap shape must match tile_map (height, width)")
    if len(rainfall) != H or any(len(row) != W for row in rainfall):
        raise ValueError("rainfall shape must match tile_map (height, width)")

    rng = random.Random(seed)
    seeds = _get_coastal_water_tiles(tile_map)
    if not seeds:
        return 0

    if min_sea_size > 1:
        comp_sizes = _compute_water_component_sizes(tile_map)
        seeds = [s for s in seeds if comp_sizes.get((s.x, s.y), 0) >= min_sea_size]
        if not seeds:
            return 0

    if min_seed_spacing > 1:
        seeds = _downsample_seeds(seeds, tile_map, heightmap, min_seed_spacing)
        if not seeds:
            return 0

    parent = _flood_paths_with_cost_for_tree(tile_map, heightmap, seeds)
    children = _build_children(tile_map, parent)

    if temperature is None:
        temperature = [[_approximate_temperature(y, H)] * W for y in range(H)]
    elif len(temperature) != H or any(len(row) != W for row in temperature):
        raise ValueError("temperature shape must match tile_map (height, width)")
    rainfall_scaled: list[list[float]] = [
        [rainfall[y][x] * rainfall_scale for x in range(W)] for y in range(H)
    ]

    flow: list[list[float]] = [[0.0] * W for _ in range(H)]
    for s in seeds:
        _accumulate_flow_from(flow, children, s, rainfall_scaled, temperature, evaporation_scale)

    painted = 0
    for s in seeds:
        painted += _create_rivers_from_seed(
            tile_map, flow, children, s,
            spawn_flow_threshold,
            degrade_threshold,
            branch_flow_threshold,
            branch_chance,
            flow_strength_scale,
            rng,
        )
    return painted
