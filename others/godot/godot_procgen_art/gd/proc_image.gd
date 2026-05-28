class_name ProcImage extends RefCounted

# 共用 Image 操作工具（純 GDScript，無 C++ 依賴）。
#
# CONCEPT 原本規畫走 C++ GDExtension（mapcore_cpp_square 模式），
# 但 mapcore 端目前沒做 procgen_art 對應 C++。本檔提供純 GDScript 版作為原型/後備：
#   - 32×32 ~ 128×128 像素級別在 GDScript 操作完全夠快（一次性生成，不每幀算）
#   - C++ 端要做時，本檔 API 是合約規格
#
# 三大功能：
#   1. SDF helpers：圓 / 矩形 / 多邊形 → signed distance value，可組合 union/subtract
#   2. Bézier raster：二次/三次曲線 → 像素線
#   3. Image 填色 / 邊緣描繪 / 高斯模糊（簡化版）


# ── 新空白 Image ──────────────────────────────────────────────────────────

static func new_image(width: int, height: int,
		fill: Color = Color(0, 0, 0, 0)) -> Image:
	var img := Image.create(width, height, false, Image.FORMAT_RGBA8)
	img.fill(fill)
	return img


static func to_texture(image: Image) -> ImageTexture:
	return ImageTexture.create_from_image(image)


# ── SDF helpers（單位：像素）──────────────────────────────────────────────

# 回傳 < 0 表示在圓內、= 0 邊界、> 0 在外。
static func sd_circle(p: Vector2, center: Vector2, radius: float) -> float:
	return p.distance_to(center) - radius


# 軸對齊矩形 SDF。half_size = (寬/2, 高/2)。
static func sd_box(p: Vector2, center: Vector2, half_size: Vector2) -> float:
	var d := (p - center).abs() - half_size
	var outside := Vector2(max(d.x, 0.0), max(d.y, 0.0)).length()
	var inside := min(max(d.x, d.y), 0.0)
	return outside + inside


# 兩個 SDF 聯集（min）
static func sd_union(a: float, b: float) -> float:
	return min(a, b)


# 從 a 減去 b：a ∩ ¬b（max(a, -b)）
static func sd_subtract(a: float, b: float) -> float:
	return max(a, -b)


# 平滑聯集（k 控制混合區寬度）。
static func sd_smooth_union(a: float, b: float, k: float = 2.0) -> float:
	var h := clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
	return lerp(b, a, h) - k * h * (1.0 - h)


# 用 SDF callable 填整張 image。
# sdf: Callable(Vector2) -> float（< 0 = 內，> 0 = 外）
# inside_color / outside_color：內外的填色（alpha=0 = 不畫）
# edge_color / edge_threshold：|sdf| < threshold 視為邊緣
static func fill_sdf(image: Image, sdf: Callable,
		inside_color: Color = Color.WHITE,
		outside_color: Color = Color(0, 0, 0, 0),
		edge_color: Color = Color(0, 0, 0, 0),
		edge_threshold: float = 0.0) -> void:
	for y in image.get_height():
		for x in image.get_width():
			var d: float = sdf.call(Vector2(x + 0.5, y + 0.5))
			var c: Color
			if edge_threshold > 0.0 and abs(d) < edge_threshold:
				c = edge_color
			elif d < 0.0:
				c = inside_color
			else:
				c = outside_color
			image.set_pixel(x, y, c)


# ── Bézier raster ─────────────────────────────────────────────────────────

# 二次貝茲：B(t) = (1-t)²·p0 + 2(1-t)t·p1 + t²·p2
static func quadratic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, t: float) -> Vector2:
	var u := 1.0 - t
	return u * u * p0 + 2.0 * u * t * p1 + t * t * p2


# 三次貝茲
static func cubic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
	var u := 1.0 - t
	return u * u * u * p0 + 3.0 * u * u * t * p1 + 3.0 * u * t * t * p2 + t * t * t * p3


# 把曲線取樣 N 個點，於每點之間 draw_line。
# Image 沒有 draw_line API，用簡化的 Bresenham 替代。
static func raster_quadratic(image: Image, p0: Vector2, p1: Vector2, p2: Vector2,
		color: Color, samples: int = 32) -> void:
	var prev := p0
	for i in range(1, samples + 1):
		var t := float(i) / samples
		var pt := quadratic_bezier(p0, p1, p2, t)
		draw_line(image, prev, pt, color)
		prev = pt


static func raster_cubic(image: Image, p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2,
		color: Color, samples: int = 48) -> void:
	var prev := p0
	for i in range(1, samples + 1):
		var t := float(i) / samples
		var pt := cubic_bezier(p0, p1, p2, p3, t)
		draw_line(image, prev, pt, color)
		prev = pt


# 簡化版 Bresenham（不抗鋸齒、pixel art 風格）
static func draw_line(image: Image, p0: Vector2, p1: Vector2, color: Color) -> void:
	var x0 := int(round(p0.x))
	var y0 := int(round(p0.y))
	var x1 := int(round(p1.x))
	var y1 := int(round(p1.y))
	var dx := abs(x1 - x0)
	var dy := -abs(y1 - y0)
	var sx := 1 if x0 < x1 else -1
	var sy := 1 if y0 < y1 else -1
	var err := dx + dy
	while true:
		if x0 >= 0 and x0 < image.get_width() and y0 >= 0 and y0 < image.get_height():
			image.set_pixel(x0, y0, color)
		if x0 == x1 and y0 == y1:
			break
		var e2 := 2 * err
		if e2 >= dy:
			err += dy
			x0 += sx
		if e2 <= dx:
			err += dx
			y0 += sy


# ── Noise displacement（程序輪廓擾動）─────────────────────────────────────

# 對 SDF 結果加 noise，產生有機輪廓。
# 用法：包一層 callable，把 base_sdf 的結果加 noise(p) * amplitude
static func noisy_sdf(base_sdf: Callable, frequency: float = 0.1,
		amplitude: float = 2.0, seed_: int = 0) -> Callable:
	var n := FastNoiseLite.new()
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX
	n.frequency = frequency
	n.seed = seed_
	return func(p: Vector2) -> float:
		var d: float = base_sdf.call(p)
		return d + n.get_noise_2dv(p) * amplitude
