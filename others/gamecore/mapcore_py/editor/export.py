"""把 EditorState 的手繪 heightmap 注入 mapcore pipeline，輸出 WorldGenResult。"""
from __future__ import annotations
import sys
from pathlib import Path

# 確保能找到 mapcore 模組（無論從哪裡啟動）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.classify import heightmap_to_tilemap
from mapcore.generation.biome import apply_biomes
from mapcore.generation.climate import apply_climate
from mapcore.generation.pipeline import WorldGenResult
from mapcore.terrain import DEFAULT_REGISTRY
from .state import EditorState


def export_to_worldgen_result(state: EditorState) -> WorldGenResult:
    """將手繪 heightmap 跑完 classify → biome → climate，回傳 WorldGenResult。

    moisture 暫以 rainfall（0–1）代替；若氣候模擬尚未執行，使用均值 0.5 fallback。
    """
    hm = state.heightmap
    w, h = state.width, state.height

    # moisture：以 rainfall 代替（歸一化到 0–1）
    if state.rainfall and state.rainfall[0]:
        moisture = state.rainfall
    else:
        moisture = [[0.5] * w for _ in range(h)]

    tile_map = heightmap_to_tilemap(hm, sea_level=state.sea_level, coast_depth=1)

    apply_biomes(tile_map, hm, moisture, sea_level=state.sea_level)

    # 氣候（以編輯器自己算的溫/濕度為底，再讓 mapcore 補 hilliness）
    temp_c, rain_mm = apply_climate(tile_map, hm, moisture, sea_level=state.sea_level)

    return WorldGenResult(
        tile_map=tile_map,
        heightmap=hm,
        moisture=moisture,
        temperature_celsius=temp_c,
        rainfall_mm=rain_mm,
        extra_noise={},
        registry=DEFAULT_REGISTRY,
        seed=None,
    )
