# 村民生成模板與邏輯解析

村民的生成不是隨機的，而是由 **`VillagerType`** 與 **村莊需求** 共同決定的。

## 1. 村民模板 (`VillagerType.java`)
每個村民的「藍圖」定義在 `cultures/[culture]/villagerconfig/` 的 TXT 文件中。
- **標籤系統 (Tags)**：
    - `child`: 標記為兒童，會隨著時間成長。
    - `chief`: 村長，擁有特殊的互動介面。
    - `hostile`: 敵對實體（如強盜）。
    - `merchant`: 商人，具有跨村莊旅行的邏輯。
- **初始狀態**：定義了初始背包 (`startingInv`)、最大生命值與移動速度。

## 2. 自動補完機制 (Population Control)
村莊中心會監控人口。
- **生育邏輯**：當一對男女村民居住在同一棟房屋且村莊有足夠食物時，會觸發「生育」目標。
- **村民記錄 (`VillagerRecord`)**：
    - 即使實體未生成，系統也會保留一個 `VillagerRecord` 存儲在 `MillWorldData` 中。
    - 當玩家靠近時，系統會根據 Record 實例化 `MillVillager`。

## 3. 自動生成過程
1. **讀取配置**：從 TXT 載入 `VillagerType` 實例。
2. **分配身份**：給予隨機姓名（由 `CultureLanguage` 決定）。
3. **分配住宅**：尋找有空餘床位的建築。
4. **掛載 AI**：根據職業 (`VillagerType`) 為其分配可執行的 `Goal` 池。

## 4. 原始碼與移植位置
- **模板定義**：`OldSource/java/org/millenaire/common/culture/VillagerType.java`
- **持久化記錄**：`OldSource/java/org/millenaire/common/village/VillagerRecord.java`
- **數據映射**：`OldSource/java/org/millenaire/common/world/MillWorldData.java`
