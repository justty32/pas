# 教學 04：創造模式標籤頁與資產自動化

你的物品與方塊已經註冊，現在我們要讓它們漂亮地出現在遊戲中。

## 1. 建立專屬創造模式標籤頁
打開 `src/main/java/me/devupdates/millenaireReborn/common/registry/MillCreativeTabs.java`。

```java
public static final RegistryKey<ItemGroup> MY_CULTURE_TAB_KEY = RegistryKey.of(
    Registries.ITEM_GROUP.getKey(), 
    Identifier.of(MillenaireReborn.MOD_ID, "my_culture_tab")
);

public static final ItemGroup MY_CULTURE_TAB = register("my_culture_tab", 
    FabricItemGroup.builder()
        .displayName(Text.translatable("itemGroup.millenaire-reborn.my_culture_tab"))
        .icon(() -> new ItemStack(MillItems.MY_CULTURE_SWORD)) // 圖標
        .entries((displayContext, entries) -> {
            // 在這裡加入你的物品
            entries.add(MillItems.MY_CULTURE_SWORD);
            entries.add(MillBlocks.MY_CULTURE_BRICKS);
        }).build());
```

## 2. 資產自動化 (Data Generation)
手寫數百個 JSON 模型文件是非常痛苦的。Fabric 提供 Data Generation。
- **路徑：** `src/client/java/me/devupdates/millenaireReborn/client/MillenaireRebornDataGenerator.java`

當你執行 `./gradlew runDatagen` 時，系統會：
1. **物品模型：** 根據 `MillItems` 的內容自動生成 `.json` 模型路徑。
2. **方塊狀態：** 為 `MillBlocks` 中的方塊生成預設狀態文件。
3. **翻譯：** 如果你在翻譯生成器中定義了對應關係，它會自動更新語系檔。

## 3. 實作本地化 (Translations)
編輯 `src/main/resources/assets/millenaire-reborn/lang/en_us.json`。
```json
{
  "item.millenaire-reborn.my_culture_sword": "My Culture Sword",
  "block.millenaire-reborn.my_culture_bricks": "My Culture Bricks",
  "itemGroup.millenaire-reborn.my_culture_tab": "Millénaire: My Culture"
}
```

**提示：** 執行 `runDatagen` 後，請檢查 `src/main/resources/assets/millenaire-reborn/` 目錄，你會發現模型文件已經自動生成了！
