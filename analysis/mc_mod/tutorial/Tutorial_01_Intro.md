# 教學 01：在 Millénaire Reborn 中新增文化概論

歡迎來到 Millénaire Reborn 的擴充教學！既然你已經具備 Java 基礎，我們將重點放在 **Minecraft (MC) 模組開發** 與 **Fabric 框架** 的實作細節。

## 什麼是「一個文化」？
在 Millénaire 中，一個文化不僅僅是皮膚，它包含：
1. **物品 (Items)：** 工具、武器、盔甲、特殊物資（如諾曼的蘋果酒）。
2. **方塊 (Blocks)：** 建築所需的特殊材料（如泥磚、裝飾性瓦片）。
3. **創造模式標籤 (Creative Tabs)：** 讓玩家能方便找到該文化的物品。
4. **建築 (Buildings)：** PNG 藍圖定義的結構（Phase 4+）。
5. **村民 (Villagers)：** 具有特定行為與目標的 NPC (Phase 5+)。

## 開發流程 (當前 Phase 3 可實作部分)
目前的開發進度集中在「內容註冊」，這是新增文化的基礎。你的目標是：
1. **註冊物品：** 在 `MillItems.java` 中新增你的文化區塊。
2. **定義材質：** 在 `MillCustomMaterials.java` 中定義盔甲與工具數值。
3. **註冊方塊：** 在 `MillBlocks.java` 中註冊建築方塊。
4. **建立標籤頁：** 在 `MillCreativeTabs.java` 中建立專屬標籤。
5. **自動生成資產：** 使用 `MillenaireRebornDataGenerator.java` 生成 JSON 模型與翻譯。

## 核心概念：Registry (註冊表)
MC 是一個由「註冊表」驅動的遊戲。所有的東西（物品、方塊、實體）都必須在遊戲啟動時，透過一個唯一的 **Identifier** (ID) 登記到對應的註冊表。
- **ID 格式：** `命名空間:路徑` (例如 `millenaire-reborn:my_custom_sword`)。

接下來，請閱讀 **教學 02**，我們將動手註冊你的第一個物品。
