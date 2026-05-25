# 教學：日夜循環視覺效果（Day-Night Cycle Visual）

本教學說明如何將 `TimeSystem`（`npc_radiant_ai_schedule.md` 中建立的 Autoload）與場景的視覺元素連接，讓天空色彩、光線角度、環境色隨遊戲時間動態變化。

## 前置知識
- 已完成 [教學：NPC 輻射 AI 排程](./npc_radiant_ai_schedule.md)（`TimeSystem` 已存在）。
- 已閱讀 [教學：畫面表現設定](./visual_presentation_and_rendering.md)。

---

## 一、日夜循環的三個核心視覺元素

| 元素 | 作用 | 節點 |
|---|---|---|
| 太陽/月亮方向 | 投影陰影方向、主光源強度 | `DirectionalLight3D` |
| 天空色彩 | 天頂色、地平線色隨時間漸變 | `ProceduralSkyMaterial` |
| 環境光 | 整體亮度、陰影深度 | `WorldEnvironment.Environment` |

---

## 二、DayNightController：場景內的視覺控制器

建立 `res://scripts/day_night_controller.gd`，掛在場景的根節點下：

```gdscript
# res://scripts/day_night_controller.gd
extends Node

## 太陽光（DirectionalLight3D）
@export var sun_light: DirectionalLight3D
## 月亮光（可用另一個 DirectionalLight3D，強度較低）
@export var moon_light: DirectionalLight3D
## WorldEnvironment
@export var world_environment: WorldEnvironment

## 一天（24 遊戲小時）對應的旋轉：
## 0:00 → -90° (正北面地平線以下)
## 6:00 → 0°  (日出，東方地平線)
## 12:00 → 90° (正午頭頂)
## 18:00 → 180° (日落)
## 24:00 → 270° (正北面地平線以下，=0°)

## 各時段的天空色彩（時間 → 天空頂色, 地平線色）
var sky_colors: Dictionary = {
    0:  [Color(0.02, 0.02, 0.08), Color(0.05, 0.05, 0.15)],  # 深夜
    5:  [Color(0.1, 0.05, 0.15),  Color(0.4, 0.2, 0.1)],     # 黎明前
    6:  [Color(0.2, 0.3, 0.6),    Color(0.8, 0.5, 0.2)],     # 日出
    8:  [Color(0.15, 0.4, 0.9),   Color(0.7, 0.85, 1.0)],    # 早晨
    12: [Color(0.1, 0.3, 0.8),    Color(0.6, 0.75, 0.9)],    # 正午
    17: [Color(0.2, 0.25, 0.6),   Color(0.9, 0.5, 0.15)],    # 傍晚
    19: [Color(0.08, 0.05, 0.2),  Color(0.3, 0.1, 0.05)],    # 日落後
    21: [Color(0.02, 0.02, 0.1),  Color(0.05, 0.04, 0.12)],  # 夜晚
}

## 各時段的主光源強度
var sun_energy: Dictionary = {
    0: 0.0, 5: 0.1, 6: 0.4, 8: 0.8, 12: 1.0, 17: 0.7, 19: 0.2, 21: 0.0
}

## 各時段的月光強度
var moon_energy: Dictionary = {
    0: 0.15, 5: 0.05, 6: 0.0, 8: 0.0, 12: 0.0, 17: 0.0, 19: 0.05, 21: 0.1
}

var _sky_material: ProceduralSkyMaterial


func _ready() -> void:
    if world_environment and world_environment.environment:
        var sky = world_environment.environment.sky
        if sky:
            _sky_material = sky.sky_material as ProceduralSkyMaterial

    # 連接 TimeSystem 的每分鐘更新
    if TimeSystem:
        TimeSystem.hour_changed.connect(_on_hour_changed)
        TimeSystem.minute_changed.connect(_on_minute_changed)

    # 初始化
    _update_visuals(TimeSystem.game_hour, TimeSystem.game_minute)


func _on_hour_changed(new_hour: int) -> void:
    _update_visuals(new_hour, TimeSystem.game_minute)


func _on_minute_changed(new_minute: int) -> void:
    _update_visuals(TimeSystem.game_hour, new_minute)


func _update_visuals(hour: int, minute: int) -> void:
    var total_minutes := hour * 60.0 + minute
    var day_fraction := total_minutes / 1440.0  # 0.0 → 1.0

    # --- 太陽旋轉 ---
    # 正午 (12:00, fraction=0.5) → 旋轉角 = 0° (照射正下方)
    # 日出 (6:00, fraction=0.25) → 旋轉角 = -90° (東方水平)
    var sun_angle_x = (day_fraction - 0.5) * 360.0 - 90.0
    if sun_light:
        sun_light.rotation_degrees.x = sun_angle_x
        sun_light.light_energy = _lerp_at_time(sun_energy, hour, minute)

    if moon_light:
        moon_light.rotation_degrees.x = sun_angle_x + 180.0
        moon_light.light_energy = _lerp_at_time(moon_energy, hour, minute)

    # --- 天空色彩 ---
    if _sky_material:
        var colors = _lerp_colors_at_time(sky_colors, hour, minute)
        _sky_material.sky_top_color = colors[0]
        _sky_material.sky_horizon_color = colors[1]


func _lerp_at_time(table: Dictionary, hour: int, minute: int) -> float:
    var sorted_hours = table.keys()
    sorted_hours.sort()
    var prev_h := sorted_hours[-1]
    var next_h := sorted_hours[0]

    for h in sorted_hours:
        if h <= hour:
            prev_h = h
        if h > hour and next_h == sorted_hours[0]:
            next_h = h

    var prev_total = prev_h * 60.0
    var next_total = next_h * 60.0
    var cur_total = hour * 60.0 + minute

    # 跨午夜處理
    if next_total <= prev_total:
        next_total += 1440.0
    if cur_total < prev_total:
        cur_total += 1440.0

    var t = (cur_total - prev_total) / (next_total - prev_total)
    return lerp(float(table[prev_h]), float(table[next_h]), t)


func _lerp_colors_at_time(table: Dictionary, hour: int, minute: int) -> Array:
    var sorted_hours = table.keys()
    sorted_hours.sort()
    var prev_h := sorted_hours[-1]
    var next_h := sorted_hours[0]

    for h in sorted_hours:
        if h <= hour:
            prev_h = h
        if h > hour and next_h == sorted_hours[0]:
            next_h = h

    var prev_total = prev_h * 60.0
    var next_total = next_h * 60.0
    var cur_total = hour * 60.0 + minute
    if next_total <= prev_total:
        next_total += 1440.0
    if cur_total < prev_total:
        cur_total += 1440.0

    var t = (cur_total - prev_total) / (next_total - prev_total)
    var c0 = table[prev_h][0].lerp(table[next_h][0], t)
    var c1 = table[prev_h][1].lerp(table[next_h][1], t)
    return [c0, c1]
```

