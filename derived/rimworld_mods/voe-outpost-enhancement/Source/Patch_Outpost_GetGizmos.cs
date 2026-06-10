using System;
using System.Collections.Generic;
using HarmonyLib;
using Outposts;
using RimWorld;
using UnityEngine;
using Verse;
using VOE;

namespace VOEOutpostEnhancement
{
    // 向所有 Outpost（基底類）注入升級 gizmo。
    // Harmony IEnumerable 後綴：自動以迭代器包裝，將我們的 gizmo 追加在原始列舉之後。
    [HarmonyPatch(typeof(Outpost), "GetGizmos")]
    public static class Patch_Outpost_GetGizmos
    {
        static IEnumerable<Gizmo> Postfix(IEnumerable<Gizmo> __result, Outpost __instance)
        {
            foreach (var g in __result)
                yield return g;

            var rec = WorldComponent_OutpostUpgrades.Instance?.GetOrCreate(__instance);
            if (rec == null) yield break;

            // ── 所有哨站：產量升級 ──
            yield return BuildProductionGizmo(__instance, rec);

            // ── 火炮哨站專屬 ──
            if (__instance is Outpost_Artillery art)
            {
                yield return BuildAmmoCapGizmo(art, rec);
                yield return BuildAmmoRateGizmo(art, rec);
                yield return BuildRangeGizmo(art, rec);
                yield return BuildRestockGizmo(art, rec);
            }
        }

