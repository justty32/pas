# RimWorld 實體與組件系統 (Thing & Comp)

RimWorld 的世界是由各種實體組成的，這些實體統一繼承自 `Thing`。

## 1. 實體層級結構
*   **Entity**: 最基礎的類別。
*   **Thing**: 遊戲中所有可交互物體的基類（掉落物、建築、家具、生物）。
    *   `def`: 指向 `ThingDef`，包含靜態屬性（如最大血量、貼圖、價格）。
    *   `Position`: 在地圖上的座標。
    *   `Faction`: 所屬派系。
*   **ThingWithComps**: 繼承自 `Thing`，支援附加 `ThingComp`（組件）。絕大多數複雜物體都繼承自它。
*   **Pawn**: 繼承自 `ThingWithComps`。遊戲中最複雜的類別，代表所有生物（人、動物、機械族）。

## 2. 組件系統 (Comp System)
組件是擴展實體功能的首選方式，因為它不需要修改繼承鏈。

### A. ThingComp
`ThingComp` 是附加在 `ThingWithComps` 上的邏輯模組。
*   **如何運作**: 
    1.  撰寫繼承自 `ThingComp` 的 C# 類別。
    2.  撰寫繼承自 `CompProperties` 的數據類別。
    3.  在 XML 中的 `comps` 列表裡添加該組件。
*   **常用 Hook**:
    *   `CompTick()`: 每 Tick 執行。
    *   `PostDraw()`: 渲染時執行。
    *   `PostExposeData()`: 存檔時執行。
    *   `CompGetGizmosExtra()`: 顯示選中按鈕（如「啟動」、「開火」）。

### B. Pawn 的 Tracker 系統
由於 `Pawn` 太過複雜，它將功能拆分到了多個 `Tracker` 類別中：
*   `Pawn_HealthTracker`: 生命值、傷口、疾病。
*   `Pawn_SkillTracker`: 技能等級。
*   `Pawn_NeedsTracker`: 飢餓、娛樂、睡眠。
*   `Pawn_MindState`: 臨時狀態（如「正在逃跑」）。
*   `Pawn_JobTracker`: 目前執行的任務。

## 3. Mod 開發建議
*   **優先使用 Comp**: 如果你想給某種建築物（如牆壁、桌子）添加功能，寫一個 `ThingComp`。
*   **修改現有實體**: 透過 `PatchOperationAdd` 向現有的 `ThingDef` 注入你的 `ThingComp`。
*   **訪問數據**: 使用 `pawn.TryGetComp<T>()` 來安全地獲取組件。

---
*這份文件是由 Gemini CLI 透過分析 Verse.Thing 與 Verse.Pawn 產生的分析報告。*
