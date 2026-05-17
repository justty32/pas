# 怪物美術、動畫與音效系統 深入分析

## 模型資訊（dragon.gltf）

| 項目 | 內容 |
|------|------|
| 格式 | GLTF（純文字 JSON，貼圖嵌入） |
| 動畫幀率 | 15 FPS（import 設定） |
| 縮放 | 0.01（場景中縮放修正，模型原始單位約為遊戲單位的 100 倍） |
| 骨架 | 動畫嵌入 GLTF，由 Godot 自動解析為 AnimationPlayer |
| 貼圖 | 嵌入 GLTF 內部（無獨立貼圖檔案，故無材質 .tres 覆蓋） |

---

## 碰撞體結構（dragon.tscn:521-648）

Dragon 使用 **33 個 ConvexPolygonShape3D** 拼湊出怪物全身的精確碰撞外殼：

```
dragon (CharacterBody3D)
├── @CollisionShape3D@29210  ← 軀幹右翼區
├── @CollisionShape3D@29209  ← 軀幹後翼區
├── head                     ← 頭部（具名，未來可用於弱點部位偵測）
├── @CollisionShape3D@29207  ← 頸部前段
├── ... (共 20 個匿名碰撞體)
├── leg_front_left           ← 左前腳（具名）
├── leg_rear_left            ← 左後腳（具名）
├── leg_front_right          ← 右前腳（具名）
├── leg_rear_right           ← 右後腳（具名）
├── tail                     ← 尾巴（具名）
└── CollisionShape3D         ← 翅膀右側
```

**設計意義**：  
- 具名部位（head, leg_*, tail）預留了未來部位破壞系統的基礎，符合 Monster Hunter 原作砍尾設計
- 全部縮放 0.01，與模型縮放一致
- ConvexPolygon 由 Godot 編輯器自動分解（Vhacd/AutoConvex），不需手工建模

---

## AnimationTree 狀態機（dragon.tscn:499-512）

### 主狀態機

```
Start → idle-loop
idle-loop → movement   [moving]
idle-loop → attack     [attacking]
idle-loop → rest       [resting]
idle-loop → death      [dead]
movement  → idle       [idle]
movement  → attack     [attacking]
movement  → rest       [resting]
attack    → idle-loop  (自動，播完)
rest      → idle-loop  [idle]
death     → End        (自動，播完)
```

### 移動子狀態機（movement 內部）

```
Start → walk-loop [walking] / run-loop [running]
walk-loop ↔ run-loop    (walking/running 條件)
run-loop → jump         [jumping]
jump → run-loop         (落地，switch_mode=2 立即切)
walk-loop → dodge       [dodging]
dodge → walk-loop       [walking]
```

---

## 動畫庫與音效綁定（dragon.tscn:372-382）

怪物的動畫架構分**兩層**：

```
AnimationPlayer（從 GLTF 載入的骨骼動畫）
    ↑ 被引用
AnimationTree（狀態機控制播放）
    ↑ 同時
AnimationPlayer（自定義層，覆蓋 fire 粒子與音效）
```

第二個 `AnimationPlayer`（龍場景內自建）的動畫庫：

| 動畫名 | 長度 | 控制內容 |
|--------|------|---------|
| `attack` | 5.0s | `fire:emitting=true`（0~3.5s），`entity_audio` 播放 `dragon.wav`（t=0.2s） |
| `death` | 2.5s | `entity_audio` 播放 `dragon-roar.wav`（t=0s），`fire:emitting=false` |
| `dodge` | - | `fire:emitting=false` |
| `idle` | - | `fire:emitting=false` |
| `jump` | - | `fire:emitting=false` |
| `rest` | - | `fire:emitting=false` |
| `run` | - | `fire:emitting=false` |
| `walk` | - | `fire:emitting=false` |

**設計要點**：
- 攻擊動畫（5秒）= 骨骼攻擊動畫 + 火焰粒子開啟 + 龍吟音效
- 死亡動畫（2.5秒）= 骨骼死亡動畫 + 龍吼音效 + 確保火焰關閉
- 其他狀態確保火焰是關閉的（防止殘留）

---

## 音效資源

