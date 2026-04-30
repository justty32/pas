# Cogito — Level 5B Attribute 子類深度分析

## 一、CogitoAttribute 基類

**位置**：`addons/cogito/Components/Attributes/cogito_attribute.gd`，繼承 `Node`

### 核心欄位

| 欄位 | 類型 | 用途 |
|---|---|---|
| `attribute_name` | String | 程式識別鍵（如 "health"，對應 `player_attributes` 字典） |
| `attribute_display_name` | String | UI 顯示名稱 |
| `attribute_color` / `attribute_icon` | Color/Texture2D | HUD 顯示用 |
| `value_max` / `value_start` | float | 最大值 / 初始值 |
| `is_locked` | bool | 鎖定時 add/subtract 仍發射信號但值不變 |
| `dont_save_current_value` | bool | 不存讀當前值（固定滿格屬性用） |
| `attribute_visibility` | Enum | Hud / Hud_and_Interface / Interface_Only / Hidden |

### value_current 響應式屬性（setter）

```
var value_current : float:
  set(value):
    var prev_value = value_current
    value_current = value
    
    if prev_value < value_current:  // 值上升
      value_current = clamp(value_current, 0, value_max)
      attribute_changed.emit(name, current, max, true)   // has_increased = true
    elif prev_value > value_current:  // 值下降
      value_current = clamp(value_current, 0, value_max)
      attribute_changed.emit(name, current, max, false)  // has_increased = false
    
    if value_current <= 0:
      value_current = 0
      attribute_reached_zero.emit(name, current, max)
```

只在值真正改變時發射信號，避免重複廣播。

### 基礎方法

```
add(amount):
  if is_locked: 只重新發射信號，不改值
  value_current += amount

subtract(amount):
  if is_locked: 只重新發射信號，不改值
  last_passed_subtracted_amount = amount  // 供 AutoConsume 使用
  value_current -= amount

set_attribute(current, max):
  value_max = max  // 先設 max（setter 的 clamp 需要它）
  value_current = clamp(current, 0, max)
```

### 玩家端的屬性字典

**位置**：`cogito_player.gd:228-245`

```
// _ready() 中自動掃描
for attribute in find_children("","CogitoAttribute",false):
  player_attributes[attribute.attribute_name] = attribute

// 特殊屬性額外掛鉤
health_attribute.death.connect(_on_death)
stamina_attribute = player_attributes.get("stamina")   // 移動系統直接引用
visibility_attribute = player_attributes.get("visibility")

// sanity 與 visibility 連接
visibility_attribute.attribute_changed.connect(sanity_attribute.on_visibility_changed)
```

---

## 二、CogitoHealthAttribute

**位置**：`Components/Attributes/cogito_health_attribute.gd`

### 額外信號與欄位

```
signal damage_taken()    // 受傷（非死亡）時發射
signal death()           // 血量歸零時發射

@export var no_sanity_damage : float     // 理智為零時的每秒持續傷害
@export var sound_on_hit : AudioStream   // 命中音效（也在死亡時播）
@export var sound_on_damage_taken : AudioStream  // 受傷音效（不在死亡時播）
@export var sound_on_death : AudioStream
@export var destroy_on_death : Array[NodePath]  // 死亡時銷毀的節點
@export var spawn_on_death : Array[PackedScene]  // 死亡時生成的場景
```

### 初始化與連接

```
_ready():
  value_current = value_start
  attribute_reached_zero.connect(on_death)
  attribute_changed.connect(on_health_change)
  attribute_changed.emit(...)  // 主動廣播一次初始值，讓 HUD 正確顯示
```

### on_health_change（受傷回應）

```
on_health_change(_, _, _, has_increased):
  if !has_increased:
    damage_taken.emit()
    Audio.play_sound_3d(sound_on_hit)
    if sound_on_damage_taken and current > 0:   // 未死亡才播受傷音
      Audio.play_sound_3d(sound_on_damage_taken)
```

### on_death（死亡處理）

