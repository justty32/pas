# 專案構想：GDExtension 後端 RPG

> 記錄日期：2026-04-18
> 參考專案：godot-open-rpg（GDQuest）

---

## 構想概述

製作一款 RPG 遊戲，採用「**GDScript 純前端、GDExtension 純後端**」的嚴格分工：

- **GDScript**：只負責渲染、UI 顯示、玩家輸入接收、動畫播放。
- **GDExtension（C++）**：負責所有遊戲邏輯，包含對話文本、事件判斷、物品互動結果、戰鬥計算、AI 決策、地圖狀態。

## 互動模式

1. **操作傳遞**：玩家輸入 → GDScript 封裝為 `PlayerAction` → 呼叫 `GameEngine.submit_action()` → 取得 `ActionResult` → GDScript 依結果更新畫面。
2. **幀狀態同步**：GDScript 的 `_process()` 呼叫 `GameEngine.tick(delta)` 推進邏輯，然後 `poll_state_updates()` 取得「本幀有哪些物件狀態變化」，只更新變化的部分。

## 核心動機

- 遊戲邏輯可用 C++ 撰寫，具備強型別、高效能與可移植性。
- GDScript 保持薄且乾淨，純做 View 層，未來換引擎或移植相對容易。
- 可獨立測試 GDExtension 邏輯（不需要啟動 Godot 編輯器）。

## 參考 godot-open-rpg 的對應關係

| godot-open-rpg 模組 | 本專案對應方式 |
| :--- | :--- |
| Signal Bus（FieldEvents / CombatEvents） | 保留在 GDScript，但訊號改由 GDExtension emit |
| Gameboard + Pathfinder（AStar2D） | 移入 GDExtension，GDScript 只接收 move_path |
| Battler / BattlerStats / BattlerAction | 移入 GDExtension，GDScript 只接收 snapshot |
| CombatAI | 完全在 GDExtension |
| Cutscene / Trigger | GDExtension 決定觸發，GDScript 播放演出 |
| Dialogic 對話插件 | 不使用；改從 GDExtension 取得 DialogueLine |

## 技術關鍵點（詳見 answers/ 目錄）

- API 邊界：暴露強型別 `RefCounted` 物件，避免 Dictionary 造成的 GC 壓力。
- Delta Update：GDExtension 維護 pending update 列表，每幀 poll 後清空。
- 執行緒：邏輯耗時時考慮 WorkerThreadPool；GDExtension 嚴禁在非主執行緒操作 Godot 節點。
- 建構管線：需為每個目標平台編譯獨立的 `.dll/.so/.dylib`。

## 目前狀態

- [ ] 設計最小可行 API 介面（`GameEngine` autoload 的方法清單）
- [ ] 以純 GDScript mock 實作 `GameEngine`，驗證 GDScript 端架構
- [ ] 建立 GDExtension 骨架（godot-cpp）
- [ ] 實作第一個功能：NPC 對話文本從 GDExtension 取得
- [ ] 實作 `poll_state_updates()` 的 delta 同步流程
