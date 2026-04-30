# 玩家美術、動畫、音效與操控系統 深入分析

## 模型資訊（male.glb）

| 項目 | 內容 |
|------|------|
| 格式 | GLB（Binary GLTF，所有資料打包成單一二進制檔） |
| 動畫幀率 | 15 FPS（import 設定） |
| 骨骼數量 | 70 根骨骼（bones/0 ~ bones/69，從 Skeleton3D 的初始姿勢可見） |
| 附著點 | head (bone_idx=19)、weapon_L (bone_idx=41)、weapon_R (bone_idx=61) |

### 重要骨骼附著點

```
Armature/Skeleton3D
├── head (BoneAttachment3D, bone_idx=19)
│   └── audio (AudioStreamPlayer3D)   ← 玩家語音/音效來源
├── weapon_L (BoneAttachment3D, bone_idx=41)
│   └── audio (AudioStreamPlayer3D)   ← 武器音效（磨刀聲等）
└── weapon_R (BoneAttachment3D, bone_idx=61)
    └── audio (AudioStreamPlayer3D)   ← 右手武器音效（未使用）
```

---

## 動畫庫完整清單（AnimationLibrary_vhmvp）

玩家動畫架構採「**雙層 AnimationPlayer**」設計：

```
male.glb 內嵌的 AnimationPlayer（骨骼動畫）
    ↑ 被包裝
AnimationsWithSounds（自建 AnimationPlayer）
    每個動畫 = 骨骼動畫 track + 音效 audio track
    ↑ 被驅動
AnimationTree（狀態機，控制哪個動畫播放）
```

| 動畫名 | 長度 | 骨骼動畫 | 音效 | 音效節點 | 音效時機 |
|--------|------|---------|------|---------|---------|
| `death` | 1.4s | death | `death.wav` | head/audio | t=0.1s |
| `dodge` | 1.5s | dodge | `dodge.wav` | head/audio | t=0.2s |
| `drink` | 2.0s | drink | `potion_drink.wav` | head/audio | t=0.35s（舉起瓶子時） |
| `eat` | - | - | `eat.wav` | head/audio | t=0 |
| `fall` | 2.0s | - | `male_fall_death_02.wav` | head/audio | t=0（開始尖叫） |
| `idle` | 1.5s | idle | - | - | - |
| `jump` | - | - | `jump.wav` | head/audio | t=0 |
| `left_attack_0` | - | left_attack_0 | - | - | - |
| `rest` | 5.0s | rest | - | - | - |
| `run` | - | run | - | - | - |
| `walk` | 1.5s | walk | - | - | - |
| `whetstone` | 1.7s | whetstone | `whetstone.wav` | weapon_L/audio | t=0.2s（開始磨刀時） |

**音效延遲設計的意義**：
- `drink`: 延遲 0.35s = 配合「拿起藥瓶→喝下」的動畫幀，聲音在喝藥時響起
- `dodge`: 延遲 0.2s = 配合身體開始移動的時機
- `death`: 延遲 0.1s = 微小延遲讓死亡音效不會在第一幀就爆出

---

## AnimationTree 狀態機（male.tscn:225-244）

### 主狀態機（31）

```
Start → idle-loop

idle-loop → movement     [moving, xfade=0.2s]
idle-loop → drink        [drinking]
idle-loop → eat          [eating]
idle-loop → whetstone    [whetstone]
idle-loop → rest         [resting]
idle-loop → left_attack_0[attacking]
idle-loop → death        [dead, xfade=0.2s]

movement → idle-loop     [idle, xfade=0.2s]
movement → left_attack_0 [attacking]
movement → rest          [resting]

left_attack_0 → idle-loop[idle（自動播完）]
left_attack_0 → movement [moving]

drink/eat/whetstone/rest → idle-loop（自動播完）
death → idle-loop [idle]（復活用）
```

**xfade_time=0.2~0.5s**：主狀態切換有過渡混合，避免動畫突變。

### 移動子狀態機（50）

