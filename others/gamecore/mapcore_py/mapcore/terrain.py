"""地形定義 (TerrainDef) 與登錄系統 (TerrainRegistry)。

設計對齊 RimWorld 的平坦 TerrainDef + DefDatabase 模式：
- TerrainDef 是純資料 dataclass，沒有繼承關係；繼承是使用者自己建構 def 時的責任
- TerrainRegistry 以 id (int) 與 name (str) 雙索引；對應 C++ 側的 std::unordered_map
- gen_default() 把內建 TerrainType（id 0-9）填入一個新的 TerrainRegistry 並回傳
- DEFAULT_REGISTRY 在模組載入時由 gen_default() 建立，是全域預設登錄表
- 衍生地形從 ID 100 起，避免與內建地形 id 衝突；呼叫 registry.register() 自行加入

C++ 移植備注：
  TerrainDef → POD struct（id: uint16_t, name: std::string_view, move_cost: float,
                           is_water: bool, tags: uint32_t bitmask 或 std::vector<std::string>）
  TerrainRegistry → std::unordered_map<uint16_t, TerrainDef*> + std::unordered_map<std::string, TerrainDef*>
  DEFAULT_REGISTRY → 全域單例或 GameState 持有的成員
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class TerrainDef:
    """單一地形類型的完整描述；平坦結構，無繼承。

    id 和 name 必須在同一個 TerrainRegistry 內唯一。
    move_cost：進入該格的移動成本，math.inf 代表不可通行。
    is_water：是否屬於水域；取代過去 terrain <= COAST 的隱式假設。
    tags：分類用字串集合，對齊 RimWorld TerrainDef.tags / HasTag()。
          例：{"water", "ocean"} / {"land", "forest", "passable"}
    """
    id: int
    name: str
    move_cost: float
    is_water: bool
    tags: frozenset[str] = field(default_factory=frozenset)


class TerrainRegistry:
    """TerrainDef 的雙索引容器（id / name）。

    同一個 id 或 name 不可重複登錄；重複時拋 ValueError。
    對齊 RimWorld DefDatabase<TerrainDef> 的查詢介面。
    """

    def __init__(self) -> None:
        self._by_id: dict[int, TerrainDef] = {}
        self._by_name: dict[str, TerrainDef] = {}

    # ------------------------------------------------------------------
    # 登錄
    # ------------------------------------------------------------------

    def register(self, defn: TerrainDef) -> None:
        """登錄一個 TerrainDef；id 與 name 不可與已登錄者重複。"""
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

    # ------------------------------------------------------------------
    # 查詢
    # ------------------------------------------------------------------

    def get(self, terrain_id: int) -> TerrainDef:
        """依 id 查詢；找不到拋 KeyError。"""
        try:
            return self._by_id[terrain_id]
        except KeyError:
            raise KeyError(f"No TerrainDef with id={terrain_id}")

    def get_by_name(self, name: str) -> TerrainDef:
        """依 name 查詢；找不到拋 KeyError。"""
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"No TerrainDef with name={name!r}")

    def contains(self, terrain_id: int) -> bool:
        return terrain_id in self._by_id

    # ------------------------------------------------------------------
    # 常用屬性快捷
    # ------------------------------------------------------------------

    def move_cost(self, terrain_id: int) -> float:
        return self._by_id[terrain_id].move_cost

    def is_passable(self, terrain_id: int) -> bool:
        return math.isfinite(self._by_id[terrain_id].move_cost)

    def is_water(self, terrain_id: int) -> bool:
        return self._by_id[terrain_id].is_water

    def has_tag(self, terrain_id: int, tag: str) -> bool:
        defn = self._by_id.get(terrain_id)
        return defn is not None and tag in defn.tags

    # ------------------------------------------------------------------
    # 遍歷
    # ------------------------------------------------------------------

    def all_defs(self) -> Iterable[TerrainDef]:
        return self._by_id.values()

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"TerrainRegistry({len(self)} defs)"


# ---------------------------------------------------------------------------
# 內建地形登錄
# ---------------------------------------------------------------------------

def gen_default(registry: TerrainRegistry | None = None) -> TerrainRegistry:
    """建立含內建地形（id 0-9）的 TerrainRegistry 並回傳。

    registry=None（預設）：建立一個新的 TerrainRegistry，填入內建地形後回傳。
    傳入 registry：把內建地形填進去（適用於想在同一個 registry 上追加的情況；
                   若 id 0-9 已存在會拋 ValueError）。

    內建地形 id 對應 map.TerrainType IntEnum，數值保持不變（0-9）。
    衍生地形請從 id=100 起自行分配，避免衝突。
    """
    if registry is None:
        registry = TerrainRegistry()

    _builtin: list[TerrainDef] = [
        TerrainDef(0, "OCEAN",     math.inf, True,  frozenset({"water", "ocean"})),
        TerrainDef(1, "COAST",     math.inf, True,  frozenset({"water", "coast"})),
        TerrainDef(2, "PLAINS",    1.0,      False, frozenset({"land", "plains"})),
        TerrainDef(3, "GRASSLAND", 1.0,      False, frozenset({"land", "grassland"})),
        TerrainDef(4, "DESERT",    1.5,      False, frozenset({"land", "desert"})),
        TerrainDef(5, "TUNDRA",    1.0,      False, frozenset({"land", "tundra"})),
        TerrainDef(6, "SNOW",      2.0,      False, frozenset({"land", "snow"})),
        TerrainDef(7, "FOREST",    2.0,      False, frozenset({"land", "forest"})),
        TerrainDef(8, "HILL",      2.0,      False, frozenset({"land", "hill"})),
        TerrainDef(9,  "MOUNTAIN", math.inf, False, frozenset({"land", "mountain"})),
        TerrainDef(10, "LAKE",     math.inf, True,  frozenset({"water", "lake"})),
    ]
    for d in _builtin:
        registry.register(d)
    return registry


# 全域預設 registry；模組載入時立即填入內建地形
# 使用方式：from mapcore.terrain import DEFAULT_REGISTRY
DEFAULT_REGISTRY: TerrainRegistry = gen_default()
