# 教學 02：物品註冊與材質定義

在本節中，我們將學習如何新增你的文化專屬物品。

## 1. 在 `MillItems` 中聲明物品
打開 `src/main/java/me/devupdates/millenaireReborn/common/registry/MillItems.java`。

在檔案末尾（或對應文化的區塊）新增你的物品變數：
```java
// 我的自定義文化 (MyCulture)
public static Item MY_CULTURE_SWORD;
public static Item MY_CULTURE_BREAD;
```

## 2. 定義自定義材質
如果你的文化有盔甲或工具，需要在 `MillCustomMaterials.java` 中定義它們的屬性。
- **路徑：** `src/main/java/me/devupdates/millenaireReborn/common/registry/MillCustomMaterials.java`

```java
// 範例：定義我的文化工具材質
public static final ToolMaterial MY_TOOL_MATERIAL = new ToolMaterial(
    BlockTags.INCORRECT_FOR_DIAMOND_TOOL, // 挖掘等級
    1000, // 耐久度
    8.0F, // 挖掘速度
    3.0F, // 攻擊力
    15,   // 附魔能力
    ItemTags.DIAMOND_TOOL_MATERIALS // 修復材料
);
```

## 3. 實作註冊邏輯
回到 `MillItems.java` 的 `register()` 方法（或 `initialize()`）。

使用專案提供的輔助方法進行註冊：
```java
MY_CULTURE_SWORD = MillRegistry.registerItem("my_culture_sword", 
    new SwordItem(MillCustomMaterials.MY_TOOL_MATERIAL, new Item.Settings()));

// 如果是食物，可以使用 MillFoodItemBuilder
MY_CULTURE_BREAD = MillFoodItemBuilder.CreateItem(new Item.Settings(), MillFoodType.MY_CUSTOM_FOOD);
```

## 4. 關鍵：為什麼要用 `MillRegistry`？
本專案封裝了 `MillRegistry.registerItem`，這會幫你處理：
1. **Identifier (ID)：** 自動加上 `millenaire-reborn` 命名空間。
2. **RegistryKey：** 1.21.8 所需的類型安全標記。

**下一步：** 物品註冊完了，但它們在遊戲裡還是紫色黑色的方塊（遺失材質）。我們將在教學 04 處理這部分。
