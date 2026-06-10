using UnityEngine;
using Verse;

namespace ColonyArchivalOutpost
{
    // N2：採樣中查看狀況視窗。打開時算一次 snapshot，顯示當前速率預覽與已歷時。
    public class Dialog_SamplingStatus : Window
    {
        private readonly ProductivitySnapshot snapshot;
        private readonly int elapsedTicks;
        private readonly float daysPerCycle;

        private Vector2 previewScroll;
        private float previewContentH;

        public override Vector2 InitialSize => new Vector2(440f, 420f);

        public Dialog_SamplingStatus(Map map)
        {
            var tracker = map.GetComponent<ColonyArchivalTracker>();
            if (tracker == null) { closeOnClickedOutside = true; return; } // Bug N2 fix
            elapsedTicks = Find.TickManager.TicksGame - tracker.startTick;
            snapshot = ArchivalService.ComputeSnapshot(map, tracker);
            daysPerCycle = 900000f / 60000f;

            doCloseX = true;
            forcePause = false;
            absorbInputAroundWindow = false;
            closeOnClickedOutside = true;
            previewContentH = SnapshotPreviewDrawer.CalcHeight(snapshot, elapsedTicks);
        }

        public override void DoWindowContents(Rect inRect)
        {
            if (snapshot == null) { Close(); return; } // Bug N2 guard
            float x = inRect.x;
            float w = inRect.width;
            float y = inRect.y;

            // 標題
            Text.Font = GameFont.Medium;
            Widgets.Label(new Rect(x, y, w, 32f), "CAO.SamplingStatus.Title".Translate());
            Text.Font = GameFont.Small;
            y += 36f;

            // 已歷時
            int days = elapsedTicks / 60000;
            int hours = (elapsedTicks % 60000) / 2500;
            string elapsedStr = $"{days}d {hours}h";
            Widgets.Label(new Rect(x, y, w, 24f), "CAO.SamplingStatus.Elapsed".Translate(elapsedStr));
            y += 28f;

            // 預覽 scroll view（填滿剩餘空間，預留按鈕高度）
            const float btnH = 44f;
            float previewOuterH = inRect.yMax - y - btnH;
            Rect outerRect = new Rect(x, y, w, previewOuterH);
            Widgets.DrawBoxSolid(outerRect, new Color(0f, 0f, 0f, 0.12f));
            Rect viewRect = new Rect(0f, 0f, w - 20f, Mathf.Max(previewOuterH, previewContentH));
            Widgets.BeginScrollView(outerRect, ref previewScroll, viewRect);
            SnapshotPreviewDrawer.Draw(new Rect(4f, 4f, viewRect.width - 8f, viewRect.height), snapshot, elapsedTicks, daysPerCycle, previewScroll, previewOuterH);
            Widgets.EndScrollView();

            // 關閉按鈕
            float btnY = inRect.yMax - 34f;
            if (Widgets.ButtonText(new Rect(x + w / 4f, btnY, w / 2f, 30f), "CAO.SamplingStatus.Close".Translate()))
                Close();
        }
    }
}
