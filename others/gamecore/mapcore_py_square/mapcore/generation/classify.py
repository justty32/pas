"""海平面切割 (Phase 2)。

把高程陣列轉成 TileMap：
- height <= sea_level：OCEAN
- height >  sea_level：PLAINS（陸地細分留 Phase 3 生物群系做）

接著做 coast_depth 圈的 BFS 擴張：每一圈把「OCEAN 但至少有一個非 OCEAN 鄰居」改為
COAST。第二圈起 COAST 本身就算非 OCEAN，所以海岸會自然向外加深。

對齊 mapcore_py 的 hex 版 generation/classify.py；本檔僅把 Hex(q,r) 換成 Coord(x,y)、
6 鄰居換成 4 鄰居。
"""

from __future__ import annotations

from ..grid import Coord
from ..map import TerrainType, TileMap


def heightmap_to_tilemap(
    heightmap: list[list[float]],
    sea_level: float = 0.4,
    coast_depth: int = 1,
) -> TileMap:
    """以 sea_level 切割 heightmap，回傳含 OCEAN / COAST / PLAINS 的 TileMap。

    coast_depth：海岸向海延伸的圈數。
    - 0：只有 OCEAN / PLAINS，沒有 COAST。
    - 1（預設）：只有緊貼陸地的那一圈海是 COAST。
    - 2、3 …：更寬的淺海帶。
    """
    if not heightmap or not heightmap[0]:
        raise ValueError("heightmap must be non-empty")
    height = len(heightmap)
    width = len(heightmap[0])
    for row in heightmap:
        if len(row) != width:
            raise ValueError("heightmap rows must all be the same length")
    if not 0.0 <= sea_level <= 1.0:
        raise ValueError(f"sea_level must be in [0, 1], got {sea_level}")
    if coast_depth < 0:
        raise ValueError(f"coast_depth must be >= 0, got {coast_depth}")

    tile_map = TileMap(width, height, default_terrain=TerrainType.PLAINS)

    for y in range(height):
        for x in range(width):
            if heightmap[y][x] <= sea_level:
                tile = tile_map._rows[y][x]
                tile.terrain = TerrainType.OCEAN
                tile.water_depth = sea_level - heightmap[y][x]

    expand_coast(tile_map, coast_depth)
    return tile_map


def expand_coast(tile_map: TileMap, coast_depth: int) -> None:
    """從現有 OCEAN 出發擴張 coast_depth 圈 COAST。

    每輪把「OCEAN 且鄰接非 OCEAN」的格子改成 COAST。COAST 在下一輪會被視為非 OCEAN，
    所以海岸自然向外擴張。給 Phase 2 與 Phase 4 (relabel_coast) 共用。
    """
    if coast_depth < 0:
        raise ValueError(f"coast_depth must be >= 0, got {coast_depth}")
    # 兩 pass（先收集再改）：邊掃邊改會讓本輪剛變 COAST 的格子立刻被當作「非 OCEAN」，
    # 導致同輪內擴張失控，一次吃掉整片海。
    for _ in range(coast_depth):
        to_coast: list[Coord] = []
        for y in range(tile_map.height):
            for x in range(tile_map.width):
                c = Coord(x, y)
                if tile_map.get(c).terrain != TerrainType.OCEAN:
                    continue
                for n in tile_map.neighbors(c):
                    if tile_map.get(n).terrain != TerrainType.OCEAN:
                        to_coast.append(c)
                        break
        if not to_coast:
            return
        for c in to_coast:
            tile_map.set_terrain(c, TerrainType.COAST)
