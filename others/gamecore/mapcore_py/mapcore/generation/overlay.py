"""地形 Overlay Phase（Phase 7）。

在基底地形（Phase 1~6）產出後，根據 TerrainPatch 清單把特定格子升級為衍生地形。
對應 RimWorld 的 TerrainPatchMaker 模式，但支援更多條件類型。

使用方式：
    result = generate_world(...)
    apply_terrain_patches(result, [
        TerrainPatch(
            derived_terrain=MAGICAL_FOREST,
            base_terrain_tags=frozenset({"forest"}),
            noise_channel="magic",
            noise_min=0.7,
        ),
    ])
"""

from __future__ import annotations  # 讓 TYPE_CHECKING 的型態標注在執行期也能解析為字串

import random
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from ..hex import Hex
from ..map import Hilliness, TileMap
from ..terrain import TerrainRegistry

if TYPE_CHECKING:
    from .pipeline import WorldGenResult


@dataclass
class TerrainPatch:
    """一條衍生地形生成規則；對應 RimWorld TerrainPatchMaker。

    所有條件 AND 運算：未設定的條件（None / 空集合）視為「不限制」。
    base_terrain_ids 與 base_terrain_tags 若都空，表示接受所有地形。
    """

    derived_terrain: int                    # 套用的衍生地形 id

    # ── 基底篩選（哪些格子有資格）────────────────────────────────────────
    base_terrain_ids: frozenset[int] = field(default_factory=frozenset)
    base_terrain_tags: frozenset[str] = field(default_factory=frozenset)

    # ── Noise 條件（對應 RimWorld TerrainPatchMaker 的 Perlin noise）──────
    # noise_channel 對應 WorldGenResult.extra_noise 的 key；空字串 = 不用 noise
    noise_channel: str = ""
    noise_min: float = 0.0
    noise_max: float = 1.0
    # 對應 RimWorld minSize：flood-fill 確認連通塊大小，0 = 不檢查
    min_patch_size: int = 0

    # ── 氣候條件（需要 climate=True 才有資料）────────────────────────────
    temp_min: Optional[float] = None        # °C 下界（None = 不限）
    temp_max: Optional[float] = None        # °C 上界
    rainfall_min: Optional[float] = None    # mm 下界
    rainfall_max: Optional[float] = None    # mm 上界

    # ── 鄰接條件──────────────────────────────────────────────────────────
    # near_terrain_tags 非空時，格子 near_radius 格內必須存在有這些 tag 的地形
    near_terrain_tags: frozenset[str] = field(default_factory=frozenset)
    near_radius: int = 1

    # ── Hilliness 條件───────────────────────────────────────────────────
    # 非 None 時，tile.hilliness 必須在此集合內
    hilliness_filter: Optional[frozenset[int]] = None   # Hilliness int 值的集合

    # ── Feature 條件─────────────────────────────────────────────────────
    # 非空時，tile 所屬 feature 的 feature_type 必須在此集合內
    feature_types: frozenset[str] = field(default_factory=frozenset)

    # ── 隨機性───────────────────────────────────────────────────────────
    probability: float = 1.0
    seed_offset: int = 0


# ---------------------------------------------------------------------------
# 條件判斷
# ---------------------------------------------------------------------------

def _base_filter(tile_terrain: int, patch: TerrainPatch, registry: TerrainRegistry) -> bool:
    if not patch.base_terrain_ids and not patch.base_terrain_tags:
        return True  # 空 = 接受所有
    if patch.base_terrain_ids and tile_terrain in patch.base_terrain_ids:
        return True
    if patch.base_terrain_tags:
        for tag in patch.base_terrain_tags:
            if registry.has_tag(tile_terrain, tag):
                return True
    return False


def _noise_pass(h: Hex, patch: TerrainPatch, world: WorldGenResult) -> bool:
    if not patch.noise_channel:
        return True
    noise_grid = world.extra_noise.get(patch.noise_channel)
    if noise_grid is None:
        return False  # 指定了 channel 但 world 沒有這張圖
    val = noise_grid[h.r][h.q]
    return patch.noise_min <= val <= patch.noise_max


