class_name ProcPart extends RefCounted

# CONCEPT Level 3 的部件圖像生成基本款（CONCEPT 點到的 generate_limb/eye/body 等）。
# 純 GDScript，pixel art 級解析度（16~64 px 邊長）夠用。
#
# 全部輸出**灰階 alpha mask**：白色不透明 = 形狀，透明 = 背景。
# 顏色交給上層材質系統（godot_material/SpriteMaterial）。

const WHITE := Color(1, 1, 1, 1)


# ── 軀幹 ─────────────────────────────────────────────────────────────────
# 拉伸橢圓 + noise 擾動輪廓。length:width 比通常 1.5~3。
static func generate_body(width: int, height: int,
		contour_roughness: float = 0.15, seed_: int = 0) -> Image:
	var img := ProcImage.new_image(width, height)
	var center := Vector2(width * 0.5, height * 0.5)
	var half_size := Vector2(width * 0.35, height * 0.45)

	var base := func(p: Vector2) -> float:
		# 橢圓 SDF：把 p 歸一化到圓座標後算距離
		var local := (p - center) / half_size
		return local.length() - 1.0

	var sdf := ProcImage.noisy_sdf(base, 0.25, contour_roughness, seed_)
	ProcImage.fill_sdf(img, sdf, WHITE)
	return img


# ── 四肢 ─────────────────────────────────────────────────────────────────
# Cylinder 漸細：兩個圓的 smooth union。length 是長軸（像素）。
static func generate_limb(length: int, width: int, taper: float = 0.6,
		seed_: int = 0) -> Image:
	var w := width
	var h := length + width  # 兩端各留一個半徑高度
	var img := ProcImage.new_image(w, h)

	var top := Vector2(w * 0.5, width * 0.5)
	var bottom := Vector2(w * 0.5, h - width * taper * 0.5)
	var top_radius := width * 0.5
	var bottom_radius := width * 0.5 * taper

	var base := func(p: Vector2) -> float:
		var d_top := ProcImage.sd_circle(p, top, top_radius)
		var d_bot := ProcImage.sd_circle(p, bottom, bottom_radius)
		# 加上連接兩圓的矩形
		var mid := top.lerp(bottom, 0.5)
		var mid_half := Vector2(top_radius * 0.7, top.distance_to(bottom) * 0.5)
		var d_mid := ProcImage.sd_box(p, mid, mid_half)
		return ProcImage.sd_smooth_union(
				ProcImage.sd_smooth_union(d_top, d_bot, 2.0), d_mid, 1.5)

	var sdf := ProcImage.noisy_sdf(base, 0.3, 0.4, seed_)
	ProcImage.fill_sdf(img, sdf, WHITE)
	return img


# ── 頭部 ─────────────────────────────────────────────────────────────────
static func generate_head(size: int, roughness: float = 0.1,
		seed_: int = 0) -> Image:
	var img := ProcImage.new_image(size, size)
	var center := Vector2(size * 0.5, size * 0.5)
	var radius := size * 0.42

	var base := func(p: Vector2) -> float:
		return ProcImage.sd_circle(p, center, radius)

	var sdf := ProcImage.noisy_sdf(base, 0.35, roughness * radius, seed_)
	ProcImage.fill_sdf(img, sdf, WHITE)
	return img


# ── 眼睛 ─────────────────────────────────────────────────────────────────
# 凸起的圓 + 中央瞳孔（用 sd_subtract 挖洞）。回傳 RGBA：白底黑瞳。
static func generate_eye(size: int, pupil_ratio: float = 0.4,
		seed_: int = 0) -> Image:
	var img := ProcImage.new_image(size, size)
	var center := Vector2(size * 0.5, size * 0.5)
	var iris := size * 0.45
	var pupil := iris * pupil_ratio

	var sdf := func(p: Vector2) -> float:
		return ProcImage.sd_circle(p, center, iris)

	# 鞏膜（白）
	ProcImage.fill_sdf(img, sdf, WHITE)
	# 瞳孔（黑）
	var pupil_sdf := func(p: Vector2) -> float:
		return ProcImage.sd_circle(p, center, pupil)
	ProcImage.fill_sdf(img, pupil_sdf, Color.BLACK, Color(0, 0, 0, 0))
	# 第二步把瞳孔覆蓋上去：因為 fill_sdf 會把外面寫成 outside_color (透明)，
	# 所以要分兩 pass 避免清掉鞏膜。改用直接掃描：
	for y in size:
		for x in size:
			var p := Vector2(x + 0.5, y + 0.5)
			if ProcImage.sd_circle(p, center, pupil) < 0:
				img.set_pixel(x, y, Color.BLACK)
	return img


# ── 翅膀 ─────────────────────────────────────────────────────────────────
# 用兩條三次貝茲曲線勾勒翅膀輪廓 + 內部填充。
static func generate_wing(span: int, height: int, vein_count: int = 0,
		seed_: int = 0) -> Image:
	var img := ProcImage.new_image(span, height)
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_

	# 翅膀輪廓：從翼根 (0, h*0.5) 上邊到翼尖 (span-1, h*0.3) 再下邊回到翼根
	var root := Vector2(0, height * 0.5)
	var tip := Vector2(span - 1, height * 0.3 + rng.randf_range(-3, 3))
	var upper_ctrl1 := Vector2(span * 0.3, -height * 0.1 + rng.randf_range(-2, 2))
	var upper_ctrl2 := Vector2(span * 0.7, height * 0.1)
	var lower_ctrl1 := Vector2(span * 0.6, height * 0.7)
	var lower_ctrl2 := Vector2(span * 0.3, height * 0.9)

	# 內部填充：以中軸（root → tip）為基準，每行掃 y 看是否落在輪廓內。
	# 簡化方案：先在外圈描 N 條貝茲線，再 flood fill。Image 沒 flood fill API，
	# 改用「以 SDF 近似」——用 root→tip 的線段 SDF 加上高度 modulation。
	var axis_dir := (tip - root).normalized()
	var axis_len := root.distance_to(tip)

	var sdf := func(p: Vector2) -> float:
		var to_p := p - root
		var t := to_p.dot(axis_dir) / axis_len
		if t < 0.0 or t > 1.0:
			# 端點圓
			return min(p.distance_to(root), p.distance_to(tip)) - 2.0
		var on_axis := root + axis_dir * (t * axis_len)
		var perp_dist := p.distance_to(on_axis)
		# 翅膀厚度沿 t 變化：根部厚、尖端薄
		var half_thick := lerp(height * 0.45, 4.0, smoothstep(0.0, 1.0, t))
		return perp_dist - half_thick

	ProcImage.fill_sdf(img, sdf, WHITE)

	# 畫翼脈（從 root 拉貝茲線到輪廓邊緣的隨機點）
	for i in vein_count:
		var t_end := lerp(0.2, 0.95, float(i + 1) / (vein_count + 1))
		var end := root.lerp(tip, t_end) + Vector2(0, rng.randf_range(-height * 0.15, height * 0.15))
		var ctrl := root.lerp(end, 0.5) + Vector2(rng.randf_range(-3, 3), rng.randf_range(-3, 3))
		ProcImage.raster_quadratic(img, root, ctrl, end, Color(0.4, 0.4, 0.4, 1.0), 24)

	return img
