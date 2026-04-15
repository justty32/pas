# 任務定義與腳本化邏輯深度分析

Millénaire 的任務系統是一個高度「資料驅動」的框架，允許透過腳本定義複雜的劇情線。

## 1. 任務加載機制 (`Quest.java`)
- **Key-Value 腳本解析**：任務透過 `Quest.loadQuest(File file)` 從 `.txt` 文件加載。
- **全球標籤 (Global Tags)**：
    - `requiredglobaltag` / `forbiddenglobaltag`：控制任務是否在特定世界狀態下開啟（例如：某個村莊是否已被摧毀）。
- **玩家標籤 (Player Tags)**：
    - `requiredplayertag` / `forbiddenplayertag`：追蹤玩家的個人進度（例如：是否完成了前置任務）。

## 2. 觸發門檻
- **`minreputation` (最小聲望)**：定義了玩家必須在該文化中達到多少聲望才能開啟任務。
- **`chanceperhour` (觸發機率)**：定義了任務隨機出現的機率，模擬了村莊生活的偶然性。
- **`maxsimultaneous`**：限制同時進行的任務數量，防止玩家任務欄過載。

## 3. 創世任務 (Creation Quests, WQ)
- **核心 Key**：`sadhu` (印度), `alchemist` (諾曼), `fallenking` (瑪雅)。
- **結構**：這些是長篇任務，通常包含數十個步驟，引導玩家深入了解文化的背景故事。

## 4. 原始碼位置
- **核心架構**：`OldSource/java/org/millenaire/common/quest/Quest.java`
- **任務實例**：`OldSource/java/org/millenaire/common/quest/QuestInstance.java` (處理正在進行中的任務狀態)
