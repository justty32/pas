import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.hex import DIRECTIONS, Hex
from mapcore.map import TerrainType, TileMap
from mapcore.pathfinding import astar, path_cost
from mapcore.rivers import (
    EDGE_CORNERS,
    RIVER_MAX_STRENGTH,
    add_river_flow,
    generate_rivers,
    get_river_strength,
    has_river_edge,
    iter_river_edges,
    set_river_edge,
    set_river_strength,
)


class TestEdgeOwnership(unittest.TestCase):
    def test_set_then_query_all_directions(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.PLAINS)
        h = Hex(2, 2)
        for d in range(6):
            set_river_edge(tm, h, d, True)
            self.assertTrue(has_river_edge(tm, h, d))

    def test_symmetry_between_neighbors(self):
        # 從 A 看方向 d 的邊 = 從鄰居 B 看方向 (d+3) % 6 的邊
        tm = TileMap(5, 5, default_terrain=TerrainType.PLAINS)
        a = Hex(2, 2)
        for d in range(6):
            b = a + DIRECTIONS[d]
            set_river_edge(tm, a, d, True)
            opp = (d + 3) % 6
            self.assertTrue(has_river_edge(tm, b, opp))
            # 清掉後對面查到的也應為 False
            set_river_edge(tm, a, d, False)
            self.assertFalse(has_river_edge(tm, b, opp))

    def test_edge_corners_table_has_six_unique_pairs(self):
        self.assertEqual(len(EDGE_CORNERS), 6)
        # 每組 (a, b) 兩端不同；6 組合起來應該覆蓋所有 corner pair
        seen = set()
        for a, b in EDGE_CORNERS:
            self.assertNotEqual(a, b)
            pair = tuple(sorted((a, b)))
            self.assertNotIn(pair, seen)
            seen.add(pair)

    def test_query_out_of_bounds(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        # 在地圖外的格子查河流 → False
        self.assertFalse(has_river_edge(tm, Hex(99, 99), 0))
        # owner 在地圖外的邊（d=3/4/5 指向 OOB 鄰居）→ 設值靜默忽略、查值為 False
        # 從 (0, 0) 看 d=3 (W)，owner 是 (-1, 0) OOB
        set_river_edge(tm, Hex(0, 0), 3, True)
        self.assertFalse(has_river_edge(tm, Hex(0, 0), 3))


class TestIterRiverEdges(unittest.TestCase):
    def test_iter_yields_only_set_edges(self):
        tm = TileMap(4, 4, default_terrain=TerrainType.PLAINS)
        set_river_edge(tm, Hex(1, 1), 0, True)
        set_river_edge(tm, Hex(2, 1), 1, True)
        edges = list(iter_river_edges(tm))
        self.assertEqual(len(edges), 2)
        for h, d, s in edges:
            self.assertGreater(s, 0)

    def test_only_canonical_owners_yielded(self):
        # 設一條 d=4 (SW) 的邊，但 iter 應該從鄰居 (d=1, NE) 那邊 yield 出來
        tm = TileMap(4, 4, default_terrain=TerrainType.PLAINS)
        set_river_edge(tm, Hex(2, 2), 4, True)
        edges = list(iter_river_edges(tm))
        self.assertEqual(len(edges), 1)
        h, d, s = edges[0]
        self.assertLess(d, 3)
        self.assertEqual(s, 1)


class TestRiverStrength(unittest.TestCase):
    def test_add_flow_accumulates(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        add_river_flow(tm, Hex(1, 1), 0, 1)
        add_river_flow(tm, Hex(1, 1), 0, 3)
        self.assertEqual(get_river_strength(tm, Hex(1, 1), 0), 4)

    def test_strength_clamped_to_max(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        add_river_flow(tm, Hex(1, 1), 0, 1000)
        self.assertEqual(get_river_strength(tm, Hex(1, 1), 0), RIVER_MAX_STRENGTH)

    def test_set_strength_overwrites(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        add_river_flow(tm, Hex(1, 1), 0, 5)
        set_river_strength(tm, Hex(1, 1), 0, 2)
        self.assertEqual(get_river_strength(tm, Hex(1, 1), 0), 2)

    def test_slots_independent(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        set_river_strength(tm, Hex(1, 1), 0, 7)
        set_river_strength(tm, Hex(1, 1), 1, 50)
        set_river_strength(tm, Hex(1, 1), 2, 200)
        self.assertEqual(get_river_strength(tm, Hex(1, 1), 0), 7)
        self.assertEqual(get_river_strength(tm, Hex(1, 1), 1), 50)
        self.assertEqual(get_river_strength(tm, Hex(1, 1), 2), 200)

    def test_strength_visible_from_neighbor(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        set_river_strength(tm, Hex(1, 1), 0, 42)
        # d=3 是反向 (W)，鄰居應該也看到強度 42
        self.assertEqual(get_river_strength(tm, Hex(2, 1), 3), 42)

    def test_has_river_edge_truthiness(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        self.assertFalse(has_river_edge(tm, Hex(1, 1), 0))
        set_river_strength(tm, Hex(1, 1), 0, 1)
        self.assertTrue(has_river_edge(tm, Hex(1, 1), 0))
        set_river_strength(tm, Hex(1, 1), 0, 0)
        self.assertFalse(has_river_edge(tm, Hex(1, 1), 0))


class TestRiverConfluence(unittest.TestCase):
    def test_shared_downstream_accumulates(self):
        # 構造兩條從不同源頭流向同一條主流的拓撲：
        # 高程 layout (q, r 對應 axial)：
        #   兩個源頭 (0, 0) 與 (4, 0) 高度都是 0.9
        #   中間 (2, 0) 高度 0.5
        #   r=1 全是 0.3，r=2 是海
        # 兩個源頭都會往低處走，最終會匯入同一條下游
        tm = TileMap(5, 3, default_terrain=TerrainType.PLAINS)
        for q in range(5):
            tm.set_terrain(Hex(q, 2), TerrainType.OCEAN)
        hm = [
            [0.9, 0.7, 0.5, 0.7, 0.9],
            [0.3, 0.3, 0.3, 0.3, 0.3],
            [0.0, 0.0, 0.0, 0.0, 0.0],
        ]
        # 強制兩個源頭都成為實際源頭：threshold 設低一點，density=1
        generate_rivers(
            tm, hm,
            seed=1, source_threshold=0.7, source_density=1.0,
            min_river_length=1,
        )
        # 任何流量 >= 2 的邊代表那邊被兩條河共用過
        max_flow = max((s for _, _, s in iter_river_edges(tm)), default=0)
        self.assertGreaterEqual(max_flow, 2)


class TestGenerateRivers(unittest.TestCase):
    def test_no_rivers_when_density_zero(self):
        tm = TileMap(8, 8, default_terrain=TerrainType.PLAINS)
        hm = [[r / 7.0 for q in range(8)] for r in range(8)]
        n = generate_rivers(tm, hm, seed=0, source_density=0.0)
        self.assertEqual(n, 0)
        self.assertEqual(list(iter_river_edges(tm)), [])

    def test_river_terminates_at_water(self):
        # 8x8：r=0 整列是海，其他是陸地；高程隨 r 遞增 → 河流會從高 r 一路往低 r 流到海
        tm = TileMap(8, 8, default_terrain=TerrainType.PLAINS)
        for q in range(8):
            tm.set_terrain(Hex(q, 0), TerrainType.OCEAN)
        hm = [[r / 7.0 for q in range(8)] for r in range(8)]
        # 強制把所有候選都當源頭
        generate_rivers(tm, hm, seed=1, source_threshold=0.5, source_density=1.0)
        # 至少要有河流邊存在
        self.assertGreater(len(list(iter_river_edges(tm))), 0)
        # 不會在水格上新增離開水的邊（OCEAN 不會被當源頭）

    def test_deterministic(self):
        tm_a = TileMap(10, 10, default_terrain=TerrainType.PLAINS)
        tm_b = TileMap(10, 10, default_terrain=TerrainType.PLAINS)
        hm = [[r * 0.1 + q * 0.05 for q in range(10)] for r in range(10)]
        # 加一格海作為終點
        tm_a.set_terrain(Hex(0, 0), TerrainType.OCEAN)
        tm_b.set_terrain(Hex(0, 0), TerrainType.OCEAN)
        generate_rivers(tm_a, hm, seed=7, source_threshold=0.5, source_density=0.5)
        generate_rivers(tm_b, hm, seed=7, source_threshold=0.5, source_density=0.5)
        self.assertEqual(list(iter_river_edges(tm_a)), list(iter_river_edges(tm_b)))

    def test_min_length_rejects_short(self):
        # 一格高、四周低 → 河流最多走 1 邊就到水
        tm = TileMap(5, 5, default_terrain=TerrainType.OCEAN)
        tm.set_terrain(Hex(2, 2), TerrainType.PLAINS)
        hm = [[0.1] * 5 for _ in range(5)]
        hm[2][2] = 0.9
        n = generate_rivers(
            tm, hm,
            seed=1, source_threshold=0.5, source_density=1.0,
            min_river_length=5,
        )
        self.assertEqual(n, 0)

    def test_param_validation(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.PLAINS)
        hm = [[0.5] * 3 for _ in range(3)]
        with self.assertRaises(ValueError):
            generate_rivers(tm, hm, source_density=-0.1)
        with self.assertRaises(ValueError):
            generate_rivers(tm, hm, source_density=1.5)
        with self.assertRaises(ValueError):
            generate_rivers(tm, hm, min_river_length=0)


class TestAstarWithRivers(unittest.TestCase):
    def test_river_crossing_cost_avoided(self):
        # 5x1 平原，中央 (2,0)→(3,0) 之間有河流
        tm = TileMap(5, 3, default_terrain=TerrainType.PLAINS)
        set_river_edge(tm, Hex(2, 1), 0, True)  # (2,1) 向東 → (3,1)
        # 不加跨河成本：直線最短 = 4 步
        path_a = astar(tm, Hex(0, 1), Hex(4, 1))
        self.assertEqual(len(path_a) - 1, 4)
        # 加大量跨河成本：A* 應該找替代路徑（繞道更便宜）
        path_b = astar(tm, Hex(0, 1), Hex(4, 1), river_crossing_cost=100.0)
        cost_b = path_cost(tm, path_b)
        # 沒被河流懲罰擊中（成本不該包含 100）
        self.assertLess(cost_b, 50)

    def test_inf_river_crossing_blocks(self):
        # 用 inf 跨河，南北兩排陸地中間一條河（橫切）
        # 5x3 全陸地，r=1 整列向 r=2 的邊都是河
        tm = TileMap(5, 3, default_terrain=TerrainType.PLAINS)
        for q in range(5):
            set_river_edge(tm, Hex(q, 1), 5, True)  # SE direction → 連到 r=2
        # 啟用 inf 跨河 — 但其他方向 (SW, d=4) 也跨越同一條河帶嗎？
        # axial 中 r=1→r=2 走 d=5 (0,1) 或 d=4 (-1,1)。
        # 為了完整封路，連 d=4 也要設河。
        for q in range(5):
            set_river_edge(tm, Hex(q, 1), 4, True)
        path = astar(tm, Hex(2, 0), Hex(2, 2), river_crossing_cost=math.inf)
        # 不可能跨過去
        self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main()
