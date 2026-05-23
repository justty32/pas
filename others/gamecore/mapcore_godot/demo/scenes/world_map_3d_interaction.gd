## WorldMap3DInteraction：3D 世界地圖的互動層（2D 互動的 3D 對應）。
##
## 把 world_map_2d.gd 的互動搬到 3D：
##   - 點選：相機射線打到地形（trimesh collision）→ 換算成格子 (x, y)
##   - 懸停高亮、選格 + feature 邊界輪廓、單位選取、成本感知尋路逐格走、
##     Shift 路徑預覽、3D 路徑線、L 標籤、C/Esc 清除
##
## 場景結構（此腳本掛在 WorldMap3D 下、與 MapRenderer3D / CameraRig3D 同層的 Node3D）：
##   WorldMap3D
##   ├── MapRenderer3D            ← @export map_renderer（接 terrain_ready）
##   ├── CameraRig3D/CameraArm/Camera3D  ← @export camera
##   ├── Interaction (此腳本)     ← 動態建立所有高亮 / 線 / 單位 / 標籤子節點
##   └── UI/InfoPanel (Label)     ← @export info_label
##
## 操作：
##   左鍵            點單位→選取；已選單位再點格→下移動令（A*，逐格走）；點空地→選格+feature
##   Shift+左鍵      路徑預覽：點起點再點終點 → 畫 A* 路徑並顯示步數/成本
##   C / Esc         清除選取 / 路徑 / 高亮
##   L               切換 feature 標籤
##   WASD/QE/RF/滾輪  相機（由 CameraRig3D 處理）
class_name WorldMap3DInteraction
extends Node3D

@export var map_renderer: MapRenderer3D
@export var camera: Camera3D
@export var info_label: Label

@export_group("尋路 / 標籤")
## 尋路跨越河流的額外成本（乘上河流強度）。0=不影響；越大越會繞開大河
@export var river_crossing_cost: float = 0.05
## feature 標籤只顯示面積 ≥ 此格數的區域
@export var label_min_size: int = 40
## feature 標籤數量上限（取面積最大的前幾個）
@export var label_max_count: int = 24
## 初始隨機生成的單位數
@export var unit_count: int = 3

# ── 視覺常數 ──────────────────────────────────────────────────────────────────
const _CELL_Y    := 0.06   # 懸停 / 選格高亮方塊離地表高度
const _OUTLINE_Y := 0.10   # feature 邊界線離地表高度
const _LINE_Y    := 0.40   # 路徑線離地表高度（浮空，清楚可見）
const _MARK_Y    := 0.08   # 起點 / 終點圓盤離地表高度
const _DISC_Y    := 0.05   # 選取單位底圓盤離地表高度
const _LABEL_Y   := 1.20   # 標籤離地表高度
const _UNIT_H    := 0.80   # 單位柱體高度
const _RAY_LEN   := 4000.0

const _STEP_TIME := 0.12               # 單位每格移動間隔（秒）
const _IMPASSABLE := [0, 1, 9, 10]     # OCEAN / COAST / MOUNTAIN / LAKE（不可通行）

const _NONE := Vector2i(-1, -1)

const _TERRAIN_NAMES := {
	0: "海洋", 1: "海岸", 2: "平原", 3: "草原",
	4: "沙漠", 5: "凍原", 6: "雪地", 7: "森林",
	8: "丘陵", 9: "山脈", 10: "湖泊",
}

const COL_HOVER  := Color(1.0, 1.0, 0.2)
const COL_SELECT := Color(0.1, 1.0, 1.0)
const COL_FEAT   := Color(1.0, 0.6, 0.1)
const COL_PATH   := Color(1.0, 1.0, 1.0)
const COL_START  := Color(0.2, 1.0, 0.3)
const COL_GOAL   := Color(1.0, 0.25, 0.25)

const _LEGEND := "左鍵:選單位/下移動令  Shift+左鍵:路徑預覽  C/Esc:清除  L:標籤  WASD/QE/RF:相機  滾輪:縮放"

# ── 狀態 ─────────────────────────────────────────────────────────────────────
var _data: MapCoreMapData
var _ts: float = 1.0
var _hs: float = 3.0
var _mw: int = 0
var _mh: int = 0
var _feature_grid: PackedInt32Array = PackedInt32Array()  # 每格 feature_id 快取

var _hover: Vector2i = _NONE
var _selected: Vector2i = _NONE
var _path_pending_start: Vector2i = _NONE
var _selected_unit: int = -1
var _units: Array = []            # [{ cell, color, name, queue, node }]
var _move_accum: float = 0.0
var _show_labels: bool = false

