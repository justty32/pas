# ARCHITECTURE：專案架構與設計哲學

> 本文是給**規劃者（你自己）**看的架構總覽。
> 任何執行模型都不需要讀這份；他們只需要依 `TASKS.md` 行動，必要時讀 `00_master_guide.md` / `01_*.md` / `02_*.md` 的規格細節。
> 若架構有新想法要改動，**先改這裡**，再同步到規格文件與 `TASKS.md`。

---

## 1. 專案定位

仿照 **Tales of Maj'Eyal (ToME) / T-Engine 4** 的分工哲學，用 Godot 4.5 打造一個 **前後端分離的回合制 tilemap RPG**：

- **前端**（GDScript）：純粹的**顯示層**與**輸入層**。
- **後端**（GDExtension / C++）：擁有所有遊戲狀態與邏輯，前端完全不持有權威數據。
- **參考素材**：`projects/godot-open-rpg`（GDQuest 示範，Godot 4.5 + GDScript）。

本專案**刻意不複用** godot-open-rpg 的戰鬥、對話、AI、觸發器等邏輯層，只保留其場景節點框架（Gameboard / Gamepiece / Animation）作為前端骨架。

---

## 2. 設計哲學（三條原則）

### 2.1 MUD 風格的單向事件流

前端與後端的關係類比 **MUD client / server**：

- 後端推進世界，把結果以「**視覺提示事件**」送給前端。
- 事件只帶前端顯示所需的最小資料（`visual_key`、`cell`、`direction`），**不含完整狀態**。
- 前端不試圖還原後端狀態，只負責「演出」後端告訴它的事情。

### 2.2 三方法契約（Minimal Surface）

前後端之間**只有三個方法**作為契約邊界：

```
GameEngine.tick(delta)                    前端拉取本幀事件
GameEngine.submit_action(PlayerAction)    前端送玩家動作
GameEngine.query(QueryRequest)            前端做唯讀查詢（不影響時間）
```

沒有 signal、沒有 callback、沒有雙向 reference。後端不 import 前端任何東西。

### 2.3 前端拉取，而非後端推送

`tick()` 由**前端每幀呼叫**，後端是被動的。這保證：

- 畫面更新與邏輯推進同步。
- 後端不需要知道「渲染」存在。
- Mock 後端（GDScript 版）與真實後端（GDExtension 版）可無縫替換。

---

## 3. 前端架構總覽

### 3.1 Autoload 層（全域服務）

| Autoload | 角色 |
| :--- | :--- |
| `GameEngine` | 後端單例（GDExtension 或 GDScript mock） |
| `DisplayAPI` | 每幀呼叫 `tick()`，把事件拆成 signal 派發給元件 |
| `InputHandler` | 捕捉輸入、依輸入鎖狀態送 `PlayerAction` |
| `VisualRegistry` | `visual_key` → 場景/圖磚/動畫名的查找表 |
| `Gameboard` | 格子座標系統（從 godot-open-rpg 複製） |
| `GamepieceRegistry` | `entity_id` ↔ Gamepiece 節點映射 |
| `Transition` / `Music` | 轉場與音樂（從 godot-open-rpg 複製） |

### 3.2 場景層（純顯示，全部 subscribe `DisplayAPI`）

- `MapDisplay`：Terrain / Entity / Effect / Fog 四個子層。
- `HUD`：MessageLog / StatusPanel / HotkeyBar / MiniMap。
- `UIManager`：物品欄、角色面板、法術書等 Modal 對話框。

元件之間**不互相 reference**，全部透過 `DisplayAPI` 的 signal 串接。

### 3.3 資料流（單向）

```
後端邏輯迴圈 ──tick()──► DisplayAPI ──signal──► 各顯示元件
                                                    │
                                                    ▼
                                              Gamepiece 節點
                                              （Tween 動畫）
玩家輸入 ──► InputHandler ──submit_action()──► 後端
```

---

## 4. 契約文件（四份）

