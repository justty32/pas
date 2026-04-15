# 教學 07：新建村民種類與職業 (Villager Types)

在 Millénaire 中，每個村民的「職業」就是一個 `VillagerType`。

## 1. 核心定義
每個村民種類包含：
- **Key**: 唯一的內部 ID (如 `norman_farmer`)。
- **Gender**: 性別 (0: 男, 1: 女)。
- **Tags**: 決定行為的標籤（如 `child`, `merchant`, `helpinattacks`）。

## 2. 實作步驟
### A. 在 Java 中定義 (Phase 5+)
在未來的職業系統中，你會像這樣定義：
```java
public static VillagerType FARMER = new VillagerType("my_culture_farmer")
    .setGender(0)
    .addTag(VillagerType.TAG_HELPSINATTACKS)
    .setBaseHealth(20);
```

### B. 設定初始背包 (Starting Inventory)
這決定了村民出生時帶什麼。
```java
FARMER.addStartingItem(MillItems.MY_CULTURE_HOE, 1);
FARMER.addStartingItem(Items.WHEAT_SEEDS, 5);
```

## 3. 分配行為 (Goals)
職業的核心是行為池。在 `cultures/.../villagerconfig/` 中定義：
- 農夫：執行 `GoalSow` (播種), `GoalHarvest` (收割)。
- 衛兵：執行 `GoalDefendVillage` (守衛), `GoalPatrol` (巡邏)。

## 4. 參考原始碼位置
- `OldSource/java/org/millenaire/common/culture/VillagerType.java`
- 各文化的 `villagerconfig/*.txt` 配置。
