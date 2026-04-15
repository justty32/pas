# RimWorld 進階教程：實現持久化的大地圖小人 (Persistent World Pawns)

在標準的 RimWorld 流程中，襲擊者在離開地圖後通常會被系統回收（除非是派系領袖）。如果你想讓一個特定的小人在襲擊結束後，在大地圖上「活下去」並成為一個長期的威脅或盟友，你需要遵循本教程的步驟。

## 1. 概念核心：WorldPawns 與 WorldObject
*   **WorldPawns**: 這是遊戲的全球存儲池。位於此處的小人不會被渲染，但其數據（健康、關係、裝備）會被永久保存。
*   **WorldObject**: 這是大地圖上的顯示載體。要讓小人能在世界地圖上「移動」，你需要建立一個自定義的 `WorldObject` 來充當他的「外殼」。

## 2. 第一步：從小人離開地圖時截獲
當事件結束，你想保留某個小人時，必須先將他從地圖移除並轉入世界池。

```csharp
public void PersistPawnToWorld(Pawn pawn)
{
    // 1. 從當前地圖移除 (但不銷毀)
    if (pawn.Spawned) pawn.DeSpawn();

    // 2. 進入 WorldPawns 存儲池
    // 使用 Constant 參數保證他不會被垃圾回收 (GC) 掉
    Find.WorldPawns.PassToWorld(pawn, PawnDiscardDecideMode.KeepForever);
}
```

## 3. 第二步：建立大地圖載體 (The Stalker)
定義一個在大地圖上代表該小人的物件。

```csharp
public class WorldObject_Stalker : WorldObject
{
    public Pawn trackedPawn; // 存儲目標小人

    public override void ExposeData()
    {
        base.ExposeData();
        // 必須使用 References，因為小人主體在 WorldPawns 裡
        Scribe_References.Look(ref trackedPawn, "trackedPawn");
    }

    public override void Tick()
    {
        base.Tick();

        // 每 2500 Ticks (1小時) 運行一次狀態模擬
        if (Find.TickManager.TicksGame % 2500 == 0)
        {
            SimulatePawnStatus();
        }
    }

    private void SimulatePawnStatus()
    {
        if (trackedPawn == null) return;

        // 模擬生存狀態：即使不在地圖上，他也會餓，傷口也會好
        // 使用小人的健康與需求系統的 Tick 邏輯
        trackedPawn.TickRare(); 

        // 模擬大地圖移動：隨機向玩家基地靠近
        int playerTile = Faction.OfPlayer.HomeWithMostPawns.Tile;
        if (this.Tile != playerTile)
        {
            this.Tile = Find.WorldGrid.FindNextTileTowards(this.Tile, playerTile);
        }
    }
}
```

## 4. 第三步：重新進入地圖 (Re-spawning)
當這個「追擊者」抵達玩家基地時，觸發一個新的襲擊事件，並將「同一個」小人放回地圖。

```csharp
public void ReSpawnStalker(WorldObject_Stalker stalker, Map map)
{
    Pawn p = stalker.trackedPawn;
    
    // 從大地圖移除載體
    stalker.Destroy();

    // 在地圖邊緣生成
    IntVec3 loc = CellFinder.RandomEdgeCell(map);
    GenSpawn.Spawn(p, loc, map);

    // 保持他之前的傷口和記憶
    Messages.Message($"{p.LabelShort} 回來找你算帳了！他身上還帶著上次留下的傷疤。", p, MessageTypeDefOf.ThreatBig);
}
```

## 5. 進階：實作時限過期與垃圾回收 (Garbage Collection)
為了防止地圖上充斥著無關緊要的舊角色，我們需要為 `WorldObject_Stalker` 加入一個過期機制。

```csharp
public class WorldObject_Stalker : WorldObject
{
    public Pawn trackedPawn;
    public int lastInteractionTick; // 記錄最後一次與玩家互動的時間
    private const int ExpiryTicks = 600000; // 10 天 (60,000 * 10)

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_References.Look(ref trackedPawn, "trackedPawn");
        Scribe_Values.Look(ref lastInteractionTick, "lastInteractionTick", 0);
    }

    public override void Tick()
    {
        base.Tick();

        // 檢查是否過期
        if (Find.TickManager.TicksGame - lastInteractionTick > ExpiryTicks)
        {
            AbandonTracking();
            return;
        }

        // 每小時運行一次模擬... (同前文)
    }

    private void AbandonTracking()
    {
        if (trackedPawn != null)
        {
            // 關鍵：將小人標記為可被回收 (Discard)
            // 這樣遊戲在下次清理 WorldPawns 時就會徹底刪除他
            Find.WorldPawns.RemoveAndDiscardPawn(trackedPawn);
        }
        
        // 銷毀大地圖上的圖示
        this.Destroy();
        Log.Message($"MyMod: 由於長期無互動，已放棄對 {trackedPawn?.LabelShort} 的持久化追蹤。");
    }

    // 當玩家與他再次戰鬥或交易時，務必呼叫此方法刷新時間
    public void Notify_Interaction()
    {
        lastInteractionTick = Find.TickManager.TicksGame;
    }
}
```

## 6. XML 配置
為了讓 `WorldObject` 生效... (同前文)

## 7. 技術注意事項
1.  **記憶體管理**：永遠不要在 `ExposeData` 中使用 `Scribe_Deep`... (同前文)
2.  **主動釋放**：當你決定不再追蹤某人時，呼叫 `Find.WorldPawns.RemoveAndDiscardPawn()` 是最安全且最乾淨的做法，這能確保他不會殘留在存檔的底層數據中。
3.  **效能考量**：在大地圖上運行 `TickRare()` 是有成本的。如果你有數百個持久化小人，建議將模擬頻率從 2500 Ticks 降低到 15000 Ticks (6小時)。

---
*這份教程由 Gemini CLI 針對持久化 AI 邏輯開發而撰寫。*
