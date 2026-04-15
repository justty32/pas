using RimWorld;
using RimWorld.Planet;
using Verse;
using System.Collections.Generic;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：在大地圖上表示「獨特祭壇」的地點。
/// </summary>
public class UniqueAltarSite : WorldObject
{
    // 能量積累數值
    public float energyLevel = 0f;
    private const float MaxEnergy = 100f;

    /// <summary>
    /// 數據持久化：保存能量等級。
    /// </summary>
    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref energyLevel, "energyLevel", 0f);
    }

    /// <summary>
    /// 大地圖的心跳：每 Tick 執行一次。
    /// </summary>
    public override void Tick()
    {
        base.Tick();
        
        // 1. 每隔一段時間增加能量 (每 2500 Ticks 增加 1%)
        if (Find.TickManager.TicksGame % 2500 == 0 && energyLevel < MaxEnergy)
        {
            energyLevel += 1f;
        }
    }

    /// <summary>
    /// 動態圖示：根據能量等級改變大地圖上的外觀。
    /// </summary>
    public override Texture2D DrawGraphic
    {
        get
        {
            if (energyLevel >= 80f)
                return ContentFinder<Texture2D>.Get("World/WorldObjects/Sites/Portal_Active");
            if (energyLevel >= 40f)
                return ContentFinder<Texture2D>.Get("World/WorldObjects/Sites/Portal_Charging");
            
            return base.DrawGraphic; // 預設圖示
        }
    }

    public override string GetInspectString()
    {
        return base.GetInspectString() + $"\n能量等級: {energyLevel:F1}%";
    }

    /// <summary>
    /// 當玩家商隊進入該點位時觸發。
    /// </summary>
    public override IEnumerable<FloatMenuOption> GetFloatMenuOptions(Caravan caravan)
    {
        foreach (var o in base.GetFloatMenuOptions(caravan)) yield return o;

        yield return new FloatMenuOption("進入祭壇地點", () =>
        {
            Enter(caravan);
        });
    }

    private void Enter(Caravan caravan)
    {
        // 1. 獲取或生成地圖
        // 這裡我們指向自定義的 MapGeneratorDef: MyMod_UniqueAltarMapGen
        Map map = GetOrGenerateMapUtility.GetOrGenerateMap(this.Tile, new IntVec2(100, 100), null);

        // 2. 將商隊小人傳送進去
        CaravanEnterMapUtility.Enter(caravan, map, CaravanEnterMode.Edge, CaravanDropInventoryMode.DoNotDrop, true);
        
        // 3. 標記為已知地點
        Find.LetterStack.ReceiveLetter("抵達祭壇", "你已到達神祕的祭壇地點。", LetterDefOf.PositiveEvent, this);
    }
}
