"""World Sculptor — Dear PyGui interactive hex map editor.

Requirements: pip install dearpygui
Launch: python run_editor.py
"""
from __future__ import annotations

import math
import pickle
import random as _random
import time
from pathlib import Path

import dearpygui.dearpygui as dpg

from .state import EditorState
from .hex_layout import hex_to_pixel, pixel_to_hex, hex_corners
from .tools import apply_brush, apply_ridge_stamp, apply_rift_stamp, toggle_water_source
from .sim.hydrology import run_flood_fill
from .sim.climate import run_climate

# ── Constants ────────────────────────────────────────────────────────────────

PANEL_W   = 240
CANVAS_W  = 1140   # fixed drawlist width
CANVAS_H  = 790    # fixed drawlist height
_CAM_INIT = 40.0   # initial camera offset (pixels)
_TARGET_FRAME_DT = 1.0 / 60.0   # cap render loop at ~60 FPS to stop CPU spinning

_BORDER = (0, 0, 0, 25)

# Height overlay: each band fades from a light colour (band start) to a dark colour (band end).
# At the threshold the next band starts bright again, creating visible elevation zones.
_HEIGHT_BANDS = (
    # (h_end, colour_at_t=0,          colour_at_t=1         )
    (0.35,  ( 40,  95, 195),  ( 10,  30,  90)),  # ocean
    (0.40,  (205, 185, 120),  (165, 148,  95)),  # beach
    (0.58,  (100, 178,  62),  ( 55, 120,  30)),  # lowland
    (0.72,  (148, 132,  84),  ( 95,  85,  50)),  # highland
    (0.87,  (132, 122, 116),  ( 85,  78,  74)),  # mountain
    (1.00,  (242, 242, 246),  (185, 183, 190)),  # snow
)

# ── Color helpers ────────────────────────────────────────────────────────────

_OCEAN_BAND = _HEIGHT_BANDS[0]   # (h_end, light, dark)
_LAND_BANDS = _HEIGHT_BANDS[1:]


def _lerp_rgb(c0: tuple[int, int, int], c1: tuple[int, int, int], t: float) -> tuple[int, int, int, int]:
    return (
        int(c0[0] + (c1[0] - c0[0]) * t),
        int(c0[1] + (c1[1] - c0[1]) * t),
        int(c0[2] + (c1[2] - c0[2]) * t),
        255,
    )


def _height_color(h: float, is_ocean: bool, sea_level: float = 0.35) -> tuple[int, int, int, int]:
    """高程著色。

    - `is_ocean=True`：強制使用 ocean band 漸層（用 sea_level 算深度），即使
      h > sea_level —— 用來顯示「flood fill 認定連通到海，但 h 被後續 raise 抬高」
      的異常格。
    - 其餘：依 _HEIGHT_BANDS 線性查表（h ≤ sea_level 自然落在 ocean band）。
    """
    if is_ocean:
        _, c0, c1 = _OCEAN_BAND
        t = max(0.0, min(1.0, h / max(sea_level, 1e-6)))
        return _lerp_rgb(c0, c1, t)

    prev = 0.0
    for h_end, c0, c1 in _HEIGHT_BANDS:
        if h <= h_end:
            bw = h_end - prev
            t  = (h - prev) / bw if bw > 0.0 else 0.0
            return _lerp_rgb(c0, c1, t)
        prev = h_end
    return (242, 242, 246, 255)


def _temp_color(t: float) -> tuple[int, int, int, int]:
    r = int(255 * min(1.0, t * 2))
    b = int(255 * min(1.0, (1 - t) * 2))
    return (r, 30, b, 255)


def _rain_color(rv: float) -> tuple[int, int, int, int]:
    g = int(80 + 120 * rv)
    b = int(100 + 155 * rv)
    return (int(20 * (1 - rv)), g, b, 255)


# ── App ───────────────────────────────────────────────────────────────────────

