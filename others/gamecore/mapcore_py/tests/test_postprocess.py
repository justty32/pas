import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.postprocess import (
    find_components,
    is_land,
    is_water,
    post_process,
    relabel_coast,
    remove_small_islands,
    remove_small_lakes,
)
from mapcore.hex import Hex
from mapcore.map import TerrainType, TileMap


def _fill(tile_map: TileMap, terrain: TerrainType, hexes: list[tuple[int, int]]) -> None:
    for q, r in hexes:
        tile_map.set_terrain(Hex(q, r), terrain)


class TestFindComponents(unittest.TestCase):
    def test_single_component(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.PLAINS)
        comps = find_components(tm, is_land)
        self.assertEqual(len(comps), 1)
        self.assertEqual(len(comps[0]), 25)

    def test_two_separate_lands(self):
        # 整片海，中間用一整列 PLAINS 分成兩塊？不，axial 鄰居會穿過水。
        # 簡單做法：在全海地圖上放兩個不相鄰的單點陸地。
        tm = TileMap(7, 7, default_terrain=TerrainType.OCEAN)
        tm.set_terrain(Hex(0, 0), TerrainType.PLAINS)
        tm.set_terrain(Hex(6, 6), TerrainType.PLAINS)
        comps = find_components(tm, is_land)
        self.assertEqual(len(comps), 2)
        self.assertEqual({len(c) for c in comps}, {1})

    def test_no_components(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.OCEAN)
        self.assertEqual(find_components(tm, is_land), [])

    def test_water_components(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.PLAINS)
        tm.set_terrain(Hex(2, 2), TerrainType.OCEAN)
        comps = find_components(tm, is_water)
        self.assertEqual(len(comps), 1)
        self.assertEqual(comps[0], [Hex(2, 2)])


class TestRemoveSmallIslands(unittest.TestCase):
    def test_removes_single_tile_island(self):
        tm = TileMap(7, 7, default_terrain=TerrainType.OCEAN)
        tm.set_terrain(Hex(3, 3), TerrainType.PLAINS)
        removed = remove_small_islands(tm, min_size=3)
        self.assertEqual(removed, 1)
        self.assertEqual(tm.get(Hex(3, 3)).terrain, TerrainType.OCEAN)

    def test_keeps_large_island(self):
        tm = TileMap(7, 7, default_terrain=TerrainType.OCEAN)
        # 5 格相連的陸地
        for q, r in [(3, 3), (4, 3), (2, 3), (3, 2), (3, 4)]:
            tm.set_terrain(Hex(q, r), TerrainType.PLAINS)
        removed = remove_small_islands(tm, min_size=3)
        self.assertEqual(removed, 0)
        for q, r in [(3, 3), (4, 3), (2, 3), (3, 2), (3, 4)]:
            self.assertEqual(tm.get(Hex(q, r)).terrain, TerrainType.PLAINS)

    def test_min_size_one_is_noop(self):
        tm = TileMap(3, 3, default_terrain=TerrainType.OCEAN)
        tm.set_terrain(Hex(1, 1), TerrainType.PLAINS)
        self.assertEqual(remove_small_islands(tm, min_size=1), 0)
        self.assertEqual(tm.get(Hex(1, 1)).terrain, TerrainType.PLAINS)


