# 006 - Technical Implementation
> 狀態: 基礎定稿 | [回目錄](README.md)
> 導航: [001 視覺哲學](001-vision-and-philosophy.md) | [005 演員模擬](005-actors-and-simulation.md)

## 9. 技術架構
*   **Godot (前端)**：UI、渲染、動畫、輸入。
*   **C++ GDExtension (後端)**：狀態管理、計算密集型邏輯（影響力、AI、路徑）。

## 9.2 通訊協議
*   **狀態讀取**：前端讀取後端快照。
*   **命令模式**：前端修改意向以 Command 形式送入後端佇列。

## 11. 專案結構
```
gamecore/
├── core/       # C++ 後端 (world, influence, ai, events, economy, save)
├── godot/      # Godot 前端 (scenes, ui, scripts, bridge)
├── assets/     # 美術、資料表
└── tests/      # 單元與整合測試
```

---

## 12. 開發路線圖
- **Phase 1**: 世界層原型（GDExtension 骨架、格子地圖、影響力場）。
- **Phase 2**: 地區層與孤身模式。
- **Phase 3**: 區域層 JRPG 原型。

---

## 開放問題 (Open Questions)
*   **AI 計算成本**：數千個具名 NPC 的每回合計算成本如何控制在 2 秒內？
*   **存檔膨脹**：極致的物件持久化在長時間遊玩下，如何有效進行增量儲存與壓縮？
*   **確定性隨機**：如何確保所有計算在不同平台上的確定性，以便於重播與測試？
