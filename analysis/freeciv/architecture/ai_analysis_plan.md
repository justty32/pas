# Freeciv AI 子模塊深度剖析計畫

基於總綱分析，我擬定以下計畫，將 Freeciv AI 系統拆解為五大核心專題進行源碼級剖析。每個專題都將產出獨立的 `details/` 文件。

---

## 專題 1：核心決策引擎與資源調度 (Core Engine & Macro-Economy)
*   **目標**: 分析 AI 如何在全局層面管理帝國。
*   **重點分析文件**: `ai/default/daihand.c`, `ai/default/daitech.c`
*   **關鍵問題**: 
    *   AI 如何決定金錢與科研的比例？
    *   技術研究路徑是如何量化評估的？

## 專題 2：城市規劃與經濟顧問 (City Management & Construction)
*   **目標**: 解構 AI 的基礎設施與產能分配。
*   **重點分析文件**: `ai/default/daicity.c`, `server/advisors/advchoice.c`
*   **關鍵問題**: 
    *   AI 如何評估「建造市場」與「建造戰士」的優劣？
    *   奇觀競爭的權重計算邏輯為何？

## 專題 3：軍事指揮與威脅評估 (Military Command & Strategy)
*   **目標**: 深入探討 AI 的戰爭機器實作。
*   **重點分析文件**: `ai/default/daimilitary.c`, `ai/default/daiguard.c`
*   **關鍵問題**: 
    *   AI 如何選擇進攻目標？
    *   防禦單位的配置策略是什麼？

## 專題 4：單位戰術與自動化 (Unit Tactics & Automation)
*   **目標**: 剖析具體單位的微操邏輯。
*   **重點分析文件**: `ai/default/daiunit.c`, `server/advisors/autoworkers.c`
*   **關鍵問題**: 
    *   工人的開發邏輯（灌溉、修路）是如何排序的？
    *   單位在移動時如何進行風險規避？

## 專題 5：外交政治與海運後勤 (Diplomacy & Logistics)
*   **目標**: 探究跨玩家互動與複雜交通。
*   **重點分析文件**: `ai/default/daidiplomacy.c`, `ai/default/daiferry.c`
*   **關鍵問題**: 
    *   AI 如何判斷一個盟友是否值得信任？
    *   渡輪 (Ferry) 系統如何解決「單位過海」的同步難題？

---

## 執行流程
1.  **逐個剖析**: 每個專題都會進行原始碼掃描與邏輯追蹤。
2.  **細節產出**: 產出包含 Mermaid 決策圖與權重公式的文件。
3.  **互聯校對**: 確保不同模組間的互動（如軍事與外交）被正確解釋。
