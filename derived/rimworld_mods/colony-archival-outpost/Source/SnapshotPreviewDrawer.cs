using System;
using System.Collections.Generic;
using System.Linq;
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
            return h;
        }

        // 繪製 snapshot 預覽，回傳實際使用高度
        public static float Draw(Rect rect, ProductivitySnapshot snapshot, int elapsedTicks, float daysPerCycle)
        {
            float y = rect.y;
            float x = rect.x;
            float w = rect.width;
            GameFont prevFont = Text.Font;
            Color prevColor = GUI.color;

            if (elapsedTicks < 60000)
            {
                GUI.color = Color.yellow;
                Widgets.Label(new Rect(x, y, w, WarnH), "CAO.ShortSampleWarning".Translate());
                GUI.color = prevColor;
                y += WarnH + 4f;
            }

            DrawSection(ref y, x, w, daysPerCycle,
                "CAO.Preview.Production".Translate(Mathf.RoundToInt(daysPerCycle)),
                snapshot.dailyRates.Where(kv => kv.Value > 0f).OrderByDescending(kv => kv.Value));

            y += SectionGap;

            DrawSection(ref y, x, w, daysPerCycle,
                "CAO.Preview.Consumption".Translate(Mathf.RoundToInt(daysPerCycle)),
                snapshot.dailyRates.Where(kv => kv.Value < 0f).OrderBy(kv => kv.Value));

            Text.Font = prevFont;
            GUI.color = prevColor;
            return y - rect.y;
        }

        private static void DrawSection(ref float y, float x, float w,
            float daysPerCycle, string header,
            IEnumerable<KeyValuePair<ThingDef, float>> items)
        {
            Text.Font = GameFont.Tiny;
            Widgets.Label(new Rect(x, y, w, HeaderH), header);
            Text.Font = GameFont.Small;
            y += HeaderH;

            var list = items.ToList();
            if (list.Count == 0)
            {
                GUI.color = Color.gray;
                Widgets.Label(new Rect(x + 4f, y, w, RowH), "CAO.Preview.None".Translate());
                GUI.color = Color.white;
                y += RowH;
                return;
            }

            foreach (var kv in list)
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

                y += RowH;
            }
        }
    }
}
