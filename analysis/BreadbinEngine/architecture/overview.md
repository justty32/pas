# BreadbinEngine — 架構總覽 (Level 1 & 2)

> 分析日期：2026-04-30  
> 引擎版本：Godot 4.0（Mobile 渲染器）  
> 專案目標：仿 Dark Souls / Bloodborne 風格的第三人稱動作 RPG 框架

---

## 一、專案定位與技術棧

| 項目 | 內容 |
|---|---|
| 引擎 | Godot 4.0 |
| 語言 | GDScript |
| 渲染 | Mobile Renderer（`renderer/rendering_method="mobile"`）|
| 主場景 | `res://Scenes/Levels/TestLevel.tscn` |
| 設計哲學 | 高度 softcoded，所有武器招式透過資料表驅動 |

---

## 二、目錄結構

```
BreadbinEngine/
├── Animations/          # Mixamo 骨架映射
├── Data/                # AttackTable.tres（CSV 格式）
├── Meshes/              # 3D 模型
├── Scenes/              # 場景：Levels、Weapons、UI 等
├── Scripts/
│   ├── Actors/          # 角色基底類與 AI
│   │   ├── AI/          # AI 感知碰撞區
│   │   └── Models/      # 模型掛載點（Model Base）
│   ├── Combat/          # 武器、傷害 Hitbox、受擊區
│   ├── Debug/           # Debug 工具
│   ├── Globals/         # Autoload 全域腳本
│   ├── Inventory/       # 物品資源
│   ├── LevelManager/    # Spawner
│   ├── UI/              # 敵方血條
│   └── VFX/             # 特效基底
├── Sound/               # 音訊匯流排設定
└── Textures/
```

---

## 三、Autoload 全域腳本

共 4 個 Autoload，在所有場景啟動時自動載入：

| 名稱 | 路徑 | 職責 |
|---|---|---|
| `GlobalActorSettings` | `Scripts/Globals/Global_Actor_Settings.gd` | 隊伍矩陣、體力回復速率 |
| `GlobalDisplaySettings` | `Scripts/Globals/Global_Display_Settings.gd` | 敵人血條顯示模式 |
| `GlobalSystemSettings` | `Scripts/Globals/Global_System_Settings.gd` | 儲存路徑、Debug 模式、攝影機速度 |
| `AttackTable` | `Scripts/Globals/AttackTable.gd` | CSV 攻擊表（ID → 動畫名稱 + 傷害倍率）|

---

## 四、Class 繼承體系

```
CharacterBody3D
└── ActorBase              (Scripts/Actors/ActorBase.gd)
    ├── PlayerActor        (Scripts/Actors/PlayerBase.gd)
    └── AIActor            (Scripts/Actors/Actor_AI.gd)

Node
└── WeaponBase             (Scripts/Combat/Weapon_Base.gd)

Node3D
├── ActorModel             (Scripts/Actors/Models/ActorModelBase.gd)
│   └── PlayerModel        (Scripts/Actors/Models/PlayerModelBase.gd)
├── Spawner                (Scripts/LevelManager/Spawner_Base.gd)
├── VFX_Base               (Scripts/VFX/VFXBase.gd)
└── BGProp_Breakable       (Scripts/Actors/BGProp_Breakable.gd)

AnimationPlayer
└── ActorAnimationPlayer   (Scripts/Actors/ActorAnimationPlayer.gd)

AnimationTree
└── ActorAnimationTree     (Scripts/Actors/ActorAnimationTree.gd)

Area3D
├── ActorHitArea           (Scripts/Combat/ActorHitArea_Base.gd)   ← 受擊
├── Hitbox_Damage          (Scripts/Combat/Hitbox_Damage.gd)       ← 攻擊判定
└── Hitbox_AIChecker       (Scripts/Actors/AI/AI_CheckerHitbox.gd) ← AI 感知

Resource
└── ItemBase               (Scripts/Inventory/InventoryBase.gd)
```

---

## 五、物理層分配

| Layer | 名稱 | 用途 |
|---|---|---|
| 3 | ActorCollision | 角色碰撞體 |
| 4 | World | 場景幾何 |
| 5 | Killbox | 即死區域 |
| 10 | DamageHitboxes | 武器攻擊發射層（廣播） |
| 11 | ActorHitboxes | 角色受擊偵測層（監聽） |
| 12 | BreakableObjects | 可破壞道具 |

**碰撞規則**：
- `Hitbox_Damage`（武器）在 Layer 10 廣播 → `ActorHitArea`（角色）在 Layer 11 監聽
- 互相感應後觸發 `_ActorHitArea_entered()` 傷害流程

---

## 六、隊伍友傷矩陣

定義於 `Global_Actor_Settings.gd:6`：

```gdscript
const Teams_CanHurt : Array = [
    [],                # 0: Inactive
    [0,3,4,5,6],       # 1: Players → 可傷害 Inactive、FF Friendly、兩隊敵人
    [4,5,6],           # 2: Friendly NPC（無友傷）
    [4,5,6],           # 3: Friendly NPC（有友傷）
    [1,2,3],           # 4: Hostile NPC
    [1,2,3,4,6],       # 5: Enemy Team A
    [1,2,3,4,5]        # 6: Enemy Team B
]
```

---

## 七、輸入對照表

| 動作 | 鍵盤/滑鼠 | 手把 |
|---|---|---|
| 移動 | WASD | 左搖桿 |
| 攝影機 | 滑鼠移動 | 右搖桿 |
| R1（輕攻擊） | 左鍵 | RB |
| R2（重攻擊） | Shift + 左鍵 / E | RT |
| L1（左手/格擋） | 右鍵 | — |
| L2（左手強攻） | Shift + 右鍵 | — |
| 翻滾 | Space | — |
| 跳躍/衝刺（長按）| Shift | — |
| 鎖定目標 | Q | — |

---

## 八、儲存系統

- 儲存路徑：`user://BreadbinSave.save`（二進位格式）
- 每個 Actor 依序存入：HP、Stamina、Transform、Two_Handing_State（僅玩家）、HasBeenKilled
- `SaveStatus` 標誌控制是否儲存該 Actor
