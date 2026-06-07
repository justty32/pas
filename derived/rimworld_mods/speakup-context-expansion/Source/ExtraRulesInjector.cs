using System;
using System.Collections.Generic;
using HarmonyLib;
using RimWorld;
using SpeakUp;            // DialogManager
using Verse;
using Verse.Grammar;     // Rule, Rule_String

namespace SpeakUpContextExpansion
{
    /// <summary>
    /// 核心注入點：Postfix SpeakUp.ExtraGrammarUtility.ExtraRules()。
    ///
    /// 為何選 Postfix ExtraRules 而非自己 patch GrammarResolver.Resolve：
    ///  - SpeakUp 自己的 GrammarResolver_Resolve Prefix（SpeakUp/HarmonyPatches/GrammarResolver_Resolve.cs:15）
    ///    會把 ExtraRules() 的結果整批 AddRange 進 grammar request，再做解析。
    ///  - 只要我把規則「附加」到 ExtraRules() 的回傳集合，就會自然被 SpeakUp 既有管線收走，
    ///    完全沿用它的 r_logentry 流程與數值約束擴充（RuleEntry_ValidateConstantConstraints.cs:43）。
    ///  - 不必再自行攔截 Resolve，避免與 SpeakUp 的 Prefix 競合改同一份 request.rules。
    ///
    /// ExtraRules 原型（SpeakUp/ExtraGrammarUtility.cs:54）：
    ///   public static IEnumerable&lt;Rule&gt; ExtraRules()  // 可能回傳 null
    /// 因此 __result 可能為 null，需自行建立容器。
    ///
    /// 新增的情境變數（皆為地圖／殖民地層級，vanilla SpeakUp 未覆蓋）：
    ///   COLONY_DANGER          : none / low / high      （StoryDanger，地圖威脅等級）
    ///   INITIATOR_drafted /
    ///   RECIPIENT_drafted      : 是 / 否                （該 pawn 是否被徵召＝臨戰）
    ///   COLONY_FOOD_DAYS       : 數值（天）             （可吃天數，供 &lt; 比較判斷糧食危機）
    ///   COLONY_DAYS_SINCE_DEATH: 數值（天）；無死亡時不發此 rule（以利用「不存在」判斷）
    ///   INITIATOR_pain /
    ///   RECIPIENT_pain         : 數值（0~1）           （該 pawn 總疼痛；數值門檻 &gt; 比較的最小驗證點）
    /// </summary>
    [HarmonyPatch(typeof(ExtraGrammarUtility), nameof(ExtraGrammarUtility.ExtraRules))]
    public static class ExtraRulesInjector
    {
        // 與 SpeakUp 一致的前綴（SpeakUp/ExtraGrammarUtility.cs:14-15）。
        private const string InitPrefix = "INITIATOR_";
        private const string ReciPrefix = "RECIPIENT_";

        public static void Postfix(ref IEnumerable<Rule> __result)
        {
            try
            {
                Pawn initiator = DialogManager.Initiator;
                if (initiator == null || !initiator.Spawned) return;

                Map map = initiator.Map;
                if (map == null) return;

                // 若 SpeakUp 回傳 null（例如其內部出錯吞掉），自建容器；否則沿用其清單。
                List<Rule> rules = __result != null ? new List<Rule>(__result) : new List<Rule>();

                // --- 情境 1：殖民地威脅等級（含個別 pawn 是否臨戰）---
                AddDangerRules(rules, map, initiator, DialogManager.Recipient);

                // --- 情境 2：糧食危機（可吃天數）---
                AddFoodRules(rules, map);

                // --- 情境 3：近期殖民者死亡 ---
                AddRecentDeathRules(rules);

                // --- 情境 4：個別 pawn 受傷 ---
                AddInjuryRules(rules, initiator, DialogManager.Recipient);

                __result = rules;
            }
            catch (Exception e)
            {
                // 任何失敗都不可影響 SpeakUp 原本的對話；保留原 __result。
                Log.Warning($"[SpeakUpContextExpansion] ExtraRulesInjector error: {e.Message}");
            }
        }

