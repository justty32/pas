# 魔紋 Mod (Magic Tattoo) 技術設計方案

這個 Mod 旨在透過採集、加工與手術，為殖民者提供永久性的體質強化。以下是基於 RimWorld 架構的實作藍圖。

## 1. 核心流程拆解

### A. 材料與產物 (Items & Materials)
*   **原始材料**: 利用現有的動植物產出（如：草藥、特定動物的血、魔法植物），或新增特定的 `ThingDef`。
*   **魔紋汁液 (Magic Inks)**: 
    *   類別：`Item`
    *   定義：不同的汁液對應不同的強化方向（例如：龍血汁液強化生命值、疾風草汁液強化速度）。

### B. 生產設施與配方 (Workbenches & Recipes)
*   **鍊藥鍋/工作台**: 
    *   可以新增一個自定義工作台，或是將配方加入現有的「藥物實驗室 (Drug Lab)」。
    *   `RecipeDef`: 定義「熬煮」過程，消耗材料產出汁液。

### C. 強化機制 (Hediffs - Health Differences)
這是 Mod 的核心。魔紋在遊戲底層會被視為一種 **Hediff**（健康狀態）。
*   **HediffDef**: 每個魔紋都是一個特殊的 Hediff。
    *   `StatOffsets`: 透過此標籤直接修改 Pawn 的屬性（血量乘數、閃避率、移動速度）。
    *   `isBad`: 設為 `false`（這是一種增益）。
    *   `partEfficiencyOffset`: 若紋在特定部位（如手臂），可以增加部位效率。

### D. 賦予方式 (Surgery)
*   **手術項目**: 透過 `RecipeDef` 定義一個手術。
    *   `workerClass`: `Recipe_InstallImplant` 或自定義的 `Recipe_Surgery`。
    *   `ingredients`: 需要特定的「魔紋汁液」。
    *   `appliedOnFixedBodyParts`: 指定可以紋身的部位（如軀幹、手臂、腿）。

## 2. 預計實作清單

| 功能模組 | RimWorld 類別 | 關鍵屬性 |
| :--- | :--- | :--- |
| **魔紋汁液** | `ThingDef` | `category: Item`, `stackLimit: 75` |
| **熬煮配方** | `RecipeDef` | `jobString: 正在熬煮魔紋汁液`, `workAmount` |
| **魔紋效果** | `HediffDef` | `stages -> statOffsets` (MoveSpeed, MeleeDodgeChance, MaxHitPoints) |
| **紋身手術** | `RecipeDef` | `workerClass: Recipe_Surgery`, `addsHediff` |

## 3. 技術難點與擴充
*   **血量強化**: RimWorld 的 `StatDef` 中，`MaxHitPoints` 通常是針對物品的。強化 Pawn 的生存能力通常透過修改 `IncomingDamageFactor`（減傷）或 `Pawn_HealthTracker` 的相關屬性。
*   **視覺效果**: 是否要在 Pawn 的外觀上顯示紋身？這需要動到 `PawnGraphicSet` 或使用 `HediffComp_Draw`。

## 4. 存檔安全性 (Data Persistence & Scribe)

由於魔紋是動態生成的，必須確保所有自定義數據在讀檔後能正確恢復。

### A. IExposable 接口實作
*   **CompMagicInk**: 必須紀錄 `List<StatModifier>`。
    ```csharp
    public override void ExposeData() {
        base.ExposeData();
        Scribe_Collections.Look(ref this.customEffects, "customEffects", LookMode.Deep);
        Scribe_Values.Look(ref this.quality, "quality", 1f);
    }
    ```
*   **Hediff_MagicTattoo**: 必須在存檔時保留從汁液繼承來的屬性數據。

### B. 異常處理
*   若讀檔時發現數據丟失（例如 Mod 版本更新導致類別名變更），應有備份邏輯將魔紋設為預設值，避免紅字報錯導致存檔損壞。

## 5. DLC 兼容性 (DLC Compatibility)

### A. Ideology (文化)
*   **文化認同**: 新增一個「魔紋崇尚」的迷思 (Meme) 或戒律 (Precept)。
*   **心理加成**: 擁有魔紋的 Pawn 在「崇尚魔紋」的文化中會獲得滿意度加成，反之則會感到羞恥。

### B. Biotech (生物技術)
*   **基因衝突**: 某些強化基因（如強壯體格）可能與魔紋效果「加法疊加」或「乘法疊加」。需在 `StatPart` 中處理計算優先級。
*   **代謝負擔**: 魔紋可以增加 Pawn 的食物消耗量（Metabolism），作為獲得強大力量的代價。

### C. Royalty (皇權)
*   **地位象徵**: 高級魔紋可以增加 Pawn 的「尊嚴值 (Dignity)」，讓他們更容易獲得帝國的認可。

---
*文件路徑: analysis/rimworld/others/magic_tattoo_mod_design.md*
