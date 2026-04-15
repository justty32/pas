# 勢力宏觀機制 (Faction)

## 1. 關係矩陣 (Goodwill)
*   **數據結構**: `FactionRelation`。
*   **動態變動**: 透過 `TryAffectGoodwillWith` 修改關係。
*   **狀態切換**: 關係值低於 -75 切換為敵對，高於 75 切換為盟友。

## 2. 實力與戰力
*   **領袖管理**: 領袖死亡後會自動生成新的 `Pawn`。
*   **技術限制**: 由 `FactionDef.techLevel` 決定襲擊時的裝備水平。
*   **兵種池**: `PawnGroupMaker` 定義了勢力的組成權重。

## 3. 虛擬人口
*   **綁架追蹤**: `KidnappedPawnsTracker` 存儲玩家被抓的小人。
*   **非人類勢力**: 機械族、蟲族是單例物件 (`OfMechanoids`, `OfInsects`)，沒有領土但有全局威脅。

---
*由 Gemini CLI 分析 RimWorld.Faction 生成。*
