using System;
using System.Linq;
using Outposts;
using RimWorld;
using Verse;

namespace VOEOutpostEnhancement
{
    public static class UpgradeService
    {
        // ── 產量（無上限，每級 ×0.20 累加）────────────────────────
        public static float ProdMultiplierForLevel(int level) => 1f + level * 0.2f;
        public static int   ProdSilverCost => VOEE_Mod.Settings?.prodSilverPerLevel ?? 200;

        // ── 彈藥容量（無上限，每級 +20）────────────────────────────
        public static int   GetMaxAmmo(OutpostUpgradeRecord rec) => 20 + rec.artAmmoCapLevel * 20;
        public static int   AmmoCapSteelCost => VOEE_Mod.Settings?.ammoCapSteelPerLevel ?? 200;

        // ── 蓄積速度（無上限，每級 +6 發/人/天）────────────────────
        public static float GetAmmoRate(OutpostUpgradeRecord rec) => 12f + rec.artAmmoRateLevel * 6f;
        public static int   AmmoRateCompCost => VOEE_Mod.Settings?.ammoRateCompPerLevel ?? 20;

        // ── 射程（無上限，每級 +3）──────────────────────────────────
        public static int   GetRangeBonus(OutpostUpgradeRecord rec) => rec.artRangeLevel * 3;
        public static int   RangeSteelCost => VOEE_Mod.Settings?.rangeSteelPerLevel ?? 150;
        public static int   RangeCompCost  => VOEE_Mod.Settings?.rangeCompPerLevel  ?? 20;

        // ── 即時補給 ────────────────────────────────────────────────
        public static int   AmmoBuyCostPerShell => VOEE_Mod.Settings?.restockSteelPerShell ?? 8;
        public const  int   AmmoBuyBatchSize    = 5;

        // ── 砲彈種類 ────────────────────────────────────────────────
        public static readonly string[] ShellProjectile =
        {
            "Bullet_Shell_HighExplosive", "Bullet_Shell_Incendiary",
            "Bullet_Shell_EMP",           "Bullet_Shell_Firefoam",
        };
        public static readonly string[] ShellItemDef =
        {
            "Shell_HighExplosive", "Shell_Incendiary",
            "Shell_EMP",           "Shell_Firefoam",
        };
        public static readonly string[] ShellLabelKey =
        {
            "VOEE.Shell.HE", "VOEE.Shell.Incendiary",
            "VOEE.Shell.EMP", "VOEE.Shell.Firefoam",
        };

        // ── 費用查核／扣除（哨站倉庫）──────────────────────────────
        public static bool CanAfford(Outpost outpost, ThingDef def, int count)
        {
            if (count <= 0 || def == null) return true;
            int total = 0;
            foreach (var t in outpost.Things)
                if (t.def == def) total += t.stackCount;
            return total >= count;
        }

        public static bool TryConsume(Outpost outpost, ThingDef def, int count)
        {
            if (count <= 0 || def == null) return true;
            if (!CanAfford(outpost, def, count)) return false;
            int remaining = count;
            var held = outpost.Things;
            foreach (var t in held.ToList())
            {
                if (remaining <= 0) break;
                if (t.def != def) continue;
                int take = Math.Min(remaining, t.stackCount);
                if (take >= t.stackCount)
                    t.Destroy(DestroyMode.Vanish);
                else
                    t.stackCount -= take;
                remaining -= take;
            }
            return true;
        }
    }
}
