# 對話機制深度解析 (Dialogue System)

Millénaire 的對話系統透過本地化模板與動態標籤實現高度的沉浸感。

## 1. 對話觸發
當玩家與村民互動，或村民執行特定目標時，會調用對話邏輯。
- **原始碼位置：** `OldSource/java/org/millenaire/common/entity/MillVillager.java` 中的 `speech_started` 變數與相關方法。

## 2. 標籤替換邏輯 (`$name` 系統)
根據 `OldSource/java/org/millenaire/common/utilities/LanguageUtilities.java`：
- **`fillInName(String s)`**: 
    - 將 `$name` 替換為玩家的名稱。
    - 將 `$villagername` 替換為村民自己的名稱。
- **其他標籤：** `$culture`, `$targetvillage`, `$money` 等，讓對話與遊戲狀態緊密結合。

## 3. 多語言支援
對話內容存放在 `OldSource/todeploy/millenaire/languages/[lang]/` 目錄下。
- 每個對話都有一個唯一的 Key。
- **移植建議：** 1.21.8 應利用 `MutableText` 與 `Text.translatable()` 的參數替換功能，例如：
  `Text.translatable("millenaire.speech.hello", player.getName())`。

## 4. 氣泡與聊天欄
- 村民說話時，頭頂會出現文字氣泡（客戶端渲染），同時在聊天欄顯示。
- **同步機制：** 伺服器決定要說什麼 -> 發送封包 -> 客戶端讀取語言檔並顯示。
