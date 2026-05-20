"""氣候模擬：太陽軌跡 + 風向 → 溫度 / 降雨（含雨影效應）（方格版）。"""
from __future__ import annotations
import math
from ..state import EditorState


def run_climate(state: EditorState) -> None:
    """計算溫度（0=冷, 1=熱）與降雨量（0=乾, 1=濕）並存回 state。

    與 mapcore_py 版邏輯完全相同，座標改為 (x, y) 方格。
    """
    w, h = state.width, state.height
    lat_scale = state.sun_angle / 90.0

    temp = [[0.0] * w for _ in range(h)]
    for y in range(h):
        lat_frac = y / (h - 1) if h > 1 else 0.5
        lat_heat = 1.0 - abs(lat_frac * 2 - 1) * lat_scale
        for x in range(w):
            elev_penalty = state.get_h(x, y) * 0.45
            temp[y][x] = max(0.0, min(1.0, lat_heat - elev_penalty))
    state.temperature = temp

    wind_rad = math.radians(state.wind_dir)
    wdx = math.sin(wind_rad)
    wdy = -math.cos(wind_rad)

    moisture = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if state.ocean_mask[y][x]:
                moisture[y][x] = 1.0

    x_order = list(range(w)) if wdx >= 0 else list(range(w - 1, -1, -1))
    y_order = list(range(h)) if wdy >= 0 else list(range(h - 1, -1, -1))
    evap_per_step = state.evaporation * 0.08

    for _ in range(4):
        for y in y_order:
            for x in x_order:
                if state.ocean_mask[y][x]:
                    moisture[y][x] = 1.0
                    continue
                sx = x - round(wdx)
                sy = y - round(wdy)
                if state.in_bounds(sx, sy):
                    incoming = moisture[sy][sx]
                    elev_diff = max(0.0, state.get_h(x, y) - state.get_h(sx, sy))
                    rain_shadow_loss = elev_diff * 4.0
                else:
                    incoming = 0.0
                    rain_shadow_loss = 0.0
                moisture[y][x] = max(
                    moisture[y][x],
                    max(0.0, incoming * (1 - evap_per_step) - rain_shadow_loss),
                )

    state.rainfall = moisture
