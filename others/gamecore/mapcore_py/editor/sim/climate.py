"""氣候模擬：太陽軌跡 + 風向 → 溫度 / 降雨（含雨影效應）。"""
from __future__ import annotations
import math
from ..state import EditorState


def run_climate(state: EditorState) -> None:
    """計算溫度（0=冷, 1=熱）與降雨量（0=乾, 1=濕）並存回 state。

    溫度模型：
      - 赤道（r=height/2）最熱；極端（r=0 或 r=height-1）最冷
      - sun_angle 控制緯度溫差幅度（越大越冷）
      - 高程每 +0.1 降溫

    降雨模型：
      - 海洋格為初始水氣源（moisture=1.0）
      - 按 wind_dir 方向逐格傳播水氣
      - 越過山脈上坡時失去水氣（雨影效應）
    """
    w, h = state.width, state.height
    lat_scale = state.sun_angle / 90.0

    # 溫度
    temp = [[0.0] * w for _ in range(h)]
    for r in range(h):
        lat_frac = r / (h - 1) if h > 1 else 0.5
        # 赤道 lat_frac=0.5 → lat_heat=1.0；極端 → 1 - lat_scale
        lat_heat = 1.0 - abs(lat_frac * 2 - 1) * lat_scale
        for q in range(w):
            elev_penalty = state.get_h(q, r) * 0.45
            temp[r][q] = max(0.0, min(1.0, lat_heat - elev_penalty))
    state.temperature = temp

    # 降雨（風向傳播 + 雨影）
    wind_rad = math.radians(state.wind_dir)
    # 風「吹去」方向的單位向量（dx=東西, dy=南北；r 增加=南）
    wdq = math.sin(wind_rad)
    wdr = -math.cos(wind_rad)

    moisture = [[0.0] * w for _ in range(h)]
    for r in range(h):
        for q in range(w):
            if state.ocean_mask[r][q]:
                moisture[r][q] = 1.0

    # 掃描順序：逆風方向（上風側先算，再向下風傳播）
    q_order = list(range(w)) if wdq >= 0 else list(range(w - 1, -1, -1))
    r_order = list(range(h)) if wdr >= 0 else list(range(h - 1, -1, -1))

    evap_per_step = state.evaporation * 0.08

    for _ in range(4):
        for r in r_order:
            for q in q_order:
                if state.ocean_mask[r][q]:
                    moisture[r][q] = 1.0
                    continue
                # 上風格座標（風從那邊吹來）
                src_q = q - round(wdq)
                src_r = r - round(wdr)
                if state.in_bounds(src_q, src_r):
                    incoming = moisture[src_r][src_q]
                    # 爬坡損失（雨影）
                    elev_diff = max(0.0, state.get_h(q, r) - state.get_h(src_q, src_r))
                    rain_shadow_loss = elev_diff * 4.0
                else:
                    incoming = 0.0
                    rain_shadow_loss = 0.0
                moisture[r][q] = max(
                    moisture[r][q],
                    max(0.0, incoming * (1 - evap_per_step) - rain_shadow_loss),
                )

    state.rainfall = moisture
