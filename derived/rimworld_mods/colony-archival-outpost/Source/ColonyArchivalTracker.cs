using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ColonyArchivalOutpost
{
    // 掛在每張地圖上(MapComponent 子類由遊戲自動實例化)。記錄採樣窗的期初狀態。
    public class ColonyArchivalTracker : MapComponent
    {
        public bool isSampling;
        public int startTick = -1;
        public Dictionary<ThingDef, int> startCounts = new Dictionary<ThingDef, int>();

        public ColonyArchivalTracker(Map map) : base(map) { }

        public void BeginSampling()
        {
            isSampling = true;
            startTick = Find.TickManager.TicksGame;
            // copy 一份期初庫存快照(AllCountedAmounts 是活字典，必須複製)
            startCounts = new Dictionary<ThingDef, int>(map.resourceCounter.AllCountedAmounts);
        }

        public void Reset()
        {
            isSampling = false;
            startTick = -1;
            startCounts = new Dictionary<ThingDef, int>();
        }

        public override void ExposeData()
        {
            base.ExposeData();
            Scribe_Values.Look(ref isSampling, "caoIsSampling", false);
            Scribe_Values.Look(ref startTick, "caoStartTick", -1);
            Scribe_Collections.Look(ref startCounts, "caoStartCounts", LookMode.Def, LookMode.Value);
            if (Scribe.mode == LoadSaveMode.PostLoadInit && startCounts == null)
                startCounts = new Dictionary<ThingDef, int>();
        }
    }
}
