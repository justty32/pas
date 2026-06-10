using System.Collections.Generic;
using RimWorld;
using Verse;

namespace ColonyArchivalOutpost
{
    // 採樣結果：資源每日有號淨流（N1–N5）+ 技能基礎 XP 速率（N7）。封存當下算好、隨 Outpost_Sampled 存檔。
    public class ProductivitySnapshot : IExposable
    {
        public Dictionary<ThingDef, float> dailyRates = new Dictionary<ThingDef, float>();

        // N4：per-pawn 縮放
        public bool perPawnScaling;
        public int basePawnCount = 1;

        // N7：技能採樣——每日平均基礎 XP 速率（已除以採樣 pawn 的 passion 倍率；套用時用 direct=true 讓 occupant passion 作用）
        public Dictionary<SkillDef, float> dailySkillXP = new Dictionary<SkillDef, float>();
        public bool applySkillXP; // 封存視窗開關

        public ProductivitySnapshot() { }

        public ProductivitySnapshot(Dictionary<ThingDef, float> rates)
        {
            dailyRates = rates ?? new Dictionary<ThingDef, float>();
        }

        public bool IsEmpty => (dailyRates == null || dailyRates.Count == 0)
                            && (dailySkillXP == null || dailySkillXP.Count == 0);

        public void ExposeData()
        {
            Scribe_Collections.Look(ref dailyRates, "dailyRates", LookMode.Def, LookMode.Value);
            Scribe_Values.Look(ref perPawnScaling, "perPawnScaling", false);
            Scribe_Values.Look(ref basePawnCount, "basePawnCount", 1);
            Scribe_Collections.Look(ref dailySkillXP, "dailySkillXP", LookMode.Def, LookMode.Value);
            Scribe_Values.Look(ref applySkillXP, "applySkillXP", false);
            if (Scribe.mode == LoadSaveMode.PostLoadInit)
            {
                if (dailyRates == null) dailyRates = new Dictionary<ThingDef, float>();
                if (dailySkillXP == null) dailySkillXP = new Dictionary<SkillDef, float>();
            }
        }
    }
}
