# Session Resume: Godot-GameTemplate Analysis

## 1. 目前狀態
- **分析專案**: Godot-GameTemplate (projects/Godot-GameTemplate)
- **完成等級**: Level 1-6 (全流程完成)
- **分析目錄**: `analysis/godot-gametemplate/`

## 2. 核心理解摘要
- **架構模式**: 資源導向依賴注入 (Resource-based DI)。利用 `ResourceNode` 作為組件間的中介，實現高度解耦。
- **移動系統**: `MoverTopDown2D` 透過 `axis_multiplier` 模擬 2.5D 透視，手動處理碰撞與重疊，表現極佳。
- **AI 系統**: 採用「決策填充輸入軸」的模式，AI 與玩家共享移動邏輯。實作了樹狀實體追蹤，解決了分裂敵人的計數問題。
- **數據持久化**: `SaveableResource` 支援多後端存儲 (File/Steam)，且具備內存暫存功能。
- **視覺特效**: 基於著色器的溶解式轉場與對象池化的殘影系統。

## 3. 剩餘待辦事項
- [ ] 撰寫針對「如何新增武器」的目標導向教學 (`tutorial/01_new_weapon.md`)。
- [ ] 分析其 GDExtension 擴展潛力（若未來需遷移至 C++）。
- [ ] 完成 `godot-cpp` 的 Level 1 分析（目前由其他 Agent 處理中）。

## 4. 上下文快照
- **主要路徑**: `addons/top_down/`
- **核心腳本**: `ResourceNode.gd`, `MoverTopDown2D.gd`, `SaveableResource.gd`
- **關鍵著色器**: `transition.gdshader`
