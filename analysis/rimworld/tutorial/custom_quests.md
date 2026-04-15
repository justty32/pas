# 製作自定義任務 (Custom Quests)

RimWorld 的任務系統是基於 `QuestScriptDef` (腳本化 XML) 運行的。

## 1. 任務的三大支柱
*   **Slate (變數板)**: 儲存任務執行期間的數據（如：`[pawn]`, `[map]`）。
*   **Signals (信號)**: 節點間的通信機制（如：`pawn.Destroyed`, `timer.Elapsed`）。
*   **Grammar (語法)**: 負責生成動態的任務名稱與描述。

## 2. 核心 QuestNodes 介紹
*   **`QuestNode_Sequence`**: 按順序執行子節點。
*   **`QuestNode_GetPawn`**: 從地圖或世界中挑選符合條件的小人。
*   **`QuestNode_Delay`**: 計時器，時間到後執行特定的 `node`。
*   **`QuestNode_Signal`**: 監聽特定信號（例如小人被綁架、受傷、或抵達某處）。
*   **`QuestNode_End`**: 終結任務並定義結果 (Success, Fail, Invalidated)。

## 3. 如何測試你的任務
1.  開啟 **開發者模式 (Dev Mode)**。
2.  打開 **Debug Actions Menu** (閃電圖示)。
3.  搜尋 `Generate Quest`。
4.  在列表中找到你的 `defName` 並點擊，任務會立即生成。

## 4. Mod 開發建議
*   **從原版學習**: 推薦查看遊戲目錄下 `Data/Core/Defs/QuestScriptDefs` 中的原版腳本。
*   **信號命名**: 預設信號如 `artisan.Destroyed` 是由變數名 (`artisan`) 加上狀態組成的。
*   **C# 擴充**: 如果 XML 節點不夠用，你可以寫一個繼承自 `QuestNode` 的 C# 類別，然後在 XML 中直接呼叫它。

---
*由 Gemini CLI 分析 RimWorld.QuestGen 生成。*
