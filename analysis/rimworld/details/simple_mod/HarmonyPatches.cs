using HarmonyLib;
using RimWorld;
using Verse;
using UnityEngine;

namespace MyMod;

/// <summary>
/// 在遊戲啟動時自動執行 Patch。
/// </summary>
[StaticConstructorOnStartup]
public static class HarmonyInit
{
    static HarmonyInit()
    {
        // 建立 Harmony 實例，ID 必須唯一
        var harmony = new Harmony("com.mymod.doubleberries");
        // 自動搜尋所有標註了 [HarmonyPatch] 的類別並套用
        harmony.PatchAll();
        Log.Message("MyMod: Harmony Patches 已成功套用！");
    }
}

/// <summary>
/// 攔截 Plant.YieldNow 方法的 Postfix 補丁。
/// </summary>
[HarmonyPatch(typeof(Plant), "YieldNow")]
public static class Patch_Plant_YieldNow
{
    // __result 代表原版方法的返回值
    // __instance 代表呼叫該方法的對象 (即當前的植物實例)
    public static void Postfix(Plant __instance, ref int __result)
    {
        // 檢查這棵植物是不是莓果叢 (透過 DefName 判斷)
        if (__instance.def.defName == "Plant_BerryBush")
        {
            // 將產量翻倍
            int originalYield = __result;
            __result *= 2;
            
            // 可以在日誌中輸出，方便 Debug (稍後會講)
            // Log.Message($"MyMod: 偵測到莓果收割！原產量: {originalYield}, 現產量: {__result}");
        }
    }
}
