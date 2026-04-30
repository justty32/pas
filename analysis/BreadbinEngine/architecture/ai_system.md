# BreadbinEngine — AI 系統分析

> 分析日期：2026-04-30

---

## 一、AIActor 繼承結構

```
ActorBase (CharacterBody3D)
└── AIActor (Scripts/Actors/Actor_AI.gd)
```

`AIActor` 繼承 `ActorBase` 所有戰鬥與物理功能，加上 AI 決策層。

---

## 二、NPC Tier 系統

```gdscript
# Actor_AI.gd:5
@export_enum("Wildlife","Private","Corporal","Sergeant","Lieutenant","Captain","Colonel")
var NPC_Tier : int
```

Tier 影響 **process priority**（`Actor_AI.gd:36`）：
```gdscript
process_priority = (50 + NPC_Tier)
```
高等級 NPC 每幀優先更新，確保 Boss 級敵人反應優先於雜兵。

---

## 三、感知系統

```gdscript
@export var VisionArea: Area3D    # Inspector 指定感知範圍 Area3D
var TargetNode = self             # 當前追蹤目標
```

感知 Hitbox 使用 `Hitbox_AIChecker`（`Scripts/Actors/AI/AI_CheckerHitbox.gd`）— 繼承 Area3D，屬於獨立 Area3D 用於偵測角色進入感知範圍。

---

## 四、攻擊機率系統

### 三層攻擊分級
| 變數 | 含義 |
|---|---|
| `AttackChanceLight` | 輕攻擊機率權重（0-100）|
| `AttackChanceMid` | 中攻擊機率權重（0-100）|
| `AttackChanceHeavy` | 重攻擊機率權重（0-100）|

### 標準化計算（`CalculateAttackChances()`，Actor_AI.gd:44）
```gdscript
var FinalAttackSum = AttackChanceLight + AttackChanceMid + AttackChanceHeavy
RealAttackChanceLight = AttackChanceLight / FinalAttackSum   # 歸一化比例
RealAttackChanceMid   = AttackChanceMid   / FinalAttackSum
RealAttackChanceHeavy = AttackChanceHeavy / FinalAttackSum
```

**範例**：Light=70, Mid=60, Heavy=50 → 比例約 38.9% / 33.3% / 27.8%

### 攻擊決策（`ChooseNextAttackTier()`，Actor_AI.gd:55）
```gdscript
var AttackChoiceResult: float = randf_range(0, 1.05)
var HeavyAttackChance = RealAttackChanceLight + RealAttackChanceMid

if AttackChoiceResult > HeavyAttackChance:
    AttackArrayPrefix = "Heavy"
elif AttackChoiceResult > RealAttackChanceLight:
    AttackArrayPrefix = "Mid"
else:
    AttackArrayPrefix = "Light"
```

回傳字串，例如 `"LightAttackNames"` → 後續從對應 ID 陣列選取攻擊動畫。

### 攻擊 ID 陣列
```gdscript
@export var LightAttackIDs: Array[int]   # Inspector 填入
@export var MidAttackIDs: Array[int]
@export var HeavyAttackIDs: Array[String]  # 注意：類型為 String（疑似 Bug）
```

---

## 五、AI 可客製化指標（Inspector）

設計目標是讓關卡設計師不需寫程式便可調整 AI 行為。目前已定義的可調參數：

| 參數 | 預設值 | 說明 |
|---|---|---|
| `NPC_Tier` | — | 等級（影響優先權與強度）|
| `VisionArea` | — | 感知 Area3D 節點 |
| `AttackChanceLight` | 70 | 輕攻擊權重 |
| `AttackChanceMid` | 60 | 中攻擊權重 |
| `AttackChanceHeavy` | 50 | 重攻擊權重 |
| `LightAttackIDs` | [] | 輕攻擊可用招式 ID |
| `MidAttackIDs` | [] | 中攻擊可用招式 ID |
| `HeavyAttackIDs` | [] | 重攻擊可用招式 ID |

README 提到的其他預計實作指標（尚未在程式碼中實現）：
- 被非當前目標攻擊時轉換目標的機率
- 攻擊後滾離或待機的機率
- 目標距離偏好

---

## 六、已知問題 / 待完成項目

1. `HeavyAttackIDs` 類型為 `Array[String]`（`Actor_AI.gd:27`），與 Light/Mid 的 `Array[int]` 不一致，可能是遺留 Bug。
2. `_custom_physics_process(delta)` 目前為空（`Actor_AI.gd:71`），AI 移動邏輯尚未實作。
3. `TargetNode` 的選擇/切換邏輯尚未實作。
