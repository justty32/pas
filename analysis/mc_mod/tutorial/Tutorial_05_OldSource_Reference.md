# 教學 05：參考 OldSource 設計文化邏輯

這部分是針對具備 Java 基礎的你，如何「閱讀」舊版代碼來設計你的新文化。

## 1. 學習村民行為偏好
打開 `OldSource/todeploy/millenaire/cultures/` 下的任一文化資料夾。
- 尋找 `villagerconfig/default.txt`：這裡定義了村民的生命值、速度、以及他們對物品的權重（例如日本文化更看重武士刀）。
- **移植目標：** 在 Phase 5，我們將建立一個 Data-Driven 的系統來載入這些 TXT 內容。

## 2. 藍圖與方塊映射
打開 `OldSource/todeploy/millenaire/blocktypes.txt`。
- 你會看到類似 `255,0,0;cobblestone` 的行。
- 這意味著在 PNG 藍圖中，紅色的像素會被置換為鵝卵石。
- **你的任務：** 為你的新方塊選一個獨特的顏色，並記錄下來。

## 3. 任務與對話
參考 `OldSource/todeploy/millenaire/languages/en/` 下的對話文件。
- Millénaire 的對話是透過標籤（如 `$villagername`）實現動態替換的。
- 你可以開始構思你的文化專屬對話集。

## 總結
現在你已經掌握了：
1. 註冊物品與方塊。
2. 定義盔甲與工具材質。
3. 建立分類標籤。
4. 使用 Data Gen 生成資產。

你可以嘗試新增一個簡單的「維京 (Viking)」或「埃及 (Egyptian)」文化作為練習。祝你開發愉快！
