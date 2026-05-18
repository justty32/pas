"""生物群系視覺化 — 縮放 + 簡易 GUI 版 (pygame)

操作：
    滾輪（地圖區）：縮放
    左鍵拖曳（地圖區）：平移
    Home：相機歸位
    Space：隨機 seed
    ESC：離開
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Optional

import pygame

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapcore.generation.climate import compute_temperature_celsius
from mapcore.generation.pipeline import generate_world
from mapcore.generation.postprocess import find_components, is_land
from mapcore.hex import DIRECTIONS, Hex
from mapcore.map import Hilliness, TerrainType
from mapcore.rivers import RiverClass, classify_river_strength, iter_river_edges

# ──────────────────────────────────────────────────────────────────────────────
# 視窗常數
# ──────────────────────────────────────────────────────────────────────────────
MAP_W, MAP_H  = 80, 50
PANEL_W       = 220
WINDOW_W      = 1280
WINDOW_H      = 760
MAP_AREA_W    = WINDOW_W - PANEL_W   # 1060

SQRT3         = math.sqrt(3)
HEX_MIN       = 4.0
HEX_MAX       = 60.0
HEX_INIT      = 16.0
ZOOM_STEP     = 1.15
MARGIN_X      = 10
MARGIN_Y      = 10

# ──────────────────────────────────────────────────────────────────────────────
# 色彩
# ──────────────────────────────────────────────────────────────────────────────
BG           = (12,  14,  20)
PANEL_BG     = (22,  26,  36)
PANEL_LINE   = (48,  54,  74)
RIVER_COLORS = {
    RiverClass.CREEK:       (150, 215, 255),  # 小溪：淺藍
    RiverClass.RIVER:       (70,  150, 240),  # 河流：藍
    RiverClass.LARGE_RIVER: (30,  80,  210),  # 大河：深藍
}
RIVER_WIDTHS = {
    RiverClass.CREEK:       1,
    RiverClass.RIVER:       3,
    RiverClass.LARGE_RIVER: 5,
}
TEXT_CLR     = (220, 220, 220)
DIM_CLR      = (130, 135, 158)
VALUE_CLR    = (120, 210, 130)
BTN_IDLE     = (48,  56,  80)
BTN_HOVER    = (64,  72, 104)
BTN_ACTIVE   = (70, 145, 225)
BTN_BORDER   = (80,  90, 124)
RAIL_CLR     = (55,  62,  86)
KNOB_CLR     = (90, 160, 240)

TERRAIN_COLOR = {
    int(TerrainType.OCEAN):     (20,  50, 110),
    int(TerrainType.COAST):     (70, 140, 200),
    int(TerrainType.PLAINS):    (200, 200, 110),
    int(TerrainType.GRASSLAND): (95,  175,  80),
    int(TerrainType.DESERT):    (230, 210, 130),
    int(TerrainType.TUNDRA):    (180, 200, 200),
    int(TerrainType.SNOW):      (240, 245, 250),
    int(TerrainType.FOREST):    (35,  110,  55),
    int(TerrainType.HILL):      (140, 110,  60),
    int(TerrainType.MOUNTAIN):  (110, 100, 100),
    int(TerrainType.LAKE):      (50,  120, 190),
}

HILLINESS_COLOR = {
    Hilliness.UNDEFINED:    (40,  50,  70),
    Hilliness.FLAT:         (220, 220, 200),
    Hilliness.SMALL_HILLS:  (180, 170, 130),
    Hilliness.LARGE_HILLS:  (140, 120,  90),
    Hilliness.MOUNTAINOUS:  (100,  90,  80),
    Hilliness.IMPASSABLE:   (60,   55,  50),
}

VIEW_TERRAIN   = "terrain"
VIEW_HEIGHT    = "height"
VIEW_MOISTURE  = "moisture"
VIEW_TEMP      = "temp"
VIEW_HILLINESS = "hilliness"
VIEW_FEATURES  = "features"

VIEW_LIST = [
    (VIEW_TERRAIN,   "地形"),
    (VIEW_HEIGHT,    "高度"),
    (VIEW_MOISTURE,  "濕度"),
    (VIEW_TEMP,      "溫度"),
    (VIEW_HILLINESS, "丘陵"),
    (VIEW_FEATURES,  "地物"),
]

RIVER_DENSITY_PRESETS = [
    # name       spawn      degrade  branch_th  branch_ch  min_sea  flow_scale  seed_spc
    # flow_scale = (e²-1) / spawn，讓 spawn 門檻恰好對應 strength≈90（RIVER低端）
    # seed_spc：seed 最小間距，較高的值讓鄰近河流合併為支流而非平行
    ("Dense",   2500.0,    700.0,   1500.0,    0.40,      3,       0.002556,   2),
    ("Medium",  9000.0,   2800.0,   6000.0,    0.28,      8,       0.000710,   3),
    ("Sparse", 28000.0,   9000.0,  19000.0,    0.18,     20,       0.000228,   4),
    ("Rare",   75000.0,  25000.0,  52000.0,    0.08,     40,       0.0000852,  5),
]

# 大陸形狀選項
SHAPE_OPTIONS = ["關", "島嶼", "群島", "盤古大陸", "諸大陸", "環海大陸", "破碎群島"]
SHAPE_VALUES  = [None, "island", "archipelago", "pangaea", "continents", "ring_sea", "shattered_archipelago"]

# 每種形狀的參數設定：(label, lo, hi, default, fmt, step) 或 None（不顯示）
# index 0 = slider_p1, index 1 = slider_p2
_NO_PARAM = None
SHAPE_PARAM_CFG: dict[Optional[str], tuple] = {
    None:                     (_NO_PARAM, _NO_PARAM),
    "island":                 (_NO_PARAM, _NO_PARAM),
    "archipelago":            (_NO_PARAM, _NO_PARAM),
    "pangaea":                (("陸地比", 0.35, 1.50, 0.70, "{:.2f}", 0.05), _NO_PARAM),
    "continents":             (("大陸數", 2.0, 7.0, 3.0, "{:.0f}", 1.0),
                               ("陸地比", 0.20, 2.50, 0.45, "{:.2f}", 0.05)),
    "ring_sea":               (("環寬",   0.20, 0.90, 0.45, "{:.2f}", 0.05), _NO_PARAM),
    "shattered_archipelago":  (("島嶼數", 5.0, 30.0, 12.0, "{:.0f}", 1.0),
                               ("島大小", 0.04, 0.20, 0.09, "{:.3f}", 0.01)),
}


# ──────────────────────────────────────────────────────────────────────────────
# GUI 元件
# ──────────────────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect: pygame.Rect, label: str, active: bool = False):
        self.rect   = rect
        self.label  = label
        self.active = active

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, mp: tuple) -> None:
        if self.active:
            bg = BTN_ACTIVE
        elif self.rect.collidepoint(mp):
            bg = BTN_HOVER
        else:
            bg = BTN_IDLE
        pygame.draw.rect(surf, bg, self.rect, border_radius=4)
        pygame.draw.rect(surf, BTN_BORDER, self.rect, 1, border_radius=4)
        s = font.render(self.label, True, TEXT_CLR)
        surf.blit(s, s.get_rect(center=self.rect.center))

    def hit(self, pos: tuple) -> bool:
        return bool(self.rect.collidepoint(pos))


class Slider:
    """水平拖曳滑條；regen 在 mouseup 才觸發。"""
    _LBL_H   = 16
    _TOTAL_H = 34

    def __init__(self, x: int, y: int, w: int, label: str,
                 lo: float, hi: float, value: float,
                 fmt: str = "{:.2f}", step: Optional[float] = None,
                 visible: bool = True):
        self.x, self.y, self.w = x, y, w
        self.label   = label
        self.lo, self.hi = float(lo), float(hi)
        self.value   = float(value)
        self.fmt     = fmt
        self.step    = step
        self.visible = visible
        self.rail    = pygame.Rect(x, y + self._LBL_H + 4, w, 5)
        self._drag   = False

    def reconfigure(self, label: str, lo: float, hi: float, default: float,
                    fmt: str = "{:.2f}", step: Optional[float] = None) -> None:
        """切換 shape 時呼叫，重設所有設定並重置值為預設值。"""
        self.label   = label
        self.lo, self.hi = float(lo), float(hi)
        self.value   = float(default)
        self.fmt     = fmt
        self.step    = step
        self.visible = True
        self._drag   = False

    @property
    def _kx(self) -> int:
        t = (self.value - self.lo) / (self.hi - self.lo)
        return int(self.x + t * self.w)

    def _snap(self, v: float) -> float:
        if self.step:
            v = round(v / self.step) * self.step
        return max(self.lo, min(self.hi, v))

    def _from_px(self, px: int) -> None:
        t = max(0.0, min(1.0, (px - self.x) / self.w))
        self.value = self._snap(self.lo + t * (self.hi - self.lo))

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, _mp) -> None:
        if not self.visible:
            return
        lbl = font.render(f"{self.label}  {self.fmt.format(self.value)}", True, DIM_CLR)
        surf.blit(lbl, (self.x, self.y))
        pygame.draw.rect(surf, RAIL_CLR, self.rail, border_radius=2)
        knob = pygame.Rect(self._kx - 5, self.rail.centery - 6, 10, 12)
        pygame.draw.rect(surf, KNOB_CLR, knob, border_radius=2)

    def on_mousedown(self, pos: tuple) -> bool:
        if not self.visible:
            return False
        area = pygame.Rect(self.x - 4, self.y, self.w + 8, self._TOTAL_H)
        if area.collidepoint(pos):
            self._drag = True
            self._from_px(pos[0])
            return True
        return False

    def on_mousemove(self, pos: tuple) -> None:
        if self._drag:
            self._from_px(pos[0])

    def on_mouseup(self) -> bool:
        changed = self._drag
        self._drag = False
        return changed


class CycleButton:
    def __init__(self, rect: pygame.Rect, options: list[str], idx: int = 0):
        self.rect    = rect
        self.options = options
        self.idx     = idx

    @property
    def current(self) -> str:
        return self.options[self.idx]

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, mp: tuple) -> None:
        bg = BTN_HOVER if self.rect.collidepoint(mp) else BTN_IDLE
        pygame.draw.rect(surf, bg, self.rect, border_radius=4)
        pygame.draw.rect(surf, BTN_BORDER, self.rect, 1, border_radius=4)
        s = font.render(f"< {self.current} >", True, VALUE_CLR)
        surf.blit(s, s.get_rect(center=self.rect.center))

    def hit(self, pos: tuple) -> bool:
        if self.rect.collidepoint(pos):
            self.idx = (self.idx + 1) % len(self.options)
            return True
        return False


# ──────────────────────────────────────────────────────────────────────────────
# 繪製輔助
# ──────────────────────────────────────────────────────────────────────────────
def _feature_color(fid: int) -> tuple:
    if fid < 0:
        return (40, 40, 50)
    hue = (fid * 0.61803398875) % 1.0
    i = int(hue * 6)
    f = hue * 6 - i
    p  = int(255 * 0.78 * (1 - 0.55))
    qc = int(255 * 0.78 * (1 - 0.55 * f))
    tc = int(255 * 0.78 * (1 - 0.55 * (1 - f)))
    v  = int(255 * 0.78)
    return [(v, tc, p), (qc, v, p), (p, v, tc), (p, qc, v), (tc, p, v), (v, p, qc)][i % 6]


def _gray(v: float) -> tuple:
    g = max(0, min(255, int(v * 255)))
    return g, g, g


def _temp_norm(row: int, col: int, hm, H: int) -> float:
    c = compute_temperature_celsius(row, H, hm[row][col])
    return max(0.0, min(1.0, (c + 40.0) / 70.0))


def _heat(v: float) -> tuple:
    stops = [
        (0.0, (40,  60, 200)),
        (0.4, (80, 200, 200)),
        (0.6, (120, 220, 120)),
        (0.8, (240, 220,  90)),
        (1.0, (230,  80,  60)),
    ]
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]; v1, c1 = stops[i + 1]
        if v <= v1:
            t = (v - v0) / (v1 - v0) if v1 > v0 else 0.0
            return tuple(int(c0[k] * (1 - t) + c1[k] * t) for k in range(3))  # type: ignore
    return stops[-1][1]


def _h2p(h: Hex, cam_x: float, cam_y: float, hz: float) -> tuple:
    x = hz * (SQRT3 * h.q + SQRT3 / 2 * (h.r & 1)) + MARGIN_X - cam_x
    y = hz * 1.5 * h.r + MARGIN_Y - cam_y
    return x, y


def _corners(cx: float, cy: float, hz: float) -> list:
    return [
        (cx + hz * math.cos(math.radians(60 * i - 30)),
         cy + hz * math.sin(math.radians(60 * i - 30)))
        for i in range(6)
    ]


def _cjk_font(size: int) -> pygame.font.Font:
    names = [
        "notosanscjktc", "notosanscjksc",
        "microsoftjhenghei", "msjh",
        "simhei", "simsun", "monospace",
    ]
    return pygame.font.SysFont(",".join(names), size)


def _sep(surf: pygame.Surface, x: int, y: int, w: int) -> None:
    pygame.draw.line(surf, PANEL_LINE, (x, y), (x + w, y))


# ──────────────────────────────────────────────────────────────────────────────
# 主程式
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("mapcore_py — biome")
    font     = _cjk_font(13)
    lbl_font = _cjk_font(14)
    clock    = pygame.time.Clock()

    # ── 狀態 ──────────────────────────────────────────────────────────────────
    seed             = random.randint(0, 99999)
    sea_level        = 0.40
    view             = VIEW_TERRAIN
    do_post          = True
    do_lakes         = False
    show_rivers      = True
    river_preset_idx = 1   # Medium
    hex_size         = HEX_INIT
    cam_x, cam_y     = 0.0, 0.0
    shape_idx        = 0
    ridge_weight     = 0.0
    ridge_dir        = 0.0
    rain_shadow      = 0.0

    map_drag   = False
    drag_start = (0, 0)
    cam_start  = (0.0, 0.0)

    # ── GUI 面板配置 ───────────────────────────────────────────────────────────
    px  = MAP_AREA_W + 8
    pw  = PANEL_W - 14
    bw2 = (pw - 4) // 2

    # y 座標（形狀參數 slider 插入在 Y_SHAPE 與 Y_RIDGE 之間，各佔 34px）
    Y_TITLE    = 8
    Y_SEED     = 26
    Y_SEED_BTN = 44
    Y_SEP1     = 72
    Y_VIEW_LBL = 78
    Y_VIEW0    = 94     # 3 行 × 26px → ends 172
    Y_SEP2     = 176
    Y_SEA      = 182    # slider 34px → ends 216
    Y_SEP_HM   = 220
    Y_SHAPE    = 226    # CycleButton 24px → ends 250
    Y_SHAPE_P1 = 254    # slider 34px → ends 288（依 shape 顯示）
    Y_SHAPE_P2 = 292    # slider 34px → ends 326（依 shape 顯示）
    Y_RIDGE    = 330    # slider 34px → ends 364
    Y_RIDGE_DIR = 364   # slider 34px → ends 398（山脊走向）
    Y_SHADOW   = 402    # slider 34px → ends 436
    Y_SEP3     = 440
    Y_POST     = 446    # button 24px → ends 470
    Y_LAKES    = 474    # button 24px → ends 498
    Y_SEP4     = 502
    Y_RIVERS   = 508    # button 24px → ends 532
    Y_DENSITY  = 536    # cycle  24px → ends 560
    Y_SEP5     = 564
    Y_STATS    = 570

    btn_random = Button(pygame.Rect(px,           Y_SEED_BTN, bw2, 24), "Random")
    btn_regen  = Button(pygame.Rect(px + bw2 + 4, Y_SEED_BTN, bw2, 24), "Regen")

    btns_view: list[Button] = []
    for i, (vk, vl) in enumerate(VIEW_LIST):
        col = i % 2; row = i // 2
        r = pygame.Rect(px + col * (bw2 + 4), Y_VIEW0 + row * 26, bw2, 22)
        btns_view.append(Button(r, vl, active=(vk == view)))

    slider_sea    = Slider(px, Y_SEA,      pw, "海平面", 0.0, 0.8, sea_level,    "{:.2f}", step=0.01)
    btn_shape     = CycleButton(pygame.Rect(px, Y_SHAPE, pw, 24), SHAPE_OPTIONS, shape_idx)
    # 形狀專屬參數 slider（visible 由 _apply_shape_cfg 控制）
    slider_p1     = Slider(px, Y_SHAPE_P1, pw, "—", 0.0, 1.0, 0.5, visible=False)
    slider_p2     = Slider(px, Y_SHAPE_P2, pw, "—", 0.0, 1.0, 0.5, visible=False)
    slider_ridge     = Slider(px, Y_RIDGE,     pw, "山脊",   0.0,   1.0, ridge_weight, "{:.2f}", step=0.05)
    slider_ridge_dir = Slider(px, Y_RIDGE_DIR, pw, "走向°",  0.0, 180.0, ridge_dir,    "{:.0f}", step=15.0)
    slider_shadow    = Slider(px, Y_SHADOW,    pw, "雨影",   0.0,   1.0, rain_shadow,  "{:.2f}", step=0.05)

    btn_post    = Button(pygame.Rect(px, Y_POST,   pw, 24), "後處理: ON",  active=True)
    btn_lakes   = Button(pygame.Rect(px, Y_LAKES,  pw, 24), "湖泊: OFF",   active=False)
    btn_rivers  = Button(pygame.Rect(px, Y_RIVERS, pw, 24), "河流: ON",    active=True)
    btn_density = CycleButton(
        pygame.Rect(px, Y_DENSITY, pw, 24),
        [p[0] for p in RIVER_DENSITY_PRESETS],
        river_preset_idx,
    )

    active_slider: Optional[Slider] = None
    all_sliders = [slider_sea, slider_p1, slider_p2, slider_ridge, slider_ridge_dir, slider_shadow]

    # ── 形狀參數輔助 ──────────────────────────────────────────────────────────
    def _apply_shape_cfg(shape_name: Optional[str]) -> None:
        """依 shape 更新 slider_p1 / slider_p2 的標籤、範圍、預設值與可見度。"""
        cfg = SHAPE_PARAM_CFG.get(shape_name, (_NO_PARAM, _NO_PARAM))
        for sl, c in zip([slider_p1, slider_p2], cfg):
            if c is None:
                sl.visible = False
                sl._drag   = False
            else:
                label, lo, hi, default, fmt, step = c
                sl.reconfigure(label, lo, hi, default, fmt, step)

    def _get_shape_params(shape_name: Optional[str]) -> Optional[dict]:
        """從目前 slider_p1/p2 值建立 shape_params dict。"""
        if shape_name == "pangaea":
            return {"land_ratio": slider_p1.value}
        if shape_name == "continents":
            return {"num_continents": max(1, int(round(slider_p1.value))),
                    "land_ratio":     slider_p2.value}
        if shape_name == "ring_sea":
            return {"land_ratio": slider_p1.value}
        if shape_name == "shattered_archipelago":
            return {"num_islands":  max(1, int(round(slider_p1.value))),
                    "island_size":  slider_p2.value}
        return None

    # 初始化 shape cfg（預設為「關」，p1/p2 都不顯示）
    _apply_shape_cfg(SHAPE_VALUES[shape_idx])

    # ── 地圖生成 ──────────────────────────────────────────────────────────────
    def regen():
        _, sp, dg, br_th, br_ch, min_sea, flow_scale, seed_spc = RIVER_DENSITY_PRESETS[river_preset_idx]
        shape_name = SHAPE_VALUES[shape_idx]
        r = generate_world(
            MAP_W, MAP_H,
            seed=seed,
            sea_level=sea_level,
            post_process=do_post,
            lake_depressions=do_lakes,
            climate=True,
            rivers=True,
            features=True,
            heightmap_ridge_weight=ridge_weight,
            heightmap_ridge_direction=ridge_dir,
            heightmap_shape=shape_name,
            heightmap_shape_params=_get_shape_params(shape_name),
            climate_rain_shadow_strength=rain_shadow,
            river_spawn_flow_threshold=sp,
            river_degrade_threshold=dg,
            river_branch_flow_threshold=br_th,
            river_branch_chance=br_ch,
            river_min_sea_size=min_sea,
            river_flow_strength_scale=flow_scale,
            river_min_seed_spacing=seed_spc,
        )
        return r.tile_map, r.heightmap, r.moisture

    tile_map, heightmap, moisture = regen()
    dirty   = False
    running = True

    # ── 快取統計 ──────────────────────────────────────────────────────────────
    def _compute_stats(tm):
        c: dict = {}
        for _, t in tm:
            c[t.terrain] = c.get(t.terrain, 0) + 1
        total     = sum(c.values()) or 1
        water_n   = c.get(int(TerrainType.OCEAN), 0) + c.get(int(TerrainType.COAST), 0)
        lake_n    = c.get(int(TerrainType.LAKE), 0)
        lc        = find_components(tm, is_land)
        return {
            "land_pct":   (total - water_n - lake_n) * 100 // total,
            "ocean_pct":  water_n * 100 // total,
            "lake_tiles": lake_n,
            "n_islands":  len(lc),
            "biggest":    max((len(x) for x in lc), default=0),
            "feat_count": len(tm.features) if tm.features is not None else 0,
            "edge_count": sum(1 for _ in iter_river_edges(tm)),
        }

    cached = _compute_stats(tile_map)

    # ── 主迴圈 ────────────────────────────────────────────────────────────────
    while running:
        mp = pygame.mouse.get_pos()

        btn_post.label    = f"後處理: {'ON' if do_post else 'OFF'}"
        btn_post.active   = do_post
        btn_lakes.label   = f"湖泊: {'ON' if do_lakes else 'OFF'}"
        btn_lakes.active  = do_lakes
        btn_rivers.label  = f"河流: {'ON' if show_rivers else 'OFF'}"
        btn_rivers.active = show_rivers
        for i, (vk, _) in enumerate(VIEW_LIST):
            btns_view[i].active = (vk == view)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False

            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key == pygame.K_SPACE:
                    seed = random.randint(0, 99999); dirty = True
                elif ev.key == pygame.K_HOME:
                    cam_x, cam_y = 0.0, 0.0

            elif ev.type == pygame.MOUSEWHEEL:
                if mp[0] < MAP_AREA_W:
                    factor = ZOOM_STEP if ev.y > 0 else 1.0 / ZOOM_STEP
                    hex_size = max(HEX_MIN, min(HEX_MAX, hex_size * factor))

            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if mp[0] < MAP_AREA_W:
                    map_drag   = True
                    drag_start = mp
                    cam_start  = (cam_x, cam_y)
                else:
                    if btn_random.hit(mp):
                        seed = random.randint(0, 99999); dirty = True
                    elif btn_regen.hit(mp):
                        dirty = True
                    elif btn_post.hit(mp):
                        do_post = not do_post; dirty = True
                    elif btn_lakes.hit(mp):
                        do_lakes = not do_lakes; dirty = True
                    elif btn_rivers.hit(mp):
                        show_rivers = not show_rivers
                    elif btn_density.hit(mp):
                        river_preset_idx = btn_density.idx; dirty = True
                    elif btn_shape.hit(mp):
                        shape_idx = btn_shape.idx
                        _apply_shape_cfg(SHAPE_VALUES[shape_idx])
                        dirty = True
                    else:
                        for i, (vk, _) in enumerate(VIEW_LIST):
                            if btns_view[i].hit(mp):
                                view = vk; break
                    for sl in all_sliders:
                        if sl.on_mousedown(mp):
                            active_slider = sl
                            break

            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                map_drag = False
                if active_slider:
                    if active_slider.on_mouseup():
                        sea_level    = slider_sea.value
                        ridge_weight = slider_ridge.value
                        ridge_dir    = slider_ridge_dir.value
                        rain_shadow  = slider_shadow.value
                        dirty = True
                    active_slider = None

            elif ev.type == pygame.MOUSEMOTION:
                if map_drag:
                    cam_x = cam_start[0] - (mp[0] - drag_start[0])
                    cam_y = cam_start[1] - (mp[1] - drag_start[1])
                if active_slider:
                    active_slider.on_mousemove(mp)

        if dirty:
            sea_level    = slider_sea.value
            ridge_weight = slider_ridge.value
            ridge_dir    = slider_ridge_dir.value
            rain_shadow  = slider_shadow.value
            tile_map, heightmap, moisture = regen()
            cached = _compute_stats(tile_map)
            dirty = False

        # ── 繪製地圖 ──────────────────────────────────────────────────────────
        screen.fill(BG)
        screen.set_clip(pygame.Rect(0, 0, MAP_AREA_W, WINDOW_H))

        for row in range(MAP_H):
            for col in range(MAP_W):
                cx, cy = _h2p(Hex(col, row), cam_x, cam_y, hex_size)
                if cx < -hex_size or cx > MAP_AREA_W + hex_size: continue
                if cy < -hex_size or cy > WINDOW_H + hex_size:   continue
                pts  = _corners(cx, cy, hex_size)
                tile = tile_map.get(Hex(col, row))
                if view == VIEW_TERRAIN:
                    color = TERRAIN_COLOR.get(tile.terrain, (128, 128, 128))
                elif view == VIEW_HEIGHT:
                    color = _gray(heightmap[row][col])
                elif view == VIEW_MOISTURE:
                    color = _gray(moisture[row][col])
                elif view == VIEW_TEMP:
                    color = _heat(_temp_norm(row, col, heightmap, MAP_H))
                elif view == VIEW_HILLINESS:
                    color = HILLINESS_COLOR.get(tile.hilliness, (50, 50, 60))
                else:
                    color = _feature_color(tile.feature_id)
                pygame.draw.polygon(screen, color, pts)

        if show_rivers:
            for h, d, strength in iter_river_edges(tile_map):
                nb = h + DIRECTIONS[d]
                ox, oy = _h2p(h,  cam_x, cam_y, hex_size)
                nx, ny = _h2p(nb, cam_x, cam_y, hex_size)
                rc = classify_river_strength(strength)
                pygame.draw.line(screen, RIVER_COLORS[rc],
                                 (int(ox), int(oy)), (int(nx), int(ny)),
                                 RIVER_WIDTHS[rc])

        if view == VIEW_FEATURES and tile_map.features is not None:
            for f in tile_map.features:
                cx, cy = _h2p(f.center, cam_x, cam_y, hex_size)
                if -60 < cx < MAP_AREA_W + 60 and -30 < cy < WINDOW_H + 30:
                    lbl = lbl_font.render(f.name, True, (250, 250, 250))
                    shd = lbl_font.render(f.name, True, (0, 0, 0))
                    bx  = int(cx) - lbl.get_width() // 2
                    by  = int(cy) - lbl.get_height() // 2
                    screen.blit(shd, (bx + 1, by + 1))
                    screen.blit(lbl, (bx, by))

        screen.set_clip(None)

        # ── 繪製 GUI 面板 ──────────────────────────────────────────────────────
        pygame.draw.rect(screen, PANEL_BG, (MAP_AREA_W, 0, PANEL_W, WINDOW_H))
        pygame.draw.line(screen, PANEL_LINE, (MAP_AREA_W, 0), (MAP_AREA_W, WINDOW_H), 1)

        screen.blit(font.render("mapcore_py  biome", True, TEXT_CLR), (px, Y_TITLE))
        screen.blit(font.render(f"Seed: {seed}", True, VALUE_CLR),     (px, Y_SEED))
        btn_random.draw(screen, font, mp)
        btn_regen.draw(screen, font, mp)

        _sep(screen, px, Y_SEP1, pw)
        screen.blit(font.render("── 視角 ──", True, DIM_CLR), (px, Y_VIEW_LBL))
        for b in btns_view:
            b.draw(screen, font, mp)

        _sep(screen, px, Y_SEP2, pw)
        slider_sea.draw(screen, font, mp)

        _sep(screen, px, Y_SEP_HM, pw)
        btn_shape.draw(screen, font, mp)
        slider_p1.draw(screen, font, mp)
        slider_p2.draw(screen, font, mp)
        slider_ridge.draw(screen, font, mp)
        slider_ridge_dir.draw(screen, font, mp)
        slider_shadow.draw(screen, font, mp)

        _sep(screen, px, Y_SEP3, pw)
        btn_post.draw(screen, font, mp)
        btn_lakes.draw(screen, font, mp)

        _sep(screen, px, Y_SEP4, pw)
        btn_rivers.draw(screen, font, mp)
        btn_density.draw(screen, font, mp)

        _sep(screen, px, Y_SEP5, pw)

        stats = [
            f"陸地 {cached['land_pct']}%  海洋 {cached['ocean_pct']}%",
            f"湖泊 {cached['lake_tiles']} 格  島嶼 {cached['n_islands']}",
            f"最大島 {cached['biggest']} 格",
            f"地物 {cached['feat_count']}  河流邊 {cached['edge_count']}",
            f"縮放 {hex_size:.1f}px",
            f"視角 ({int(cam_x)}, {int(cam_y)})",
        ]
        hints = [
            "滾輪=縮放  拖曳=平移",
            "Space=換seed  Home=歸位  ESC",
        ]
        for i, s in enumerate(stats):
            screen.blit(font.render(s, True, TEXT_CLR), (px, Y_STATS + i * 19))
        y_hint = Y_STATS + len(stats) * 19 + 6
        for i, s in enumerate(hints):
            screen.blit(font.render(s, True, DIM_CLR), (px, y_hint + i * 18))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
