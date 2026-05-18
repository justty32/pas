"""高程 noise (Phase 1)。

純 stdlib 的多層 value noise (fBm-like)：
1. 每個 octave 各自產生一張低解析度隨機網格 (值 ∈ [0,1])。
2. 用 smoothstep + 雙線性插值 (bilinear) 放大到 width×height。
3. 用 persistence^octave 當權重加總，最後除以權重和，輸出仍在 [0,1]。

頻率倍增 (lacunarity=2)。要换 Perlin/Simplex 之後再說，先求架構與決定性。
對齊 analysis/wesnoth/details/encyclopedia_vol1_heightmap.md 的分層概念。
"""

from __future__ import annotations

import math
import random
from typing import Optional

# 山脊各向異性壓縮比：沿稜線方向採樣範圍壓縮至此倍數（越小越筆直）
# 0.1 = 沿稜線只看 10% coarse grid → 幾乎純 1D 橫向 noise → 形成清晰條帶
_RIDGE_ANISOTROPY = 0.1

# 所有合法的 shape 名稱；同時作為文件與驗證用
_VALID_SHAPES: frozenset[str] = frozenset({
    "island",                 # 單一大島（原有）
    "archipelago",            # 少量中型群島（原有）
    "pangaea",                # 盤古大陸：單一超大陸居中
    "continents",             # 諸大陸：N 塊大陸分散
    "ring_sea",               # 環海大陸：環形陸地包圍內海
    "shattered_archipelago",  # 破碎群島：大量小島散布
})


def _smoothstep(t: float) -> float:
    # Perlin 用的 Hermite 平滑曲線：t² × (3 − 2t)
    # 比起純線性，能讓 grid cell 邊界處看不到「方塊感」（一階導數連續）
    return t * t * (3.0 - 2.0 * t)


def _bilinear(coarse: list[list[float]], x: float, y: float) -> float:
    """在 coarse 網格上做 smoothstep + bilinear 取樣；x、y 為 coarse 座標系。"""
    gh = len(coarse)
    gw = len(coarse[0])
    x = max(0.0, min(x, float(gw - 1)))  # clamp：防止旋轉後座標越界
    y = max(0.0, min(y, float(gh - 1)))
    x0 = int(x)
    y0 = int(y)
    x1 = min(x0 + 1, gw - 1)
    y1 = min(y0 + 1, gh - 1)
    fx = _smoothstep(x - x0)
    fy = _smoothstep(y - y0)
    top = coarse[y0][x0] * (1.0 - fx) + coarse[y0][x1] * fx
    bot = coarse[y1][x0] * (1.0 - fx) + coarse[y1][x1] * fx
    return top * (1.0 - fy) + bot * fy


