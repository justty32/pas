# 資料持久化與 NBT 重構分析

## 1. 世界數據持久化 (參考 `OldSource/java/org/millenaire/common/world/MillWorldData.java`)
- **核心邏輯：** 舊版 `MillWorldData.java` 處理整個世界的村莊索引與聲望。
- **現代化：** 應轉化為 `net.minecraft.world.PersistentState`。

## 2. 物品與 NBT (1.21.8 Data Components)
- **核心註冊：** `src/main/java/me/devupdates/millenaireReborn/common/registry/MillItems.java`。
- **自定義組件：** 規劃於 `common.component` (尚未實作)。
- **參考邏輯：** `OldSource/java/org/millenaire/common/item/InvItem.java`。

## 3. 實體存檔
- **村民屬性：** `OldSource/java/org/millenaire/common/entity/EntityMillVillager.java` 中的 `writeCustomDataToNbt`。
- **建築屬性：** `OldSource/java/org/millenaire/common/village/Building.java` 中的 `saveBuildingData`。