# ── 視覺節點 ──────────────────────────────────────────────────────────────────
var _hover_marker: MeshInstance3D
var _select_marker: MeshInstance3D
var _unit_disc: MeshInstance3D
var _start_disc: MeshInstance3D
var _goal_disc: MeshInstance3D
var _outline: MeshInstance3D
var _path_line: MeshInstance3D
var _route_line: MeshInstance3D
var _labels_root: Node3D


func _ready() -> void:
	if not map_renderer:
		push_error("WorldMap3DInteraction: map_renderer 未設定")
		return
	_build_visual_nodes()
	if map_renderer.map_data:        # 地形可能已建好（連線晚於生成）
		_on_terrain_ready(map_renderer.map_data)
	else:
		map_renderer.terrain_ready.connect(_on_terrain_ready)

# ── 地形就緒 ──────────────────────────────────────────────────────────────────

func _on_terrain_ready(data: MapCoreMapData) -> void:
	_data = data
	_ts = map_renderer.tile_size
	_hs = map_renderer.height_scale
	_mw = data.get_width()
	_mh = data.get_height()
	_resize_markers()
	_build_collision()
	_build_feature_grid()
	_build_labels()
	_spawn_units(unit_count)
	_update_info()
	print("WorldMap3DInteraction: 互動就緒，size=%dx%d  features=%d" % [
		_mw, _mh, data.get_feature_count()])

# 為地形 mesh 加上 trimesh 碰撞體，供相機射線點選。
func _build_collision() -> void:
	var mesh := map_renderer.terrain_mesh_node.mesh
	if not mesh:
		push_error("WorldMap3DInteraction: terrain mesh 尚未建立，無法產生碰撞")
		return
	var shape := mesh.create_trimesh_shape()
	# 地形三角面繞序使正面朝下（見 terrain_mesh_builder.cpp），俯視射線會打到背面；
	# 開 backface_collision 讓射線不分正反面都命中。
	shape.backface_collision = true
	var body := StaticBody3D.new()
	var col := CollisionShape3D.new()
	col.shape = shape
	body.add_child(col)
	map_renderer.terrain_mesh_node.add_child(body)

# ── 輸入 ──────────────────────────────────────────────────────────────────────

func _unhandled_input(event: InputEvent) -> void:
	if not _data:
		return
	if event is InputEventMouseMotion:
		_update_hover()
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.shift_pressed:
				_on_path_click()
			else:
				_on_select_click()
	elif event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_L:
				_toggle_labels()
			KEY_C, KEY_ESCAPE:
				_clear_interactions()

# ── 座標換算（相機射線 → 地形格子）──────────────────────────────────────────

func _cell_at_mouse() -> Vector2i:
	if not _data or not camera:
		return _NONE
	var mp := get_viewport().get_mouse_position()
	var space := get_world_3d().direct_space_state
	var from := camera.project_ray_origin(mp)
	var to := from + camera.project_ray_normal(mp) * _RAY_LEN
	var q := PhysicsRayQueryParameters3D.create(from, to)
	var hit := space.intersect_ray(q)
	if hit.is_empty():
		return _NONE
	var p: Vector3 = hit["position"]
	# 格子對應地形格點，最近格點 = round(world / tile_size)
	var cx := int(round(p.x / _ts))
	var cy := int(round(p.z / _ts))
	if cx < 0 or cy < 0 or cx >= _mw or cy >= _mh:
		return _NONE
	return Vector2i(cx, cy)

# 格子 (x, y) 在世界座標的位置；y_off 為離地表的額外高度
func _cell_world(x: int, y: int, y_off: float = 0.0) -> Vector3:
	var h := 0.0
	if _data and x >= 0 and y >= 0 and x < _mw and y < _mh:
		h = _data.get_height_value(x, y) * _hs
	return Vector3(x * _ts, h + y_off, y * _ts)

# ── 懸停 ──────────────────────────────────────────────────────────────────────

func _update_hover() -> void:
	var c := _cell_at_mouse()
	if c == _hover:
		return
	_hover = c
	if c == _NONE:
		_hover_marker.visible = false
	else:
		_hover_marker.position = _cell_world(c.x, c.y, _CELL_Y)
		_hover_marker.visible = (c != _selected)
	_update_info()

# ── 選取 + feature 高亮 ───────────────────────────────────────────────────────

