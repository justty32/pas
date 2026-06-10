using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using HarmonyLib;
using Outposts;
using RimWorld.Planet;
using UnityEngine;
using Verse;
using VOE;

namespace VOEOutpostEnhancement
{
    internal class StrikeShellInfo
    {
        public int shellType;
    }

    // ── TravellingArtilleryStrike.Fire：調整 pawns 數量並記錄砲彈種類 ──
    [HarmonyPatch(typeof(TravellingArtilleryStrike), "Fire",
        new System.Type[] { typeof(Outpost), typeof(GlobalTargetInfo) })]
    public static class Patch_Strike_Fire
    {
        internal static readonly ConditionalWeakTable<TravellingArtilleryStrike, StrikeShellInfo>
            ShellTypes = new ConditionalWeakTable<TravellingArtilleryStrike, StrikeShellInfo>();

        static void Postfix(TravellingArtilleryStrike __instance)
        {
            var pawnsField = AccessTools.Field(typeof(TravellingArtilleryStrike), "pawns");
            var pawns = (List<Pawn>)pawnsField.GetValue(__instance);
            if (pawns == null || pawns.Count == 0) return;

            int wantedCount = System.Math.Max(1, ArtilleryFireState.PendingCount);
            int originalCount = pawns.Count;

            // 不足時循環補位（每位人員可連射多發）
            while (pawns.Count < wantedCount)
                pawns.Add(pawns[pawns.Count % originalCount]);
            // 過多時裁切
            while (pawns.Count > wantedCount)
                pawns.RemoveAt(pawns.Count - 1);

            // 同步 numShots 標籤
            var numShotsField = AccessTools.Field(typeof(TravellingArtilleryStrike), "numShots");
            numShotsField?.SetValue(__instance, wantedCount);

            // 記錄砲彈種類
            ShellTypes.Add(__instance, new StrikeShellInfo
            {
                shellType = Mathf.Clamp(ArtilleryFireState.PendingShellType, 0, 3)
            });
        }
    }

    // ── TravellingArtilleryStrike.Arrived：以選擇的砲彈取代 HighExplosive ──
    [HarmonyPatch(typeof(TravellingArtilleryStrike), "Arrived")]
    public static class Patch_Strike_Arrived
    {
        static IEnumerable<CodeInstruction> Transpiler(IEnumerable<CodeInstruction> instructions)
        {
            var helper = typeof(Patch_Strike_Arrived).GetMethod(
                nameof(GetShellDefName), BindingFlags.NonPublic | BindingFlags.Static);
            bool found = false;

            foreach (var code in instructions)
            {
                if (!found && code.opcode == OpCodes.Ldstr &&
                    (string)code.operand == "Bullet_Shell_HighExplosive")
                {
                    found = true;
                    yield return new CodeInstruction(OpCodes.Ldarg_0); // push this
                    yield return new CodeInstruction(OpCodes.Call, helper);
                    continue; // drop original ldstr
                }
                yield return code;
            }

            if (!found)
                Log.Warning("[VOEE] Transpiler: ldstr 'Bullet_Shell_HighExplosive' not found in Arrived()");
        }

        private static string GetShellDefName(TravellingArtilleryStrike strike)
        {
            if (Patch_Strike_Fire.ShellTypes.TryGetValue(strike, out var info))
                return UpgradeService.ShellProjectile[Mathf.Clamp(info.shellType, 0, 3)];
            return "Bullet_Shell_HighExplosive";
        }
    }
}
