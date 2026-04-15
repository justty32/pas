# RimWorld 技術教程：自定義生態系 (Custom Biomes)

生態系 (Biome) 是地圖生成的頂層框架，決定了玩家在點擊大地圖時看到的環境。本教程將引導你建立一個完整的自定義生態系。

---

## 1. 核心定義：BiomeDef (XML)

所有的生態系都在 `BiomeDef` 中定義。

### A. 大地圖生成邏輯 (Placement)
*   **`WorkerClass`**: 負責在大地圖生成時，根據 Tile 的屬性給出「分數」。分數最高者將贏得該地塊。
*   **`animalDensity` / `plantDensity`**: 全域生成頻率。
*   **`terrestrial`**: 是否為陸地。

### B. 生態構成 (Bio-Lists)
*   **`wildAnimals`**: 在該處生成的動物列表及其權重。
*   **`wildPlants`**: 在該處生成的植物列表及其權重。
*   **`allowedPackAnimals`**: 允許在該地活動的商隊馱獸。

---

## 2. 大地圖分佈機制 (BiomeWorker)

你需要撰寫一個 C# 類別來告訴遊戲「這個生態系應該出現在哪」。

```csharp
public class BiomeWorker_CrystalForest : BiomeWorker
{
    public override float GetScore(Tile tile, int tileID)
    {
        // 1. 基礎條件：如果是有水的，排除掉
        if (tile.WaterCovered) return -100f;

        // 2. 氣候過濾：我們希望它出現在寒冷且降雨量中等的地方
        if (tile.temperature < -5f || tile.temperature > 15f) return 0f;
        if (tile.rainfall < 500f) return 0f;

        // 3. 分數計算：降雨量越多、溫度越接近 0 度，分數越高
        return 15f + (tile.rainfall / 100f);
    }
}
```

---

## 3. 地形與環境優化

為了讓生態系與眾不同，你通常需要定義專屬的地表。

*   **`TerrainDef`**: 定義藍色的土地或水晶岩層。
*   **`Pollution`**: 也可以設定該生態系是否天然帶有污染或放射性。

---

## 4. 進階：地貌修改器 (GenStep)

如果你想讓這個生態系生成特殊的結構（例如：滿地的水晶簇），你需要建立一個 `GenStep` 並掛鉤到該生態系。

```xml
<BiomeDef>
  <defName>MyMod_CrystalForest</defName>
  <modExtensions>
    <li Class="MyMod.Examples.BiomeExtension">
      <extraGenSteps>
        <li>MyMod_GenStep_CrystalFormations</li>
      </extraGenSteps>
    </li>
  </modExtensions>
</BiomeDef>
```

---

## 5. 開發建議
1.  **資源平衡**：確保你的生態系有足夠的可食用植物或木材，除非你故意想做一個極限生存挑戰。
2.  **視覺風格**：自定義生態系的靈魂在於貼圖。適當地修改 `TerrainDef` 的 `color` 屬性能快速改變視覺觀感。
3.  **導航成本**：如果你的生態系到處是「水晶簇」，請記得調整 `pathCost`。

---
*這份指南由 Gemini CLI 針對 RimWorld.BiomeDef 系統撰寫。*