def _climate_pass(h: Hex, patch: TerrainPatch, world: WorldGenResult) -> bool:
    if patch.temp_min is not None or patch.temp_max is not None:
        if world.temperature_celsius is None:
            return False  # 需要 climate 資料但沒有
        t = world.temperature_celsius[h.r][h.q]
        if patch.temp_min is not None and t < patch.temp_min:
            return False
        if patch.temp_max is not None and t > patch.temp_max:
            return False
    if patch.rainfall_min is not None or patch.rainfall_max is not None:
        if world.rainfall_mm is None:
            return False
        r = world.rainfall_mm[h.r][h.q]
        if patch.rainfall_min is not None and r < patch.rainfall_min:
            return False
        if patch.rainfall_max is not None and r > patch.rainfall_max:
            return False
    return True


def _adjacency_pass(h: Hex, patch: TerrainPatch, tile_map: TileMap, registry: TerrainRegistry) -> bool:
    if not patch.near_terrain_tags:
        return True
    # BFS 在 near_radius 範圍內找是否有符合 tag 的格子
    visited: set[tuple[int, int]] = {(h.q, h.r)}
    frontier: list[Hex] = [h]
    for _ in range(patch.near_radius):
        next_frontier: list[Hex] = []
        for cur in frontier:
            for nb in cur.neighbors():
                key = (nb.q, nb.r)
                if key in visited:
                    continue
                visited.add(key)
                nb_tile = tile_map.get(nb)
                if nb_tile is None:
                    continue
                for tag in patch.near_terrain_tags:
                    if registry.has_tag(nb_tile.terrain, tag):
                        return True
                next_frontier.append(nb)
        frontier = next_frontier
    return False


def _hilliness_pass(hilliness_val: int, patch: TerrainPatch) -> bool:
    if patch.hilliness_filter is None:
        return True
    return hilliness_val in patch.hilliness_filter


def _feature_pass(feature_id: int, patch: TerrainPatch, tile_map: TileMap) -> bool:
    if not patch.feature_types:
        return True
    if tile_map.features is None or feature_id < 0:
        return False
    feat = tile_map.features.get(feature_id)
    return feat is not None and feat.feature_type in patch.feature_types


# ---------------------------------------------------------------------------
# 連通塊過濾（對應 RimWorld minSize）
# ---------------------------------------------------------------------------

def _filter_by_patch_size(candidates: list[Hex], tile_map: TileMap, min_size: int) -> list[Hex]:
    """把 candidates 中連通塊大小 < min_size 的格子移除。"""
    candidate_set: set[tuple[int, int]] = {(h.q, h.r) for h in candidates}
    visited: set[tuple[int, int]] = set()
    result: list[Hex] = []

    for h in candidates:
        key = (h.q, h.r)
        if key in visited:
            continue
        # BFS 找連通塊（只在 candidate_set 內走）
        component: list[Hex] = []
        queue: list[Hex] = [h]
        visited.add(key)
        while queue:
            cur = queue.pop()
            component.append(cur)
            for nb in cur.neighbors():
                nk = (nb.q, nb.r)
                if nk in candidate_set and nk not in visited and tile_map.in_bounds(nb):
                    visited.add(nk)
                    queue.append(nb)
        if len(component) >= min_size:
            result.extend(component)

    return result


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def apply_terrain_patches(
    world: WorldGenResult,
    patches: list[TerrainPatch],
    seed: Optional[int] = None,
) -> int:
    """依序套用 patches，回傳實際改動的格數。

    patches 按定義順序執行，後面的 patch 可以把前面套用的衍生地形當作 base（串聯）。
    seed=None 時使用 world.seed；兩者都 None 時結果不可重現（使用系統亂數）。
    """
    tile_map = world.tile_map
    registry = world.registry
    base_seed = seed if seed is not None else world.seed
    total_changed = 0

    for patch in patches:
        rng = random.Random(
            None if base_seed is None else base_seed + patch.seed_offset
        )

        candidates: list[Hex] = []
        for h, tile in tile_map:
            if not _base_filter(tile.terrain, patch, registry):
                continue
            if not _noise_pass(h, patch, world):
                continue
            if not _climate_pass(h, patch, world):
                continue
            if not _adjacency_pass(h, patch, tile_map, registry):
                continue
            if not _hilliness_pass(int(tile.hilliness), patch):
                continue
            if not _feature_pass(tile.feature_id, patch, tile_map):
                continue
            if rng.random() > patch.probability:
                continue
            candidates.append(h)

        if patch.min_patch_size > 1:
            candidates = _filter_by_patch_size(candidates, tile_map, patch.min_patch_size)

        for h in candidates:
            tile_map.get(h).terrain = patch.derived_terrain
        total_changed += len(candidates)

    return total_changed
