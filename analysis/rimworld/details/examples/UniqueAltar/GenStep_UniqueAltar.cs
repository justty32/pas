using Verse;
using RimWorld;
using RimWorld.BaseGen;
using System.Linq;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：強化版地圖生成步驟。
/// 負責在地圖中心生成一個完整的祭壇遺跡佈局，包含守衛與環境美化。
/// </summary>
public class GenStep_UniqueAltar : GenStep
{
    public override int SeedPart => 135792468;

    public override void Generate(Map map, GenStepParams parms)
    {
        IntVec3 center = map.Center;
        ResolveParams rp = new ResolveParams();
        rp.rect = CellRect.CenteredOn(center, 25, 25);
        BaseGen.globalSettings.map = map;

        // 1. 生成遺跡佈局
        // A. 基礎地板 (大型圓形或矩形)
        rp.floorDef = TerrainDefOf.TileGranite;
        BaseGen.symbolStack.Push("floor", rp);

        // B. 四周的斷垣殘壁
        ResolveParams wallRp = rp;
        wallRp.wallStuff = ThingDefOf.BlocksGranite;
        wallRp.chanceToSkipWallBlock = 0.4f; // 讓牆壁看起來破損
        BaseGen.symbolStack.Push("edgeWalls", wallRp);

        // C. 四角放置大型石柱
        foreach (IntVec3 corner in rp.rect.ContractedBy(3).Corners)
        {
            ResolveParams columnRp = rp;
            columnRp.rect = CellRect.SingleCell(corner);
            columnRp.singleThingDef = ThingDefOf.Column;
            columnRp.stuff = ThingDefOf.BlocksGranite;
            BaseGen.symbolStack.Push("thing", columnRp);
        }

        // D. 放置核心祭壇 (隨機選擇一種類型)
        ResolveParams altarRp = rp;
        altarRp.rect = CellRect.CenteredOn(center, 3, 3);
        altarRp.singleThingDef = Rand.Bool ? ThingDef.Named("MyMod_Altar_Healing") : ThingDef.Named("MyMod_Altar_Destruction");
        BaseGen.symbolStack.Push("thing", altarRp);

        // 執行基礎生成
        BaseGen.Generate();

        // 2. 環境裝飾：在祭壇周圍生成靈能植物
        for (int i = 0; i < 20; i++)
        {
            IntVec3 cell = rp.rect.RandomCell;
            if (cell.Standable(map) && !cell.GetThingList(map).Any())
            {
                GenSpawn.Spawn(ThingDef.Named("MyMod_PsychicPlant"), cell, map);
            }
        }

        // 3. 放置守衛：休眠的無人機兵
        Faction mechFaction = Faction.OfMechanoids;
        for (int i = 0; i < 3; i++)
        {
            IntVec3 spawnCell = rp.rect.EdgeCells.RandomElement();
            Pawn mech = PawnGenerator.GeneratePawn(PawnKindDefOf.Mech_Scyther, mechFaction);
            GenSpawn.Spawn(mech, spawnCell, map);
            
            // 設為休眠狀態 (使用原版的自衛邏輯)
            mech.mindState.duty = new PawnDuty(DutyDefOf.DefendBase, center, 10f);
        }

        // 4. 清理周圍
        foreach (IntVec3 cell in rp.rect)
        {
            map.roofGrid.SetRoof(cell, null);
            foreach (Thing t in cell.GetThingList(map).ToArray())
            {
                if (t.def.category == ThingCategory.Plant && t.def.defName != "MyMod_PsychicPlant") t.Destroy();
            }
        }
    }
}