前後端**只需要共同遵守這四份文件**，任何一端的內部實作都可自由替換：

| 文件 | 內容 | 位置 |
| :--- | :--- | :--- |
| 三方法簽章 | `tick` / `submit_action` / `query` 的參數與回傳型別 | `00_master_guide.md` §3 |
| `GameEvent` 事件表 | 13 種事件的欄位定義 | `00_master_guide.md` §4 |
| `PlayerAction` 動作表 | 11 種動作的參數定義（含 `REQUEST_TURN`） | `00_master_guide.md` §5 |
| `visual_keys.md` | 共享的視覺識別名清單（專案根目錄） | 實作時建立 |

---

## 5. Milestone 總覽

開發分七個 Milestone，每個都以「mock 後端可跑通」為驗收標準：

| Milestone | 主題 | 產出 |
| :--- | :--- | :--- |
| M0 | 專案骨架 | 空 Godot 專案 + Autoload 註冊 + `visual_keys.md` |
| M1 | 靜態地圖 + 玩家移動 | 能移動、輸入鎖正確 |
| M2 | 訊息日誌 + 狀態列 | 文字 & 數值能顯示 |
| M3 | 視野霧（FOV） | 可見/已探索/未知三層 |
| M4 | NPC 與多實體 | 同時多個 Gamepiece 正確演出 |
| M5 | 特效與投射物 | `EFFECT_AT` / `PROJECTILE_LAUNCH` |
| M6 | 物品欄 + query 接口 | 純 UI 不暫停時間 |
| M7 | 雙層地圖切換 | WorldMap ↔ LocalMap |

M0-M6 全部用 **GDScript mock 版 `GameEngine`** 開發，M7 之後才接真實 GDExtension。

詳細驗收條件見 `00_master_guide.md` §10。

---

## 6. 執行模型的工作邊界

### 執行模型可以做的事

- 依 `TASKS.md` 的單一任務寫程式碼（元件、autoload、場景）。
- 按規格文件（`00` / `01` / `02`）照抄 API 形狀。
- 寫簡單的 mock `GameEngine` 回傳假事件讓 M1-M3 跑起來。
- 修 bug（當驗收未通過時）。

### 執行模型不該做的事

- **不要擅自改動契約**（三方法簽章、GameEvent 欄位、PlayerAction 欄位）。
- **不要設計 GDExtension 內部**（那是後端開發者的事，本專案前端不管）。
- **不要跨 Milestone 實作**（一次只做當前任務）。
- **不要引入新 autoload 或改動資料流方向**。

架構決策一律由規劃者（你）決定。執行模型遇到「規格沒寫」的情況，回報待規劃者補規格。

---

## 7. 非目標（Non-Goals）

本專案**刻意不做**的事：

- **不做多人連線**。雖然架構像 MUD，但後端只服務單一前端。
- **不做存檔 / 讀檔**（留給後端實作時再決定）。
- **不復刻 godot-open-rpg 的戰鬥系統**（完全丟棄，後端自己寫）。
- **不用 Dialogic**（對話由後端送 `LOG_MESSAGE` 或 `UI_PROMPT`）。
- **不做即時戰鬥**。純回合制，受 `PLAYER_TURN` 事件控制。
- **不在前端放任何遊戲規則**（傷害計算、命中率、AI 決策全在後端）。

---

## 8. 何時更新本文件

- 發現新的架構缺口 → 先改本文件的「原則」或「邊界」。
- 新增 Milestone → 改 §5 表格與 `00_master_guide.md`。
- 新增契約項目（新 GameEvent / 新 PlayerAction）→ 改 §4 的引用點，然後更新 `00_master_guide.md`。
- 發現某個實作細節反覆出錯 → 不改本文件，改 `TASKS.md` 的驗收標準或 `PROMPT_TEMPLATES.md`。

**原則**：本文件是「哲學與邊界」，不是「實作手冊」。寫進來的東西，應該在半年後還成立。