```
Start → walk-loop [walking] / run-loop [running]

walk-loop ↔ run-loop    (xfade=0.5s)
run-loop  → jump        [jumping]
jump      → run-loop    [running AND is_on_floor()]   ← 需同時落地
jump      → walk-loop   [walking AND is_on_floor()]
jump      → falling     [jumping AND velocity.y < -10] ← 快速下落進入 screaming
falling   → screaming   [jumping AND velocity.y < -10]
falling   → run-loop    [running AND is_on_floor()]
falling   → walk-loop   [walking AND is_on_floor()]
screaming → End         (自動)
walk-loop → dodge       [dodging]
dodge     → walk-loop   (自動播完)
```

**advance_expression 特性**：
```gdscript
# 這些 transition 用 GDScript 表達式作為觸發條件
# 例如 jump→run-loop 的條件：
advance_condition = "running"
advance_expression = "get_parent().is_on_floor()"  # 須同時滿足
```

`falling` 狀態（動畫 = `run`）→ `screaming`（動畫 = `fall`）：  
當玩家下落速度超過 10 m/s，播放「fall」動畫（即恐懼聲音），模擬高空墜落的驚嚇反應。

---

## 玩家節點結構（male.tscn）

```
player (CharacterBody3D, floor_max_angle=40°)
├── Armature (GLB 模型)
│   └── Skeleton3D (70 bones)
│       ├── head BoneAttachment (bone 19)
│       │   └── audio AudioStreamPlayer3D
│       ├── weapon_L BoneAttachment (bone 41)
│       │   └── audio AudioStreamPlayer3D
│       └── weapon_R BoneAttachment (bone 61)
│           └── audio AudioStreamPlayer3D
├── shape CollisionShape3D (BoxShape 0.5×1.8×0.2)   ← 站立碰撞
│   （center at y=0.9）
├── drop_item Marker3D (0, 1, 2)                     ← 物品丟出位置（身前2m）
├── interact Area3D                                  ← 互動偵測
│   └── shape BoxShape 1.5×2×0.4 (center y=1)       ← 正面扇形範圍
├── name Marker3D (y=2.25)                           ← 玩家名稱標籤位置
├── AnimationTree                                    ← 狀態機
│   └── anim_player = AnimationsWithSounds
├── AnimationsWithSounds AnimationPlayer             ← 雙層包裝
└── Flames GPUParticles3D                            ← 燃燒異常效果
```

---

## 燃燒粒子效果（Flames）

```
GPUParticles3D:
    emitting = false（預設關閉）
    amount = 32
    lifetime = 1.6s

ParticleProcessMaterial:
    emission_sphere_radius = 0.3（從身體範圍噴出）
    angle_max = 360°（四面八方）
    direction = (0, -1, 0)（向下，但有浮力）
    spread = 5°
    gravity = (0, 0, 0)（無重力，自行上漂）
    radial_accel_max = 0.5（向外輻散）
    lifetime_randomness = 0.42（壽命不一，自然感）

顏色漸層：
    t=0.00: 黃色 (1, 0.986, 0.16)   ← 新生火星
    t=0.12: 橙色 (0.95, 0.57, 0)    ← 火焰
    t=0.43: 深橙 (1, 0.337, 0.03)   ← 熱核心
    t=1.00: 紅色 (1, 0, 0)          ← 消散
```

觸發條件（player.gd:63-67）：
```gdscript
func _on_ailment_added(ailment):
    match ailment:
        "fire":
            $Flames.emitting = true
            effect_over_time("burning", 1.0, 3, damage.bind(10, 0.5), func():
                ailments.erase("fire")
                $Flames.emitting = false)
```

---

## 玩家碰撞體設計

```
BoxShape3D: size = Vector3(0.5, 1.8, 0.2)
Transform: y+0.9（底部對齊地面）
```

**薄平板碰撞體的權衡**：
- 寬=0.5, 深=0.2（非常薄），比標準 CapsuleShape 更容易穿越門縫
- 可能導致側面碰撞不精確（怪物爪子從側面穿過）
- 優點：進入狹窄空間（門廊、峽谷）不易卡住

---

## 互動偵測區域（interact）

```
Area3D → interact
    BoxShape3D: size = Vector3(1.5, 2.0, 0.4)
    Transform: y=1（中心在腰部）
```

