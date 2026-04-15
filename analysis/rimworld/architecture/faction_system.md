# RimWorld 勢力行為與管理 (Faction System)

RimWorld 的勢力系統定義了玩家與世界各個群體之間的長期關係及其動態行為。

## 1. 勢力的本質 (Faction)
*   **Faction**: 全局物件，代表一個具體的組織（如：閃耀世界殖民地、部落、海盜）。
    *   `def`: 指向 `FactionDef`，定義了該勢力的技術等級、初始關係、生成權重與可用兵種 (`PawnGroupKindDef`)。
    *   `relations`: 存儲與其他勢力的關係值 (Goodwill)。
    *   `leader`: 該勢力的領袖（若領袖死亡，會生成新領袖）。
*   **FactionManager**: 全局單例，管理所有現存勢力。
    *   `OfPlayer`: 玩家自己的勢力。
    *   `OfMechanoids`, `OfInsects`: 特殊的非人類勢力。

## 2. 關係系統 (Relations & Goodwill)
*   **Goodwill**: 介於 -100 到 100 之間。
    *   <-75: 敵對 (Hostile)。
    *   >75: 盟友 (Ally)。
*   **動態變化**: 透過貿易、贈送禮物、完成任務或釋放囚犯來增加；透過攻擊、非法拘捕或自然衰減來減少。

## 3. 襲擊與突發事件 (Incidents)
勢力對玩家的主要影響是透過 `IncidentWorker` 觸發的。
*   **IncidentWorker_Raid**: 襲擊邏輯的基類。
    *   `TryResolveRaidFaction`: 決定哪個勢力會來襲擊（通常是敵對勢力）。
    *   `ResolveRaidPoints`: 根據財富與威脅規模決定敵人的數量。
    *   `ResolveRaidStrategy`: 決定戰術（如：原地圍攻、直接進攻、空投降落）。
*   **PawnGroupMaker**: 根據勢力的 `PawnKindDef` 組成具體的戰鬥單位。

## 4. 勢力基地的分布 (Settlement)
*   勢力在世界地圖 (World) 上以 `Settlement`（定居點）形式存在。
*   這是 `WorldObject` 的一種。玩家可以派遣商隊進行交易或發動進攻。

## 5. Mod 開發建議
*   **新增勢力**: 
    1.  XML 定義 `FactionDef`。
    2.  定義 `PawnGroupKindDef` 以確定該勢力會派出哪些兵種。
*   **修改襲擊邏輯**: 
    1.  攔截 `IncidentWorker_Raid` 類別。
    2.  自定義 `RaidStrategyDef` 以實現全新的戰鬥 AI（如：特種部隊潛入）。
*   **動態關係**: 透過 `faction.TryAffectGoodwillWith` 方法在程式碼中調整關係。

---
*這份文件是由 Gemini CLI 透過分析 RimWorld.Faction 產生的分析報告。*
