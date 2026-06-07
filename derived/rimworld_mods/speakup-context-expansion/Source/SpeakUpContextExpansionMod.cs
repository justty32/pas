using System.Reflection;
using HarmonyLib;
using Verse;

namespace SpeakUpContextExpansion
{
    /// <summary>
    /// Mod 入口：載入時建立自己的 Harmony id 並 PatchAll（套用本組件內所有 [HarmonyPatch]）。
    /// 仿 SpeakUp 入口 SpeakUp/Settings.cs:9（new Harmony("jpt.speakup").PatchAll()）。
    /// 本 mod 在 About.xml 以 loadAfter cn.speakup.ttyet 確保 SpeakUp 已就緒，
    /// 但 Harmony patch 的目標方法只需在「執行時」存在即可，載入順序不影響 patch 成功與否。
    /// </summary>
    public class SpeakUpContextExpansionMod : Mod
    {
        public SpeakUpContextExpansionMod(ModContentPack content) : base(content)
        {
            var harmony = new Harmony("pas.speakup.contextexpansion");
            harmony.PatchAll(Assembly.GetExecutingAssembly());
            Log.Message("[SpeakUpContextExpansion] Harmony patches applied (COLONY_DANGER / drafted / COLONY_FOOD_DAYS / COLONY_DAYS_SINCE_DEATH / pain).");
        }
    }
}
