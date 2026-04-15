using System.Collections.Generic;
using RimWorld;
using RimWorld.Planet;
using Verse;
using UnityEngine;

namespace MyMod.Examples;

/// <summary>
/// 實戰範例：自動採藥商隊組件。
/// 展示如何結合 WorldComponent, Caravan 模擬, UI 開關與數據保存。
/// </summary>
public class WorldComponent_AutoGathering : WorldComponent
{
    // 用於存儲每個商隊的設定 (ID -> 是否開啟)
    private Dictionary<int, bool> gatheringSettings = new Dictionary<int, bool>();

    public WorldComponent_AutoGathering(World world) : base(world) { }

    /// <summary>
    /// 全局數據保存：存檔時會保存所有商隊的設定。
    /// </summary>
    public override void ExposeData()
    {
        base.ExposeData();
        Scribe_Collections.Look(ref gatheringSettings, "gatheringSettings", LookMode.Value, LookMode.Value);
        if (gatheringSettings == null) gatheringSettings = new Dictionary<int, bool>();
    }

    /// <summary>
    /// 每 2500 Ticks (遊戲內 1 小時) 執行一次採藥檢查。
    /// </summary>
    public override void WorldComponentTick()
    {
        base.WorldComponentTick();

        if (Find.TickManager.TicksGame % 2500 == 0)
        {
            DoGatheringCycle();
        }
    }

    private void DoGatheringCycle()
    {
        foreach (Caravan caravan in Find.WorldObjects.Caravans)
        {
            // 1. 檢查玩家是否開啟了此商隊的自動採藥
            if (!gatheringSettings.TryGetValue(caravan.ID, out bool enabled) || !enabled)
                continue;

            // 2. 檢查地形是否有植物
            Tile tile = Find.WorldGrid[caravan.Tile];
            if (tile.biome.plantDensity <= 0.1f) continue;

            // 3. 尋找商隊中技能最高的小人
            Pawn bestGatherer = null;
            float bestSkill = 0f;
            foreach (Pawn p in caravan.PawnsListForReading)
            {
                if (p.RaceProps.Humanlike && p.skills != null)
                {
                    float skill = p.skills.GetSkill(SkillDefOf.Plants).Level;
                    if (skill > bestSkill) { bestSkill = skill; bestGatherer = p; }
                }
            }

            // 4. 根據技能計算成功率並給予獎勵
            if (bestGatherer != null && Rand.Chance(bestSkill * 0.02f))
            {
                Thing herbs = ThingMaker.MakeThing(ThingDefOf.HerbalMedicine);
                herbs.stackCount = Rand.Range(1, (int)(bestSkill / 5) + 1);
                CaravanInventoryUtility.GiveThing(caravan, herbs);
                
                // 增加小人的經驗值
                bestGatherer.skills.Learn(SkillDefOf.Plants, 50f);
            }
        }
    }

    // --- 以下為 UI 注入部分，利用 Harmony 或是自定義 Gizmo 顯示按鈕 ---
    // (這裡展示如何讓外部呼叫來切換設定)
    public void ToggleGathering(int caravanID)
    {
        if (gatheringSettings.ContainsKey(caravanID))
            gatheringSettings[caravanID] = !gatheringSettings[caravanID];
        else
            gatheringSettings[caravanID] = true;
    }

    public bool IsEnabled(int caravanID)
    {
        return gatheringSettings.TryGetValue(caravanID, out bool enabled) && enabled;
    }
}

/// <summary>
/// 利用 Harmony 為所有的商隊 (Caravan) 增加一個指令按鈕 (Gizmo)。
/// </summary>
[HarmonyLib.HarmonyPatch(typeof(Caravan), "GetGizmos")]
public static class Patch_Caravan_Gizmos
{
    public static IEnumerable<Gizmo> Postfix(IEnumerable<Gizmo> __result, Caravan __instance)
    {
        // 先顯示原有的按鈕
        foreach (Gizmo g in __result) yield return g;

        // 獲取我們的 WorldComponent
        var comp = Find.World.GetComponent<WorldComponent_AutoGathering>();

        // 添加我們的自動採藥切換按鈕
        yield return new Command_Toggle
        {
            defaultLabel = "自動採集藥草",
            defaultDesc = "若開啟，商隊成員在旅行途中會利用閒暇時間搜尋並採集周遭的藥草。",
            isActive = () => comp.IsEnabled(__instance.ID),
            toggleAction = () => comp.ToggleGathering(__instance.ID),
            icon = ContentFinder<Texture2D>.Get("UI/Icons/Gathering") // 假設已有圖示
        };
    }
}
