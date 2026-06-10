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
    [HarmonyPatch(typeof(Outpost), "GetGizmos")]
    public static class Patch_Outpost_GetGizmos
    {
        static IEnumerable<Gizmo> Postfix(IEnumerable<Gizmo> __result, Outpost __instance)
        {
            foreach (var g in __result)
                yield return g;

            var rec = WorldComponent_OutpostUpgrades.Instance?.GetOrCreate(__instance);
            if (rec == null) yield break;

            yield return BuildProductionGizmo(__instance, rec);

            if (__instance is Outpost_Artillery art)
            {
                yield return BuildAmmoCapGizmo(art, rec);
                yield return BuildAmmoRateGizmo(art, rec);
                yield return BuildRangeGizmo(art, rec);
                yield return BuildRestockGizmo(art, rec);
            }
        }

        // ── 產量升級（白銀，哨站倉庫）──────────────────────────────
        private static Command_Action BuildProductionGizmo(Outpost outpost, OutpostUpgradeRecord rec)
        {
            int   cost      = UpgradeService.ProdSilverCost;
            bool  canAfford = UpgradeService.CanAfford(outpost, ThingDefOf.Silver, cost);
            float cur       = UpgradeService.ProdMultiplierForLevel(rec.productionLevel);
            float next      = UpgradeService.ProdMultiplierForLevel(rec.productionLevel + 1);

            return new Command_Action
            {
                defaultLabel   = "VOEE.Gizmo.Prod.Label".Translate(rec.productionLevel),
                defaultDesc    = "VOEE.Gizmo.Prod.Desc".Translate(
                                     $"\xd7{cur:F2}", $"\xd7{next:F2}",
                                     cost, ThingDefOf.Silver.LabelCap),
                icon           = ThingDefOf.Silver.uiIcon,
                iconDrawScale  = 0.85f,
                Disabled       = !canAfford,
                disabledReason = "VOEE.CantAfford".Translate(cost, ThingDefOf.Silver.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(outpost, ThingDefOf.Silver, cost))
                    {
                        Messages.Message("VOEE.CantAfford".Translate(cost, ThingDefOf.Silver.LabelCap),
                            MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    rec.productionLevel++;
                    Messages.Message("VOEE.Upgraded".Translate(
                        "VOEE.Gizmo.Prod.Name".Translate(), rec.productionLevel,
                        $"\xd7{UpgradeService.ProdMultiplierForLevel(rec.productionLevel):F2}"),
                        outpost, MessageTypeDefOf.PositiveEvent, false);
                }
            };
        }

        // ── 彈藥容量升級（鋼鐵，哨站倉庫）────────────────────────
        private static Command_Action BuildAmmoCapGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            int  cost      = UpgradeService.AmmoCapSteelCost;
            bool canAfford = UpgradeService.CanAfford(art, ThingDefOf.Steel, cost);
            int  cur       = UpgradeService.GetMaxAmmo(rec);
            int  next      = cur + 20;

            return new Command_Action
            {
                defaultLabel   = "VOEE.Gizmo.AmmoC.Label".Translate(rec.artAmmoCapLevel),
                defaultDesc    = "VOEE.Gizmo.AmmoC.Desc".Translate(
                                     cur, next, cost, ThingDefOf.Steel.LabelCap),
                icon           = ThingDefOf.Steel.uiIcon,
                iconDrawScale  = 0.85f,
                Disabled       = !canAfford,
                disabledReason = "VOEE.CantAfford".Translate(cost, ThingDefOf.Steel.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(art, ThingDefOf.Steel, cost))
                    {
                        Messages.Message("VOEE.CantAfford".Translate(cost, ThingDefOf.Steel.LabelCap),
                            MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    rec.artAmmoCapLevel++;
                    Messages.Message("VOEE.Upgraded".Translate(
                        "VOEE.Gizmo.AmmoC.Name".Translate(), rec.artAmmoCapLevel,
                        UpgradeService.GetMaxAmmo(rec) + " shells"),
                        art, MessageTypeDefOf.PositiveEvent, false);
                }
            };
        }

        // ── 蓄積速度升級（零件，哨站倉庫）────────────────────────
        private static Command_Action BuildAmmoRateGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            int   cost      = UpgradeService.AmmoRateCompCost;
            bool  canAfford = UpgradeService.CanAfford(art, ThingDefOf.ComponentIndustrial, cost);
            float cur       = UpgradeService.GetAmmoRate(rec);
            float next      = cur + 6f;

            return new Command_Action
            {
                defaultLabel   = "VOEE.Gizmo.AmmoR.Label".Translate(rec.artAmmoRateLevel),
                defaultDesc    = "VOEE.Gizmo.AmmoR.Desc".Translate(
                                     cur, next, cost, ThingDefOf.ComponentIndustrial.LabelCap),
                icon           = ThingDefOf.ComponentIndustrial.uiIcon,
                iconDrawScale  = 0.85f,
                Disabled       = !canAfford,
                disabledReason = "VOEE.CantAfford".Translate(cost, ThingDefOf.ComponentIndustrial.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(art, ThingDefOf.ComponentIndustrial, cost))
                    {
                        Messages.Message("VOEE.CantAfford".Translate(cost, ThingDefOf.ComponentIndustrial.LabelCap),
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

        // ── 射程升級（鋼鐵 + 零件，哨站倉庫）────────────────────
        private static Command_Action BuildRangeGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            int  ns        = UpgradeService.RangeSteelCost;
            int  nc        = UpgradeService.RangeCompCost;
            bool canAfford = UpgradeService.CanAfford(art, ThingDefOf.Steel, ns)
                          && UpgradeService.CanAfford(art, ThingDefOf.ComponentIndustrial, nc);
            string costStr = nc > 0
                ? $"{ns} {ThingDefOf.Steel.LabelCap} + {nc} {ThingDefOf.ComponentIndustrial.LabelCap}"
                : $"{ns} {ThingDefOf.Steel.LabelCap}";
            int curBonus  = UpgradeService.GetRangeBonus(rec);
            int nextBonus = curBonus + 3;

            return new Command_Action
            {
                defaultLabel   = "VOEE.Gizmo.Range.Label".Translate(rec.artRangeLevel),
                defaultDesc    = "VOEE.Gizmo.Range.Desc".Translate(curBonus, nextBonus, costStr),
                icon           = ThingDefOf.Steel.uiIcon,
                iconDrawScale  = 0.70f,
                Disabled       = !canAfford,
                disabledReason = "VOEE.CantAfford2".Translate(costStr),
                action = () =>
                {
                    if (!UpgradeService.CanAfford(art, ThingDefOf.Steel, ns) ||
                        !UpgradeService.CanAfford(art, ThingDefOf.ComponentIndustrial, nc))
                    {
                        Messages.Message("VOEE.CantAfford2".Translate(costStr),
                            MessageTypeDefOf.RejectInput, false);
                        return;
                    }
                    UpgradeService.TryConsume(art, ThingDefOf.Steel, ns);
                    UpgradeService.TryConsume(art, ThingDefOf.ComponentIndustrial, nc);
                    rec.artRangeLevel++;
                    Messages.Message("VOEE.Upgraded".Translate(
                        "VOEE.Gizmo.Range.Name".Translate(), rec.artRangeLevel,
                        "+" + UpgradeService.GetRangeBonus(rec)),
                        art, MessageTypeDefOf.PositiveEvent, false);
                }
            };
        }

        // ── 即時補給（鋼鐵，哨站倉庫）────────────────────────────
        private static Command_Action BuildRestockGizmo(Outpost_Artillery art, OutpostUpgradeRecord rec)
        {
            int   max       = UpgradeService.GetMaxAmmo(rec);
            int   cur       = (int)rec.ammoStockpile;
            int   space     = max - cur;
            int   toAdd     = Math.Min(UpgradeService.AmmoBuyBatchSize, space);
            int   cost      = toAdd * UpgradeService.AmmoBuyCostPerShell;
            bool  canAfford = toAdd > 0 && UpgradeService.CanAfford(art, ThingDefOf.Steel, cost);

            return new Command_Action
            {
                defaultLabel   = "VOEE.Gizmo.Restock.Label".Translate(toAdd, cost),
                defaultDesc    = "VOEE.Gizmo.Restock.Desc".Translate(toAdd, cur, max),
                icon           = DefDatabase<ThingDef>.GetNamedSilentFail("Shell_HighExplosive")?.uiIcon
                                 ?? ThingDefOf.Steel.uiIcon,
                iconDrawScale  = 0.85f,
                Disabled       = space <= 0 || !canAfford,
                disabledReason = space <= 0
                    ? "VOEE.Artillery.AmmoFull".Translate()
                    : "VOEE.CantAfford".Translate(cost, ThingDefOf.Steel.LabelCap),
                action = () =>
                {
                    if (!UpgradeService.TryConsume(art, ThingDefOf.Steel, cost))
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
