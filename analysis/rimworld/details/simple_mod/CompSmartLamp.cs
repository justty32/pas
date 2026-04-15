using UnityEngine;
using Verse;
using RimWorld;
using System.Collections.Generic;

namespace MyMod;

/// <summary>
/// 智慧型電燈組件，展示 UI、Gizmo 與 Scribe 系統。
/// </summary>
public class CompSmartLamp : ThingComp
{
    // 需要持久化的數據
    public float lightIntensity = 1.0f;
    public bool isAutoMode = false;

    // 獲取該物體原有的發光組件 (如果有)
    private CompGlower Glower => parent.TryGetComp<CompGlower>();

    /// <summary>
    /// 數據持久化：存檔與讀檔
    /// </summary>
    public override void PostExposeData()
    {
        base.PostExposeData();
        // 將數據存入存檔，標籤名稱必須唯一
        Scribe_Values.Look(ref lightIntensity, "smartLampIntensity", 1.0f);
        Scribe_Values.Look(ref isAutoMode, "smartLampAutoMode", false);
    }

    /// <summary>
    /// 檢查面板文字：顯示當前設定
    /// </summary>
    public override string CompInspectStringExtra()
    {
        return $"亮度: {lightIntensity:P0}\n模式: {(isAutoMode ? "自動" : "手動")}";
    }

    /// <summary>
    /// 指令按鈕：提供開啟 UI 的入口
    /// </summary>
    public override IEnumerable<Gizmo> CompGetGizmosExtra()
    {
        // 基礎按鈕
        yield return new Command_Action
        {
            defaultLabel = "設定智慧燈",
            defaultDesc = "開啟詳細設定面板。",
            icon = ContentFinder<Texture2D>.Get("UI/Icons/Settings"), // 假設有這個圖示
            action = () => Find.WindowStack.Add(new Dialog_SmartLampConfig(this))
        };

        // 開關按鈕 (Toggle)
        yield return new Command_Toggle
        {
            defaultLabel = "自動模式",
            defaultDesc = "根據周遭環境自動調整亮度。",
            isActive = () => isAutoMode,
            toggleAction = () => isAutoMode = !isAutoMode,
            icon = ContentFinder<Texture2D>.Get("UI/Icons/AutoMode")
        };
    }

    /// <summary>
    /// 每 Tick 執行的邏輯 (示範)
    /// </summary>
    public override void CompTick()
    {
        base.CompTick();
        if (isAutoMode && parent.IsHashIntervalTick(250)) // 每 250 Ticks 檢查一次
        {
            // 這裡是自動調整亮度的邏輯
            // 例如：白天空關燈，晚上開燈
        }
    }
}