class App:
    def __init__(self, width: int = 60, height: int = 40) -> None:
        self.state   = EditorState(width=width, height=height)
        self._dirty         = True
        self._pan_last:      tuple[float, float] | None = None
        self._last_tool_hex: tuple[int, int]   | None = None
        self._rtool_active   = False
        self._last_tick_t    = 0.0
        # Set whenever heightmap mutates after the last Flood Fill / Climate run;
        # cleared when those simulations run again. Lets the UI warn that the
        # Ocean / Temperature / Rainfall overlays are stale.
        self._sim_dirty:        bool  = False
        # Smooth-random rate state: cosine-interpolate between _rate_prev and _rate_target
        self._rate_prev:        float = self.state.brush_rate
        self._rate_target:      float = self.state.brush_rate
        self._rate_phase_start: float = 0.0
        self._rate_phase_dur:   float = 1.5
        self._cam_x  = _CAM_INIT
        self._cam_y  = _CAM_INIT
        # Cached screen-space origin of the canvas drawlist.
        # Initialized to a reasonable default; refreshed every time rect_min is available.
        self._canvas_origin: list[float] = [float(PANEL_W + 8), 8.0]

    # ── Entry point ──────────────────────────────────────────────────────────

    def run(self) -> None:
        dpg.create_context()
        self._build_ui()
        self._register_handlers()

        dpg.create_viewport(
            title="World Sculptor — mapcore_py Editor",
            width=PANEL_W + CANVAS_W + 20,
            height=CANVAS_H + 30,
        )
        dpg.setup_dearpygui()
        dpg.show_viewport()
        self.redraw_canvas()

        while dpg.is_dearpygui_running():
            frame_start = time.monotonic()
            self._tick()
            if self._dirty:
                self.redraw_canvas()
                self._dirty = False
            dpg.render_dearpygui_frame()
            slack = _TARGET_FRAME_DT - (time.monotonic() - frame_start)
            if slack > 0.0:
                time.sleep(slack)

        dpg.destroy_context()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        with dpg.window(tag="main_window"):
            with dpg.group(horizontal=True):
                self._build_left_panel()
                self._build_canvas_area()
        dpg.set_primary_window("main_window", True)

    def _build_left_panel(self) -> None:
        with dpg.child_window(tag="left_panel", width=PANEL_W, height=-1, border=True):

            dpg.add_text("TOOLS", color=(255, 220, 80))
            dpg.add_separator()
            dpg.add_radio_button(
                tag="tool_radio",
                items=["Raise", "Lower", "Ridge", "Rift", "Water Source"],
                default_value="Raise",
                callback=self._cb_tool,
            )

            dpg.add_spacing(count=2)
            dpg.add_text("BRUSH", color=(255, 220, 80))
            dpg.add_separator()
            dpg.add_slider_int(
                label="Size", tag="brush_size",
                min_value=1, max_value=10, default_value=self.state.brush_size,
                callback=lambda s, a: setattr(self.state, "brush_size", a),
            )
            dpg.add_slider_float(
                label="Strength", tag="brush_str",
                min_value=0.01, max_value=0.25, default_value=self.state.brush_strength,
                callback=lambda s, a: setattr(self.state, "brush_strength", a),
            )
            dpg.add_slider_float(
                label="Rate/s", tag="brush_rate",
                min_value=1.0, max_value=60.0, default_value=self.state.brush_rate,
                callback=lambda s, a: setattr(self.state, "brush_rate", a),
            )
            dpg.add_checkbox(
                label="Random Rate", tag="brush_rate_rand",
                default_value=self.state.brush_rate_rand,
                callback=self._cb_rate_rand,
            )
            dpg.add_slider_float(
                label="Rate Min", tag="brush_rate_min",
                min_value=1.0, max_value=60.0, default_value=self.state.brush_rate_min,
                callback=lambda s, a: setattr(self.state, "brush_rate_min", a),
            )
            dpg.add_slider_float(
                label="Rate Max", tag="brush_rate_max",
                min_value=1.0, max_value=60.0, default_value=self.state.brush_rate_max,
                callback=lambda s, a: setattr(self.state, "brush_rate_max", a),
            )
            dpg.add_text("Ridge / Rift", color=(160, 160, 160))
            dpg.add_slider_float(
                label="Falloff", tag="brush_falloff",
                min_value=1.0, max_value=4.0, default_value=self.state.brush_falloff,
                callback=lambda s, a: setattr(self.state, "brush_falloff", a),
            )
            dpg.add_slider_float(
                label="Chaos", tag="brush_chaos",
                min_value=0.0, max_value=1.0, default_value=self.state.brush_chaos,
                callback=lambda s, a: setattr(self.state, "brush_chaos", a),
            )
            dpg.add_slider_int(
                label="Spokes", tag="brush_spokes",
                min_value=0, max_value=8, default_value=self.state.brush_spokes,
                callback=lambda s, a: setattr(self.state, "brush_spokes", a),
            )
            dpg.add_checkbox(
                label="Random", tag="brush_spokes_rand",
                default_value=self.state.brush_spokes_rand,
                callback=lambda s, a: setattr(self.state, "brush_spokes_rand", a),
            )
            dpg.add_slider_int(
                label="  Min", tag="brush_spokes_min",
                min_value=0, max_value=8, default_value=self.state.brush_spokes_min,
                callback=lambda s, a: setattr(self.state, "brush_spokes_min", a),
            )
            dpg.add_slider_int(
                label="  Max", tag="brush_spokes_max",
                min_value=0, max_value=8, default_value=self.state.brush_spokes_max,
                callback=lambda s, a: setattr(self.state, "brush_spokes_max", a),
            )
            dpg.add_checkbox(
                label="Invert Spokes", tag="brush_spokes_invert",
                default_value=self.state.brush_spokes_invert,
                callback=lambda s, a: setattr(self.state, "brush_spokes_invert", a),
            )

            dpg.add_spacing(count=2)
            dpg.add_text("VIEW", color=(255, 220, 80))
            dpg.add_separator()
            dpg.add_radio_button(
                tag="overlay_radio",
                items=["Height", "Ocean", "Temperature", "Rainfall"],
                default_value="Height",
                callback=self._cb_overlay,
            )

            dpg.add_spacing(count=2)
            dpg.add_text("HYDROLOGY", color=(255, 220, 80))
            dpg.add_separator()
            dpg.add_slider_float(
                label="Sea Level", tag="sea_level",
                min_value=0.0, max_value=0.8, default_value=self.state.sea_level,
                callback=lambda s, a: setattr(self.state, "sea_level", a),
            )
            dpg.add_button(label="Run Flood Fill", width=-1, callback=self._cb_flood_fill)

            dpg.add_spacing(count=2)
            dpg.add_text("CLIMATE", color=(255, 220, 80))
            dpg.add_separator()
            dpg.add_slider_float(
                label="Sun Angle", tag="sun_angle",
                min_value=0.0, max_value=90.0, default_value=self.state.sun_angle,
                callback=lambda s, a: setattr(self.state, "sun_angle", a),
            )
            dpg.add_slider_float(
                label="Wind Dir", tag="wind_dir",
                min_value=0.0, max_value=360.0, default_value=self.state.wind_dir,
                callback=lambda s, a: setattr(self.state, "wind_dir", a),
            )
            dpg.add_text("0=N  90=E  180=S  270=W", color=(160, 160, 160))
            dpg.add_slider_float(
                label="Evaporation", tag="evaporation",
                min_value=0.0, max_value=1.0, default_value=self.state.evaporation,
                callback=lambda s, a: setattr(self.state, "evaporation", a),
            )
            dpg.add_button(label="Run Climate", width=-1, callback=self._cb_climate)

            dpg.add_spacing(count=2)
            dpg.add_text("MAP", color=(255, 220, 80))
            dpg.add_separator()
            dpg.add_input_int(label="Width",  tag="new_w", default_value=60,
                              min_value=10, max_value=300)
            dpg.add_input_int(label="Height", tag="new_h", default_value=40,
                              min_value=10, max_value=300)
            dpg.add_button(label="New Map",      width=-1, callback=self._cb_new_map)
            dpg.add_button(label="Reset Heights", width=-1, callback=self._cb_reset)

            dpg.add_spacing(count=2)
            dpg.add_text("NOISE", color=(255, 220, 80))
            dpg.add_separator()
            with dpg.group(horizontal=True):
                dpg.add_input_int(
                    label="", tag="noise_seed",
                    default_value=self.state.noise_seed,
                    width=PANEL_W - 90,
                    callback=lambda s, a: setattr(self.state, "noise_seed", a),
                )
                dpg.add_button(label="Rand", width=50, callback=self._cb_random_seed)
            dpg.add_text("Seed", color=(160, 160, 160))
            dpg.add_combo(
                label="Shape", tag="noise_shape",
                items=["None", "Continents", "Pangaea", "Ring Sea",
                       "Island", "Archipelago", "Shattered Archipelago"],
                default_value="None",
                width=-1,
                callback=lambda s, a: setattr(self.state, "noise_shape", a),
            )
            dpg.add_slider_float(
                label="Shape Str", tag="noise_shape_str",
                min_value=0.0, max_value=1.0,
                default_value=self.state.noise_shape_strength,
                callback=lambda s, a: setattr(self.state, "noise_shape_strength", a),
            )
            dpg.add_slider_float(
                label="Ridge", tag="noise_ridge_w",
                min_value=0.0, max_value=1.0,
                default_value=self.state.noise_ridge_weight,
                callback=lambda s, a: setattr(self.state, "noise_ridge_weight", a),
            )
            dpg.add_combo(
                label="Ridge Mode", tag="noise_ridge_mode",
                items=["plates", "musgrave"],
                default_value=self.state.noise_ridge_mode,
                width=-1,
                callback=lambda s, a: setattr(self.state, "noise_ridge_mode", a),
            )
            dpg.add_slider_int(
                label="Plates", tag="noise_plates",
                min_value=3, max_value=60,
                default_value=self.state.noise_num_plates,
                callback=lambda s, a: setattr(self.state, "noise_num_plates", a),
            )
            dpg.add_slider_int(
                label="Octaves", tag="noise_oct",
                min_value=1, max_value=8,
                default_value=self.state.noise_octaves,
                callback=lambda s, a: setattr(self.state, "noise_octaves", a),
            )
            dpg.add_slider_float(
                label="Persistence", tag="noise_persist",
                min_value=0.1, max_value=0.9,
                default_value=self.state.noise_persistence,
                callback=lambda s, a: setattr(self.state, "noise_persistence", a),
            )
            dpg.add_slider_int(
                label="Base Freq", tag="noise_freq",
                min_value=1, max_value=12,
                default_value=self.state.noise_base_freq,
                callback=lambda s, a: setattr(self.state, "noise_base_freq", a),
            )
            dpg.add_slider_float(
                label="Blend", tag="noise_blend",
                min_value=0.0, max_value=1.0,
                default_value=self.state.noise_blend,
                callback=lambda s, a: setattr(self.state, "noise_blend", a),
            )
            dpg.add_text("0=replace  1=keep existing", color=(160, 160, 160))
            dpg.add_button(label="Generate Noise", width=-1, callback=self._cb_generate_noise)

            dpg.add_spacing(count=2)
            dpg.add_separator()
            dpg.add_button(label="Export → WorldGenResult", width=-1, callback=self._cb_export)
            dpg.add_text("", tag="status_bar", color=(100, 220, 100), wrap=PANEL_W - 16)

    def _build_canvas_area(self) -> None:
        with dpg.child_window(
            tag="canvas_window",
            width=-1, height=-1,
            border=False,
            no_scrollbar=True,
            no_scroll_with_mouse=True,
        ):
            dpg.add_drawlist(tag="hex_canvas", width=CANVAS_W, height=CANVAS_H)

    # ── Canvas rendering ──────────────────────────────────────────────────────

    def redraw_canvas(self) -> None:
        dpg.delete_item("hex_canvas", children_only=True)
        s    = self.state
        size = s.hex_size
        ox   = self._cam_x
        oy   = self._cam_y

        for r in range(s.height):
            for q in range(s.width):
                cx, cy = hex_to_pixel(q, r, size, ox, oy)
                # Viewport culling
                if cx + size < 0 or cy + size < 0 or cx - size > CANVAS_W or cy - size > CANVAS_H:
                    continue
                h        = s.get_h(q, r)
                is_ocean = s.ocean_mask[r][q]

                if s.overlay == "temperature":
                    color = _temp_color(s.temperature[r][q])
                elif s.overlay == "rainfall":
                    color = _rain_color(s.rainfall[r][q])
                elif s.overlay == "ocean":
                    color = (30, 90, 180, 255) if is_ocean else (120, 170, 80, 255)
                else:
                    color = _height_color(h, is_ocean, s.sea_level)

                dpg.draw_polygon(hex_corners(cx, cy, size),
                                 fill=color, color=_BORDER, parent="hex_canvas")

        for sq, sr in s.water_sources:
            cx, cy = hex_to_pixel(sq, sr, size, ox, oy)
            dpg.draw_circle((cx, cy), radius=size * 0.35,
                            color=(60, 180, 255, 255),
                            fill=(60, 180, 255, 180),
                            parent="hex_canvas")

    # ── Mouse & keyboard helpers ──────────────────────────────────────────────

    def _refresh_canvas_origin(self) -> None:
        """Try to update the cached canvas screen-space origin from DPG state."""
        try:
            state = dpg.get_item_state("hex_canvas")
            rm = state.get("rect_min")
            if rm is not None:
                self._canvas_origin[0] = float(rm[0])
                self._canvas_origin[1] = float(rm[1])
        except Exception:
            pass

    def _get_hex(self) -> tuple[int, int]:
        self._refresh_canvas_origin()
        mx, my = dpg.get_mouse_pos(local=False)
        lx = mx - self._canvas_origin[0]
        ly = my - self._canvas_origin[1]
        return pixel_to_hex(lx, ly, self.state.hex_size, self._cam_x, self._cam_y)

    # ── Event handlers ────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """Called every frame. Continuously applies the active tool while right button is held."""
        if not self._rtool_active or not dpg.is_mouse_button_down(1):
            self._last_tool_hex = None
            return
        now = time.monotonic()
        rate = self._effective_rate(now)
        if now - self._last_tick_t < 1.0 / max(0.1, rate):
            return
        self._last_tick_t = now
        q, r = self._get_hex()
        if not self.state.in_bounds(q, r):
            return
        tool = self.state.current_tool
        if tool in ("raise", "lower"):
            delta = self.state.brush_strength if tool == "raise" else -self.state.brush_strength
            apply_brush(self.state, q, r, delta)
            self._dirty = self._sim_dirty = True
        elif tool in ("ridge", "rift"):
            (apply_ridge_stamp if tool == "ridge" else apply_rift_stamp)(self.state, q, r)
            self._dirty = self._sim_dirty = True
        elif tool == "water_source":
            if (q, r) != self._last_tool_hex:
                self._last_tool_hex = (q, r)
                toggle_water_source(self.state, q, r)
                self._dirty = True

    def _refresh_sim_warning(self) -> None:
        """If the current overlay depends on simulation results, warn when stale."""
        if self._sim_dirty and self.state.overlay in ("ocean", "temperature", "rainfall"):
            dpg.set_value(
                "status_bar",
                "⚠ Heightmap changed since last sim — re-run Flood Fill / Climate.",
            )

    def _effective_rate(self, now: float) -> float:
        """Return the rate (Hz) used for the current frame; cosine-interpolate when random mode is on."""
        s = self.state
        if not s.brush_rate_rand:
            return s.brush_rate
        lo = min(s.brush_rate_min, s.brush_rate_max)
        hi = max(s.brush_rate_min, s.brush_rate_max)
        if hi <= lo:
            return lo
        elapsed = now - self._rate_phase_start
        if elapsed >= self._rate_phase_dur:
            self._rate_prev        = self._rate_target
            self._rate_target      = _random.uniform(lo, hi)
            self._rate_phase_dur   = _random.uniform(1.0, 2.0)
            self._rate_phase_start = now
            elapsed = 0.0
        t = max(0.0, min(1.0, elapsed / self._rate_phase_dur))
        eased = 0.5 * (1.0 - math.cos(t * math.pi))
        return self._rate_prev + (self._rate_target - self._rate_prev) * eased

    def _on_mouse_move(self, sender, app_data) -> None:
        """Left button drag = pan camera."""
        if not dpg.is_mouse_button_down(0) or self._pan_last is None:
            return
        mx, my = dpg.get_mouse_pos(local=False)
        self._cam_x += mx - self._pan_last[0]
        self._cam_y += my - self._pan_last[1]
        self._pan_last = (mx, my)
        self._dirty = True

    def _on_mouse_click(self, sender, app_data) -> None:
        if not dpg.is_item_hovered("canvas_window"):
            return
        if app_data == 0:
            # Don't start panning while a brush stroke is active — would warp
            # the cursor's hex coordinate while stamps are being placed.
            if self._rtool_active:
                return
            mx, my = dpg.get_mouse_pos(local=False)
            self._pan_last = (mx, my)
        elif app_data == 1:
            # Don't start a brush stroke while panning, same reason in reverse.
            if self._pan_last is not None:
                return
            self._rtool_active = True

    def _on_mouse_release(self, sender, app_data) -> None:
        if app_data == 0:
            self._pan_last = None
        elif app_data == 1:
            self._rtool_active = False
            self._last_tool_hex = None

    def _on_mouse_wheel(self, sender, app_data) -> None:
        if not dpg.is_item_hovered("canvas_window"):
            return
        delta    = app_data   # positive = scroll up = zoom in
        old_size = self.state.hex_size
        step     = 1 if old_size < 16 else 2
        new_size = max(4, min(40, old_size + (step if delta > 0 else -step)))
        if new_size == old_size:
            return
        # Zoom toward the pixel under cursor
        self._refresh_canvas_origin()
        mx, my = dpg.get_mouse_pos(local=False)
        lx     = mx - self._canvas_origin[0]
        ly     = my - self._canvas_origin[1]
        scale  = new_size / old_size
        self._cam_x = lx - (lx - self._cam_x) * scale
        self._cam_y = ly - (ly - self._cam_y) * scale
        self.state.hex_size = new_size
        self._dirty = True

    def _on_key_down(self, sender, app_data) -> None:
        key  = app_data
        step = max(20, self.state.hex_size * 2)
        if   key == dpg.mvKey_Left:  self._cam_x += step
        elif key == dpg.mvKey_Right: self._cam_x -= step
        elif key == dpg.mvKey_Up:    self._cam_y += step
        elif key == dpg.mvKey_Down:  self._cam_y -= step
        else: return
        self._dirty = True

    def _register_handlers(self) -> None:
        with dpg.handler_registry():
            dpg.add_mouse_move_handler(callback=self._on_mouse_move)
            dpg.add_mouse_click_handler(callback=self._on_mouse_click)
            dpg.add_mouse_release_handler(callback=self._on_mouse_release)
            dpg.add_mouse_wheel_handler(callback=self._on_mouse_wheel)
            dpg.add_key_down_handler(callback=self._on_key_down)

    # ── Button callbacks ──────────────────────────────────────────────────────

    _TOOL_MAP = {
        "Raise":        "raise",
        "Lower":        "lower",
        "Ridge":        "ridge",
        "Rift":         "rift",
        "Water Source": "water_source",
    }
    _OVERLAY_MAP = {
        "Height":      "height",
        "Ocean":       "ocean",
        "Temperature": "temperature",
        "Rainfall":    "rainfall",
    }
    _SHAPE_MAP = {
        "None":                    None,
        "Continents":              "continents",
        "Pangaea":                 "pangaea",
        "Ring Sea":                "ring_sea",
        "Island":                  "island",
        "Archipelago":             "archipelago",
        "Shattered Archipelago":   "shattered_archipelago",
    }

    def _cb_tool(self, sender, app_data) -> None:
        self.state.current_tool = self._TOOL_MAP.get(app_data, "raise")

    def _cb_overlay(self, sender, app_data) -> None:
        self.state.overlay = self._OVERLAY_MAP.get(app_data, "height")
        self._dirty = True
        self._refresh_sim_warning()

    def _cb_rate_rand(self, sender, app_data) -> None:
        self.state.brush_rate_rand = bool(app_data)
        # Re-seed the smooth-random state so the next tick starts a fresh segment.
        lo = min(self.state.brush_rate_min, self.state.brush_rate_max)
        hi = max(self.state.brush_rate_min, self.state.brush_rate_max)
        if hi <= lo:
            self._rate_prev = self._rate_target = lo
        else:
            self._rate_prev   = _random.uniform(lo, hi)
            self._rate_target = _random.uniform(lo, hi)
        self._rate_phase_start = time.monotonic()
        self._rate_phase_dur   = _random.uniform(1.0, 2.0)

    def _cb_flood_fill(self, sender, app_data) -> None:
        run_flood_fill(self.state)
        dpg.set_value("overlay_radio", "Ocean")
        self.state.overlay = "ocean"
        self._sim_dirty = False
        self._dirty = True
        dpg.set_value("status_bar", "Flood fill done.")

    def _cb_climate(self, sender, app_data) -> None:
        # Climate uses ocean_mask as the moisture source; refresh it first so
        # Run Climate is correct on its own without a prior Flood Fill click.
        run_flood_fill(self.state)
        run_climate(self.state)
        dpg.set_value("overlay_radio", "Temperature")
        self.state.overlay = "temperature"
        self._sim_dirty = False
        self._dirty = True
        dpg.set_value("status_bar", "Climate simulation done.")

    def _cb_new_map(self, sender, app_data) -> None:
        w, h = dpg.get_value("new_w"), dpg.get_value("new_h")
        self.state.new_map(w, h)
        self._cam_x = _CAM_INIT
        self._cam_y = _CAM_INIT
        self._sim_dirty = False
        self._dirty = True
        dpg.set_value("status_bar", f"New map {w}x{h}")

    def _cb_reset(self, sender, app_data) -> None:
        self.state.reset()
        self._sim_dirty = False
        self._dirty = True
        dpg.set_value("status_bar", "Heights reset.")

    def _cb_random_seed(self, sender, app_data) -> None:
        import random
        seed = random.randint(0, 999999)
        self.state.noise_seed = seed
        dpg.set_value("noise_seed", seed)

    def _cb_generate_noise(self, sender, app_data) -> None:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from mapcore.generation.heightmap import generate_heightmap

        s     = self.state
        shape = self._SHAPE_MAP.get(s.noise_shape)
        seed  = s.noise_seed if s.noise_seed >= 0 else None
        try:
            new_hm = generate_heightmap(
                s.width, s.height,
                seed=seed,
                octaves=s.noise_octaves,
                persistence=s.noise_persistence,
                base_frequency=s.noise_base_freq,
                ridge_weight=s.noise_ridge_weight,
                ridge_mode=s.noise_ridge_mode,
                num_plates=s.noise_num_plates,
                shape=shape,
                shape_strength=s.noise_shape_strength,
                shape_sea_level=s.sea_level,
            )
        except Exception as e:
            dpg.set_value("status_bar", f"Generate failed: {e}")
            return

        blend = s.noise_blend
        if blend <= 0.0:
            s.heightmap = new_hm
        else:
            for r in range(s.height):
                for q in range(s.width):
                    s.heightmap[r][q] = blend * s.heightmap[r][q] + (1 - blend) * new_hm[r][q]

        # Wipe stale simulation results so Ocean/Temperature/Rainfall overlays
        # don't show the previous heightmap's data.
        s.ocean_mask  = [[False] * s.width for _ in range(s.height)]
        s.temperature = [[0.5]   * s.width for _ in range(s.height)]
        s.rainfall    = [[0.5]   * s.width for _ in range(s.height)]
        self._sim_dirty = True

        s.overlay = "height"
        dpg.set_value("overlay_radio", "Height")
        self._dirty = True
        dpg.set_value("status_bar", f"Noise generated (seed={seed}, shape={shape})")

    def _cb_export(self, sender, app_data) -> None:
        try:
            from .export import export_to_worldgen_result
            result = export_to_worldgen_result(self.state)
            out = Path("exported_world.pkl")
            with open(out, "wb") as f:
                pickle.dump(result, f)
            dpg.set_value("status_bar", f"Exported to {out.resolve()}")
        except Exception as e:
            dpg.set_value("status_bar", f"Export failed: {e}")


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