```
on_death(_, _, _):
  death.emit()
  Audio.play_sound_3d(sound_on_death)
  
  for scene in spawn_on_death:
    spawned = scene.instantiate()
    spawned.position = parent_position
    spawned.rotation = parent_rotation
    scene_tree.current_scene.add_child(spawned)  // 生成碎片/血跡等
  
  for nodepath in destroy_on_death:
    get_node(nodepath).queue_free()  // 移除軀體等節點
```

**注意**：死亡僅觸發效果，不自動移除宿主。宿主節點需透過 `destroy_on_death` 或 `LootComponent` 自行處理。

---

## 三、CogitoStaminaAttribute（耐力）

**位置**：`Components/Attributes/cogito_stamina_attribute.gd`

### 機制一覽

| 機制 | 欄位 | 說明 |
|---|---|---|
| 奔跑消耗 | `run_exhaustion_speed` | 平地每秒扣減量 |
| 跳躍消耗 | `jump_exhaustion` | 每次跳躍扣減量 |
| 自動恢復 | `stamina_regen_speed` | 恢復速率（每秒） |
| 恢復延遲 | `regenerate_after` | 停止奔跑後多少秒才恢復（Timer） |

### _process 流程

```
_process(delta):
  if is_regenerating:
    add(stamina_regen_speed * delta)
    if current >= max: is_regenerating = false
  
  if player.is_sprinting and player.current_speed > WALKING_SPEED and velocity > 0.1:
    regen_timer.stop()
    is_regenerating = false
    subtract(_run_exhaustion() * delta)   // 奔跑中持續扣減
  
  last_y = player.global_position.y   // 記錄本幀 Y 位置（坡度偵測用）
  
  if 不在奔跑 and 未在恢復 and current < max:
    regen_timer.start()  // 開始等待恢復延遲
```

### 坡度消耗計算（_run_exhaustion）

```
_run_exhaustion() -> float:
  if !use_floor_slope_for_run_exhaustion: return run_exhaustion_speed
  
  floor_normal = player.get_floor_normal()
  movement_direction = player.main_velocity.normalized()
  slope_factor = movement_direction.dot(floor_normal)  // -1~1
  
  if slope_factor ≈ 0:  // 平地
    if player.position.y != last_y:  // 但其實在上下台階
      slope_factor = (last_y - player.position.y) * step_slope_multiplier
      slope_factor = clamp(slope_factor, -1, 1)
    else: return run_exhaustion_speed
  
  if slope_factor < 0.0001:  // 上坡（dot 接近 0 但面法線朝上）
    return lerp(run_exhaustion_speed, uphill_run_exhaustion_max_speed, abs(slope_factor))
  else:  // 下坡
    return lerp(run_exhaustion_speed, downhill_run_exhaustion_max_speed, slope_factor)
```

上坡消耗最多可達 `uphill_run_exhaustion_max_speed`（預設 6）倍基礎值。

---

## 四、CogitoSanityAttribute（理智）

**位置**：`Components/Attributes/cogito_sanity_attribute.gd`

### 狀態旗標

```
is_decaying : bool    // 正在衰減（黑暗中、觸發點）
is_recovering : bool  // 正在恢復（走入光照）
recovery_max : float  // 恢復目標上限（與光照強度正比）
```

### _process 流程

```
_process(delta):
  if is_decaying:   subtract(decay_rate * delta)
  if is_recovering and current < recovery_max:  add(recovery_rate * delta)
  
  if value_current <= 0:
    player.decrease_attribute("health", damage_when_zero * delta)  // 直接扣血
```

理智為零時，直接呼叫 `player.decrease_attribute("health",...)` 造成持續傷害，不依賴 HitboxComponent。

### 可見度連接（on_visibility_changed）

```
on_visibility_changed(_, visibility_current, visibility_max, _):
  if visibility_current > 0:   // 有光
    stop_decay()
    recovery_max = visibility_current / visibility_max * value_max  // 恢復上限與亮度成比例
    is_recovering = true
  
  if visibility_current <= 0 and decay_in_darkness:  // 完全黑暗
    stop_recovery()
    start_decay()
```

**連接方式（cogito_player.gd:244）**：
```
visibility_attribute.attribute_changed.connect(sanity_attribute.on_visibility_changed)
```

---

