from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

ToolName = Literal["raise", "lower", "ridge", "rift", "water_source"]
OverlayName = Literal["height", "ocean", "temperature", "rainfall"]


@dataclass
class EditorState:
    width: int = 60
    height: int = 40

    # 主畫布：原始高程 [r][q]，範圍 0.0–1.0
    heightmap: list[list[float]] = field(default_factory=list)

    # 水源點：(q, r) 列表；漫水模擬的起點
    water_sources: list[tuple[int, int]] = field(default_factory=list)

    # 模擬參數
    sea_level: float = 0.35
    sun_angle: float = 23.5    # 黃道傾角（度），控制緯度受熱強度
    wind_dir: float = 270.0    # 風向（度）：0=N, 90=E, 180=S, 270=W
    evaporation: float = 0.5   # 水氣越山損失係數

    # 工具參數
    current_tool: ToolName = "raise"
    brush_size: int = 3
    brush_strength: float = 0.05
    brush_rate: float = 10.0   # applications per second while button held
    brush_falloff: float = 2.0  # ridge/rift radial falloff exponent (1=linear, higher=steeper)
    brush_chaos: float = 0.0    # ridge/rift shape noise (0=smooth circle, 1=jagged)
    brush_spokes: int = 0            # ridge/rift radial arms (fixed count when rand=False)
    brush_spokes_rand: bool = False  # randomise spoke count each stamp
    brush_spokes_min: int = 2        # random lower bound
    brush_spokes_max: int = 6        # random upper bound
    brush_spokes_invert: bool = False  # True = spokes go opposite direction to base tool

    # 顯示選項
    overlay: OverlayName = "height"
    hex_size: int = 14

    # 雜訊生成參數
    noise_seed: int = 42
    noise_octaves: int = 5
    noise_persistence: float = 0.5
    noise_base_freq: int = 4
    noise_shape: str = "無 None"
    noise_shape_strength: float = 0.85
    noise_ridge_weight: float = 0.0
    noise_ridge_mode: str = "plates"
    noise_num_plates: int = 20
    noise_blend: float = 0.0   # 0=完全取代, 1=完全保留現有

    # 模擬結果（按鈕觸發後填入）
    ocean_mask: list[list[bool]] = field(default_factory=list)
    temperature: list[list[float]] = field(default_factory=list)   # 0–1
    rainfall: list[list[float]] = field(default_factory=list)      # 0–1

    def __post_init__(self) -> None:
        if not self.heightmap:
            self.reset()

    def reset(self) -> None:
        self.heightmap   = [[0.3] * self.width for _ in range(self.height)]
        self.ocean_mask  = [[False] * self.width for _ in range(self.height)]
        self.temperature = [[0.5] * self.width for _ in range(self.height)]
        self.rainfall    = [[0.5] * self.width for _ in range(self.height)]
        self.water_sources = []

    def new_map(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.reset()

    def in_bounds(self, q: int, r: int) -> bool:
        return 0 <= q < self.width and 0 <= r < self.height

    def get_h(self, q: int, r: int) -> float:
        return self.heightmap[r][q]

    def set_h(self, q: int, r: int, v: float) -> None:
        self.heightmap[r][q] = max(0.0, min(1.0, v))
