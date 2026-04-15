# Harmony Patch：Modding 的靈魂技術

Harmony 允許我們動態攔截並修改原版 C# 方法。

## 1. 基本架構
1.  **實例化**: `new Harmony("com.mymod.rimworld")`。
2.  **標註**: 使用 `[HarmonyPatch]` 標籤指定類別與方法名。
3.  **執行**: 在 `StaticConstructorOnStartup` 中呼叫 `harmony.PatchAll()`。

## 2. 核心 Hooks
*   **Prefix**: 
    *   攔截輸入參數。
    *   控制是否執行原版：`return false;` (跳過), `return true;` (繼續)。
*   **Postfix**: 
    *   獲取執行結果：使用 `ref __result` 參數。
    *   在原版結束後追加邏輯。
*   **存取私有欄位**: 
    *   使用下劃線語法，如 `___pawn` 可以獲取該類別內部的私有 `pawn` 變數。

## 3. 開發建議
*   **盡量使用 Postfix**: 因為多個 Mod 修改同一個 Prefix 可能會導致衝突（如果有人返回了 False）。
*   **效能注意**: 避開在 `Tick` 頻率極高的方法（如 `Pawn_PathFollower.PatherTick`）中使用複雜的 Patch 邏輯。

---
*由 Gemini CLI 分析 HarmonyLib 運作機制生成。*
