using Verse;
using RimWorld;
using System.Collections.Generic;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：自定義派系生成邏輯。
/// 針對中世紀商人派系，優化商隊的生成構成。
/// </summary>
public class PawnGroupKindWorker_MedievalMerchant : PawnGroupKindWorker
{
    /// <summary>
    /// 核心機制：定義商隊如何選擇小人。
    /// 在這裡我們可以加入複雜的邏輯，而不僅僅是 XML 中的權重。
    /// </summary>
    public override void GeneratePawns(PawnGroupMakerParms parms, PawnGroupMaker groupMaker, List<Pawn> outPawns, bool errorOnNullPawnKind = true)
    {
        // 1. 呼叫基礎生成（根據 XML 定義挑選小人）
        base.GeneratePawns(parms, groupMaker, outPawns, errorOnNullPawnKind);

        // 2. 自定義修正：確保商隊中至少有一個商人，並為其分發特殊的財貨。
        Pawn merchant = outPawns.FirstOrDefault(p => p.kindDef.defName == "MyMod_Medieval_Merchant");
        if (merchant != null)
        {
            // 為商人添加一些「中世紀特色」的隨身財物
            Thing gold = ThingMaker.MakeThing(ThingDefOf.Gold);
            gold.stackCount = Rand.Range(5, 15);
            merchant.inventory.innerContainer.TryAdd(gold);
            
            // 給予一個隨機的中世紀藝術品
            if (Rand.Value < 0.3f)
            {
                Thing sculpture = ThingMaker.MakeThing(ThingDefOf.SculptureSmall, ThingDefOf.WoodLog);
                merchant.inventory.innerContainer.TryAdd(sculpture);
            }
        }

        // 3. 防禦加強：如果商隊非常有錢（點數高），則強制升級一名護衛為重裝騎士。
        if (parms.points > 1000)
        {
            Pawn guard = outPawns.FirstOrDefault(p => p.kindDef.defName == "MyMod_Medieval_Guard");
            if (guard != null)
            {
                // 這裡僅作示範，實際替換需要從清單中移除並重新生成
                Log.Message("MyMod: 中世紀商隊規模龐大，騎士已加入護航。");
            }
        }
    }

    /// <summary>
    /// 決定該商隊是否能生成。
    /// 例如：我們可以在極端氣候下禁止中世紀商隊生成。
    /// </summary>
    public override bool CanGenerateFrom(PawnGroupMakerParms parms, PawnGroupMaker groupMaker)
    {
        if (parms.tile != -1)
        {
            // 如果目標地塊太冷，中世紀商人可能不會出現（他們沒保暖科技）
            float temp = Find.World.tileTemperatures.GetOutdoorTemp(parms.tile);
            if (temp < -20f) return false;
        }
        return base.CanGenerateFrom(parms, groupMaker);
    }
}

/// <summary>
/// 實戰範例：大市集事件。
/// 生成一支規模巨大的商隊，並在地圖中心停留較長時間。
/// </summary>
public class IncidentWorker_MedievalFair : IncidentWorker
{
    protected override bool CanFireNowSub(IncidentParms parms)
    {
        return base.CanFireNowSub(parms) && Find.FactionManager.FirstFactionOfDef(DefDatabase<FactionDef>.GetNamed("MyMod_MedievalMerchantFaction")) != null;
    }

    protected override bool TryExecuteWorker(IncidentParms parms)
    {
        Map map = (Map)parms.target;
        Faction faction = Find.FactionManager.FirstFactionOfDef(DefDatabase<FactionDef>.GetNamed("MyMod_MedievalMerchantFaction"));

        // 1. 生成一個特大號的商隊 (點數加倍)
        PawnGroupMakerParms groupParms = IncidentParmsUtility.GetDefaultPawnGroupMakerParms(PawnGroupKindDefOf.Trader, parms);
        groupParms.points *= 3f; 
        groupParms.faction = faction;
        groupParms.traderKind = DefDatabase<TraderKindDef>.GetNamed("MyMod_TraderKind_Medieval");

        List<Pawn> pawns = PawnGroupMakerUtility.GeneratePawns(groupParms).ToList();
        
        // 2. 在地圖邊緣生成並移動到中心
        IntVec3 loc = CellFinder.RandomEdgeCell(map);
        foreach (Pawn p in pawns)
        {
            GenSpawn.Spawn(p, loc, map);
        }

        // 3. 發送橫幅通知
        Find.LetterStack.ReceiveLetter(def.letterLabel, def.letterText, def.letterDef, pawns[0]);

        return true;
    }
}

/// <summary>
/// 自定義派系類別，追蹤與玩家的貿易往來。
/// </summary>
public class Faction_MedievalMerchants : Faction
{
    public int tradeCount = 0;

    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Values.Look(ref tradeCount, "tradeCount", 0);
    }

    /// <summary>
    /// 當玩家與該派系完成一次交易時呼叫 (這需要透過 Harmony Patch 注入，此處為示範邏輯)。
    /// </summary>
    public void Notify_TradeAccomplished()
    {
        tradeCount++;
        if (tradeCount % 5 == 0)
        {
            Messages.Message("商貿同盟對你的信用感到滿意，未來的商隊將攜帶更高級的貨物。", MessageTypeDefOf.PositiveEvent);
        }
    }
}
