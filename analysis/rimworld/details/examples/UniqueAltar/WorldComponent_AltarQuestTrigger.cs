using RimWorld;
using RimWorld.Planet;
using Verse;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：在大約第 3 天觸發祭壇任務。
/// 展示如何尋找鄰近地塊並手動啟動任務。
/// </summary>
public class WorldComponent_AltarQuestTrigger : WorldComponent
{
    private bool questFired = false;
    private const int TriggerTick = 180000; // 第 3 天 (60,000 * 3)

    public WorldComponent_AltarQuestTrigger(World world) : base(world) { }

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref questFired, "questFired", false);
    }

    public override void WorldComponentTick()
    {
        base.WorldComponentTick();

        // 每隔一段時間檢查一次，避免每幀計算
        if (!questFired && Find.TickManager.TicksGame > TriggerTick && Find.TickManager.TicksGame % 1000 == 0)
        {
            TryFireAltarQuest();
        }
    }

    private void TryFireAltarQuest()
    {
        // 1. 找到玩家的家（基地）所在的 Tile
        int playerTile = Faction.OfPlayer.HomeWithMostPawns.Tile;

        // 2. 在附近尋找一個可以通行且距離合適的 Tile (距離 2 到 8 格)
        if (TileFinder.TryFindPassableTileWithTraversalDistance(playerTile, 2, 8, out int targetTile))
        {
            // 3. 獲取任務定義
            QuestScriptDef questDef = DefDatabase<QuestScriptDef>.GetNamed("MyMod_AltarQuest");

            // 4. 設定任務參數 (Slate)
            Slate slate = new Slate();
            slate.Set("targetTile", targetTile);

            // 5. 生成並啟動任務
            Quest quest = QuestUtility.GenerateQuestAndMakeAvailable(questDef, slate);
            Find.QuestManager.Add(quest);

            questFired = true;
            Log.Message("MyMod: 祭壇任務已成功觸發！");
        }
    }
}
