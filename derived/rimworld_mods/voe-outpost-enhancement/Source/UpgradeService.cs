using System;
using System.Linq;
using RimWorld;
using UnityEngine;
using Verse;

namespace VOEOutpostEnhancement
{
    public static class UpgradeService
    {
        public const int MaxLevel = 3;

        // ── 所有哨站：產量倍率 ─────────────────
        // 費用：白銀
        public static readonly int[]   ProdSilverCost = { 0, 200, 600, 1800 };
        public static readonly float[] ProdMultiplier = { 1f, 1.25f, 1.60f, 2.20f };

        // ── 火炮：彈藥容量 ────────────────────
        // 費用：鋼鐵
        public static readonly int[] AmmoCapLevels   = { 20, 40, 60, 80 };
        public static readonly int[] AmmoCapSteelCost = { 0, 200, 400, 700 };

        // ── 火炮：蓄積速度（發/人/天）────────
        // 費用：工業零件
        // 2 人基礎 12/天 → 24/天，默認上限 20 → ~20 小時滿；每隔約 1 小時跳一格
        public static readonly float[] AmmoRateLevels   = { 12f, 18f, 24f, 36f };
        public static readonly int[]   AmmoRateCompCost = { 0, 20, 50, 100 };

        // ── 火炮：射程 ────────────────────────
        // 費用：鋼鐵 + 工業零件
        public static readonly int[] RangeSteelCost = { 0, 150, 200, 300 };
        public static readonly int[] RangeCompCost  = { 0, 0, 20, 40 };
        public static readonly int[] RangeBonus     = { 0, 3, 6, 9 };

        // ── 火炮：即時補給 ───────────────────
        // 每發鋼鐵費用
        public const int AmmoBuyCostPerShell = 8;
        // 每次補給量
        public const int AmmoBuyBatchSize = 5;

        // ── 砲彈種類（免費循環選擇） ─────────
        public static readonly string[] ShellProjectile =
        {
            "Bullet_Shell_HighExplosive",
            "Bullet_Shell_Incendiary",
            "Bullet_Shell_EMP",
            "Bullet_Shell_Firefoam",
        };
        public static readonly string[] ShellItemDef =
        {
            "Shell_HighExplosive",
            "Shell_Incendiary",
            "Shell_EMP",
            "Shell_Firefoam",
        };
        public static readonly string[] ShellLabelKey =
        {
            "VOEE.Shell.HE",
            "VOEE.Shell.Incendiary",
            "VOEE.Shell.EMP",
            "VOEE.Shell.Firefoam",
        };

        // ── 輔助函式 ─────────────────────────
        public static int GetMaxAmmo(OutpostUpgradeRecord rec) =>
            AmmoCapLevels[Mathf.Clamp(rec.artAmmoCapLevel, 0, MaxLevel)];

        public static float GetAmmoRate(OutpostUpgradeRecord rec) =>
            AmmoRateLevels[Mathf.Clamp(rec.artAmmoRateLevel, 0, MaxLevel)];

        public static bool CanAfford(ThingDef def, int count)
        {
            if (count <= 0 || def == null || Find.Maps == null) return true;
            return Find.Maps.Where(m => m.IsPlayerHome)
                       .Sum(m => m.resourceCounter.GetCount(def)) >= count;
        }

        public static bool TryConsume(ThingDef def, int count)
        {
            if (count <= 0 || def == null) return true;
            if (!CanAfford(def, count)) return false;
            int remaining = count;
            foreach (var map in Find.Maps.Where(m => m.IsPlayerHome))
            {
                if (remaining <= 0) break;
                foreach (var t in map.listerThings.ThingsOfDef(def)
                             .Where(t => t.Spawned && !t.Destroyed).ToList())
                {
                    if (remaining <= 0) break;
                    int take = Math.Min(remaining, t.stackCount);
                    if (take >= t.stackCount)
                        t.Destroy(DestroyMode.Vanish);
                    else
                        t.stackCount -= take;
                    remaining -= take;
                }
            }
            return true;
        }
    }
}