| 音效檔 | 用途 | 播放時機 |
|--------|------|---------|
| `dragon.wav` | 龍吟/攻擊音效 | attack 動畫 t=0.2s（稍微延遲，避免攻擊動作開始就響） |
| `dragon-roar.wav` | 龍吼/死亡音效 | death 動畫 t=0s（立即播放） |

音效透過場景中的 `entity_audio`（AudioStreamPlayer3D）播放：
```
[node name="entity_audio" type="AudioStreamPlayer3D" parent="." index="38"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2.177, 1.289)
unit_size = 20.0   ← 3D 空間衰減，距離 20 單位聽不到
```

---

## 火焰噴射粒子系統（dragon.tscn:661-671）

```gdscript
[node name="fire" type="GPUParticles3D" parent="." index="35"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 2.0775, 1.637)
emitting = false
amount = 256
lifetime = 5.0
randomness = 0.5
visibility_aabb = AABB(-16, -16, -16, 32, 32, 32)
```

**粒子材質設定（ParticleProcessMaterial）：**
```
emission_shape = sphere, radius=0.1（從嘴部小範圍噴出）
direction = (0, -1, 1)（斜向前下方，火焰噴射感）
spread = 5°（集中噴出，不散射）
flatness = 0.25（稍微壓扁，水平擴散）
initial_velocity = 1.2~1.5
gravity = (0, 0.3, 0)（輕微向上漂浮）
collision_mode = 1，bounce=0.5（粒子可與地面彈跳）
```

**顏色漸層（時間軸）：**
```
t=0.00: 黑色（alpha=1）        ← 噴出點藏在嘴裡看不到
t=0.09: 深橙紅 (0.98, 0.22, 0) ← 火焰核心
t=0.43: 橙黃 (0.97, 0.62, 0)   ← 火焰中段
t=0.68: 淡橙 (0.80, 0.58, 0.17)← 火焰外緣
t=0.84: 灰白 (0.72, 0.72, 0.72)← 煙霧
t=1.00: 黑色（消散）
```

**粒子材質（StandardMaterial3D）：**
- `billboard_mode = 3`（粒子面向相機）
- `vertex_color_use_as_albedo = true`（使用粒子顏色漸層）
- `blend_mode = 1`（Additive 加法混合，火焰發光效果）
- Texture：`flame_01.png`（kenney_particlePack 噴焰貼圖）

**RayCast3D 傷害感測器：**
```
target_position = (0, -3, 5)   ← 向前方 5 單位、略向下，覆蓋火焰噴射範圍
enabled = false（平時關閉，攻擊時在 check_fire_collision() 開啟）
```

---

## 感嘆號（exclamation）視覺效果（dragon.tscn:674-681）

```
[node name="exclamation" type="MeshInstance3D"]
visible = false
mesh = QuadMesh (0.5x0.5)   ← 顯示 warning.png 的公告板
材質：warning.png + billboard_keep_scale=true + transparency
```

動畫（5秒）：
```
t=0: visible=true, scale=(0.1, 0.1, 0.1)  ← 彈出
t=0.5: scale=(1, 1, 1)                    ← 放大
t=4.5: scale=(1, 1, 1)                    ← 維持
t=5: scale=(0.1, 0.1, 0.1), visible=false ← 縮小消失
```

當怪物進入戰鬥模式（`hunt_target()` 首次呼叫）觸發：
```gdscript
# monster.gd:156-159
if not combat:
    combat = true
    $exclamation/AnimationPlayer.play("exclamation")
```

---

## 視野偵測範圍

```
[node name="view" type="Area3D"]
└── radius (SphereShape3D) radius=20.0   ← 20 單位球形視野
```

玩家進入/離開此 Area3D → `_on_view_body_entered/exited` → 加入/移出 `players[]` 候選清單

---

## 導航設定

```
NavigationAgent3D:
    target_desired_distance = 5.0    ← 距目標 5 單位視為「到達」
    path_max_distance = 30.01        ← 偏離路徑 30 單位時重算
    simplify_path = true
    simplify_epsilon = 0.2           ← 路徑簡化精度
    debug_enabled = true             ← 開發中可視化路徑（正式版應關閉）
```
