# RimWorld 程式碼架構概覽 (Modder 視角)

RimWorld 的架構高度模組化且數據驅動。對於 Mod 開發者來說，理解 **Verse** 與 **RimWorld** 命名空間的差異至關重要。

## 1. 核心命名空間
*   **Verse**: 這是遊戲的基礎引擎層。處理底層邏輯，如 XML 加載 (Defs)、地圖渲染、物理實體 (Thing) 的基類、隨機數生成、數學工具以及最核心的遊戲循環 (TickManager)。
*   **RimWorld**: 這是建立在 Verse 之上的遊戲邏輯層。包含具體的遊戲機制，如：社交 (Social)、派系 (Factions)、工作系統 (Jobs)、隨機事件 (Incidents)、情緒與需求 (Thoughts/Needs) 以及所有 DLC 的特有機制 (Royalty, Ideology, Biotech, Anomaly)。

## 2. 核心設計模式
### A. 數據驅動 (Def System)
RimWorld 幾乎所有的屬性都定義在 XML 中，稱為 `Def`。
*   `Def`: 所有數據定義的基類（如 `ThingDef`, `JobDef`, `PawnKindDef`）。
*   `DefDatabase<T>`: 靜態類別，負責在啟動時將 XML 反序列化為 C# 物件，並提供全局訪問。
*   **Mod 切入點**: 絕大多數 Mod 是透過 XML 繼承或修改現有的 Defs 來實現的。

### B. 組件模式 (Comp System)
為了避免類別爆炸，RimWorld 大量使用組件模式。
*   **ThingComp**: 附加在 `Thing` 上的邏輯模組（如發電、腐爛、照明）。
*   **HediffComp**: 附加在健康狀態 (Hediff) 上的模組。
*   **Mod 切入點**: 如果你想給現有物體增加新功能，通常是寫一個 `ThingComp` 並透過 XML 注入。

### C. 任務系統 (Job & Toil)
Pawn 的行為是由 Job 驅動的。
*   `Job`: Pawn 目前正在做的事情（由 `JobDef` 定義）。
*   `Toil`: Job 的具體執行步驟（原子化動作，如「走到目標」、「等待 100 Ticks」）。
*   `JobDriver`: 負責將 Job 拆解為一系列 Toils 的類別。
*   **Mod 切入點**: 自定義工作通常需要編寫新的 `JobDriver`。

### D. 存檔與加載 (Scribe)
RimWorld 使用自定義的 `Scribe` 系統進行序列化。
*   `IExposable`: 物件若需要存檔，必須實現此接口的 `ExposeData` 方法。
*   `Scribe_Values`, `Scribe_Deep`, `Scribe_References`: 負責不同類型的數據讀寫。

## 3. Mod 加載流程
1. 啟動遊戲。
2. `LoadedModManager` 遍歷 `Mods/` 資料夾。
3. 加載各 Mod 的 `About/About.xml`。
4. 加載 `Assemblies/` 中的 DLL。
5. 加載 `Defs/` 中的 XML 並進行合並。
6. 執行標註有 `[StaticConstructorOnStartup]` 的 C# 靜態構造函數。

---
*這份文件是由 Gemini CLI 透過分析源碼自動生成的架構總結。*