**0.4 深度的設計意義**：
- 只偵測正前方很窄的範圍
- 避免背後的互動物件誤觸發
- 配合 Player.get_nearest_interact() 的距離排序，確保互動的是玩家正在面對的物件

---

## 操控輸入完整流程

### 每幀更新（_physics_process）

```
1. 讀取移動輸入（鍵盤 WASD / 觸控搖桿）
   → 轉換為相機相對的 direction 向量
   → 移除 Y 分量（純水平移動）
   → 正規化

2. 判斷動畫狀態
   if direction != Vector3():
       if idle: walk()
       if run key: run()
   else:
       stop()

3. 呼叫 Entity.move_entity(delta)
   → AnimationTree 狀態決定速度倍率
   → 加重力
   → move_and_slide()

4. 相機 yaw_node 跟隨玩家位置
```

### 事件輸入（_input）

| 按鍵 | 動作 | 條件 |
|------|------|------|
| 左鍵 | `attack("left_attack_0")` | 無 |
| 右鍵 | `attack("right_attack_0")` | 無（注：right_attack 動畫未在狀態機中，TODO） |
| 空白（跑中） | `jump()` | 正在 running 狀態 |
| 空白（非跑） | `dodge()` | 非 running |
| Shift 按下 | `run()` | 無 |
| Shift 放開 | `walk()` | 無 |
| E | `interact_with_nearest()` | 無 |
| I（放開） | `open_player_inventory()` | 無 |

### 跑步→跳躍 vs 靜止→閃避

```gdscript
# player.gd:103-109
elif event.is_action_pressed("player_dodge"):
    if $AnimationTree["parameters/movement/conditions/running"]:
        jump()     ← 跑步時按空白 = 跳躍
    else:
        dodge()    ← 靜止/走路時按空白 = 閃避
```

這個設計使空白鍵具備「語境感知」行為，符合 Monster Hunter 原作（跑步起跳/靜止閃避）。

---

## 右攻擊缺失問題

```gdscript
# player.gd:100
elif event.is_action_pressed("player_attack_right"):
    attack("right_attack_0")
```

`attack("right_attack_0")` 呼叫 Entity.attack()：
```gdscript
# entity.gd:342
func attack(_attack_name):
    $AnimationTree["parameters/conditions/attacking"] = true
```

**問題**：`attack()` 完全忽略傳入的 `_attack_name` 參數，狀態機只有 `left_attack_0` 節點，右攻擊按鍵實際上也播放左攻擊動畫。

---

## 音效資源總表

| 檔案 | 用途 |
|------|------|
| `whetstone.wav` | 磨刀音效（via weapon_L/audio，動畫 t=0.2s） |
| `dodge.wav` | 閃避音效（via head/audio，動畫 t=0.2s） |
| `jump.wav` | 跳躍音效（via head/audio，動畫 t=0s） |
| `potion_drink.wav` | 喝藥水音效（via head/audio，動畫 t=0.35s） |
| `death.wav` | 死亡音效（via head/audio，動畫 t=0.1s） |
| `eat.wav` | 吃肉音效（via head/audio，動畫 t=0s） |
| `345434__artmasterrich__male_fall_death_02.wav` | 高空墜落驚叫（via head/audio） |
| `laser.wav` | 雷射劍命中音效（via weapon.gd `$audio.play()`） |
| `switch.ogg` | 切換快捷物品欄音效 |
| `beatbox.wav` | （用途未確認，可能是背景音或測試音） |

---

## AnimationsWithSounds 設計模式分析

```
標準做法：
    GDScript 中在 play_animation() 後手動 play_sound()

本專案做法：
    AnimationPlayer 的 audio track 直接在特定時間點觸發音效

優點：
    1. 音效與動畫幀精確同步（不受程式碼執行時機影響）
    2. 調整音效時機只需在編輯器移動 audio key，不改程式碼
    3. 不同聲音來源（頭部/武器）可在同一動畫軌道管理

缺點：
    1. AnimationPlayer 不能在執行時期動態替換音效（需改場景）
    2. 無法依情境（HP 低、環境）選擇不同音效
```