func _on_select_click() -> void:
	var c := _cell_at_mouse()
	if c == _NONE:
		return
	var ui := _unit_at(c)
	if ui >= 0:
		# 點到單位 → 選取它（清掉格子選取 / 高亮）
		_selected_unit = ui
		_selected = _NONE
		_select_marker.visible = false
		_outline.visible = false
	elif _selected_unit >= 0:
		# 已選單位 → 對該格下移動指令
		_order_move(_selected_unit, c)
	else:
		# 沒選單位 → 一般格子選取 + feature 高亮
		_selected = c
		_select_marker.position = _cell_world(c.x, c.y, _CELL_Y)
		_select_marker.visible = true
		_highlight_feature(c)
	_refresh_unit_visuals()
	_update_info()

func _highlight_feature(c: Vector2i) -> void:
	var fid := _fid_at(c.x, c.y)
	var im := ImmediateMesh.new()
	if fid >= 0:
		im.surface_begin(Mesh.PRIMITIVE_LINES)
		# 走訪整塊 feature，收集與「非同 feature 鄰格」相鄰的邊（格子方塊以格點為中心）
		for y in range(_mh):
			for x in range(_mw):
				if _fid_at(x, y) != fid:
					continue
				var by := _data.get_height_value(x, y) * _hs + _OUTLINE_Y
				if _fid_at(x + 1, y) != fid:  # 右邊界
					_seg(im, x + 0.5, y - 0.5, x + 0.5, y + 0.5, by)
				if _fid_at(x - 1, y) != fid:  # 左邊界
					_seg(im, x - 0.5, y - 0.5, x - 0.5, y + 0.5, by)
				if _fid_at(x, y - 1) != fid:  # 上邊界
					_seg(im, x - 0.5, y - 0.5, x + 0.5, y - 0.5, by)
				if _fid_at(x, y + 1) != fid:  # 下邊界
					_seg(im, x - 0.5, y + 0.5, x + 0.5, y + 0.5, by)
		im.surface_end()
	_outline.mesh = im
	_outline.visible = fid >= 0

func _seg(im: ImmediateMesh, fx0: float, fz0: float, fx1: float, fz1: float, by: float) -> void:
	im.surface_add_vertex(Vector3(fx0 * _ts, by, fz0 * _ts))
	im.surface_add_vertex(Vector3(fx1 * _ts, by, fz1 * _ts))

# ── 尋路預覽 ──────────────────────────────────────────────────────────────────

func _on_path_click() -> void:
	var c := _cell_at_mouse()
	if c == _NONE:
		return
	if _path_pending_start == _NONE:
		# 設起點，清掉上一條預覽
		_path_pending_start = c
		_start_disc.position = _cell_world(c.x, c.y, _MARK_Y)
		_start_disc.visible = true
		_goal_disc.visible = false
		_path_line.visible = false
	else:
		# 設終點並求路徑
		_goal_disc.position = _cell_world(c.x, c.y, _MARK_Y)
		_goal_disc.visible = true
		var p := _map_path(_path_pending_start, c)
		_rebuild_line(_path_line, p, COL_PATH)
		if p.is_empty():
			info_label.text = "(%d,%d)→(%d,%d) 找不到路徑（可能被水域阻隔）\n%s" % [
				_path_pending_start.x, _path_pending_start.y, c.x, c.y, _LEGEND]
		else:
			info_label.text = "路徑預覽: %d 步　地形成本 %.1f\n%s" % [
				p.size() - 1, _data.path_cost(p), _LEGEND]
		_path_pending_start = _NONE

# ── 單位（生成 / 選取 / 移動）─────────────────────────────────────────────────

func _process(delta: float) -> void:
	if _units.is_empty():
		return
	_move_accum += delta
	if _move_accum < _STEP_TIME:
		return
	_move_accum = 0.0
	var moved := false
	for u in _units:
		if not u["queue"].is_empty():
			u["cell"] = u["queue"].pop_front()
			moved = true
	if moved:
		_refresh_unit_visuals()
		_update_info()

func _unit_at(c: Vector2i) -> int:
	for i in range(_units.size()):
		if _units[i]["cell"] == c:
			return i
	return -1

func _is_walkable(x: int, y: int) -> bool:
	return not _IMPASSABLE.has(_data.get_terrain(x, y))

func _spawn_units(count: int) -> void:
	for u in _units:
		(u["node"] as Node).queue_free()
	_units.clear()
	var colors := [Color(0.95, 0.3, 0.3), Color(0.3, 0.55, 0.95), Color(0.95, 0.8, 0.25), Color(0.6, 0.35, 0.9)]
	var unit_names := ["部隊 A", "部隊 B", "部隊 C", "部隊 D"]
	var spawned := 0
	var tries := 0
	while spawned < count and tries < 5000:
		tries += 1
		var x := randi() % _mw
		var y := randi() % _mh
		if not _is_walkable(x, y) or _unit_at(Vector2i(x, y)) >= 0:
			continue
		var color: Color = colors[spawned % colors.size()]
		_units.append({
			"cell": Vector2i(x, y),
			"color": color,
			"name": unit_names[spawned % unit_names.size()],
			"queue": [],
			"node": _make_unit_mesh(color),
		})
		spawned += 1
	_refresh_unit_visuals()

