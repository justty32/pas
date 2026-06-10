using System;
using System.Collections.Generic;
using HarmonyLib;
using Outposts;
using RimWorld;
using RimWorld.Planet;
using UnityEngine;
using Verse;
using VOE;

namespace VOEOutpostEnhancement
{
    // 靜態狀態：攔截 Fire() 後向 Strike Postfix 傳遞玩家選擇
    public static class ArtilleryFireState
    {
        public static bool SkipNextIntercept;
        public static int PendingShellType;
        public static int PendingCount;
    }

    // ── GetGizmos：強制以彈藥量控制發射按鈕（取代原 cooldown 邏輯） ──
    [HarmonyPatch(typeof(Outpost_Artillery), "GetGizmos")]
    public static class Patch_Artillery_GetGizmos
    {
        static IEnumerable<Gizmo> Postfix(IEnumerable<Gizmo> __result, Outpost_Artillery __instance)
        {
            var rec = WorldComponent_OutpostUpgrades.Instance?.GetOrCreate(__instance);
            int avail = rec != null ? (int)rec.ammoStockpile : 0;
            int maxAmmo = rec != null ? UpgradeService.GetMaxAmmo(rec) : 20;
            string fireLabel = "Outposts.Commands.Fire.Label".Translate();

            foreach (var g in __result)
            {
                if (g is Command_Action cmd && cmd.defaultLabel == fireLabel)
                {
                    cmd.Disabled = avail < 1;
                    cmd.disabledReason = avail < 1
                        ? "VOEE.Artillery.NoAmmo".Translate(avail, maxAmmo)
                        : null;
                }
                yield return g;
            }
        }
    }

    // ── GetInspectString：追加彈藥資訊 ──
    [HarmonyPatch(typeof(Outpost_Artillery), "GetInspectString")]
    public static class Patch_Artillery_GetInspectString
    {
        static void Postfix(ref string __result, Outpost_Artillery __instance)
        {
            var rec = WorldComponent_OutpostUpgrades.Instance?.GetOrCreate(__instance);
            if (rec == null) return;
            int cur = (int)rec.ammoStockpile;
            int max = UpgradeService.GetMaxAmmo(rec);
            string shellLabel = UpgradeService.ShellLabelKey[
                Mathf.Clamp(rec.artShellType, 0, UpgradeService.ShellLabelKey.Length - 1)].Translate();
            __result += "\n" + "VOEE.Artillery.InspectAmmo".Translate(cur, max, shellLabel);
        }
    }

    // ── Fire：Prefix 攔截顯示對話框；Postfix 清除 cooldown ──
    [HarmonyPatch(typeof(Outpost_Artillery), "Fire")]
    public static class Patch_Artillery_Fire
    {
        private static bool _shouldClearCooldown;

        static bool Prefix(Outpost_Artillery __instance, GlobalTargetInfo target)
        {
            if (ArtilleryFireState.SkipNextIntercept)
            {
                ArtilleryFireState.SkipNextIntercept = false;
                _shouldClearCooldown = true;
                return true;
            }

            _shouldClearCooldown = false;
            var rec = WorldComponent_OutpostUpgrades.Instance?.GetOrCreate(__instance);
            if (rec == null) return true;

            int avail = (int)rec.ammoStockpile;
            if (avail < 1)
            {
                Messages.Message("VOEE.Artillery.NoAmmo".Translate(avail, UpgradeService.GetMaxAmmo(rec)),
                    MessageTypeDefOf.RejectInput, false);
                return false;
            }

            Find.WindowStack.Add(new Dialog_ArtilleryFire(__instance, target, rec));
            return false;
        }

        static void Postfix(Outpost_Artillery __instance)
        {
            if (!_shouldClearCooldown) return;
            var f = AccessTools.Field(typeof(Outpost_Artillery), "cooldownTicksLeft");
            f?.SetValue(__instance, 0);
        }
    }
}
