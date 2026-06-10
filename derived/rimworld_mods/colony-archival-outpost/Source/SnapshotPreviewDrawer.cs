using System;
using System.Collections.Generic;
using System.Linq;
using RimWorld;
using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    // 共用的 snapshot 預覽繪製工具，供 N1 確認視窗與 N2 採樣狀況視窗共用。
    public static class SnapshotPreviewDrawer
    {
        private const float RowH = 28f;
        private const float IconSize = 24f;
        private const float HeaderH = 20f;
        private const float SectionGap = 10f;
        private const float WarnH = 28f;

        // 預算高度（供 scroll view 設定 viewRect.height 用）
        public static float CalcHeight(ProductivitySnapshot snapshot, int elapsedTicks)
        {
            float h = 0f;
            if (elapsedTicks < 60000) h += WarnH + 4f;
            int pos = snapshot.dailyRates.Count(kv => kv.Value > 0f);
            int neg = snapshot.dailyRates.Count(kv => kv.Value < 0f);
            h += HeaderH + Mathf.Max(1, pos) * RowH;
            h += SectionGap;
            h += HeaderH + Mathf.Max(1, neg) * RowH;
            if (snapshot.dailySkillXP?.Count > 0)
            {
                h += SectionGap;
                h += HeaderH + snapshot.dailySkillXP.Count * RowH;
            }
            if (snapshot.avgHealthDeltaPerDay != 0f)
            {
                h += SectionGap;
                h += HeaderH + RowH;
            }
            if (snapshot.dailyHediffDeltas?.Count > 0)
            {
                h += SectionGap;
                h += HeaderH + snapshot.dailyHediffDeltas.Count * RowH;
            }
            return h;
        }

        // 繪製 snapshot 預覽，回傳實際使用高度。
        // scrollPos/outerHeight 供視口剔除用（只繪可見列）；不傳則全部繪製（小資料量時安全）。
        public static float Draw(Rect rect, ProductivitySnapshot snapshot, int elapsedTicks, float daysPerCycle,
            Vector2 scrollPos = default, float outerHeight = float.MaxValue)
        {
            float y = rect.y;
            float x = rect.x;
            float w = rect.width;
            GameFont prevFont = Text.Font;
            Color prevColor = GUI.color;

            if (elapsedTicks < 60000)
            {
                if (IsVisible(y, WarnH, rect.y, scrollPos.y, outerHeight))
                {
                    GUI.color = Color.yellow;
                    Widgets.Label(new Rect(x, y, w, WarnH), "CAO.ShortSampleWarning".Translate());
                    GUI.color = prevColor;
                }
                y += WarnH + 4f;
            }

            DrawSection(ref y, x, w, daysPerCycle,
                "CAO.Preview.Production".Translate(Mathf.RoundToInt(daysPerCycle)),
                snapshot.dailyRates.Where(kv => kv.Value > 0f).OrderByDescending(kv => kv.Value),
                rect.y, scrollPos.y, outerHeight);

            y += SectionGap;

            DrawSection(ref y, x, w, daysPerCycle,
                "CAO.Preview.Consumption".Translate(Mathf.RoundToInt(daysPerCycle)),
                snapshot.dailyRates.Where(kv => kv.Value < 0f).OrderBy(kv => kv.Value),
                rect.y, scrollPos.y, outerHeight);

            // N7：技能訓練預覽段落
            if (snapshot.dailySkillXP?.Count > 0)
            {
                y += SectionGap;
                DrawSkillSection(ref y, x, w, daysPerCycle,
                    "CAO.Preview.SkillTraining".Translate(Mathf.RoundToInt(daysPerCycle)),
                    snapshot.dailySkillXP.OrderByDescending(kv => kv.Value),
                    rect.y, scrollPos.y, outerHeight);
            }

            // N6：傷勢變化段落
            if (snapshot.avgHealthDeltaPerDay != 0f)
            {
                y += SectionGap;
                bool healing = snapshot.avgHealthDeltaPerDay < 0f;
                float perCycle = Math.Abs(snapshot.avgHealthDeltaPerDay) * daysPerCycle;

                if (IsVisible(y, HeaderH, rect.y, scrollPos.y, outerHeight))
                {
                    Text.Font = GameFont.Tiny;
                    Widgets.Label(new Rect(x, y, w, HeaderH), "CAO.Preview.HealthChange".Translate(Mathf.RoundToInt(daysPerCycle)));
                    Text.Font = GameFont.Small;
                }
                y += HeaderH;

                if (IsVisible(y, RowH, rect.y, scrollPos.y, outerHeight))
                {
                    Widgets.Label(new Rect(x + 4f, y, w * 0.55f, RowH),
                        healing ? "CAO.Preview.HealthHealing".Translate() : "CAO.Preview.HealthDamage".Translate());
                    GUI.color = healing ? new Color(0.55f, 1f, 0.55f) : new Color(1f, 0.65f, 0.4f);
                    string sign = healing ? "+" : "-";
                    Widgets.Label(new Rect(x + w * 0.56f, y, w * 0.44f, RowH),
                        $"{sign}{perCycle:F2} sev / {"CAO.Preview.Cycle".Translate()} / pawn");
                    GUI.color = Color.white;
                }
                y += RowH;
            }

            // N6b：非傷勢 hediff 變化段落
            if (snapshot.dailyHediffDeltas?.Count > 0)
            {
                y += SectionGap;
                DrawHediffDeltaSection(ref y, x, w, daysPerCycle,
                    "CAO.Preview.HediffDeltas".Translate(Mathf.RoundToInt(daysPerCycle)),
                    snapshot.dailyHediffDeltas.OrderBy(kv => kv.Value),
                    rect.y, scrollPos.y, outerHeight);
            }

            Text.Font = prevFont;
            GUI.color = prevColor;
            return y - rect.y;
        }

        // 判斷高度為 h 的元素（起點 y）是否在可見窗內
        private static bool IsVisible(float y, float h, float contentOrigin, float scrollY, float outerH)
        {
            float cy = y - contentOrigin; // 轉成 viewRect 座標
            return cy + h > scrollY && cy < scrollY + outerH;
        }

        private static void DrawSection(ref float y, float x, float w,
            float daysPerCycle, string header,
            IEnumerable<KeyValuePair<ThingDef, float>> items,
            float contentOrigin, float scrollY, float outerH)
        {
            if (IsVisible(y, HeaderH, contentOrigin, scrollY, outerH))
            {
                Text.Font = GameFont.Tiny;
                Widgets.Label(new Rect(x, y, w, HeaderH), header);
                Text.Font = GameFont.Small;
            }
            y += HeaderH;

            var list = items.ToList();
            if (list.Count == 0)
            {
                if (IsVisible(y, RowH, contentOrigin, scrollY, outerH))
                {
                    GUI.color = Color.gray;
                    Widgets.Label(new Rect(x + 4f, y, w, RowH), "CAO.Preview.None".Translate());
                    GUI.color = Color.white;
                }
                y += RowH;
                return;
            }

            foreach (var kv in list)
            {
                if (IsVisible(y, RowH, contentOrigin, scrollY, outerH))
                {
                    bool positive = kv.Value > 0f;
                    float absRate = Mathf.Abs(kv.Value);
                    int perCycle = (int)Math.Min(Math.Round((double)absRate * daysPerCycle), int.MaxValue);

                    Widgets.ThingIcon(new Rect(x + 2f, y + 2f, IconSize, IconSize), kv.Key);
                    Widgets.Label(new Rect(x + 30f, y, w * 0.55f, RowH), kv.Key.LabelCap);

                    string sign = positive ? "+" : "-";
                    GUI.color = positive ? new Color(0.55f, 1f, 0.55f) : new Color(1f, 0.65f, 0.4f);
                    Widgets.Label(new Rect(x + w * 0.56f, y, w * 0.44f, RowH),
                        $"{sign}{perCycle} / {"CAO.Preview.Cycle".Translate()}");
                    GUI.color = Color.white;
                }
                y += RowH;
            }
        }
        // N6b：非傷勢 hediff 變化段落（正=加重/新增紅色，負=消退綠色）
        private static void DrawHediffDeltaSection(ref float y, float x, float w,
            float daysPerCycle, string header,
            IEnumerable<KeyValuePair<HediffDef, float>> items,
            float contentOrigin, float scrollY, float outerH)
        {
            if (IsVisible(y, HeaderH, contentOrigin, scrollY, outerH))
            {
                Text.Font = GameFont.Tiny;
                Widgets.Label(new Rect(x, y, w, HeaderH), header);
                Text.Font = GameFont.Small;
            }
            y += HeaderH;

            foreach (var kv in items)
            {
                if (IsVisible(y, RowH, contentOrigin, scrollY, outerH))
                {
                    bool improving = kv.Value < 0f; // 負=消退=好
                    float absPerCycle = Math.Abs(kv.Value) * daysPerCycle;
                    string sign = improving ? "-" : "+";
                    Widgets.Label(new Rect(x + 4f, y, w * 0.55f, RowH), kv.Key.LabelCap);
                    GUI.color = improving ? new Color(0.55f, 1f, 0.55f) : new Color(1f, 0.65f, 0.4f);
                    Widgets.Label(new Rect(x + w * 0.56f, y, w * 0.44f, RowH),
                        $"{sign}{absPerCycle:F3} sev / {"CAO.Preview.Cycle".Translate()}");
                    GUI.color = Color.white;
                }
                y += RowH;
            }
        }

        // N7：技能訓練段落，顯示每技能每週期基礎 XP（乘 occupant passion 後為實際 XP）
        private static void DrawSkillSection(ref float y, float x, float w,
            float daysPerCycle, string header,
            IEnumerable<KeyValuePair<SkillDef, float>> items,
            float contentOrigin, float scrollY, float outerH)
        {
            if (IsVisible(y, HeaderH, contentOrigin, scrollY, outerH))
            {
                Text.Font = GameFont.Tiny;
                Widgets.Label(new Rect(x, y, w, HeaderH), header);
                Text.Font = GameFont.Small;
            }
            y += HeaderH;

            foreach (var kv in items)
            {
                if (IsVisible(y, RowH, contentOrigin, scrollY, outerH))
                {
                    bool positive = kv.Value > 0f;
                    float absBaseXP = Mathf.Abs(kv.Value) * daysPerCycle;
                    string sign = positive ? "+" : "-";
                    Widgets.Label(new Rect(x + 4f, y, w * 0.55f, RowH), kv.Key.LabelCap);
                    GUI.color = positive ? new Color(0.55f, 1f, 0.55f) : new Color(1f, 0.65f, 0.4f);
                    Widgets.Label(new Rect(x + w * 0.56f, y, w * 0.44f, RowH),
                        $"{sign}{Mathf.RoundToInt(absBaseXP)} XP / {"CAO.Preview.Cycle".Translate()} *");
                    GUI.color = Color.white;
                }
                y += RowH;
            }
        }
    }
}
