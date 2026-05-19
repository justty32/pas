"""World Sculptor — Dear PyGui interactive hex map editor.

Requirements: pip install dearpygui
Launch: python run_editor.py
"""
from __future__ import annotations

import pickle
from pathlib import Path

import dearpygui.dearpygui as dpg

from .state import EditorState
from .hex_layout import hex_to_pixel, pixel_to_hex, hex_corners
from .tools import apply_brush, apply_ridge, apply_rift, toggle_water_source
from .sim.hydrology import run_flood_fill
from .sim.climate import run_climate

# ── Constants ────────────────────────────────────────────────────────────────

PANEL_W   = 240
CANVAS_W  = 1140   # fixed drawlist width
CANVAS_H  = 790    # fixed drawlist height
_CAM_INIT = 40.0   # initial camera offset (pixels)

_BORDER = (0, 0, 0, 25)

# ── Color helpers ────────────────────────────────────────────────────────────

def _height_color(h: float, is_ocean: bool) -> tuple[int, int, int, int]:
    if is_ocean:
        t = h * 2.5
        return (int(20 + 40 * t), int(50 + 90 * t), int(120 + 80 * t), 255)
    if h < 0.10:
        return (180, 155, 100, 255)
    if h < 0.38:
        return (int(90 + 40*h*3), int(170 - 20*h*3), int(70 + 10*h*3), 255)
    if h < 0.58:
        return (int(110 + 30*h*2), int(140 + 10*h*2), int(55 + 10*h*2), 255)
    if h < 0.72:
        return (int(140 + 30*h), int(110 + 20*h), int(55 + 10*h), 255)
    if h < 0.87:
        return (110, 100, 95, 255)
    v = int(195 + 60 * (h - 0.87) / 0.13)
    return (v, v, v, 255)


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
        self._dirty  = True
        self._drag_start: tuple[int, int] | None = None
        self._last_hex:   tuple[int, int] | None = None
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
            if self._dirty:
                self.redraw_canvas()
                self._dirty = False
            dpg.render_dearpygui_frame()

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
                    color = _height_color(h, is_ocean)

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

    def _on_mouse_move(self, sender, app_data) -> None:
        if not dpg.is_item_hovered("canvas_window"):
            return
        if self.state.current_tool not in ("raise", "lower"):
            return
        if not (dpg.is_mouse_button_down(0) or dpg.is_mouse_button_down(1)):
            return
        q, r = self._get_hex()
        if (q, r) == self._last_hex or not self.state.in_bounds(q, r):
            return
        self._last_hex = (q, r)
        delta = self.state.brush_strength
        if dpg.is_mouse_button_down(1) or self.state.current_tool == "lower":
            delta = -delta
        apply_brush(self.state, q, r, delta)
        self._dirty = True

    def _on_mouse_click(self, sender, app_data) -> None:
        if not dpg.is_item_hovered("canvas_window"):
            return
        button = app_data
        q, r   = self._get_hex()
        if not self.state.in_bounds(q, r):
            return
        tool = self.state.current_tool
        if tool in ("raise", "lower"):
            delta = self.state.brush_strength * (1 if tool == "raise" and button == 0 else -1)
            apply_brush(self.state, q, r, delta)
            self._last_hex = (q, r)
            self._dirty = True
        elif tool == "water_source" and button == 0:
            toggle_water_source(self.state, q, r)
            self._dirty = True
        elif tool in ("ridge", "rift") and button == 0:
            self._drag_start = (q, r)

    def _on_mouse_release(self, sender, app_data) -> None:
        if app_data != 0:
            return
        self._last_hex = None
        if self._drag_start is None:
            return
        q, r = self._get_hex()
        q0, r0 = self._drag_start
        self._drag_start = None
        if not self.state.in_bounds(q, r):
            return
        if self.state.current_tool == "ridge":
            apply_ridge(self.state, q0, r0, q, r)
        elif self.state.current_tool == "rift":
            apply_rift(self.state, q0, r0, q, r)
        self._dirty = True

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

    def _cb_flood_fill(self, sender, app_data) -> None:
        run_flood_fill(self.state)
        dpg.set_value("overlay_radio", "Ocean")
        self.state.overlay = "ocean"
        self._dirty = True
        dpg.set_value("status_bar", "Flood fill done.")

    def _cb_climate(self, sender, app_data) -> None:
        run_climate(self.state)
        dpg.set_value("overlay_radio", "Temperature")
        self.state.overlay = "temperature"
        self._dirty = True
        dpg.set_value("status_bar", "Climate simulation done.")

    def _cb_new_map(self, sender, app_data) -> None:
        w, h = dpg.get_value("new_w"), dpg.get_value("new_h")
        self.state.new_map(w, h)
        self._cam_x = _CAM_INIT
        self._cam_y = _CAM_INIT
        self._dirty = True
        dpg.set_value("status_bar", f"New map {w}x{h}")

    def _cb_reset(self, sender, app_data) -> None:
        self.state.reset()
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