def _make_shape_mask(
    width: int,
    height: int,
    shape: str,
    rng: random.Random,
    params: Optional[dict] = None,
) -> list[list[float]]:
    """生成形狀遮罩，值 ∈ [0, 1]；1=中心（不壓制），0=邊緣（完全壓低）。

    params 為 shape 專屬的可選參數：
        pangaea:
            land_ratio (float, 0~1, default 0.55) — 大陸佔地圖半對角線的比例
        continents:
            num_continents (int,   default 3)     — 大陸數量（幾塊）
            land_ratio     (float, default 0.4)   — 整體陸地占比（越大每塊大陸越大）
        ring_sea:
            land_ratio (float, default 0.4)        — 環形陸帶寬度（越大越寬）
        shattered_archipelago:
            num_islands  (int,   default 12)       — 島嶼數量
            island_size  (float, default 0.08)     — 單島半徑（以 min(W,H) 為 1）
    """
    p = params or {}

    if shape == "island":
        # 單一大島：中心高、邊緣低
        cx = (width - 1) / 2.0
        cy = (height - 1) / 2.0
        rx = max(cx, 1.0)
        ry = max(cy, 1.0)
        mask = [[0.0] * width for _ in range(height)]
        for r in range(height):
            for q in range(width):
                dx = (q - cx) / rx
                dy = (r - cy) / ry
                d = (dx * dx + dy * dy) ** 0.5
                mask[r][q] = max(0.0, 1.0 - d ** 1.4)
        return mask

    elif shape == "archipelago":
        # 少量中型島嶼（3~6 個）隨機散布
        n = rng.randint(3, 6)
        radius = min(width, height) * 0.22
        centers = [
            (rng.uniform(0.15, 0.85) * width, rng.uniform(0.15, 0.85) * height)
            for _ in range(n)
        ]
        mask = [[0.0] * width for _ in range(height)]
        for r in range(height):
            for q in range(width):
                best = 0.0
                for icx, icy in centers:
                    dx = (q - icx) / radius
                    dy = (r - icy) / (radius * 0.8)
                    d = (dx * dx + dy * dy) ** 0.5
                    best = max(best, max(0.0, 1.0 - d ** 1.4))
                mask[r][q] = best
        return mask

    elif shape == "pangaea":
        # 盤古大陸：單一超大陸居中，land_ratio 控制大小
        land_ratio = float(p.get("land_ratio", 0.55))
        cx = (width - 1) / 2.0
        cy = (height - 1) / 2.0
        # land_r：大陸半徑，以中心到角落的距離為基準；1.0=蓋到角落
        half_diag = (cx ** 2 + cy ** 2) ** 0.5
        land_r = max(half_diag * land_ratio, 1.0)
        mask = [[0.0] * width for _ in range(height)]
        for r in range(height):
            for q in range(width):
                d = ((q - cx) ** 2 + (r - cy) ** 2) ** 0.5
                mask[r][q] = max(0.0, 1.0 - (d / land_r) ** 1.3)
        return mask

    elif shape == "continents":
        # 諸大陸：N 塊大陸分散，每塊略帶隨機橢圓形
        num_continents = int(p.get("num_continents", 3))
        land_ratio = float(p.get("land_ratio", 0.4))

        min_side = min(width, height)
        # 每塊大陸半徑：依陸地面積預算 (land_ratio × W × H / n) 開根號估算
        # 無硬性上限，允許 land_ratio > 1 時形成超大陸（blob 間重疊合併為單一大陸）
        blob_r = (land_ratio * width * height / num_continents) ** 0.5 * 0.65
        blob_r = max(min_side * 0.12, blob_r)

        # 嘗試以 min_spacing 間隔排放大陸中心；超時退回隨機
        min_spacing = blob_r * 1.2
        margin = blob_r * 0.4
        centers: list[tuple[float, float, float]] = []  # (cx, cy, aspect_ratio)
        for _ in range(num_continents * 40):
            if len(centers) >= num_continents:
                break
            cx_c = rng.uniform(margin, width - 1 - margin)
            cy_c = rng.uniform(margin, height - 1 - margin)
            if all((cx_c - ox) ** 2 + (cy_c - oy) ** 2 >= min_spacing ** 2
                   for ox, oy, _ in centers):
                centers.append((cx_c, cy_c, rng.uniform(0.6, 1.5)))
        while len(centers) < num_continents:
            centers.append((
                rng.uniform(0.15 * width,  0.85 * width),
                rng.uniform(0.15 * height, 0.85 * height),
                1.0,
            ))

        mask = [[0.0] * width for _ in range(height)]
        for r in range(height):
            for q in range(width):
                best = 0.0
                for icx, icy, ar in centers:
                    dx = (q - icx) / blob_r
                    dy = (r - icy) / (blob_r * ar)
                    d = (dx * dx + dy * dy) ** 0.5
                    best = max(best, max(0.0, 1.0 - d ** 1.2))
                mask[r][q] = best
        return mask

    elif shape == "ring_sea":
        # 環海大陸：環形陸帶包圍中央內海，land_ratio 控制陸帶寬度
        land_ratio = float(p.get("land_ratio", 0.4))
        cx = (width - 1) / 2.0
        cy = (height - 1) / 2.0
        min_half = min(cx, cy)
        ring_r = min_half * 0.55                       # 陸帶峰值半徑
        ring_w = max(min_half * (0.2 + land_ratio * 0.35), 1.0)  # 陸帶半寬

        mask = [[0.0] * width for _ in range(height)]
        for r in range(height):
            for q in range(width):
                d = ((q - cx) ** 2 + (r - cy) ** 2) ** 0.5
                d_from_ring = abs(d - ring_r)
                mask[r][q] = max(0.0, 1.0 - (d_from_ring / ring_w) ** 1.5)
        return mask

    elif shape == "shattered_archipelago":
        # 破碎群島：大量小島散布全圖
        num_islands = int(p.get("num_islands", 12))
        island_size = float(p.get("island_size", 0.08))
        radius = max(min(width, height) * island_size, 2.0)

        # 預先為每個島計算隨機橢圓比例（不可在像素迴圈內呼叫 rng）
        centers: list[tuple[float, float, float]] = [
            (
                rng.uniform(0.05, 0.95) * width,
                rng.uniform(0.05, 0.95) * height,
                rng.uniform(0.7, 1.4),
            )
            for _ in range(num_islands)
        ]
        mask = [[0.0] * width for _ in range(height)]
        for r in range(height):
            for q in range(width):
                best = 0.0
                for icx, icy, ar in centers:
                    dx = (q - icx) / radius
                    dy = (r - icy) / (radius * ar)
                    d = (dx * dx + dy * dy) ** 0.5
                    best = max(best, max(0.0, 1.0 - d ** 1.5))
                mask[r][q] = best
        return mask

    raise ValueError(f"unknown shape {shape!r}; valid shapes: {sorted(_VALID_SHAPES)}")


