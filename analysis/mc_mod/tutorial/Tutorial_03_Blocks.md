# 教學 03：註冊建築方塊

所有的 Millénaire 村莊都依賴獨特的方塊來構建建築。

## 1. 在 `MillBlocks` 中聲明方塊
打開 `src/main/java/me/devupdates/millenaireReborn/common/registry/MillBlocks.java`。

```java
public static Block MY_CULTURE_BRICKS;
```

## 2. 實作註冊
在 `initialize()` 方法中：
```java
// 註冊方塊本身
MY_CULTURE_BRICKS = MillRegistry.registerBlock("my_culture_bricks", 
    new Block(AbstractBlock.Settings.create()
        .mapColor(MapColor.PALE_YELLOW) // 在地圖上顯示的顏色
        .instrument(NoteBlockInstrument.BASEDRUM) // 音符盒音效
        .strength(2.0f, 6.0f) // 硬度與抗炸能力
        .requiresTool() // 是否需要工具挖掘
    ));

// 重要：方塊必須同時註冊一個 Item (物品形式)，玩家才能在背包裡持有它
MillRegistry.registerBlockItem("my_culture_bricks", MY_CULTURE_BRICKS);
```

## 3. 方塊狀態 (BlockStates)
在現代 MC 中，方塊不僅僅是一個模型。它可能有 `facing` (朝向) 或 `lit` (是否點亮) 等屬性。
- 如果你的方塊很簡單（如磚塊），直接使用 `Block` 類別即可。
- 如果需要特殊行為（如磨坊方塊），你需要建立一個繼承自 `Block` 的新類別。

## 4. 方塊與藍圖的關係
記住，你的方塊 ID 必須與後續在 `OldSource` 藍圖中定義的像素顏色相對應（這將在 Phase 4 的教學詳細說明）。
