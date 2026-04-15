# Veloren 深度分析會話恢復清單 (Session Resume)

## 1. 專案理解摘要 (Current Understanding)
- **專案名稱**：Veloren (Rust 編寫的體素 RPG)。
- **核心架構**：基於 `specs` 的 ECS 系統，分為 `common` (邏輯), `server` (權威), `voxygen` (渲染前端), `world` (生成) 與 `rtsim` (宏觀模擬)。
- **核心技術**：WGPU 渲染、Kira 音訊、A* 尋路（支持 Poll 模式）、空氣動力學滑翔物理、基於幾何原語的程序化地城生成。

## 2. 已完成分析路徑 (Completed Analysis)
- **Level 1-2**: 基礎架構與核心模組職責劃分。
- **AI 系統**: 行為樹節點、Boss 戰鬥戰術、潛行與變裝感知。
- **世界生成**: 侵蝕算法、溫濕度氣候公式、文明擴張與城鎮選址。
- **戰鬥與 RPG**: Melee 射線校驗（9 射線）、技能樹數值修正、生命值定點數優化。
- **物理與載具**: `Dyna` 卷座標轉換、欄式內存佈局、滑翔翼升力與失速物理。
- **視覺與渲染**: Greedy Meshing 優化、頂點位元壓縮技術、水下波動與積水 Shader、LOD 遠景渲染。
- **音訊與交互**: 3D 空間監聽器、地理環境音濾波、音軌動態切換、程序化名稱生成（音節組合）。

## 3. 下次優先執行的分析任務 (Pending Tasks)
1. **地城橋樑幾何填充實作**：精確定位 `WorldSite::generate_bridge` 調用的體素原語 [world/src/site/gen.rs]。
2. **文明外交數值映射**：拆解 `common/src/comp/group.rs` 中的信任值計算邏輯。
3. **Boss 戰攝像機抖動觸發鏈**：定位狀態機與視覺震動訊號的具體連結點。
4. **技能音效合成邏輯**：分析 `voxygen` 如何透過多層音軌疊加 SFX。

## 4. 核心上下文參考 (Core Context)
- **SOP 位置**: `work/other/project_analysis_workflow.md`
- **主要日誌**: `work/session_log.md`
- **分析文件庫**: `work/analysis/` (目前已產出 15+ 份詳盡報告)
