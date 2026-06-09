using System.Collections.Generic;
using HarmonyLib;
using RimWorld;
using RimWorld.Planet;
using Verse;

namespace ColonyArchivalOutpost
{
    // 在玩家家園 Settlement 的世界物件 gizmo 列加「開始採樣 / 封存成哨站」兩鈕。
    [HarmonyPatch(typeof(Settlement), nameof(Settlement.GetGizmos))]
    public static class Settlement_GetGizmos_Patch
    {
        public static IEnumerable<Gizmo> Postfix(IEnumerable<Gizmo> __result, Settlement __instance)
        {
            foreach (var g in __result)
                yield return g;

            if (__instance.Faction != Faction.OfPlayer)
                yield break;
            Map map = __instance.Map;
            if (map == null || !map.IsPlayerHome)
                yield break;
            var tracker = map.GetComponent<ColonyArchivalTracker>();
            if (tracker == null)
                yield break;

            if (!tracker.isSampling)
            {
                yield return new Command_Action
                {
                    defaultLabel = "CAO.BeginSampling".Translate(),
                    defaultDesc = "CAO.BeginSampling.Desc".Translate(),
                    icon = TexCommand.ForbidOff,
                    action = () => tracker.BeginSampling()
                };
            }
            else
            {
                var cmd = new Command_Action
                {
                    defaultLabel = "CAO.Archive".Translate(),
                    defaultDesc = "CAO.Archive.Desc".Translate(),
                    icon = TexCommand.ClearPrioritizedWork,
                    action = () => ArchivalService.Archive(map)
                };
                if (!ArchivalService.CanArchive(map, out string reason))
                    cmd.Disable(reason);
                yield return cmd;
            }
        }
    }
}