class TestRemoveSmallLakes(unittest.TestCase):
    def test_interior_lake_filled(self):
        tm = TileMap(7, 7, default_terrain=TerrainType.PLAINS)
        tm.set_terrain(Hex(3, 3), TerrainType.OCEAN)  # 內陸 1 格湖
        filled = remove_small_lakes(tm, max_size=4)
        self.assertEqual(filled, 1)
        self.assertEqual(tm.get(Hex(3, 3)).terrain, TerrainType.PLAINS)

    def test_edge_water_not_filled(self):
        tm = TileMap(7, 7, default_terrain=TerrainType.PLAINS)
        tm.set_terrain(Hex(0, 0), TerrainType.OCEAN)  # 接邊界
        filled = remove_small_lakes(tm, max_size=4)
        self.assertEqual(filled, 0)
        self.assertEqual(tm.get(Hex(0, 0)).terrain, TerrainType.OCEAN)

    def test_large_lake_not_filled(self):
        tm = TileMap(9, 9, default_terrain=TerrainType.PLAINS)
        # 5 格相連的內陸湖 > max_size=4
        for q, r in [(4, 4), (5, 4), (3, 4), (4, 3), (4, 5)]:
            tm.set_terrain(Hex(q, r), TerrainType.OCEAN)
        filled = remove_small_lakes(tm, max_size=4)
        self.assertEqual(filled, 0)

    def test_custom_fill(self):
        tm = TileMap(7, 7, default_terrain=TerrainType.PLAINS)
        tm.set_terrain(Hex(3, 3), TerrainType.OCEAN)
        remove_small_lakes(tm, max_size=4, fill=TerrainType.DESERT)
        self.assertEqual(tm.get(Hex(3, 3)).terrain, TerrainType.DESERT)


class TestRelabelCoast(unittest.TestCase):
    def test_relabel_resets_then_expands(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.OCEAN)
        # 中央陸地
        tm.set_terrain(Hex(2, 2), TerrainType.PLAINS)
        # 沒有任何 COAST → 跑 relabel 應該標出 6 個 COAST
        relabel_coast(tm, coast_depth=1)
        coast_count = sum(1 for _, t in tm if t.terrain == TerrainType.COAST)
        self.assertEqual(coast_count, 6)

    def test_relabel_clears_stale_coast(self):
        tm = TileMap(5, 5, default_terrain=TerrainType.OCEAN)
        # 在沒有陸地的情況下手動設一格 COAST → relabel 後應變回 OCEAN
        tm.set_terrain(Hex(2, 2), TerrainType.COAST)
        relabel_coast(tm, coast_depth=1)
        self.assertEqual(tm.get(Hex(2, 2)).terrain, TerrainType.OCEAN)


class TestPostProcessIntegration(unittest.TestCase):
    def test_runs_full_pipeline(self):
        tm = TileMap(9, 9, default_terrain=TerrainType.OCEAN)
        tm.set_terrain(Hex(0, 0), TerrainType.PLAINS)  # 1 格小島 → 會被清掉
        tm.set_terrain(Hex(4, 4), TerrainType.PLAINS)
        tm.set_terrain(Hex(5, 4), TerrainType.PLAINS)
        tm.set_terrain(Hex(4, 5), TerrainType.PLAINS)  # 3 格陸地 → 保留
        stats = post_process(tm, island_min_size=3, lake_max_size=4, coast_depth=1)
        self.assertEqual(stats["islands_removed"], 1)
        self.assertEqual(tm.get(Hex(0, 0)).terrain, TerrainType.OCEAN)
        # 保留的陸地仍在
        self.assertEqual(tm.get(Hex(4, 4)).terrain, TerrainType.PLAINS)
        # 附近格子應該有 COAST
        coast_count = sum(1 for _, t in tm if t.terrain == TerrainType.COAST)
        self.assertGreater(coast_count, 0)

    def test_pipeline_deterministic_with_postprocess(self):
        from mapcore.generation.pipeline import generate_world
        a, _, _ = generate_world(20, 15, seed=42, post_process=True)
        b, _, _ = generate_world(20, 15, seed=42, post_process=True)
        terrains_a = [t.terrain for _, t in a]
        terrains_b = [t.terrain for _, t in b]
        self.assertEqual(terrains_a, terrains_b)

    def test_pipeline_post_process_off_vs_on(self):
        from mapcore.generation.pipeline import generate_world
        raw, _, _ = generate_world(30, 20, seed=42, post_process=False)
        clean, _, _ = generate_world(30, 20, seed=42, post_process=True)
        # post-process 後，小於 island_min_size 的陸地應該不存在了
        from mapcore.generation.postprocess import find_components, is_land
        for comp in find_components(clean, is_land):
            self.assertGreaterEqual(len(comp), 3)


if __name__ == "__main__":
    unittest.main()
