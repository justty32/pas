# godot-tactical-rpg 分析 session log

- 起始時間：2026-05-25 15:21（本機時間）
- 作業系統：Windows 11 Pro（PowerShell / bash）
- Agent：Claude Code (Opus 4.7, 1M context)
- 專案根路徑：`C:\code\mine\pas\projects\godot-tactical-rpg`
- 工作模式：Analysis（依 `analysis_workflow.md` 模板 A：遊戲原始碼分析）

---

- 讀取必讀規範（CLAUDE.md、analysis_workflow.md、Cogito Level 1/2 範例），確認圖表一律改用 Mermaid／表格，不用 ASCII art。
- 探索專案頂層：確認 Godot 4.3（mobile renderer）、MIT、autoload 僅 DebugMenu，主場景 `res://assets/scene/main.tscn`。
- 盤點 `assets/`、`data/`、`docs/` 目錄結構與全部 `.gd`／`.tscn`／`.tres` 檔案清單。
- 通讀核心腳本：main、tactics_level（回合驅動）、tactics_config／debug（靜態設定）。
- 通讀 participant 三層（module/service/resource）與 turn/combat 子 service、player/opponent service（含 AI 決策鏈）。
- 通讀 arena 格子系統：BFS flood-fill 走訪、pathfinding tilestack、tile 射線偵測鄰居、tile→StaticBody3D 執行期轉換。
- 通讀 pawn 三層：movement（沿路徑＋跳躍重力）、combat（傷害公式）、animation／sprite（billboard 朝向相機）、stats。
- 通讀 camera 五個 service（service/movement/zoom/panning/rotation）與 input capture（滑鼠射線投影、手把/鍵鼠分流）。
- 通讀 controls 三層與選擇／UI service（stage 切換與滑鼠拾取）。
- 擷取 main/level/arena/pawn 場景節點結構，並讀取 hero/mob 的 .tres 設定。
- 撰寫 architecture/level1_overview.md。
- 撰寫 architecture/level2_core_modules.md。
- 撰寫 architecture/level3_grid_pathfinding.md（格子地圖與移動範圍計算）。
- 撰寫 architecture/level3_turn_and_combat.md（回合狀態機與戰鬥判定）。
- 撰寫 architecture/level3_enemy_ai.md（敵人 AI 決策鏈）。
- 撰寫 architecture/level3_camera_input.md（攝影機系統與輸入）。
- 撰寫 tutorial/how_to_add_a_class.md（如何新增兵種／職業）。
- 撰寫 tutorial/how_to_create_a_map.md（如何自訂地圖）。
- 撰寫 others/observations.md（重構遺留問題與資料 schema 不一致觀察）。