def generate_heightmap(
    width: int,
    height: int,
    seed: Optional[int] = None,
    octaves: int = 4,
    persistence: float = 0.5,
    base_frequency: int = 4,
    ridge_weight: float = 0.0,
    ridge_direction: float = 0.0,
    ridge_direction_variation: float = 90.0,
    shape: Optional[str] = None,
    shape_strength: float = 0.85,
    shape_params: Optional[dict] = None,
    shape_sea_level: float = 0.4,
) -> list[list[float]]:
    """產生 height × width 的高程陣列，值 ∈ [0, 1]。

    - width / height：地圖尺寸，需 > 0。
    - seed：隨機種子；同 seed 同參數可完全重現。
    - octaves：疊加層數；越多越細緻、越貴。
    - persistence：每往細一層振幅乘以多少 (0~1)。0.5 是常用值。
    - base_frequency：最粗那層的網格邊長 (cells)；2 表示 3×3 的 coarse grid。
    - ridge_weight：0=純 fBm 平滑山丘，1=純山脊 noise 尖銳稜線；0.5 為混合。
    - ridge_direction：山脈主走向（度，從北方順時針）。0=南北，90=東西。
      作為 ridge_direction_variation 擾動的基準中心。
    - ridge_direction_variation：走向擾動總幅度（度）。0=固定走向；90=隨機偏移 ±45°；
      180=完全隨機（ridge_direction 無效）。預設 90.0，讓山脈自然彎曲。
      擾動由低頻 noise 驅動，確保走向變化緩慢連續，而非像素級跳變。
    - shape：大陸形狀遮罩。None=關；合法值：
        "island"               — 單一大島
        "archipelago"          — 少量中型群島
        "pangaea"              — 盤古大陸（單一超大陸居中）
        "continents"           — 諸大陸（N 塊大陸分散）
        "ring_sea"             — 環海大陸（環形陸地包圍內海）
        "shattered_archipelago"— 破碎群島（大量小島）
    - shape_strength：遮罩強度 (0~1)；0 不套用，1 完全依遮罩決定陸/海。
    - shape_params：shape 專屬參數 dict，詳見 _make_shape_mask 文件。
    - shape_sea_level：供遮罩公式使用的海平面高程（應與 pipeline 的 sea_level 一致）。
      遮罩公式為再分範圍型：mask=1 → 高程映射到 [shape_sea_level, 1]（保證陸地），
      mask=0 → 高程映射到 [0, shape_sea_level×grid]（保證海洋），保留山丘/平原分布。
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be > 0, got ({width}, {height})")
    if octaves <= 0:
        raise ValueError(f"octaves must be > 0, got {octaves}")
    if not 0.0 < persistence <= 1.0:
        raise ValueError(f"persistence must be in (0, 1], got {persistence}")
    if base_frequency < 1:
        raise ValueError(f"base_frequency must be >= 1, got {base_frequency}")
    if not 0.0 <= ridge_weight <= 1.0:
        raise ValueError(f"ridge_weight must be in [0, 1], got {ridge_weight}")
    if shape is not None and shape not in _VALID_SHAPES:
        raise ValueError(
            f"shape must be one of {sorted(_VALID_SHAPES)} or None, got {shape!r}"
        )
    if not 0.0 <= shape_strength <= 1.0:
        raise ValueError(f"shape_strength must be in [0, 1], got {shape_strength}")

    rng = random.Random(seed)
    grid: list[list[float]] = [[0.0] * width for _ in range(height)]
    total_weight = 0.0

    # 走向慣例：從北方順時針（地質走向），0°=南北，90°=東西
    # 數學角 = 90° − 走向
    _use_ridge = ridge_weight > 0.0
    _cos_grid: Optional[list[list[float]]] = None
    _sin_grid: Optional[list[list[float]]] = None
    _cos_a = _sin_a = 0.0  # 固定走向時使用

    if _use_ridge:
        if ridge_direction_variation > 0.0:
            # 方向擾動：低頻 noise 讓每格走向緩緩漂移，形成自然彎曲山脈
            # 使用獨立 rng（XOR seed），不污染主 octave 的隨機序列
            dir_freq = max(2, base_frequency // 2)
            _dir_rng = random.Random(None if seed is None else seed ^ 0x9E3779B9)
            _dir_coarse = [[_dir_rng.random() for _ in range(dir_freq + 1)]
                           for _ in range(dir_freq + 1)]
            _dxs = dir_freq / max(width - 1, 1)
            _dys = dir_freq / max(height - 1, 1)
            _cos_grid = [[0.0] * width for _ in range(height)]
            _sin_grid = [[0.0] * width for _ in range(height)]
            for _r in range(height):
                for _q in range(width):
                    _dn = _bilinear(_dir_coarse, _q * _dxs, _r * _dys)
                    # 局部走向 = 基準 ± 擾動
                    _local_dir = ridge_direction + (_dn - 0.5) * ridge_direction_variation
                    _a = math.radians(90.0 - _local_dir)
                    _cos_grid[_r][_q] = math.cos(_a)
                    _sin_grid[_r][_q] = math.sin(_a)
        else:
            _rad = math.radians(90.0 - ridge_direction)
            _cos_a = math.cos(_rad)
            _sin_a = math.sin(_rad)

    # 經典 fBm 疊加：每層頻率 ×2、振幅 ×persistence
    for octave in range(octaves):
        freq = base_frequency * (2 ** octave)
        weight = persistence ** octave
        total_weight += weight

        # coarse 用 freq+1 讓最右/最下能取到 corner（雙線性需要四個 corner）
        coarse = [[rng.random() for _ in range(freq + 1)] for _ in range(freq + 1)]

        x_scale = freq / max(width - 1, 1)
        y_scale = freq / max(height - 1, 1)
        hx = freq * 0.5
        hy = freq * 0.5
        for r in range(height):
            cy = r * y_scale
            for q in range(width):
                cx = q * x_scale
                raw = _bilinear(coarse, cx, cy)
                if _use_ridge:
                    # 取局部（或全局）走向的旋轉矩陣
                    if _cos_grid is not None:
                        _ca = _cos_grid[r][q]
                        _sa = _sin_grid[r][q]
                    else:
                        _ca = _cos_a
                        _sa = _sin_a
                    # 各向異性採樣：rx=沿稜線（壓縮）, ry=跨稜線（全幅）
                    dx = cx - hx
                    dy = cy - hy
                    rx = dx * _ca + dy * _sa
                    ry = -dx * _sa + dy * _ca
                    raw_dir = _bilinear(coarse, rx * _RIDGE_ANISOTROPY + hx, ry + hy)
                    # 折疊：0.5→峰頂(1), 0/1→谷底(0)；形成尖銳稜線
                    fold = 1.0 - abs(2.0 * raw_dir - 1.0)
                    raw = raw_dir * (1.0 - ridge_weight) + fold * ridge_weight
                grid[r][q] += weight * raw

    # 用累計權重正規化，確保輸出仍在 [0, 1]，跟 persistence/octaves 無關
    inv = 1.0 / total_weight
    for r in range(height):
        for q in range(width):
            grid[r][q] *= inv

    # 形狀遮罩：再分範圍型混合
    # target = mask × (sl + grid×(1-sl))   ← mask=1 時目標在 [sl,1]（保證陸地）
    #                                         mask=0 時目標=0（保證海洋）
    # final  = grid×(1-s) + target×s
    # 這確保遮罩高區 (mask≈1) 不論 fBm 原始值多低都能成為陸地，
    # 同時保留高程相對高低（山脊/丘陵/平原分布不變）。
    if shape is not None:
        mask = _make_shape_mask(width, height, shape, rng, params=shape_params)
        s = shape_strength
        sl = shape_sea_level
        for r in range(height):
            for q in range(width):
                m = mask[r][q]
                target = m * (sl + grid[r][q] * (1.0 - sl))
                grid[r][q] = grid[r][q] * (1.0 - s) + target * s

    return grid
