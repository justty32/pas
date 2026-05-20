from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

ToolName    = Literal["raise", "lower", "ridge", "rift", "water_source"]
OverlayName = Literal["height", "ocean", "temperature", "rainfall"]


@dataclass
class EditorState:
    width: int = 80
    height: int = 50

    # 主畫布：原始高程 [y][x]，範圍 0.0–1.0
    heightmap: list[list[float]] = field(default_factory=list)

    # 水源點：(x, y) 列表；漫水模擬的起點
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
    brush_rate_rand: bool = False
    brush_rate_min: float = 5.0
    brush_rate_max: float = 30.0
    brush_falloff: float = 2.0
    brush_chaos: float = 0.0
    brush_spokes: int = 0
    brush_spokes_rand: bool = False
    brush_spokes_min: int = 2
    brush_spokes_max: int = 6
    brush_spokes_invert: bool = False
    brush_spoke_jitter: float = 0.0   # 單個 spoke 隨機偏移上限（度）；實際偏移 uniform(-v, +v)
    brush_wheel_angle: float = 0.0    # 輪盤固定旋轉角度（度，0–360，不允許負數）
    brush_wheel_rand: bool = False     # 輪盤角度是否隨機
    brush_wheel_min: float = 0.0      # 隨機輪盤下限（度）
    brush_wheel_max: float = 360.0    # 隨機輪盤上限（度）

    # 顯示選項
    overlay: OverlayName = "height"
    cell_size: int = 12        # 每格邊長（像素）

    # 雜訊生成參數
    noise_seed: int = 42
    noise_octaves: int = 5
    noise_persistence: float = 0.5
    noise_base_freq: int = 4
    noise_shape: str = "None"
    noise_shape_strength: float = 0.85
    noise_ridge_weight: float = 0.0
    noise_ridge_mode: str = "plates"
    noise_num_plates: int = 20
    noise_blend: float = 0.0

    # 模擬結果
    ocean_mask: list[list[bool]]    = field(default_factory=list)
    temperature: list[list[float]]  = field(default_factory=list)
    rainfall: list[list[float]]     = field(default_factory=list)

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

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def get_h(self, x: int, y: int) -> float:
        return self.heightmap[y][x]

    def set_h(self, x: int, y: int, v: float) -> None:
        self.heightmap[y][x] = max(0.0, min(1.0, v))
