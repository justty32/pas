using UnityEngine;
using Verse;
using RimWorld;

namespace MyMod;

/// <summary>
/// 智慧燈設定視窗，展示 Window 與 Widgets 的用法。
/// </summary>
public class Dialog_SmartLampConfig : Window
{
    private CompSmartLamp targetComp;
    private float bufferIntensity;

    // 設定視窗大小
    public override Vector2 InitialSize => new Vector2(400f, 250f);

    public Dialog_SmartLampConfig(CompSmartLamp comp)
    {
        this.targetComp = comp;
        this.bufferIntensity = comp.lightIntensity;
        this.doCloseX = true; // 顯示關閉 X
        this.doCloseButton = true; // 顯示關閉按鈕
        this.forcePause = true; // 開啟視窗時暫停遊戲
    }

    public override void DoWindowContents(Rect inRect)
    {
        Listing_Standard listing = new Listing_Standard();
        listing.Begin(inRect);

        // 標題
        Text.Font = GameFont.Medium;
        listing.Label("智慧燈亮度設定");
        Text.Font = GameFont.Small;
        listing.Gap();

        // 亮度滑桿
        listing.Label($"當前亮度: {bufferIntensity:P0}");
        bufferIntensity = listing.Slider(bufferIntensity, 0.0f, 1.0f);
        
        listing.Gap(20f);

        // 套用按鈕
        if (listing.ButtonText("套用設定"))
        {
            targetComp.lightIntensity = bufferIntensity;
            // 提醒 Glower 組件更新光照 (如果需要)
            targetComp.parent.BroadcastCompSignal("SmartLampUpdate");
            Log.Message($"已套用亮度設定: {bufferIntensity}");
            this.Close();
        }

        listing.End();
    }
}