# 對單位下達移動指令：用成本感知 find_path 規劃路線，逐格走過去
func _order_move(idx: int, goal: Vector2i) -> void:
	var u = _units[idx]
	var p := _map_path(u["cell"], goal)
	if p.is_empty():
		info_label.text = "%s 無法移動到 (%d, %d)（不可通行或被阻隔）\n%s" % [
			u["name"], goal.x, goal.y, _LEGEND]
		return
	u["queue"] = p.slice(1)  # p[0] 為目前所在格
	info_label.text = "%s → (%d, %d)　步數 %d　地形成本 %.1f\n%s" % [
		u["name"], goal.x, goal.y, p.size() - 1, _data.path_cost(p), _LEGEND]

# find_path 回傳 TypedArray[Vector2i]（is-a Array，可直接 slice / iterate）。
# 維持原型別回傳，確保再丟回 path_cost(TypedArray<Vector2i>) 時型別相符。
func _map_path(start: Vector2i, goal: Vector2i) -> Array:
	return _data.find_path(start, goal, river_crossing_cost)

# ── 視覺刷新 ──────────────────────────────────────────────────────────────────

# 重新擺放所有單位節點、選取單位的底圓盤與剩餘路線
func _refresh_unit_visuals() -> void:
	for u in _units:
		var cell: Vector2i = u["cell"]
		(u["node"] as Node3D).position = _cell_world(cell.x, cell.y, _UNIT_H * 0.5)
	if _selected_unit >= 0 and _selected_unit < _units.size():
		var su = _units[_selected_unit]
		_unit_disc.position = _cell_world(su["cell"].x, su["cell"].y, _DISC_Y)
		_unit_disc.visible = true
		var route: Array = [su["cell"]]
		route.append_array(su["queue"])
		_rebuild_line(_route_line, route, su["color"])
	else:
		_unit_disc.visible = false
		_route_line.visible = false

# 用 ImmediateMesh 把一串格子畫成浮空折線
func _rebuild_line(mi: MeshInstance3D, cells: Array, color: Color) -> void:
	var im := ImmediateMesh.new()
	if cells.size() >= 2:
		im.surface_begin(Mesh.PRIMITIVE_LINE_STRIP)
		for c in cells:
			im.surface_add_vertex(_cell_world(c.x, c.y, _LINE_Y))
		im.surface_end()
	mi.mesh = im
	mi.material_override = MaterialLibrary.make_unshaded(color)
	mi.visible = cells.size() >= 2

# ── 清除 ──────────────────────────────────────────────────────────────────────

func _clear_interactions() -> void:
	_selected = _NONE
	_path_pending_start = _NONE
	_selected_unit = -1
	_select_marker.visible = false
	_outline.visible = false
	_start_disc.visible = false
	_goal_disc.visible = false
	_path_line.visible = false
	_unit_disc.visible = false
	_route_line.visible = false
	_update_info()

# ── 標籤 ──────────────────────────────────────────────────────────────────────

func _toggle_labels() -> void:
	_show_labels = not _show_labels
	_labels_root.visible = _show_labels

# ── feature 快取 ──────────────────────────────────────────────────────────────

func _fid_at(x: int, y: int) -> int:
	if x < 0 or y < 0 or x >= _mw or y >= _mh:
		return -1
	return _feature_grid[y * _mw + x]

func _build_feature_grid() -> void:
	_feature_grid = PackedInt32Array()
	_feature_grid.resize(_mw * _mh)
	for y in range(_mh):
		for x in range(_mw):
			_feature_grid[y * _mw + x] = _data.get_feature_id_at(x, y)

func _build_labels() -> void:
	for child in _labels_root.get_children():
		child.queue_free()
	# 收集夠大的 feature，按面積由大到小取前 label_max_count 個
	var big := []
	for fid in range(_data.get_feature_count()):
		var info := _data.get_feature_info(fid)
		if info.has("name") and info.has("center") and int(info.get("size", 0)) >= label_min_size:
			big.append({ "name": info["name"], "pos": info["center"], "size": int(info["size"]) })
	big.sort_custom(func(a, b): return a["size"] > b["size"])
	var n := 0
	for f in big:
		if n >= label_max_count:
			break
		var cell: Vector2i = f["pos"]
		var lbl := Label3D.new()
		lbl.text = f["name"]
		lbl.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		lbl.fixed_size = true
		lbl.pixel_size = 0.0007
		lbl.no_depth_test = true
		lbl.modulate = Color.WHITE
		lbl.outline_modulate = Color(0, 0, 0, 0.85)
		lbl.outline_size = 8
		lbl.position = _cell_world(cell.x, cell.y, _LABEL_Y)
		_labels_root.add_child(lbl)
		n += 1
	_labels_root.visible = _show_labels