        private static void AddDangerRules(List<Rule> rules, Map map, Pawn initiator, Pawn recipient)
        {
            // 地圖整體威脅等級：none / low / high（StoryDanger enum：None=0, Low=1, High=2）。
            // 來源 Verse.Map.dangerWatcher.DangerRating（已用 monodis 驗證存在於本機 Assembly-CSharp.dll）。
            StoryDanger danger = map.dangerWatcher.DangerRating;
            MakeRule(rules, "COLONY_DANGER", danger.ToString().ToLowerInvariant()); // none/low/high

            // 個別 pawn 是否被徵召（臨戰）。Pawn.Drafted 為玩家手動進入戰鬥姿態的明確訊號。
            MakeRule(rules, InitPrefix + "drafted", initiator.Drafted.ToStringYesNo());
            if (recipient != null && recipient.Spawned)
            {
                MakeRule(rules, ReciPrefix + "drafted", recipient.Drafted.ToStringYesNo());
            }
        }

        private static void AddFoodRules(List<Rule> rules, Map map)
        {
            // 殖民地可供人類食用的總營養（ResourceCounter.TotalHumanEdibleNutrition）。
            // 換算「還能吃幾天」：每名自由殖民者每天約消耗 1.6 營養（vanilla Need_Food 預設值）。
            float nutrition = map.resourceCounter.TotalHumanEdibleNutrition;
            int colonists = map.mapPawns.FreeColonistsCount;
            if (colonists < 1) colonists = 1;

            const float nutritionPerColonistPerDay = 1.6f;
            float days = nutrition / (colonists * nutritionPerColonistPerDay);

            // 以 1 位小數輸出，供 XML 做數值比較，例如 r_logentry(COLONY_FOOD_DAYS&lt;2)。
            MakeRule(rules, "COLONY_FOOD_DAYS", days.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture));
        }

        private static void AddRecentDeathRules(List<Rule> rules)
        {
            var tracker = ColonyDeathTracker.Current;
            if (tracker == null) return;

            int tick = Find.TickManager?.TicksGame ?? 0;
            float days = tracker.DaysSinceLastDeath(tick);

            // days < 0 代表本局尚無殖民者死亡 → 不發此 rule，
            // 讓 XML 可用 (COLONY_DAYS_SINCE_DEATH&lt;3) 隱含「有死過人且在 3 天內」。
            if (days < 0f) return;

            MakeRule(rules, "COLONY_DAYS_SINCE_DEATH", days.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture));
        }

        private static void AddInjuryRules(List<Rule> rules, Pawn initiator, Pawn recipient)
        {
            // 個別 pawn 的總疼痛（Pawn.health.hediffSet.PainTotal，0~1，已正規化）。
            // 為數值關鍵字，供 XML 以 INITIATOR_pain&gt;0.1 之類門檻引用；
            // 受傷在 dev mode 最易製造（不毀糧、不殺人），故選為 < / > 數值約束的最小驗證點。
            MakeRule(rules, InitPrefix + "pain", PainOf(initiator));
            if (recipient != null && recipient.Spawned)
            {
                MakeRule(rules, ReciPrefix + "pain", PainOf(recipient));
            }
        }

        private static string PainOf(Pawn p)
        {
            var hs = p.health?.hediffSet;
            if (hs == null) return null;
            return hs.PainTotal.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture);
        }

        /// <summary>
        /// 仿 ExtraGrammarUtility.MakeRule（SpeakUp/ExtraGrammarUtility.cs:282）：空值跳過、否則加一條 Rule_String。
        /// 因原 MakeRule 為 private，這裡複製其語意而非反射呼叫。
        /// </summary>
        private static void MakeRule(List<Rule> rules, string keyword, string output)
        {
            if (output.NullOrEmpty()) return;
            rules.Add(new Rule_String(keyword, output));
        }
    }
}
