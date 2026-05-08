# 進階哨站：地緣屏障與邊境長城 (Geopolitical Barriers & Site Synergy)

這項擴展將哨站的「物理位置」與大地圖上的「敵對威脅」深度連結，讓玩家的擴張策略具備真正的地緣政治意義。

## 1. 戰略屏障機制 (Strategic Buffer Zone)

哨站不再只是地圖上的一個點，它在大地圖上具備一個「攔截半徑」。

*   **地理攔截 (Geographic Interception)**:
    *   當敵對勢力（如海盜、部落）發起襲擊時，系統會計算其出發點（最近的敵人 Site）到玩家主基地的路徑。
    *   如果路徑穿過或鄰近玩家的「邊境哨站」，該襲擊有極高機率（如 70%-90%）被攔截並轉向該哨站。
*   **攔截強度 (Interception Strength)**:
    *   取決於哨站的「威懾力」（採樣期的防禦塔數量、武裝人員等級）。
    *   哨站與敵方據點的距離越近，攔截優先級越高。

## 2. 邊境哨站的特殊交互

### A. 監視與騷擾 (Watchtower & Harassment)
*   **提前預警**: 靠近敵營的哨站可以提供長達數天的襲擊預警，讓主基地有充足時間準備。
*   **主動出擊**: 玩家可以從哨站發起「騷擾行動」，降低敵方據點的技術等級或襲擊規模（反映哨站小人定期去搞破壞）。

### B. 談判與勒索 (Negotiation Hub)
*   對於中立或不穩定的勢力，靠近他們的哨站可以作為「收買中心」。
*   哨站可以自動向鄰近敵營發送「保護費」，以換取較長時間的和平。

## 3. 帝國藍圖：分區管理 (Imperial Zoning)

玩家可以根據地緣環境將領土劃分為：
1.  **核心區 (Core World)**: 主基地，受重重哨站保護，完全不參與任何戰鬥事件。
2.  **工業區 (Industrial Belt)**: 資源採集哨站，位於後方，負責提供物流支持。
3.  **邊境長城 (The Marches)**: 軍事與事件轉運哨站，駐紮精銳，負責攔截一切外來訪客與襲擊。

## 4. 技術實作：大地圖路徑攔截 (Pathfinding Interception)

```csharp
public static class GeopoliticalManager {
    public static OutpostWorldObject GetInterceptingOutpost(WorldObject source, WorldObject target) {
        // 獲取兩點之間的大地圖路徑
        var pathTiles = Find.WorldRoutePlanner.GetRoute(source.Tile, target.Tile);
        
        // 檢查路徑上是否有哨站
        foreach (var tile in pathTiles) {
            var outpost = Find.WorldObjects.WorldObjectAt<OutpostWorldObject>(tile);
            if (outpost != null && outpost.CanInterceptRaid) {
                return outpost;
            }
        }
        return null;
    }
}
```

## 5. 戰略深度：為什麼這像「帝國」？

1.  **領土意識**: 玩家不再只是關心一張圖，而是關心大地圖上的「勢力範圍」。
2.  **進攻性防禦**: 玩家會主動去敵方家門口蓋一個「堡壘哨站」，將所有戰火擋在國門之外。
3.  **戰略深度**: 失去一個哨站不再只是少了一點資源，而是意味著防禦線出現缺口，主基地暴露在危險之中。

---
*文件路徑: analysis/rimworld/others/geopolitical_barrier_extension.md*
