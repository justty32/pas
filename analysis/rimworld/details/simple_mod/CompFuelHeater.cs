using System.Collections.Generic;
using UnityEngine;
using Verse;
using RimWorld;

namespace MyMod;

/// <summary>
/// 燃油加熱器組件：展示燃料系統與溫控系統的整合。
/// </summary>
public class CompFuelHeater : ThingComp
{
    // 引用其他組件，方便後續呼叫
    private CompRefuelable refuelableComp;
    private CompTempControl tempControlComp;

    // 每一度熱量產生的燃料消耗率 (示範用)
    private const float FuelConsumptionPerHeat = 0.001f;

    public override void PostSpawnSetup(bool respawningAfterLoad)
    {
        base.PostSpawnSetup(respawningAfterLoad);
        // 初始化時抓取同一個 Thing 上的其他組件
        refuelableComp = parent.GetComp<CompRefuelable>();
        tempControlComp = parent.GetComp<CompTempControl>();
    }

    /// <summary>
    /// 核心物理循環：每 Tick 執行。
    /// </summary>
    public override void CompTick()
    {
        base.CompTick();

        // 1. 檢查燃料是否充足
        if (refuelableComp == null || !refuelableComp.HasFuel)
        {
            return;
        }

        // 2. 檢查溫控設定 (是否達到目標溫度)
        float currentTemp = parent.Position.GetTemperature(parent.Map);
        float targetTemp = tempControlComp.targetTemperature;

        if (currentTemp < targetTemp)
        {
            // 3. 執行「推熱 (Push Heat)」物理行為
            float energyLimit = tempControlComp.Props.energyPerTick; // 從 XML 讀取每幀能量
            float pushedEnergy = GenTemperature.ControlTemperatureTempChange(
                parent.Position, 
                parent.Map, 
                energyLimit, 
                targetTemp
            );

            // 4. 如果成功產生了溫度變化，則扣除燃料
            if (!Mathf.Approximately(pushedEnergy, 0f))
            {
                // 消耗燃料：根據產生的熱量成比例扣除
                float fuelToConsume = Mathf.Abs(pushedEnergy) * FuelConsumptionPerHeat;
                refuelableComp.ConsumeFuel(fuelToConsume);
            }
        }
    }

    /// <summary>
    /// 檢查面板擴充：顯示詳細狀態
    /// </summary>
    public override string CompInspectStringExtra()
    {
        if (refuelableComp != null && !refuelableComp.HasFuel)
        {
            return "狀態: 燃料耗盡";
        }
        return "狀態: 正在加熱";
    }
}
