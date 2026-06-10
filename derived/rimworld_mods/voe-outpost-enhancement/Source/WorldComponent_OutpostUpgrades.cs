using System;
using System.Collections.Generic;
using System.Linq;
using Outposts;
using RimWorld;
using RimWorld.Planet;
using UnityEngine;
using Verse;
using VOE;

namespace VOEOutpostEnhancement
{
    public class OutpostUpgradeRecord : IExposable
    {
        public int productionLevel;    // 0-3：產量倍率（所有哨站）
        public int artAmmoCapLevel;    // 0-3：彈藥容量（僅火炮）
        public int artAmmoRateLevel;   // 0-3：蓄積速度（僅火炮）
        public int artRangeLevel;      // 0-3：射程（僅火炮）
        public int artShellType;       // 0-3：上次使用砲彈種類
        public float ammoStockpile;    // 目前彈藥量（float 連續蓄積）
        public int artLastSliderCount; // 上次發射數量（滑桿記憶）

        public void ExposeData()
        {
            Scribe_Values.Look(ref productionLevel, "prod", 0);
            Scribe_Values.Look(ref artAmmoCapLevel, "artCap", 0);
            Scribe_Values.Look(ref artAmmoRateLevel, "artRate", 0);
            Scribe_Values.Look(ref artRangeLevel, "artRange", 0);
            Scribe_Values.Look(ref artShellType, "artShell", 0);
            Scribe_Values.Look(ref ammoStockpile, "artAmmo", 0f);
            Scribe_Values.Look(ref artLastSliderCount, "artSlider", 1);
        }
    }

    public class WorldComponent_OutpostUpgrades : WorldComponent
    {
        public static WorldComponent_OutpostUpgrades Instance;

        private Dictionary<string, OutpostUpgradeRecord> records =
            new Dictionary<string, OutpostUpgradeRecord>();

        public WorldComponent_OutpostUpgrades(World world) : base(world)
        {
            Instance = this;
        }

        public OutpostUpgradeRecord GetOrCreate(WorldObject obj)
        {
            if (obj == null) return null;
            var key = obj.GetUniqueLoadID();
            if (!records.TryGetValue(key, out var rec))
                records[key] = rec = new OutpostUpgradeRecord();
            return rec;
        }

        // 每 250 tick 蓄積一次（約 0.1 遊戲小時），讓整數在每 1-2 小時跳一格
        public override void WorldComponentTick()
        {
            if (Find.TickManager.TicksGame % 250 != 0) return;
            float dt = 250f / 60000f; // fraction of day

            foreach (var outpost in Find.WorldObjects.AllWorldObjects.OfType<Outpost_Artillery>())
            {
                if (outpost.Faction != Faction.OfPlayer) continue;
                var rec = GetOrCreate(outpost);
                int max = UpgradeService.GetMaxAmmo(rec);
                if (rec.ammoStockpile >= max) continue;

                float rate = UpgradeService.GetAmmoRate(rec) * outpost.CapablePawns.Count();
                rec.ammoStockpile = Math.Min(max, rec.ammoStockpile + rate * dt);
            }
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Collections.Look(ref records, "voeeRecords", LookMode.Value, LookMode.Deep);
            if (Scribe.mode == LoadSaveMode.PostLoadInit)
            {
                if (records == null) records = new Dictionary<string, OutpostUpgradeRecord>();
                Instance = this; // 存檔載入後重建靜態引用
            }
        }
    }
}
