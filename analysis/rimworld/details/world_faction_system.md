# 動態世界與派系邊界：地緣政治系統實作指南

要讓 RimWorld 的世界地圖「活起來」，我們需要實作一套超越原版靜態點位元的分散式勢力系統。

## 1. 數據層：WorldComponent_FactionInfluence

我們需要一個全域組件來儲存每個格子 (Tile) 的派系控制權。

```csharp
public class WorldComponent_FactionInfluence : WorldComponent
{
    // 儲存每個 Tile 的領主派系 ID
    // 使用數組以獲得最高查詢效能 (Tile 總數約 100k)
    public int[] tileOwners;
    public float[] tileInfluence; // 控制強度 (0.0~1.0)

    public WorldComponent_FactionInfluence(World world) : base(world)
    {
        tileOwners = new int[world.grid.TilesCount];
        tileInfluence = new float[world.grid.TilesCount];
        for (int i = 0; i < tileOwners.Length; i++) tileOwners[i] = -1; // -1 表示無人佔領
    }

    public override void ExposeData()
    {
        base.ExposeData();
        // ⚠️ 核對 2026-06-01：Scribe_Values.Look 只處理單一值，不支援 int[]/float[] 陣列。
        // DataExposeUtility 只提供 LookBoolArray；對 int[]/float[] 需自行做二進位序列化，
        // 或改用 List<int>/List<float> 搭配 Scribe_Collections.Look（存檔會很大，
        // 對 ~100k 元素的 world tile 陣列考慮 BitConverter 逐行寫入 XML 或用壓縮 blob）。
        // 暫以 List<int> 替代示意：
        // Scribe_Collections.Look(ref tileOwnersList, "tileOwners", LookMode.Value);
        // TODO: 選定儲存方案後替換
        Scribe_Values.Look(ref tileOwners, "tileOwners");   // ❌ 無效，需替換
        Scribe_Values.Look(ref tileInfluence, "tileInfluence"); // ❌ 無效，需替換
    }
}
```

## 2. 核心算法：影響力擴散 (Influence Spreading)

勢力應從「定居點 (Settlement)」向外擴散，受距離、地形與派系強度影響。

> ⚠️ **核對 2026-06-01（三個坑）**：
> 1. `Find.WorldFloodFiller` **不存在**。`WorldFloodFiller` 屬於 `PlanetLayer`，透過 `layer.Filler` 取得。全局不存在 `Find.WorldFloodFiller` shortcut。
> 2. lambda 參數型別應為 `PlanetTile`，不是 `int`（1.6 已全面改用 `PlanetTile` struct）。
> 3. `world.grid[tile].IsWater`：世界 Tile 沒有 `.IsWater`；應改用 `Find.WorldGrid[tile].biome.IsSeaTile`（或檢查 biome 的 `WaterCovered` 屬性）。

```csharp
public void UpdateInfluence()
{
    // 需從 settlement.Tile.Layer 取得對應的 WorldFloodFiller
    foreach (var settlement in Find.WorldObjects.Settlements)
    {
        PlanetTile centerTile = settlement.Tile;  // PlanetTile，非 int
        int factionId = settlement.Faction.loadID;
        PlanetLayer layer = centerTile.Layer;
        WorldFloodFiller filler = layer.Filler;   // ✅ 正確取法

        filler.FloodFill(
            centerTile,
            // passCheck：PlanetTile → bool
            (PlanetTile tile) => !Find.WorldGrid[tile].biome.IsSeaTile,  // ✅ IsWater 替代
            // processor：PlanetTile, int → void（或回傳 bool 表示「停止」）
            (PlanetTile tile, int dist) => {
                float strength = CalculateStrength(settlement.Faction, dist);
                if (strength > tileInfluence[tile.tileId])
                {
                    tileOwners[tile.tileId] = factionId;
                    tileInfluence[tile.tileId] = strength;
                }
            },
            maxTilesToProcess: 200 // 限制擴散格數（替代 dist > 15 的寫法）
        );
    }
}

private float CalculateStrength(Faction faction, int dist)
{
    // 基礎公式：(派系實力 / 距離^2)
    return faction.PlayerRelationKind == FactionRelationKind.Hostile ? 0.8f / (dist + 1) : 1.0f / (dist + 1);
}
```

## 3. 視覺層：WorldLayer_FactionBoundaries

為了在世界地圖上顯示漂亮的邊界，我們需要自定義一個 `WorldLayer`。

```csharp
public class WorldLayer_FactionBoundaries : WorldLayer
{
    public override IEnumerable<LayerSubMesh> Regenerate()
    {
        var comp = Find.World.GetComponent<WorldComponent_FactionInfluence>();
        
        // 遍歷所有 Tile，繪製覆蓋層
        for (int i = 0; i < comp.tileOwners.Length; i++)
        {
            if (comp.tileOwners[i] != -1)
            {
                Faction faction = Find.FactionManager.AllFactions.FirstOrDefault(f => f.loadID == comp.tileOwners[i]);
                if (faction != null)
                {
                    // 獲取該 Tile 的三角形網格並填入派系顏色
                    Color color = faction.Color;
                    color.a = 0.3f; // 半透明
                    DrawTileOverlay(i, color);
                }
            }
        }
    }
}
```

## 4. 動態衝突與邊界變更

當兩個派系的影響力在某個區域重疊時，觸發衝突事件。

*   **衝突偵測**: 在 `WorldComponent.WorldComponentTick` 中，每隔 60,000 tick (一天) 執行一次影響力刷新。
*   **動態調整**: 若 A 派系近期摧毀了 B 派系的哨所，則 A 在該區域的擴散係數暫時提升。
*   **視覺平滑**: 使用 Harmony Patch 攔截 `WorldRenderer`，實作邊界的邊緣羽化 (Alpha Blending)，讓交界處看起來是模糊的爭議區而非鋸齒狀。

## 5. 性能優化建議

*   **分片計算**: 世界地圖格子眾多，不要在同一幀計算全圖影響力。應將地圖分為數個區域，每幀只更新一個區域。
*   **緩存網格**: `WorldLayer` 的 `Regenerate` 非常耗能，只有在領土發生重大變更（如定居點被毀）時才呼叫。

---
*文件路徑: analysis/rimworld/details/world_faction_system.md*
