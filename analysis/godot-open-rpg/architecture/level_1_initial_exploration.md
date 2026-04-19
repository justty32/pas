# Level 1 — 初始探索（Initial Exploration）

> 目標：掌握專案整體定位、技術棧、進入點與頂層目錄劃分。
> 分析對象：`projects/godot-open-rpg/`
> 分析日期：2026-04-18

---

## 1. 專案定位 (Project Goal)

根據根目錄 `README.md` (第 1-24 行) 與專案 `project.godot` 的敘述：

- **類型**：2D **回合制 JRPG** 的教學示範 (demo)。
- **發行者**：GDQuest（知名 Godot 教學團體）。
- **目標受眾**：已有程式基礎、想學「如何在 Godot 4 中良好地組織 RPG 程式碼」的開發者。
- **設計方針**：
  - 並非框架 (framework)，而是「可讀、可學習、可複用」的教材 (learning resource)。
  - 嚴格遵守 [GDQuest GDScript Style Guide](https://gdquest.gitbook.io/gdquests-guidelines/godot-gdscript-guidelines)。
  - 充分利用 GDScript 4 新特性（`class_name`、型別標註、`signal` 強型別、`@tool`）。
- **涵蓋主題**：
  - 回合制戰鬥
  - 物品欄 (Inventory)
  - 角色成長 (Character progression)
  - 過場動畫、對話、網格移動的地圖切換
  - 多層選單 UI

---

## 2. 技術棧 (Tech Stack)

| 類別 | 技術 / 版本 | 來源 |
| :--- | :--- | :--- |
| 遊戲引擎 | **Godot 4.5** | `project.godot:15` `config/features=PackedStringArray("4.5", "GL Compatibility")` |
| 渲染後端 | **GL Compatibility**（OpenGL ES 3.0／支援舊硬體） | `project.godot:209-210` |
| 程式語言 | **GDScript 4** | 所有 `.gd` 檔案 |
| 對話系統 | **Dialogic**（Godot addon） | `addons/dialogic/`；`project.godot:28` `Dialogic="*res://addons/dialogic/Core/DialogicGameHandler.gd"` |
| 美術資源 | **Kenney Tiny Town**（像素風） | `README.md:38` |
| 解析度 | 邏輯 1920×1080 / 視窗 960×540（`canvas_items` 拉伸、`expand` 長寬比） | `project.godot:117-122` |
| 輸入 | 鍵盤 + 手把 + 滑鼠（已設 `ui_*`, `select`, `interact`, `back`, `dialogic_default_action`） | `project.godot:139-195` |

---

## 3. 進入點 (Entry Point)

### 3.1 主場景

`project.godot:14` 指定：

```ini
run/main_scene="res://src/main.tscn"
```

主場景掛載 `src/field/field.gd` 作為根 `Node2D` 腳本（見 `src/field/field.gd:1-51`）。其 `_ready()` 職責：

1. `randomize()` — 初始化隨機種子。
2. 連結 `Player.gamepiece_changed` signal：每當玩家操控的 Gamepiece 改變，動態附加一個 `PlayerController`，並將相機鎖定到新 Gamepiece。
3. 連結 `CombatEvents.combat_initiated` / `combat_finished`：戰鬥開始時隱藏 field 場景、結束時再顯示。
4. 將當前 Gamepiece 設為 `player_default_gamepiece`（由編輯器指派）。
5. 執行 `opening_cutscene`（若有指派）。

### 3.2 Autoload（全域單例）清單

`project.godot:18-28` 宣告九個全域單例，是整個專案「鬆耦合通訊」的骨幹：

| Autoload 名稱 | 路徑 | 職責 |
| :--- | :--- | :--- |
| `Camera` | `src/field/field_camera.gd` | 玩家相機，跟隨當前 Gamepiece |
| `CombatEvents` | `src/combat/combat_events.gd` | 戰鬥事件匯流排（`combat_initiated` / `combat_finished` / `player_battler_selected`） |
| `FieldEvents` | `src/field/field_events.gd` | 場景事件匯流排（`cell_highlighted` / `combat_triggered` / `cutscene_began` / `input_paused` 等） |
| `Gameboard` | `src/field/gameboard/gameboard.gd` | 全域遊戲棋盤（格子座標、Pathfinder） |
| `GamepieceRegistry` | `src/field/gamepieces/gamepiece_registry.gd` | 註冊表：格子座標 ↔ Gamepiece 的映射 |
| `Music` | `src/common/music/music_player.tscn` | 背景音樂播放器 |
| `Player` | `src/common/player.gd` | 玩家狀態（當前 Gamepiece 持有者） |
| `Transition` | `src/common/screen_transitions/ScreenTransition.tscn` | 畫面轉場效果（遮罩） |
| `Dialogic` | `addons/dialogic/Core/DialogicGameHandler.gd` | 對話 runtime（第三方） |

> **設計洞察**：每個子系統都有獨立的 `*_events.gd` 作為事件匯流排，而非直接互相 reference，遵循 GDQuest 一貫提倡的「Signal Bus 模式」。

---

## 4. 頂層目錄結構 (Top-Level Layout)

```text
godot-open-rpg/
├── addons/dialogic/           # 第三方對話系統插件
├── assets/                    # 共用美術資源、GUI theme、圖示
├── combat/                    # 戰鬥相關的場景資源（arenas + battlers 的 .tscn/.tres）
│   ├── arenas/
│   └── battlers/
├── overworld/                 # 場景資源（角色 .tscn + 地圖 .tscn）
│   ├── characters/
│   └── maps/
├── src/                       # 【GDScript 核心邏輯】
│   ├── combat/                # 戰鬥系統
│   ├── common/                # 跨系統共用（Inventory、Player、方向、轉場、音樂）
│   ├── field/                 # 場景系統（Gameboard、Gamepiece、Cutscene、Camera、UI）
│   └── main.tscn              # 主場景（但目前 main_scene 實際指向 field.tscn，見下方備註）
├── media/                     # Banner 圖片
├── project.godot              # 引擎設定 / Autoload / 輸入 / 變數
├── default_bus_layout.tres    # 音訊 Bus 配置
├── icon.svg                   # 專案圖示
├── README.md / LICENSE / CHANGELOG.md / CREDITS.md
```

### 資料（tscn / tres）vs 邏輯（gd）分離

- **資料層** 放在 `combat/` 與 `overworld/`（編輯器拖拉即可設計新戰鬥或地圖）。
- **邏輯層** 放在 `src/`，共 324 個 `.gd` 檔（主要為腳本、少部分 `.tscn`）。

> 此分離為 GDQuest 的慣例：美術/設計師只動頂層 `combat`、`overworld`；程式設計師只動 `src`。

---

## 5. `src/` 子目錄的「三大支柱」

| 子目錄 | 核心意義 | 代表性檔案 |
| :--- | :--- | :--- |
| `src/field/` | **場景 / 探索狀態** — 玩家在地圖上走動時的邏輯 | `field.gd`, `gameboard/gameboard.gd`, `gamepieces/gamepiece.gd`, `cutscenes/cutscene.gd` |
| `src/combat/` | **戰鬥狀態** — 回合制戰鬥的一切 | `combat.gd`, `battlers/battler.gd`, `actions/battler_action.gd`, `combat_ai_random.gd` |
| `src/common/` | **跨狀態共用服務** | `player.gd`, `inventory.gd`, `directions.gd`, `collision_finder.gd` |

---

## 6. 關鍵設計模式一瞥

從 Level 1 快速掃描中可辨識出的四個關鍵模式（將於 Level 2-3 詳述）：

1. **Signal Bus（事件匯流排）**
   以 `FieldEvents` / `CombatEvents` autoload 解耦子系統，避免「找節點」的耦合。
2. **Scene Composition（場景組合）**
   `Battler` 透過 `battler_anim_scene` 與 `ai_scene`（`@export PackedScene`）在執行期動態實例化動畫與 AI 節點，而非繼承。見 `src/combat/battlers/battler.gd:40-92`。
3. **Resource 驅動**
   `BattlerStats` 與 `BattlerAction` 繼承 `Resource`，可在編輯器中當作 `.tres` 檔製作「資料模板」，執行期再 `duplicate()` 成獨立實例。見 `src/combat/battlers/battler_stats.gd:2` 與 `src/combat/battlers/battler.gd:155-174`。
4. **@tool 腳本 + 編輯器驗證**
   多個核心類別（`Battler`, `Gamepiece`, `GamepieceController`, `Cutscene`）標註 `@tool`，於編輯器階段即進行型別驗證（例如 `ai_scene` 必須為 `CombatAI`）。見 `src/combat/battlers/battler.gd:8-9, 74-92`。

---

## 7. Level 1 小結

Godot-Open-RPG 是一個**教育性質極強、架構極為乾淨**的示範專案：

- 進入點單一且清晰（`src/main.tscn` → `src/field/field.gd`）。
- 透過九個 Autoload 分離職責，沒有任何子系統「找」其他子系統的節點。
- `src/field` 與 `src/combat` 兩大狀態以 `FieldEvents.combat_triggered` 為唯一切換點。
- 美術/場景設計師與程式設計師分工明確（`combat`/`overworld` vs `src`）。

接下來 Level 2 將逐一展開 `field` / `combat` / `common` 三大模組的入口與職責，並追蹤一次完整的「從移動到觸發戰鬥到勝利」事件流。
