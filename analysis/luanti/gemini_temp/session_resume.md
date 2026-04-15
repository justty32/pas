# 會話恢復摘要 (Session Resume) - 2026-04-10

## 1. 專案理解與核心架構
- **專案名稱**：Luanti (前身為 Minetest)
- **技術棧**：C++17, Lua, CMake, Irrlicht MT, SDL2, SQLite3。
- **架構特點**：強伺服器驗證的 C/S 架構，具備高度靈活的 Lua Modding API。世界數據以 16x16x16 的 MapBlock 為單位進行序列化與網路同步。

## 2. 已完成的分析路徑 (Architecture & Detail)
- **架構層級 (Level 1 - 12)**：
    - Level 1-2：基礎依賴、啟動流程與 C/S 職責。
    - Level 3：Mapgen 通用流程與網路協定封包結構。
    - Level 4-5：實體系統 (SAO/CAO)、物品背包與資料庫持久化。
    - Level 6：渲染管線與網格化 (Meshgen) 技術。
    - Level 7：地形生成演算法 (2D/3D 噪聲疊加)。
    - Level 8：UI 系統 (Formspecs) 解析與回傳。
    - Level 9：戰鬥系統 (粒子、投射物與陷阱)。
    - Level 10：Shader 系統與 Uniform 傳遞。
    - Level 11-12：3D 模型載入、骨架覆寫與動作同步機制。
- **深度細節 (Detail 1 - 4)**：
    - 01: `register_node` 從 Lua 到 C++ 記憶體的轉換。
    - 02: `TOSERVER_INTERACT` 挖掘流程與反作弊檢查。
    - 03: `MapgenV7::makeChunk` 的地形生成流水線。
    - 04: `minetest.find_path` 的 A* 演算法與物理約束。

## 3. 已產出的開發教學 (Tutorial 1 - 13)
1. 基礎方塊註冊。
2. 物品與合成配方。
3. 工具性能設定。
4. 基礎 Lua 實體 AI。
5. ABM 環境更新。
6. 進階生物 AI 狀態機。
7. C++ 引擎層 AI 實作架構。
8. 自定義 Mapgen 創建。
9. Formspec UI 設計。
10. 火球術與地雷實作。
11. 自定義 GLSL Shader。
12. 3D 模型動畫控制。
13. 施法動作與動畫同步。

## 4. 剩餘待辦事項與後續方向
- **物理系統**：碰撞檢測 (Collision) 與流體動力學模擬。
- **音訊系統**：3D 音效定位與環境音效觸發。
- **網路優化**：延遲補償 (Lag Compensation) 與封包壓縮策略。
- **性能監控**：伺服器端實體瓶頸分析。

## 5. 核心上下文摘要
目前的開發環境已設定為**強制繁體中文**，且所有分析皆自動存檔於 `work/` 各子目錄。`GEMINI.md` 已包含所有核心開發規範。
