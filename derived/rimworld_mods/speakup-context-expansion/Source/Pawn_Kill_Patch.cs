using System;
using HarmonyLib;
using Verse;

namespace SpeakUpContextExpansion
{
    /// <summary>
    /// Postfix Verse.Pawn.Kill：當死亡者是玩家殖民者時，把當前 tick 記到 ColonyDeathTracker。
    ///
    /// 簽章對照（已用 monodis 驗證於本機 Assembly-CSharp.dll）：
    ///   instance void Verse.Pawn::Kill(System.Nullable&lt;Verse.DamageInfo&gt; dinfo, [opt] Verse.Hediff exactCulprit)
    /// Postfix 不需要參數，只需 __instance（死亡的 Pawn）。用 Postfix 確保死亡流程已完成、IsColonist 仍可判讀。
    /// </summary>
    [HarmonyPatch(typeof(Pawn), nameof(Pawn.Kill))]
    public static class Pawn_Kill_Patch
    {
        public static void Postfix(Pawn __instance)
        {
            try
            {
                if (__instance == null) return;
                // IsColonist：自由的玩家殖民者（排除動物、敵人、囚犯、訪客）。
                if (!__instance.IsColonist) return;

                var tracker = ColonyDeathTracker.Current;
                if (tracker == null) return; // 例如剛讀入無此元件的舊存檔

                int tick = Find.TickManager?.TicksGame ?? 0;
                tracker.NotifyColonistDied(tick);
            }
            catch (Exception e)
            {
                // 對話/情境變數不是關鍵路徑，任何例外都不該打斷遊戲死亡流程。
                Log.Warning($"[SpeakUpContextExpansion] Pawn_Kill_Patch error: {e.Message}");
            }
        }
    }
}