---

## 三、TimeSystem 補充 minute_changed 信號

`npc_radiant_ai_schedule.md` 中的 `TimeSystem` 只有 `hour_changed` 信號。為了讓視覺每分鐘平滑更新，加入 `minute_changed`：

```gdscript
# time_system.gd 補充
signal minute_changed(new_minute: int)

func _process(delta: float) -> void:
    var prev_minute = int(game_minute)
    game_minute += delta * time_scale
    
    if game_minute >= 60:
        game_minute -= 60
        game_hour = (game_hour + 1) % 24
        hour_changed.emit(game_hour)
    elif int(game_minute) != prev_minute:
        minute_changed.emit(int(game_minute))
```

---

## 四、氣候效果擴充（霧、雨）

在 `WorldEnvironment` 的 `Environment` 資源中，`Fog` 設定可在夜晚加深：

```gdscript
# 在 DayNightController._update_visuals() 中加入
func _update_fog(hour: int) -> void:
    if not world_environment or not world_environment.environment:
        return
    var env = world_environment.environment
    
    # 夜晚霧氣加重（2:00~5:00 最濃）
    var fog_density_table := {0: 0.01, 2: 0.02, 5: 0.015, 6: 0.005, 12: 0.002, 21: 0.008}
    env.fog_density = _lerp_at_time(fog_density_table, hour, TimeSystem.game_minute)
    env.fog_enabled = env.fog_density > 0.003
```

---

## 五、時鐘 HUD 顯示

在 HUD 加入一個 `Label` 顯示目前時間：

```gdscript
# clock_hud.gd — 掛在 HUD 的 Label 節點
extends Label

func _ready() -> void:
    TimeSystem.hour_changed.connect(_refresh)
    TimeSystem.minute_changed.connect(func(_m): _refresh(TimeSystem.game_hour))
    _refresh(TimeSystem.game_hour)


func _refresh(_hour: int) -> void:
    var h = TimeSystem.game_hour
    var m = int(TimeSystem.game_minute)
    text = "%02d:%02d" % [h, m]
```

---

## 六、驗證清單

| 測試步驟 | 預期結果 |
|---|---|
| 加速 `time_scale`（設為 600.0） | 天空色彩快速過渡，可目視日夜循環 |
| 06:00 時刻 | 天空由暗藍變橘紅（日出色），DirectionalLight3D 幾乎水平 |
| 12:00 時刻 | 天空最亮（正午藍），光源直射正下方，陰影最短 |
| 21:00 時刻 | 天空深藍近黑，月光微亮，陰影稍長 |
| NPC 排程同步 | 排程切換時間與視覺夜晚時間一致 |
| HUD 時鐘 | 顯示正確時分 |
