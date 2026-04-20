# gamecore 專案說明

`gamecore` 是一個多層次的遊戲引擎與開發計畫，旨在結合 **Godot** 的前端表現力與 **C++** 的後端效能，打造一個「宏觀世界中的微觀個體」的模擬沙盒。

> 玩家不是上帝，也不是不死的英雄。玩家是一個「人」，在大時代中嘗試活下去、改變什麼、或只是見證什麼。

---

## 核心設計規劃 (Planning)

詳細的設計細節已拆分至 `plans/` 資料夾中：

1.  **[核心哲學與願景](plans/001-vision-and-philosophy.md)**：包含核心哲學、設計原則、靈感來源與開放問題。
2.  **[世界架構](plans/002-world-structure.md)**：三層世界架構定義、跨層聯動機制、以及世界生成管線。
3.  **[動態系統設計](plans/003-mechanics-systems.md)**：情報系統、經濟與生態模擬、政治外交、時間與迷霧機制。
4.  **[戰鬥與單位](plans/004-combat-and-units.md)**：通用戰鬥模型、跨層解析度對應、戰鬥維度與結算。
5.  **[角色與行為模擬](plans/005-actors-and-simulation.md)**：玩家角色系統、分層 AI、NPC 生活模擬 (LOD) 與敘事範例。
6.  **[技術實作路徑](plans/006-technical-implementation.md)**：架構分工、通訊介面、關鍵模組、開發路線圖與測試策略。
7.  **[體驗與呈現](plans/007-experience-and-presentation.md)**：無障礙設計、美術音效方向、UX 流程與術語表。

---

## 快速開始 (Quick Start)

目前專案處於**架構規劃與原型開發階段**。

### 目錄結構

-   `core/`：C++ GDExtension 後端邏輯。
-   `godot/`：Godot 前端場景與 UI。
-   `plans/`：頭腦風暴與初步方案定稿。
-   `specs/`：正式實作規範（資料結構、API 協議等）。

### 授權

預計採用 MIT 授權。
