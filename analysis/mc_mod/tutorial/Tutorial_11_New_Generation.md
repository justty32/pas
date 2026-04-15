# 教學 11：新建生成機制與村莊類型 (Generation)

生成機制決定了你的文化何時出現在世界中。

## 1. 村莊類型 (`VillageType`)
每個文化包含多種村莊類型：
- **Hameau (小村莊)**: 只有少數建築。
- **Chef-lieu (行政中心)**: 包含大型建築與市場。

## 2. 生物群落限制 (Biomes)
你必須定義該村莊能生成在哪裡：
```java
VILLAGE_NORMAN.addValidBiomeTag(BiomeTags.IS_FOREST);
VILLAGE_MAYAN.addValidBiomeTag(BiomeTags.IS_JUNGLE);
```

## 3. 權重與頻率
`weight` 決定了生成的機率。數字越高，玩家越容易遇到該種類的村莊。

## 4. 參考路徑
- `OldSource/java/org/millenaire/common/culture/VillageType.java`
- `OldSource/java/org/millenaire/common/world/WorldGenVillage.java`
