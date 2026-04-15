# 襲擊機制與劇本干涉 (Raids & Scenario)

## 1. 襲擊是如何定義的？
*   **觸發器**: `Storyteller` 觸發 `IncidentWorker_RaidEnemy`。
*   **規模計算**: 根據財富、難度、適應性得出 `points` (點數)。
*   **策略決定**: 襲擊策略 (`RaidStrategyDef`) 與到達方式 (`PawnsArrivalModeDef`)。
*   **選購系統**: `PawnGroupMaker` 根據技術等級 (`techLevel`) 用點數「購買」小人。
*   **群體行為**: 建立一個 `Lord` 控制器，給予 `LordJob_AssaultColony` 任務。

## 2. 劇本 (Scenario) 的影響
*   **強制/禁用**: `ScenPart_ForcedIncident` 和 `ScenPart_DisableIncident` 接管敘事者。
*   **數值因子**: `ScenPart_StatFactor` 影響財富與威脅縮放。
*   **開局與結束**: 修改開局物品、強制特性或定義失敗條件。

---
*由 Gemini CLI 分析 RimWorld.Incident 與 RimWorld.Scenario 生成。*