## 五、CogitoLightmeter（光度計）

**位置**：`Components/Attributes/cogito_light_meter_attribute.gd`

### 測量原理：SubViewport 單像素採樣

```
update_lightmeter_attribute():
  light_detection.global_position = player.global_position  // 跟隨玩家
  texture = sub_viewport.get_texture()
  color = get_average_color(texture)
    → image = texture.get_image()
    → image.resize(1, 1, INTERPOLATE_LANCZOS)  // 縮至 1x1 取平均
    → return image.get_pixel(0, 0)
  set_attribute(color.get_luminance() * 100, 100)  // 亮度轉換為 0~100
```

SubViewport 以 `subviewport_resolution`（預設 256）解析度捕捉玩家位置的場景畫面，縮至 1px 取平均亮度。

### 效能節流

```
update_on_move_only: bool = true
  → 玩家不移動時跳過更新

update_frequency: float = 1.0
  → Timer 固定間隔更新（與 move_only 疊加）

// headless 模式跳過（伺服器端不需要）
if DisplayServer.get_name() == "headless": set_process(false)
```

⚠ **效能注意**：即使有節流，每次採樣仍需 GPU 讀取像素（`get_image()` 是阻塞操作），在複雜場景中可能有 0.5~2ms 的延遲。

---

## 六、CogitoVisibilityAttribute（可見度）

**位置**：`Components/Attributes/cogito_visibility_attribute.gd`

```
extends CogitoAttribute

func _ready():
  value_current = value_start

func check_current_visibility():
  attribute_changed.emit(attribute_name, value_current, value_max, true)
```

近乎空殼。**實際值由外部設置**：
- `LightzoneComponent`：玩家進入時直接設定 visibility 值
- `LightzoneSwitchComponent`：可開關的亮度區域
- 連接至 `CogitoSanityAttribute.on_visibility_changed`

`check_current_visibility()` 用於載入後初始化，強制廣播當前值讓 sanity 正確初始化。

---

## 七、Attribute 子類關係圖

```
CogitoAttribute（基類）
  ├─ CogitoHealthAttribute
  │     ├─ signal: damage_taken, death
  │     ├─ spawn_on_death / destroy_on_death
  │     └─ 三種音效（hit / damage / death）
  │
  ├─ CogitoStaminaAttribute
  │     ├─ _process(): 奔跑扣減 + regen_timer 恢復
  │     └─ _run_exhaustion(): 坡度感知耗體力
  │
  ├─ CogitoSanityAttribute
  │     ├─ _process(): decay/recover 連續計算
  │     ├─ 零理智 → player.decrease_attribute("health")
  │     └─ on_visibility_changed: 與 visibility 信號連接
  │
  ├─ CogitoLightmeter
  │     ├─ SubViewport + 1px 採樣
  │     └─ get_luminance() → set_attribute(0~100)
  │
  └─ CogitoVisibilityAttribute
        └─ 空殼，值由 LightzoneComponent 外部設定
```

---

## 八、AutoConsume 系列（附錄）

**位置**：`Components/AutoConsumes/`

`AutoConsume`（`health_auto_consume.gd` / `stamina_auto_consume.gd`）：
- 監聽 `CogitoAttribute.attribute_reached_zero`
- 自動掃描玩家物品欄，使用最近一個可恢復的消耗品
- 使用 `last_passed_subtracted_amount` 得知「差多少」，精確補足

這讓玩家在血量快歸零時自動飲藥（如有配置），無需手動操作。

---

## 九、設計模式總結

| 模式 | 說明 |
|---|---|
| 響應式 setter 驅動 | 所有 UI 和邏輯僅訂閱 `attribute_changed` 信號，不輪詢 |
| 字典注冊 | `player_attributes[name]` 動態字典，不硬編碼 |
| `is_locked` 穿透 | 即使鎖定也發射信號，讓 HUD 維持正確顯示 |
| 子類擴充訊號 | 基類只有 `attribute_changed`/`reached_zero`，子類自由加訊號（death/damage_taken） |
| 跨屬性連接 | sanity.on_visibility_changed 連接 visibility.attribute_changed，避免集中控制 |
