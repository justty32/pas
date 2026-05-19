"""地形定義 (TerrainDef) 與登錄系統 (TerrainRegistry)。

與 mapcore_py/mapcore/terrain.py 完全相同；地形系統與拓樸無關，直接共用。
保留為獨立檔案而非從 hex 版 import，是為了讓 mapcore_py_square 套件能脫離 hex 版獨立使用。

詳細設計請見 mapcore_py 版 terrain.py 的 docstring。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class TerrainDef:
    id: int
    name: str
    move_cost: float
    is_water: bool
    tags: frozenset[str] = field(default_factory=frozenset)


class TerrainRegistry:
    """TerrainDef 的雙索引容器（id / name）。"""

    def __init__(self) -> None:
        self._by_id: dict[int, TerrainDef] = {}
        self._by_name: dict[str, TerrainDef] = {}

    def register(self, defn: TerrainDef) -> None:
        if defn.id in self._by_id:
            raise ValueError(
                f"TerrainDef id={defn.id} already registered as {self._by_id[defn.id].name!r}"
            )
        if defn.name in self._by_name:
            raise ValueError(
                f"TerrainDef name={defn.name!r} already registered with id={self._by_name[defn.name].id}"
            )
        self._by_id[defn.id] = defn
        self._by_name[defn.name] = defn

    def get(self, terrain_id: int) -> TerrainDef:
        try:
            return self._by_id[terrain_id]
        except KeyError:
            raise KeyError(f"No TerrainDef with id={terrain_id}")

    def get_by_name(self, name: str) -> TerrainDef:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"No TerrainDef with name={name!r}")

    def contains(self, terrain_id: int) -> bool:
        return terrain_id in self._by_id

    def move_cost(self, terrain_id: int) -> float:
        return self._by_id[terrain_id].move_cost

    def is_passable(self, terrain_id: int) -> bool:
        return math.isfinite(self._by_id[terrain_id].move_cost)

    def is_water(self, terrain_id: int) -> bool:
        return self._by_id[terrain_id].is_water

    def has_tag(self, terrain_id: int, tag: str) -> bool:
        defn = self._by_id.get(terrain_id)
        return defn is not None and tag in defn.tags

    def all_defs(self) -> Iterable[TerrainDef]:
        return self._by_id.values()

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"TerrainRegistry({len(self)} defs)"


def gen_default(registry: TerrainRegistry | None = None) -> TerrainRegistry:
    """建立含內建地形（id 0-10）的 TerrainRegistry 並回傳。

    id 與 mapcore_py 的 hex 版保持完全一致，方便地形定義跨版本共用。
    衍生地形請從 id=100 起自行分配。
    """
    if registry is None:
        registry = TerrainRegistry()

    _builtin: list[TerrainDef] = [
        TerrainDef(0,  "OCEAN",     math.inf, True,  frozenset({"water", "ocean"})),
        TerrainDef(1,  "COAST",     math.inf, True,  frozenset({"water", "coast"})),
        TerrainDef(2,  "PLAINS",    1.0,      False, frozenset({"land", "plains"})),
        TerrainDef(3,  "GRASSLAND", 1.0,      False, frozenset({"land", "grassland"})),
        TerrainDef(4,  "DESERT",    1.5,      False, frozenset({"land", "desert"})),
        TerrainDef(5,  "TUNDRA",    1.0,      False, frozenset({"land", "tundra"})),
        TerrainDef(6,  "SNOW",      2.0,      False, frozenset({"land", "snow"})),
        TerrainDef(7,  "FOREST",    2.0,      False, frozenset({"land", "forest"})),
        TerrainDef(8,  "HILL",      2.0,      False, frozenset({"land", "hill"})),
        TerrainDef(9,  "MOUNTAIN",  math.inf, False, frozenset({"land", "mountain"})),
        TerrainDef(10, "LAKE",      math.inf, True,  frozenset({"water", "lake"})),
    ]
    for d in _builtin:
        registry.register(d)
    return registry


DEFAULT_REGISTRY: TerrainRegistry = gen_default()
