# 村民實體組成深度分析 (NPC Composition)

在 Millénaire 中，村民 (Villager) 不是簡單的怪物，而是一個擁有複雜狀態的數據模型。以下分析基於 `OldSource/java/org/millenaire/common/entity/MillVillager.java`。

## 1. 核心身份屬性 (Identity)
每個村民都擁有唯一的標識與社會屬性：
- **`villager_id`**: 唯一識別碼，用於追蹤村民的一生。
- **`gender`**: 決定了職業池與行為模式。
- **`culture`**: 決定了外觀、語言以及可執行的目標。
- **`name`**: 基於文化庫隨機生成的姓名。
- **`profession` (職業)**: 這是最重要的屬性，決定了村民的每日行程與對村莊的貢獻。

## 2. 社會與經濟狀態 (Social & Economic)
- **`homeBuilding` (家)**: 村民居住的地方，晚上會回到這裡睡覺。
- **`workBuilding` (工作場所)**: 村民執行職業目標的地方。
- **`inventory` (背包)**: 每個村民都有自己的背包，用於存儲採集到的物資或交易用的物品。
- **`wealth` (財富)**: 以 Deniers 為單位的個人資產。
- **`family` (家族)**: 記錄配偶與子女，這影響了村民的居住空間與人口成長邏輯。

## 3. 持久化機制 (Persistence)
- **1.12.2 (OldSource)**: 透過 `writeEntityToNBT` 與 `readEntityFromNBT` 將上述所有狀態序列化。
- **1.21.8 (Reborn)**: 
    - 建議將靜態數據（姓名、性別）存儲在 **Data Components**。
    - 將動態數據（當前目標、背包）存儲在實體的 **NBT** 或自定義的 **Component** 系統中。
    - **VillagerRecord**: 這是村莊中心 (`Village.java`) 維護的輕量級索引，即使村民實體因區域卸載 (Unload) 而消失，村莊依然知道他的存在。

## 4. 成長與演進
- **成長階段**: 嬰兒 -> 兒童 -> 成年。每個階段有不同的渲染尺寸與目標優先級。
- **職業學習**: 部分村民在成長過程中會根據村莊需求選擇職業。
