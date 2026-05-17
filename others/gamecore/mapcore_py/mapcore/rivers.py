"""河流：拓撲、流量與生成（RimWorld 風）。

河流走 hex 邊，不走 tile 中心。每條邊只被「兩個共享 tile 中的一個」儲存，避免重複：
- DIRECTIONS[0,1,2] (E / NE / NW) 由 tile 本身儲存 (Tile.rivers 的 8-bit slot 0/1/2)
- DIRECTIONS[3,4,5] (W / SW / SE) 由鄰居儲存

每條邊存「流量」(0~255)：0 = 無河，>0 = 流量值。多源頭匯入同條主流時，
generate_rivers 會用 add_river_flow 在共用邊上累加，讓主流流量自然變大。

存儲對外 API（保留不變）：
- has_river_edge(map, h, d) -> bool
- get_river_strength(map, h, d) -> int
- set_river_strength(map, h, d, n) / set_river_edge(map, h, d, bool)
- add_river_flow(map, h, d, amount=1)
- iter_river_edges(map) -> yields (Hex, direction, strength)

生成對齊 projects/rimworld/RimWorld.Planet/WorldGenStep_Rivers.cs:30-210：
  1) 找所有 coastal water tiles（鄰接陸地的海/海岸）作為 seeds
  2) 反向 Dijkstra：cost = ElevationChangeCost(elev(st) − elev(ed)) × factor
     factor = 1 若 ed 的最低鄰居就是 st，否則 2；非起點水不再擴張
  3) 對每個 seed DFS 累加 rainfall，每格按 sqrt(flow)×evap_const(temp)×250 扣蒸發
  4) 從 seed 開始走樹，按 flow 門檻畫 river edge（主流走最大 flow child，其餘 children 按 branch_chance 分流）
"""

from __future__ import annotations

import heapq
import math
import random
from typing import Iterator, Optional

from .hex import DIRECTIONS, Hex
from .map import TerrainType, TileMap

WATER = (TerrainType.OCEAN, TerrainType.COAST)

# 渲染用：direction d 的邊由 hex 上哪兩個 corner 連起來（pointy-top，
# corners 從 angle -30° 開始順時針：0=右上, 1=右下, 2=下, 3=左下, 4=左上, 5=上）
EDGE_CORNERS: tuple[tuple[int, int], ...] = (
    (0, 1),  # d=0 E  右邊
    (5, 0),  # d=1 NE 右上邊
    (4, 5),  # d=2 NW 左上邊
    (3, 4),  # d=3 W  左邊
    (2, 3),  # d=4 SW 左下邊
    (1, 2),  # d=5 SE 右下邊
)

RIVER_BITS = 8
RIVER_MASK = (1 << RIVER_BITS) - 1  # 0xFF
RIVER_MAX_STRENGTH = RIVER_MASK     # 255


# ---------------------------------------------------------------------------
# 存儲層（保留不變）
# ---------------------------------------------------------------------------

def _edge_owner(h: Hex, direction: int) -> tuple[Hex, int]:
    """回傳 (owner_hex, slot_index)；direction < 3 自己擁有，其餘由鄰居擁有。

    這是「同一條邊不被兩個 hex 重複儲存」的關鍵：每條邊永遠由 direction 較小的那一側持有。
    例如 hex A 的 d=5 (SE) 邊就是它東南鄰居 B 的 d=2 (NW) 邊，由 B 儲存 slot 2。
    """
    if 0 <= direction < 3:
        return h, direction
    if 3 <= direction < 6:
        # 反向邊：跳到鄰居那邊找對應的 0..2 slot
        return h + DIRECTIONS[direction], direction - 3
    raise ValueError(f"direction must be in [0, 6), got {direction}")


def _read_slot(rivers: int, slot: int) -> int:
    # 把對應 slot 的 8 bit 取出來。slot 0 = bits 0-7, slot 1 = bits 8-15, slot 2 = bits 16-23
    return (rivers >> (slot * RIVER_BITS)) & RIVER_MASK


