# 思考樹：Pawn 的決策心臟 (ThinkTree)

思考樹決定了 Pawn 「在什麼情況下，優先做什麼」。

## 1. 運作原理：優先級選擇
思考樹從根節點開始，由上而下遞歸掃描：
1.  **檢查節點條件**: 例如 `ThinkNode_ConditionalHungry`。
2.  **執行子節點**: 如果條件滿足，進入子節點。
3.  **返回結果**: 第一個成功生成 `Job` 的節點將奪取控制權，後續節點被跳過。

## 2. 關鍵節點類別
*   **JobGiver**: 葉子節點，真正產生任務的地方（如 `JobGiver_GetFood`）。
*   **ThinkNode_QueuedJob**: 檢查玩家手動排隊的任務。
*   **ThinkNode_Tagger**: 給產生的 Job 打上標籤（如 `SatisfyingNeeds`），方便其他系統識別。

## 3. Mod 開發切入點
*   **XML 注入**: 透過 Patch 向 `ThinkTreeDef` 插入新的 `ThinkNode`。
*   **自定義 JobGiver**: 繼承 `ThinkNode_JobGiver` 並重寫 `TryGiveJob` 方法，實現全新的自主行為（如：閒暇時去寫作、鍛鍊）。

---
*由 Gemini CLI 分析 Verse.AI.ThinkTree 生成。*
