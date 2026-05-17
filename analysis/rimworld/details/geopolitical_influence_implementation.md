# 地緣政治邊界與影響力：全球勢力範圍的 C# 實作

本系統將哨所的物理位置與大地圖上的路徑演算法整合，實現真正的「領土攔截」與「全球增益」網路。

## 1. 大地圖路徑攔截邏輯 (Pathfinding Interceptor)

我們需要攔截襲擊者的路徑，判斷其是否穿過玩家的勢力範圍。

```csharp
public static class WorldPathUtility
{
    // 檢查從來源到目標的路徑是否被玩家哨所攔截
    public static WorldObject_Outpost GetInterceptingOutpost(int startTile, int endTile)
    {
        // 獲取兩點之間的大地圖路徑 (Tile 集合)
        List<int> path = new List<int>();
        Find.WorldRoutePlanner.StartPoint = startTile;
        Find.WorldRoutePlanner.EndPoint = endTile;
        // 注意：這裡假設使用自定義路徑算法或分析現有路徑
        
        foreach (int tile in path)
        {
            var outpost = Find.WorldObjects.WorldObjectAt<WorldObject_Outpost>(tile);
            if (outpost != null && outpost.CanIntercept)
            {
                return outpost;
            }
        }
        return null;
    }
}
```

## 2. 動態國界線生成 (Dynamic Border Mesh)

利用 `WorldMesh` 在世界地圖上繪製具有地理感的國界線。

```csharp
public class WorldLayer_TerritoryBorders : WorldLayer
{
    public override IEnumerable<LayerSubMesh> Regenerate()
    {
        var influenceComp = Find.World.GetComponent<WorldComponent_FactionInfluence>();
        
        foreach (var tile in influenceComp.BorderTiles)
        {
            // 獲取該 Tile 的鄰居，若鄰居屬於不同派系，則繪製邊界線
            foreach (var neighbor in Find.WorldGrid.tileNeighbors[tile])
            {
                if (influenceComp.GetOwner(neighbor) != influenceComp.GetOwner(tile))
                {
                    // 在這兩個 Tile 的交界處繪製一條粗線
                    DrawBorderLine(tile, neighbor, influenceComp.GetColor(tile));
                }
            }
        }
    }
}
```

## 3. 全球影響力加成 (Global Synergy)

實作一個全域管理器來統計所有哨所提供的 Buff。

```csharp
public class WorldComponent_GlobalSynergy : WorldComponent
{
    public float totalResearchMultiplier = 1.0f;
    public float globalMoodOffset = 0f;

    public void RecalculateSynergy()
    {
        totalResearchMultiplier = 1.0f;
        globalMoodOffset = 0f;

        foreach (var outpost in Find.WorldObjects.AllWorldObjects.OfType<WorldObject_Outpost>())
        {
            // 數據中心哨所增加研究速度
            if (outpost.HasModule(OutpostModuleDefOf.DataCenter))
                totalResearchMultiplier += 0.2f;
            
            // 宗教中心哨所增加心情
            if (outpost.HasModule(OutpostModuleDefOf.Cathedral))
                globalMoodOffset += 2.0f;
        }
    }
}
```

## 4. 戰略緩衝事件攔截 (Raid Interception)

當襲擊觸發時，透過 Harmony Patch 檢查攔截邏輯。

```csharp
[HarmonyPatch(typeof(IncidentWorker_RaidEnemy), "TryExecuteWorker")]
public static class Patch_RaidInterception
{
    [HarmonyPrefix]
    public static bool Prefix(IncidentParms parms)
    {
        if (parms.target is Map map && map.IsPlayerHome)
        {
            int sourceTile = parms.raidArrivalMode == RaidArrivalModeDefOf.EdgeWalkIn ? parms.spawnCenter.Tile : -1;
            if (sourceTile != -1)
            {
                var interceptor = WorldPathUtility.GetInterceptingOutpost(sourceTile, map.Tile);
                if (interceptor != null)
                {
                    // 轉移襲擊目標到哨所
                    interceptor.HandleRaid(parms.points);
                    Messages.Message($"襲擊已被邊境哨所 {interceptor.Label} 攔截！", MessageTypeDefOf.PositiveEvent);
                    return false; // 終止原本針對主基地的襲擊
                }
            }
        }
        return true;
    }
}
```

## 5. 視覺與戰略反饋

*   **勢力光暈 (Influence Glow)**: 在世界地圖上，哨所周圍會根據其影響力強度顯示不同亮度的光暈。
*   **物流線路圖**: 在大地圖 UI 中，玩家可以開啟「物流視圖」，看到資源在哨所間流動的虛擬虛線。
*   **預警 UI**: 當敵對商隊或襲擊部隊進入哨所攔截半徑時，大地圖上的該哨所圖示會閃爍紅光，並顯示「攔截預計時間」。

---
*文件路徑: analysis/rimworld/details/geopolitical_influence_implementation.md*
