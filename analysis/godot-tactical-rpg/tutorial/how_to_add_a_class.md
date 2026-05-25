# 教學 — 如何新增一種兵種／職業（class / expertise）

> 目標：在 `test_level` 裡加入一名全新職業的玩家棋子（例如「Mage」），擁有自己的數值與立繪。
> 路徑相對於 `projects/godot-tactical-rpg/`。

---

## 1. 前置知識

讀完以下三節即可動手：
- 數值如何進入棋子：`architecture/level2_core_modules.md` 第 4 節（Pawn）與第 1 節（Stats）。
- 一隻 pawn 的節點組成：`pawn.tscn` = `TacticsPawn`(CharacterBody3D) + `Character`(Sprite3D) + `Expertise`/`Stats`。

關鍵機制：每個 pawn 場景裡的 `Expertise` 節點掛一個 `StatsResource`（即 `.tres`），`Expertise._ready`（`data/modules/stats/expertise/expertise.gd:16-19`）呼叫 `Stats.import_stats` 把 `.tres` 數值灌進 pawn 的 `Stats` 節點。**新增職業＝新增一個 `.tres` 並指給某個 pawn 的 Expertise**。

---

## 2. 原始碼導航（會碰到的檔案）

| 檔案 | 作用 |
|---|---|
| `data/models/world/stats/stats_res.gd` | `StatsResource` 欄位定義（職業可調的所有數值） |
| `data/models/world/stats/hero/*.tres` | 現有職業範本（archer/chemist/cleric/knight） |
| `data/models/world/stats/mob/*.tres` | 敵方範本（skeleton 等） |
| `assets/textures/actor/character/` | 玩家立繪 png 放這 |
| `assets/maps/level/test_level.tscn` | 把 pawn 與其 Expertise/Stats 組起來的關卡 |
| `data/modules/tactics/level/pawn/pawn.tscn` | 單一 pawn 場景（被 instance 多份） |

`StatsResource` 目前實際生效的欄位（`stats_res.gd:7-35`）：
`override_name`、`expertise`、`strategy`(列舉)、`level`、`sprite`(png 路徑)、`movement`、`jump`(= movement/2，由 `set_jump()` 算)、`max_health`、`attack_range`、`attack_power`。

> 注意：舊範本 `.tres`（如 `hero/knight.tres`）還殘留 `mp / armor / crit_rate / def / stab / resi` 等已不存在於 `stats_res.gd` 的欄位，載入時會被忽略。新增 `.tres` 時請只填上列實際欄位（參考最新的 `mob/skeleton.tres`）。詳見 `others/observations.md`。

---

## 3. 實作步驟

### 步驟 1：準備立繪
把職業的立繪 png 放到 `assets/textures/actor/character/`（例：`chr_pawn_mage.png`）。立繪採 billboard，sprite frame 的安排沿用現有角色圖的格式（前/後視 frame，見 `pawn/service/sprite.gd:48-60` 的翻面邏輯）。

### 步驟 2：建立職業 StatsResource（.tres）
在 Godot 編輯器 `data/models/world/stats/hero/` 右鍵 → New Resource → 選 `StatsResource`，存成 `mage.tres`。或直接複製現有檔再改。最小可用內容（仿 `mob/skeleton.tres` 的乾淨格式）：

```ini
[gd_resource type="Resource" script_class="StatsResource" load_steps=2 format=3]
[ext_resource type="Script" path="res://data/models/world/stats/stats_res.gd" id="1"]
[resource]
script = ExtResource("1")
override_name = "Merlin"
expertise = "Mage"
strategy = 3            # 0Tank 1Flank 2Physical 3Distance 4Support（目前僅作標記）
level = 1
sprite = "res://assets/textures/actor/character/chr_pawn_mage.png"
movement = 4
jump = 2.0             # 載入時會被 set_jump() 重算成 floor(movement/2)
max_health = 28
attack_range = 3       # 法師遠程
attack_power = 14
```

### 步驟 3：把職業指給一個 pawn
開 `assets/maps/level/test_level.tscn`：
1. 在 `TacticsParticipant/TacticsPlayer` 下，複製一個現有的 `Pawn` 節點（它本身是 `pawn.tscn` 的 instance，內含 `Expertise`）。
2. 選中該 pawn 的 `Expertise` 子節點，在 Inspector 把 **Starting Stats** 換成你的 `mage.tres`（`expertise.gd:8` 的 `@export var starting_stats`）。
3. 調整該 pawn 的 `Transform` 位置，讓它落在某個 tile 正上方（執行時會自動 `adjust_to_center` 對齊到 tile 中心）。

> 進階（可選）：若要做「技能」而不只是改數值，`Expertise` 還有 `starting_skills: Array[String]`（`expertise.gd:11`）目前未被消費——可作為自訂技能系統的掛載點。

---

## 4. 驗證方式

1. 用 Godot 4.3 開啟專案，F5 執行 → 點「Load Map 0」。
2. 確認新棋子出現在地圖上、立繪正確、頭頂名牌顯示 `override_name`（無則顯示 expertise，見 `sprite.gd:31`）。
3. 滑鼠移到該棋子應顯示其血量 HUD；點選它 → 按 Move，藍色可達範圍格數應符合 `movement`（步驟 2 設 4 ⇒ 走 4 格）。
4. 按 Attack，紅色可攻擊範圍應符合 `attack_range`（設 3 ⇒ 3 格）。
5. 攻擊一名敵人，敵人血量應減少 `attack_power`（Output 會印 `Target initial/final health`，見 `stats.gd:51-53`）。

若範圍格數或傷害不符，多半是 `.tres` 欄位名打錯（被忽略而取預設值）——回頭核對 `stats_res.gd` 的欄位名。