# ── 資訊面板 ──────────────────────────────────────────────────────────────────

func _update_info() -> void:
	if not info_label:
		return
	# 沒有懸停目標但有選取單位時，顯示單位狀態
	if _hover == _NONE and _selected_unit >= 0 and _selected_unit < _units.size():
		var u = _units[_selected_unit]
		info_label.text = "%s　位置(%d, %d)　待走 %d 格\n%s" % [
			u["name"], u["cell"].x, u["cell"].y, u["queue"].size(), _LEGEND]
		return
	var c := _hover if _hover != _NONE else _selected
	if not _data or c == _NONE:
		info_label.text = _LEGEND
		return
	var t := _data.get_terrain(c.x, c.y)
	var h := _data.get_hilliness(c.x, c.y)
	var temp := _data.get_temperature(c.x, c.y)
	var rain := _data.get_rainfall(c.x, c.y)
	var s := "(%d, %d)  %s\n坡度: %d　溫度: %.1f°C　降雨: %.0f mm" % [
		c.x, c.y, _TERRAIN_NAMES.get(t, "?"), h, temp, rain]
	var fid := _fid_at(c.x, c.y)
	if fid >= 0:
		var info := _data.get_feature_info(fid)
		if info.has("name"):
			s += "　區域: %s" % info["name"]
	info_label.text = s + "\n" + _LEGEND

# ── 視覺節點建立 ──────────────────────────────────────────────────────────────

func _build_visual_nodes() -> void:
	_hover_marker  = _make_quad(COL_HOVER, 0.35)
	_select_marker = _make_quad(COL_SELECT, 0.45)
	_unit_disc     = _make_disc(0.55, Color.WHITE, 0.7)
	_start_disc    = _make_disc(0.45, COL_START, 0.9)
	_goal_disc     = _make_disc(0.45, COL_GOAL, 0.9)

	_outline = MeshInstance3D.new()
	_outline.material_override = MaterialLibrary.make_unshaded(COL_FEAT)
	_outline.visible = false
	add_child(_outline)

	_path_line = MeshInstance3D.new()
	_path_line.visible = false
	add_child(_path_line)

	_route_line = MeshInstance3D.new()
	_route_line.visible = false
	add_child(_route_line)

	_labels_root = Node3D.new()
	_labels_root.visible = false
	add_child(_labels_root)

# 地圖尺寸已知後，依 tile_size 調整高亮方塊 / 圓盤大小
func _resize_markers() -> void:
	(_hover_marker.mesh as PlaneMesh).size = Vector2(_ts, _ts) * 0.96
	(_select_marker.mesh as PlaneMesh).size = Vector2(_ts, _ts) * 0.96
	(_unit_disc.mesh as CylinderMesh).top_radius = _ts * 0.55
	(_unit_disc.mesh as CylinderMesh).bottom_radius = _ts * 0.55
	(_start_disc.mesh as CylinderMesh).top_radius = _ts * 0.45
	(_start_disc.mesh as CylinderMesh).bottom_radius = _ts * 0.45
	(_goal_disc.mesh as CylinderMesh).top_radius = _ts * 0.45
	(_goal_disc.mesh as CylinderMesh).bottom_radius = _ts * 0.45

func _make_quad(color: Color, alpha: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = Vector2(_ts, _ts) * 0.96
	mi.mesh = pm
	mi.material_override = MaterialLibrary.make_transparent(color, alpha)
	mi.visible = false
	add_child(mi)
	return mi

func _make_disc(radius: float, color: Color, alpha: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = radius
	cm.bottom_radius = radius
	cm.height = 0.04
	mi.mesh = cm
	mi.material_override = MaterialLibrary.make_transparent(color, alpha)
	mi.visible = false
	add_child(mi)
	return mi

func _make_unit_mesh(color: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = _ts * 0.18
	cm.bottom_radius = _ts * 0.30
	cm.height = _UNIT_H
	mi.mesh = cm
	mi.material_override = MaterialLibrary.make_unshaded(color)
	add_child(mi)
	return mi
