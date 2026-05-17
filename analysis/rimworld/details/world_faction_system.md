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
        Scribe_Values.Look(ref tileOwners, "tileOwners");
        Scribe_Values.Look(ref tileInfluence, "tileInfluence");
    }
}
```

## 2. 核心算法：影響力擴散 (Influence Spreading)

勢力應從「定居點 (Settlement)」向外擴散，受距離、地形與派系強度影響。

```csharp
public void UpdateInfluence()
{
    // 1. 初始化：每個定居點為中心點
    foreach (var settlement in Find.WorldObjects.Settlements)
    {
        int centerTile = settlement.Tile;
        int factionId = settlement.Faction.loadID;
        
        // 2. 使用廣度優先搜尋 (BFS) 擴散
        Find.WorldFloodFiller.FloodFill(centerTile, (int tile) => {
            // 判斷該格子是否可被控制 (例如：海洋不可控制)
            return !world.grid[tile].IsWater;
        }, (int tile, int dist) => {
            float strength = CalculateStrength(settlement.Faction, dist);
            if (strength > tileInfluence[tile])
            {
                tileOwners[tile] = factionId;
                tileInfluence[tile] = strength;
            }
            return dist > 15; // 擴散半徑限制
        });
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
