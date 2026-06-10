using System;
using HarmonyLib;
using Outposts;
using RimWorld.Planet;
using UnityEngine;
using Verse;
using VOE;

namespace VOEOutpostEnhancement
{
    public class Dialog_ArtilleryFire : Window
    {
        private readonly Outpost_Artillery art;
        private readonly GlobalTargetInfo target;
        private readonly OutpostUpgradeRecord rec;
        private int selectedShell;
        private float sliderCount;

        private const float RowH = 28f;
        private const float BtnH = 36f;

        public override Vector2 InitialSize => new Vector2(460f, 310f);

        public Dialog_ArtilleryFire(Outpost_Artillery art, GlobalTargetInfo target, OutpostUpgradeRecord rec)
        {
            this.art = art;
            this.target = target;
            this.rec = rec;
            selectedShell = Mathf.Clamp(rec.artShellType, 0, 3);
            int avail = Math.Max(1, (int)rec.ammoStockpile);
            sliderCount = Mathf.Clamp(rec.artLastSliderCount, 1f, (float)avail);
            doCloseButton = false;
            doCloseX = true;
            closeOnClickedOutside = false;
            forcePause = false;
            absorbInputAroundWindow = true;
        }

        public override void DoWindowContents(Rect inRect)
        {
            Text.Font = GameFont.Medium;
            Widgets.Label(new Rect(inRect.x, inRect.y, inRect.width, 36f),
                "VOEE.Artillery.Fire.Title".Translate());
            Text.Font = GameFont.Small;

            float y = inRect.y + 44f;

            // 庫存資訊
            int avail = (int)rec.ammoStockpile;
            int maxAmmo = UpgradeService.GetMaxAmmo(rec);
            Widgets.Label(new Rect(inRect.x, y, inRect.width, RowH),
                "VOEE.Artillery.Fire.Desc".Translate(avail, maxAmmo));
            y += RowH + 6f;

            // 砲彈種類選擇標題
            Widgets.Label(new Rect(inRect.x, y, inRect.width, RowH),
                "VOEE.Artillery.Fire.SelectShell".Translate());
            y += RowH;

            // 4 顆砲彈按鈕
            float btnW = (inRect.width - 9f) / 4f;
            for (int i = 0; i < 4; i++)
            {
                var shellDef = DefDatabase<ThingDef>.GetNamedSilentFail(UpgradeService.ShellItemDef[i]);
                var btnRect = new Rect(inRect.x + i * (btnW + 3f), y, btnW, 42f);

                if (selectedShell == i)
                    Widgets.DrawBoxSolid(btnRect, new Color(0.25f, 0.45f, 0.85f, 0.35f));
                Widgets.DrawHighlightIfMouseover(btnRect);
                Widgets.DrawBox(btnRect);

                if (shellDef?.uiIcon != null)
                {
                    float iconSize = 30f;
                    GUI.DrawTexture(
                        new Rect(btnRect.x + (btnW - iconSize) / 2f, btnRect.y + 4f, iconSize, iconSize),
                        shellDef.uiIcon);
                }

                TooltipHandler.TipRegion(btnRect, UpgradeService.ShellLabelKey[i].Translate());
                if (Widgets.ButtonInvisible(btnRect))
                    selectedShell = i;
            }
            y += 48f;

            // 數量滑桿
            int sliderMax = Math.Max(1, avail);
            float clamped = Mathf.Clamp(sliderCount, 1f, (float)sliderMax);
            Widgets.Label(new Rect(inRect.x, y, inRect.width, RowH),
                "VOEE.Artillery.Fire.SelectCount".Translate((int)clamped));
            y += RowH;
            sliderCount = Widgets.HorizontalSlider(
                new Rect(inRect.x, y, inRect.width, 24f),
                clamped, 1f, (float)sliderMax, false, null, null, null, 1f);
            y += 32f;

            // 確認 / 取消
            float halfW = (inRect.width - 8f) / 2f;
            if (Widgets.ButtonText(new Rect(inRect.x, y, halfW, BtnH),
                "VOEE.Artillery.Fire.Confirm".Translate()))
            {
                Confirm();
                Close();
            }
            if (Widgets.ButtonText(new Rect(inRect.x + halfW + 8f, y, halfW, BtnH),
                "Cancel".Translate()))
                Close();
        }

        private void Confirm()
        {
            int avail = (int)rec.ammoStockpile;
            int count = Mathf.Clamp((int)sliderCount, 1, Math.Max(1, avail));

            rec.artShellType = selectedShell;
            rec.artLastSliderCount = count;
            rec.ammoStockpile = Math.Max(0f, rec.ammoStockpile - count);

            ArtilleryFireState.PendingShellType = selectedShell;
            ArtilleryFireState.PendingCount = count;
            ArtilleryFireState.SkipNextIntercept = true;

            art.Fire(target);
        }
    }
}
