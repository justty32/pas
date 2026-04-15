# 世界自動生成機制深度分析

Millénaire 的生成機制不同於原版村莊，它更依賴於「後置掃描」與「文化控制」。

## 1. 生成觸發 (`WorldGenVillage.java`)
- **區塊掃描**：當新區塊生成時，`WorldGenVillage` 會檢查周圍的生物群落 (Biomes)。
- **合規性檢查**：
    - **生物群落比例**：根據 `VillageType.java`，該地點必須有超過 60% (`MINIMUM_VALID_BIOME_PERC`) 的面積屬於該文化允許的生物群落。
    - **平坦度檢查**：系統會掃描一個區域內的垂直高度變化，如果地形過於崎嶇，則放棄生成。

## 2. 村莊類型定義 (`VillageType.java`)
- **權重系統**：每個文化有多種村莊類型（如「 hameau  hamlet」或「 marvel 奇蹟」）。系統會根據 `getChoiceWeight` 隨機選擇。
- **核心建築**：每個村莊類型都定義了一個「核心建築」（通常是市政廳 Town Hall），生成時會以此為圓心展開。

## 3. 獨立建築 (Lone Buildings)
- 除了完整的村莊，系統還會生成「獨立建築」（如隱士小屋）。
- **邏輯**：從 `lonebuildings/*.txt` 載入配置，生成頻率通常遠低於完整村莊。

## 4. 原始碼位置
- **生成邏輯**：`OldSource/java/org/millenaire/common/world/WorldGenVillage.java`
- **數據管理**：`OldSource/java/org/millenaire/common/world/MillWorldData.java`
    - 它負責記錄哪些區域已經嘗試過生成，避免重複計算。