        // ──────────────────────────────────────────────────────────────
        // 產量升級（白銀）
        // ──────────────────────────────────────────────────────────────
        private static Command_Action BuildProductionGizmo(Outpost outpost, OutpostUpgradeRecord rec)
        {
            bool maxed = rec.productionLevel >= UpgradeService.MaxLevel;
            int nextCost = maxed ? 0 : UpgradeService.ProdSilverCost[rec.productionLevel + 1];
            bool canAfford = !maxed && UpgradeService.CanAfford(ThingDefOf.Silver, nextCost);
            float cur = UpgradeService.ProdMultiplier[rec.productionLevel];

            return new Command_Action
            {
                defaultLabel = "VOEE.Gizmo.Prod.Label".Translate(rec.productionLevel, UpgradeService.MaxLevel),
                defaultDesc  = maxed
                    ? "VOEE.Gizmo.Prod.DescMax".Translate($"\xd7{cur:F2}")
                    : "VOEE.Gizmo.Prod.Desc".Translate(
                        $"\xd7{cur:F2}",
                        $"\xd7{UpgradeService.ProdMultiplier[rec.productionLevel + 1]:F2}",
                        nextCost, ThingDefOf.Silver.LabelCap),
                icon          = ThingDefOf.Silver.uiIcon,
                iconDrawScale = 0.85f,
                Disabled      = maxed || !canAfford,
                disabledReason = maxed
                    ? "VOEE.MaxLevel".Translate()
                    : "VOEE.CantAfford".Translate(nextCost, ThingDefOf.Silver.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(ThingDefOf.Silver, nextCost))
                    {
                        Messages.Message("VOEE.CantAfford".Translate(nextCost, ThingDefOf.Silver.LabelCap),
                            MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    rec.productionLevel++;
                    Messages.Message("VOEE.Upgraded".Translate(
                        "VOEE.Gizmo.Prod.Name".Translate(), rec.productionLevel,
                        $"\xd7{UpgradeService.ProdMultiplier[rec.productionLevel]:F2}"),
                        outpost, MessageTypeDefOf.PositiveEvent, false);
                }
            };
        }

        // ──────────────────────────────────────────────────────────────
        // 彈藥容量升級（鋼鐵）
        // ──────────────────────────────────────────────────────────────
        private static Command_Action BuildAmmoCapGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            bool maxed = rec.artAmmoCapLevel >= UpgradeService.MaxLevel;
            int nextCost = maxed ? 0 : UpgradeService.AmmoCapSteelCost[rec.artAmmoCapLevel + 1];
            bool canAfford = !maxed && UpgradeService.CanAfford(ThingDefOf.Steel, nextCost);

            return new Command_Action
            {
                defaultLabel = "VOEE.Gizmo.AmmoC.Label".Translate(rec.artAmmoCapLevel, UpgradeService.MaxLevel),
                defaultDesc  = maxed
                    ? "VOEE.Gizmo.AmmoC.DescMax".Translate(UpgradeService.GetMaxAmmo(rec))
                    : "VOEE.Gizmo.AmmoC.Desc".Translate(
                        UpgradeService.GetMaxAmmo(rec),
                        UpgradeService.AmmoCapLevels[rec.artAmmoCapLevel + 1],
                        nextCost, ThingDefOf.Steel.LabelCap),
                icon          = ThingDefOf.Steel.uiIcon,
                iconDrawScale = 0.85f,
                Disabled      = maxed || !canAfford,
                disabledReason = maxed
                    ? "VOEE.MaxLevel".Translate()
                    : "VOEE.CantAfford".Translate(nextCost, ThingDefOf.Steel.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(ThingDefOf.Steel, nextCost))
                    {
                        Messages.Message("VOEE.CantAfford".Translate(nextCost, ThingDefOf.Steel.LabelCap),
                            MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    rec.artAmmoCapLevel++;
                    Messages.Message("VOEE.Upgraded".Translate(
                        "VOEE.Gizmo.AmmoC.Name".Translate(), rec.artAmmoCapLevel,
                        UpgradeService.GetMaxAmmo(rec) + " shell cap"),
                        art, MessageTypeDefOf.PositiveEvent, false);
                }
            };
        }

        // ──────────────────────────────────────────────────────────────
        // 蓄積速度升級（工業零件）
        // ──────────────────────────────────────────────────────────────
        private static Command_Action BuildAmmoRateGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            bool maxed = rec.artAmmoRateLevel >= UpgradeService.MaxLevel;
            int nextCost = maxed ? 0 : UpgradeService.AmmoRateCompCost[rec.artAmmoRateLevel + 1];
            bool canAfford = !maxed && UpgradeService.CanAfford(ThingDefOf.ComponentIndustrial, nextCost);
            float curRate = UpgradeService.GetAmmoRate(rec);

            return new Command_Action
            {
                defaultLabel = "VOEE.Gizmo.AmmoR.Label".Translate(rec.artAmmoRateLevel, UpgradeService.MaxLevel),
                defaultDesc  = maxed
                    ? "VOEE.Gizmo.AmmoR.DescMax".Translate(curRate)
                    : "VOEE.Gizmo.AmmoR.Desc".Translate(
                        curRate,
                        UpgradeService.AmmoRateLevels[rec.artAmmoRateLevel + 1],
                        nextCost, ThingDefOf.ComponentIndustrial.LabelCap),
                icon          = ThingDefOf.ComponentIndustrial.uiIcon,
                iconDrawScale = 0.85f,
                Disabled      = maxed || !canAfford,
                disabledReason = maxed
                    ? "VOEE.MaxLevel".Translate()
                    : "VOEE.CantAfford".Translate(nextCost, ThingDefOf.ComponentIndustrial.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(ThingDefOf.ComponentIndustrial, nextCost))
                    {
                        Messages.Message("VOEE.CantAfford".Translate(nextCost, ThingDefOf.ComponentIndustrial.LabelCap),
                            MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    rec.artAmmoRateLevel++;
                    Messages.Message("VOEE.Upgraded".Translate(
                        "VOEE.Gizmo.AmmoR.Name".Translate(), rec.artAmmoRateLevel,
                        UpgradeService.GetAmmoRate(rec)),
                        art, MessageTypeDefOf.PositiveEvent, false);
                }
            };
        }

        // ──────────────────────────────────────────────────────────────
        // 射程升級（鋼鐵 + 工業零件）
        // ──────────────────────────────────────────────────────────────
        private static Command_Action BuildRangeGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            bool maxed = rec.artRangeLevel >= UpgradeService.MaxLevel;
            int ns = maxed ? 0 : UpgradeService.RangeSteelCost[rec.artRangeLevel + 1];
            int nc = maxed ? 0 : UpgradeService.RangeCompCost[rec.artRangeLevel + 1];
            bool canAfford = !maxed
                && UpgradeService.CanAfford(ThingDefOf.Steel, ns)
                && UpgradeService.CanAfford(ThingDefOf.ComponentIndustrial, nc);
            string costStr = nc > 0
                ? $"{ns} {ThingDefOf.Steel.LabelCap} + {nc} {ThingDefOf.ComponentIndustrial.LabelCap}"
                : $"{ns} {ThingDefOf.Steel.LabelCap}";

            return new Command_Action
            {
                defaultLabel = "VOEE.Gizmo.Range.Label".Translate(rec.artRangeLevel, UpgradeService.MaxLevel),
                defaultDesc  = maxed
                    ? "VOEE.Gizmo.Range.DescMax".Translate(UpgradeService.RangeBonus[rec.artRangeLevel])
                    : "VOEE.Gizmo.Range.Desc".Translate(
                        UpgradeService.RangeBonus[rec.artRangeLevel],
                        UpgradeService.RangeBonus[rec.artRangeLevel + 1],
                        costStr),
                icon          = ThingDefOf.Steel.uiIcon,
                iconDrawScale = 0.70f,
                Disabled      = maxed || !canAfford,
                disabledReason = maxed
                    ? "VOEE.MaxLevel".Translate()
                    : "VOEE.CantAfford2".Translate(costStr),
                action = () =>
                {
                    if (!UpgradeService.CanAfford(ThingDefOf.Steel, ns) ||
                        !UpgradeService.CanAfford(ThingDefOf.ComponentIndustrial, nc))
                    {
                        Messages.Message("VOEE.CantAfford2".Translate(costStr), MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    UpgradeService.TryConsume(ThingDefOf.Steel, ns);
                    UpgradeService.TryConsume(ThingDefOf.ComponentIndustrial, nc);
                    rec.artRangeLevel++;
                    Messages.Message("VOEE.Upgraded".Translate(
                        "VOEE.Gizmo.Range.Name".Translate(), rec.artRangeLevel,
                        "+" + UpgradeService.RangeBonus[rec.artRangeLevel]),
                        art, MessageTypeDefOf.PositiveEvent, false);
                }
            };
        }

        // ──────────────────────────────────────────────────────────────
        // 即時補給（鋼鐵 → 砲彈）
        // ──────────────────────────────────────────────────────────────
        private static Command_Action BuildRestockGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            int max   = UpgradeService.GetMaxAmmo(rec);
            int cur   = (int)rec.ammoStockpile;
            int space = max - cur;
            int toAdd = Math.Min(UpgradeService.AmmoBuyBatchSize, space);
            int cost  = toAdd * UpgradeService.AmmoBuyCostPerShell;
            bool canAfford = toAdd > 0 && UpgradeService.CanAfford(ThingDefOf.Steel, cost);

            return new Command_Action
            {
                defaultLabel = "VOEE.Gizmo.Restock.Label".Translate(toAdd, cost),
                defaultDesc  = "VOEE.Gizmo.Restock.Desc".Translate(toAdd, cur, max),
                icon          = DefDatabase<ThingDef>.GetNamedSilentFail("Shell_HighExplosive")?.uiIcon
                                ?? ThingDefOf.Steel.uiIcon,
                iconDrawScale = 0.85f,
                Disabled      = space <= 0 || !canAfford,
                disabledReason = space <= 0
                    ? "VOEE.Artillery.AmmoFull".Translate()
                    : "VOEE.CantAfford".Translate(cost, ThingDefOf.Steel.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(ThingDefOf.Steel, cost))
                    {
                        Messages.Message("VOEE.CantAfford".Translate(cost, ThingDefOf.Steel.LabelCap),
                            MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    rec.ammoStockpile = Math.Min(max, rec.ammoStockpile + toAdd);
                    Messages.Message("VOEE.Artillery.Restocked".Translate(toAdd),
                        art, MessageTypeDefOf.NeutralEvent, false);
                }
            };
        }
    }
}