def _write_slot(rivers: int, slot: int, value: int) -> int:
    # clamp 到 [0, 255]，避免溢位污染相鄰 slot 的 bit
    value = max(0, min(RIVER_MAX_STRENGTH, value))
    # 先把該 slot 清零（and ~mask），再 or 上新值
    clear = ~(RIVER_MASK << (slot * RIVER_BITS))
    return (rivers & clear) | (value << (slot * RIVER_BITS))


def get_river_strength(tile_map: TileMap, h: Hex, direction: int) -> int:
    owner, slot = _edge_owner(h, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return 0
    return _read_slot(tile.rivers, slot)


def set_river_strength(tile_map: TileMap, h: Hex, direction: int, strength: int) -> None:
    owner, slot = _edge_owner(h, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return
    tile.rivers = _write_slot(tile.rivers, slot, strength)


def add_river_flow(tile_map: TileMap, h: Hex, direction: int, amount: int = 1) -> None:
    """在指定邊上累加流量；上限 RIVER_MAX_STRENGTH (255)。"""
    owner, slot = _edge_owner(h, direction)
    tile = tile_map.get(owner)
    if tile is None:
        return
    cur = _read_slot(tile.rivers, slot)
    tile.rivers = _write_slot(tile.rivers, slot, cur + amount)


def has_river_edge(tile_map: TileMap, h: Hex, direction: int) -> bool:
    return get_river_strength(tile_map, h, direction) > 0


def set_river_edge(tile_map: TileMap, h: Hex, direction: int, value: bool = True) -> None:
    """設邊上有/無河流（強度 1 或 0）。要設特定流量請用 set_river_strength。"""
    set_river_strength(tile_map, h, direction, 1 if value else 0)


def iter_river_edges(tile_map: TileMap) -> Iterator[tuple[Hex, int, int]]:
    """yield 出地圖上所有有河流的 (origin_hex, direction, strength)。

    origin_hex 永遠是 owner，direction 永遠在 0..2。strength > 0。
    """
    for h, tile in tile_map:
        if not tile.rivers:
            continue
        for slot in range(3):
            s = _read_slot(tile.rivers, slot)
            if s > 0:
                yield h, slot, s


def _is_water(t: TerrainType) -> bool:
    return t in WATER


# ---------------------------------------------------------------------------
# RimWorld 風生成
# ---------------------------------------------------------------------------

def _elevation_change_cost(delta: float) -> float:
    """對齊 WorldGenStep_Rivers.cs:22-30 的 ElevationChangeCost SimpleCurve。

    RW 原 curve key: [-1000, -100, 0, 0, 100, 1000] → [50, 100, 400, 5000, 50000, 50000]
    我們的 heightmap 是 0~1 → delta 也是 [-1, 1]，把 curve 縮 1000 倍。

    delta = elev(下游) − elev(上游)：
      delta < 0 → 下游較低（自然下流），cost 便宜（50~400）
      delta ≥ 0 → 下游較高或等高（逆流 / 平地），cost 昂貴（5000~50000）

    0 處有跳變：對齊 RW 把同 x=0 的兩 keypoint 視為上坡端起點。
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


def _get_coastal_water_tiles(tile_map: TileMap) -> list[Hex]:
    """對齊 WorldGenStep_Rivers.cs:98-125：找所有鄰接陸地的水格。"""
    result: list[Hex] = []
    for h, tile in tile_map:
        if not _is_water(tile.terrain):
            continue
        for nb in h.neighbors():
            nb_tile = tile_map.get(nb)
            if nb_tile is not None and not _is_water(nb_tile.terrain):
                result.append(h)
                break
    return result


def _flood_paths_with_cost_for_tree(
    tile_map: TileMap,
    heightmap: list[list[float]],
    seeds: list[Hex],
) -> list[list[Optional[Hex]]]:
    """對齊 WorldGenStep_Rivers.cs:48-67 的 FloodPathsWithCostForTree。

    從多個 seed 同時 Dijkstra 反向擴張，產出每格的 parent（指向「水的去處」=下游一格）。
    cost callback: cost(st → ed) = factor × ElevationChangeCost(elev(st) − elev(ed))
                   factor = 1 若 ed 的最低鄰居就是 st，否則 2
    terminator: 非起點的水格不再擴張。
    """
    W, H = tile_map.width, tile_map.height
    inf = math.inf
    g_score: list[list[float]] = [[inf] * W for _ in range(H)]
    parent: list[list[Optional[Hex]]] = [[None] * W for _ in range(H)]
    # 用 (q, r) tuple 而非 Hex 物件做 set，因為 Hex 不可雜湊
    seed_set = {(s.q, s.r) for s in seeds}

    # 多源 Dijkstra：所有 seed 同時 g=0 入 heap，自然形成「最便宜路徑回到任一 seed」
    pq: list[tuple[float, int, int, int]] = []
    counter = 0
    for s in seeds:
        g_score[s.r][s.q] = 0.0
        heapq.heappush(pq, (0.0, counter, s.q, s.r))
        counter += 1

    while pq:
        g, _, q, r = heapq.heappop(pq)
        # lazy deletion：同一 hex 可能被 push 多次，跳過已被更便宜路徑更新過的
        if g > g_score[r][q]:
            continue
        cur = Hex(q, r)
        # 終止規則：非起點水格不繼續往外擴。確保 children tree 只往陸地延伸，
        # river 也只會畫在陸地內或海陸交界邊
        if (q, r) not in seed_set and _is_water(tile_map.get(cur).terrain):
            continue

        cur_elev = heightmap[r][q]
        for nb in cur.neighbors():
            if not tile_map.in_bounds(nb):
                continue
            nb_elev = heightmap[nb.r][nb.q]
            # 找 nb 的最低鄰居（對齊 WorldGenStep_Rivers.cs:52-60）
            # 這是 RW 河流自然性的關鍵：若 cur 剛好是 nb 的自然下游，factor=1（便宜）；
            # 否則 factor=2（要繞路才能流到 cur，懲罰一倍）
            lowest_elev = inf
            lowest_q = -1
            lowest_r = -1
            for nbnb in nb.neighbors():
                if not tile_map.in_bounds(nbnb):
                    continue
                ee = heightmap[nbnb.r][nbnb.q]
                if ee < lowest_elev:
                    lowest_elev = ee
                    lowest_q, lowest_r = nbnb.q, nbnb.r
            factor = 1.0 if (lowest_q == q and lowest_r == r) else 2.0
            # delta = elev(下游 cur) − elev(上游 nb)；river 從 nb 流向 cur 是自然下流時 delta < 0
            delta = cur_elev - nb_elev
            edge_cost = factor * _elevation_change_cost(delta)
            new_g = g + edge_cost
            if new_g < g_score[nb.r][nb.q]:
                g_score[nb.r][nb.q] = new_g
                # parent[nb] = cur 表示「nb 的水流向 cur」（cur 在 nb 下游一格）
                parent[nb.r][nb.q] = cur
                counter += 1
                heapq.heappush(pq, (new_g, counter, nb.q, nb.r))

    return parent


def _build_children(
    tile_map: TileMap, parent: list[list[Optional[Hex]]]
) -> list[list[list[Hex]]]:
    """把 parent map 翻成 children list（per tile，list of 上游 tiles）。"""
    W, H = tile_map.width, tile_map.height
    children: list[list[list[Hex]]] = [[[] for _ in range(W)] for _ in range(H)]
    for r in range(H):
        for q in range(W):
            par = parent[r][q]
            if par is not None:
                children[par.r][par.q].append(Hex(q, r))
    return children


def _approximate_temperature(r: int, total_h: int) -> float:
    """近似 °C：中央列（赤道）25°C，邊緣（極地）-30°C。

    Phase B 之後會被真正的 latitude curve 取代（對齊 AvgTempByLatitudeCurve）。
    """
    half = max((total_h - 1) / 2.0, 1e-9)
    lat_abs = abs(r - (total_h - 1) / 2.0) / half
    return 25.0 - 55.0 * lat_abs


def _evaporation_constant(temp_c: float) -> float:
    """對齊 WorldGenStep_Rivers.cs:192-195 (CalculateEvaporationConstant)。"""
    return (
        0.61121
        * math.exp((18.678 - temp_c / 234.5) * (temp_c / (257.14 + temp_c)))
        / (temp_c + 273.0)
    )


def _total_evaporation(flow: float, temp_c: float, scale: float) -> float:
    """對齊 WorldGenStep_Rivers.cs:207-210 (CalculateTotalEvaporation)。

    evap = evap_const(temp) × sqrt(flow) × 250 × scale
    """
    if flow <= 0:
        return 0.0
    return _evaporation_constant(temp_c) * math.sqrt(flow) * 250.0 * scale


def _accumulate_flow_from(
    flow: list[list[float]],
    children: list[list[list[Hex]]],
    root: Hex,
    rainfall: list[list[float]],
    temperature: list[list[float]],
    evap_scale: float,
) -> None:
    """對齊 WorldGenStep_Rivers.cs:127-141。

    Post-order iterative DFS（避免大地圖 stack overflow）：
    每格 flow = rainfall + Σ child.flow - evap(self_flow, temp)
    """
    # post-order iterative DFS：(node, processed) 是否已處理完所有子樹
    # 第一次 pop 時 processed=False，把自己 push 回去 (True) 再 push 所有 child；
    # child 都處理完才會輪到自己 (True) 出來累加。深度可達整片陸地，遞迴版易爆 Python 預設 1000 限制
    stack: list[tuple[Hex, bool]] = [(root, False)]
    while stack:
        cur, processed = stack.pop()
        q, r = cur.q, cur.r
        if not processed:
            stack.append((cur, True))
            for child in children[r][q]:
                stack.append((child, False))
            continue
        # 累加自己雨量 + 所有上游 flow，最後再扣自己這格的蒸發
        # 蒸發跟 sqrt(flow) 成正比（水面積 ∝ sqrt(volume)），跟溫度的指數函式成正比
        flow[r][q] += rainfall[r][q]
        for child in children[r][q]:
            flow[r][q] += flow[child.r][child.q]
        evap = _total_evaporation(flow[r][q], temperature[r][q], evap_scale)
        flow[r][q] = max(0.0, flow[r][q] - evap)


def _hex_direction(a: Hex, b: Hex) -> Optional[int]:
    """a 與 b 鄰接時回傳 a → b 的方向（0..5），否則 None。"""
    delta = b - a
    for d, dh in enumerate(DIRECTIONS):
        if dh == delta:
            return d
    return None


def _paint_edge(tile_map: TileMap, cur: Hex, direction: int, flow_value: float, scale: float) -> None:
    strength = max(1, min(RIVER_MAX_STRENGTH, int(flow_value * scale)))
    add_river_flow(tile_map, cur, direction, strength)


def _create_rivers_from_seed(
    tile_map: TileMap,
    flow: list[list[float]],
    children: list[list[list[Hex]]],
    seed: Hex,
    spawn_flow_threshold: float,
    degrade_threshold: float,
    branch_flow_threshold: float,
    branch_chance: float,
    flow_strength_scale: float,
    rng: random.Random,
) -> int:
    """對齊 WorldGenStep_Rivers.cs:143-190 的 CreateRivers + ExtendRiver（合併迭代版）。"""
    painted = 0
    # 從 seed 的每個 children（不同入海口）獨立啟動一條河
    # 一個 coastal seed 可能有多個 children = 多條河流入海，各自獨立發河
    for first_child in children[seed.r][seed.q]:
        cf = flow[first_child.r][first_child.q]
        # 入海口流量不夠 spawn 門檻就跳過；這控制了「多大的雨量才算一條河」
        if cf < spawn_flow_threshold:
            continue
        d = _hex_direction(seed, first_child)
        if d is None:
            continue
        _paint_edge(tile_map, seed, d, cf, flow_strength_scale)
        painted += 1

        # 沿樹往上游延伸：每個 tile 從 children 中挑「最大 flow」當主流，其餘按機率分支
        # 用 stack 而非遞迴，配合 sorted children 確保結果跟 RW ExtendRiver 一致
        stack: list[Hex] = [first_child]
        while stack:
            cur = stack.pop()
            kids = children[cur.r][cur.q]
            if not kids:
                continue
            kids_sorted = sorted(kids, key=lambda k: flow[k.r][k.q], reverse=True)
            best = kids_sorted[0]
            best_flow = flow[best.r][best.q]
            # 主流：跟著最大 flow child 往上，直到 flow 降到 degrade 門檻以下就停
            # （對齊 RW degradeChild：大河往源頭走會逐級降階成 Creek 再消失）
            if best_flow >= degrade_threshold:
                bd = _hex_direction(cur, best)
                if bd is not None:
                    _paint_edge(tile_map, cur, bd, best_flow, flow_strength_scale)
                    painted += 1
                stack.append(best)
            # 分支：其他 children 中 flow ≥ branch 門檻者，按機率隨機分出去
            # 這對應現實裡同個 tile 可能同時有兩條溪匯入，但不是必然發生
            for alt in kids_sorted[1:]:
                af = flow[alt.r][alt.q]
                if af < branch_flow_threshold:
                    continue
                if rng.random() >= branch_chance:
                    continue
                ad = _hex_direction(cur, alt)
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
) -> int:
    """RimWorld 風河流生成（對齊 projects/rimworld/.../WorldGenStep_Rivers.cs:30-210）。

    流程：
      1. 找 coastal water tiles 當作 seeds
      2. 反向 Dijkstra 建下游樹（cost = ElevationChangeCost × factor）
      3. DFS 累加 rainfall − evaporation 得到每格 flow
      4. 從每個 seed 走樹：主流走最大 flow child（flow ≥ degrade_threshold），
         其餘 children 中 flow ≥ branch_flow_threshold 者按 branch_chance 分支

    參數：
      heightmap[r][q]        高程 0~1
      rainfall[r][q]         降雨（任意單位，常用 moisture 0~1 配合 rainfall_scale）
      rainfall_scale         把 rainfall 乘上的 scale；moisture 0~1 建議 800~1500
      spawn_flow_threshold   coastal seed 鄰居要 ≥ 此 flow 才生河（≈mm rainfall 累計）
      degrade_threshold      主流流量降到此值以下就停（對應 RW degradeChild）
      branch_flow_threshold  分支需要的最小 flow
      branch_chance          分支機率（0~1）
      flow_strength_scale    flow → 0~255 strength 的比例（畫面寬度直接受影響）
      evaporation_scale      蒸發整體強度倍率

    回傳：標記的河流邊數量（不去重，多源匯流時同條邊會被多次 add_river_flow 累加流量）。
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

    parent = _flood_paths_with_cost_for_tree(tile_map, heightmap, seeds)
    children = _build_children(tile_map, parent)

    if temperature is None:
        # 沒給 temperature 時用近似（中央列赤道 25°C，邊緣極地 -30°C）
        temperature = [[_approximate_temperature(r, H)] * W for r in range(H)]
    elif len(temperature) != H or any(len(row) != W for row in temperature):
        raise ValueError("temperature shape must match tile_map (height, width)")
    rainfall_scaled: list[list[float]] = [
        [rainfall[r][q] * rainfall_scale for q in range(W)] for r in range(H)
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
