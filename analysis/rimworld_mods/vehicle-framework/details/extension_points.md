# Vehicle Framework — 擴充接點 (XML vs C#)

> 目標導向：要在此框架上 create 一台新載具 / 衍生功能，先看「哪些純 XML 能做、哪些一定要改碼」。
> 行號皆指 `projects/rimworld_mods/vehicle-framework/decompiled/Vehicles/Vehicles.decompiled.cs`。

## A. 純 XML 能做什麼（不需編譯 DLL）

框架把**大量行為設計成資料驅動**，以下全部純 XML：

| 接點 | 做法 | 依據 |
|---|---|---|
| **整台新載具（外觀/數值不同）** | 新增一對 `VehicleBuildDef` + `VehicleDef`，ParentName 繼承 `Base*` 抽象範本 | `VehiclePawnBase.xml`、`Buildable_Vehicle.xml` |
| 陸/海/空/通用 | `<type>Land/Sea/Air/Universal</type>` | `VehicleType` `:50413` |
| 地形/生態通行成本與限制 | `properties` 內 `customTerrainCosts`/`customBiomeCosts`/`customRoadCosts`/`defaultImpassable`… | `VehicleProperties` `:16950` |
| 座位/角色（駕駛、砲手、乘客） | `properties/roles` 內多個 `VehicleRole`（key/handlingTypes/slots/turretIds） | `VehicleRole` `:17141` |
| 部位健康（引擎/車身可被打壞、影響 stat） | `components` 清單，用內建 `compClass` + `categories`(影響的 stat) + `efficiency` 曲線 + 內建 `reactors` | `VehicleComponentProperties` `:8850` |
| 燃料/電力行駛 | `<comps>` 加 `CompProperties_FueledTravel`（fuelType/capacity/rate；electricPowered 走電） | `:19495` |
| 武裝（砲塔，用內建砲塔行為） | `<comps>` 加 `CompProperties_VehicleTurrets` + `VehicleTurret` 清單；新 `VehicleTurretDef` | `:19853`、`VehicleTurretDef` `:64835` |
| 飛行/空降 | `<comps>` 加 `CompProperties_VehicleLauncher`（rateOfClimb/maxAltitude…） | `:17770` |
| **升級樹**（加血/加速/加砲/改座位） | 新 `UpgradeTreeDef` + `UpgradeNode`，用內建 `StatUpgrade`/`TurretUpgrade`/`VehicleUpgrade`/`CompUpgrade`/`SettingsUpgrade`/`SoundUpgrade`；comp 掛 `CompProperties_UpgradeTree` | `UpgradeTreeDef` `:34361`、`Upgrade` 子類 `:32933–33587` |
| **新塗裝 pattern / skin** | 新 `Vehicles.PatternDef`（defName/label/path 指向貼圖），純資料 | `PatternDefs/PatternDefs.xml`（`PatternDef.path`） |
| 事件音效 | `soundOneShotsOnEvent`/`soundSustainersOnEvent` 綁 `VehicleEventDef` | `:11345/11347` |
| 載具 stat 數值 | `vehicleStats`（`VehicleStatModifier`） | `:11313` |
| NPC/襲擊使用 | `npcProperties`、`combatPower`、`vehicleCategory`、`enabled=Raiders/Everyone` | `:11335/11311/11318/11303` |
| 各 DLC/mod 互通 | 走既有 `Compatibility/` 模式（PatchOperation） | `Compatibility/` |

**風險 / 注意**：
- 新載具需要對應**貼圖資產**（graphicData + pattern 圖檔），否則 `MaterialCount=4`（`:11423`）的多層染色會抓不到圖、報 `NullShaderVehicleDef`（`:11300`）。
- `components` 的 `hitbox`、`roles` 的 `hitbox` 要覆蓋到合理區域，否則受擊判定/座位暴露會異常。
- `restrictToFactions`、`enabled` 設錯會讓載具買不到/造不出。
- `designatorTypes`、`events` 雖寫在 XML，但**引用的 Type / 方法名必須在某個已載入 DLL 中存在**（純資料無法新增 Type）。

## B. 必須改碼（C#）才能做的

| 需求 | 為何要 C# | 接點 |
|---|---|---|
| **自訂武器/砲塔特殊行為**（非標準射擊，如連鎖、特殊彈道、自動鎖定邏輯） | `VehicleTurret`(`:61607`)/`VehicleTurretAlternating`(`:64800`) 的開火管線是編譯邏輯；新行為要新 turret 子類或 Harmony patch | 繼承 `VehicleTurret` 或 patch |
| **全新 VehicleComp 功能**（框架沒提供的系統，如自訂礦採、自訂能量網） | comp 行為在 `VehicleComp : ThingComp`(`:21817`) 子類的 C# tick/方法裡 | 新 `VehicleComp` + `VehicleCompProperties` 子類 |
| **特殊部位反應 Reactor**（內建 Reactor 不夠用的損壞效果） | `Reactor`（`VehicleComponentProperties.reactors` `:8880`）的反應邏輯是 C# | 新 `Reactor` 子類 |
| **升級的 ActionUpgrade 效果** | `ActionUpgrade`(`:32933`) 觸發的具體動作需綁到 C# 委派/方法 | 提供方法給 `events`/Action |
| **`events` 的 DynamicDelegate 目標方法** | `VehicleDef.events`(`:11349`) 是 `DynamicDelegate<VehiclePawn>`，XML 只是「綁方法名」，**方法本體必須存在於 DLL** | 寫 static 方法供 XML 綁 |
| **自訂尋路規則 / 通行判定**（超越 cost 字典能表達的，如動態障礙） | `VehiclePathingSystem : MapComponent`(`:54564`)、`VehiclePathFinder`/`VehicleReachability` 是編譯邏輯 | Harmony patch（謹慎，效能敏感） |
| **自訂 ITab / Designator / WorkGiver / JobDriver** | 引用的 `Type` 必須存在 | 新 C# 類別，再於 XML 引用 |
| **改框架既有行為**（改原版互動、修 bug、改算法） | 純 DLL 無源碼 | Harmony patch（本框架自身重度用 Harmony，相依 brrainz.harmony） |

**風險**：
- 框架純 DLL、無官方源碼，改碼者只能靠反編譯 + Harmony；版本更新（如 1.6.x→下一版）可能改私有結構，patch 易碎。
- 效能敏感區（尋路系統 `:54564` 起）誤 patch 易卡頓。
- `events` / `ActionUpgrade` 的「XML 綁方法名」是**半資料半碼**：資料端可調，但方法簽章固定且須先編譯。

## C. 二分結論（重點問題 5）

- **做「純外觀/數值不同的新載具」：純 XML 可成。** 繼承 `Base*`、配 graphicData/pattern 圖、設 properties/roles/components/comps（用內建 comp 與 Upgrade 子類），不需任何 C#。
- **一定要 C# 的，集中在「全新行為邏輯」**：自訂武器行為、全新 comp 系統、特殊 Reactor/ActionUpgrade、改尋路、改框架既有算法。
- 中間地帶（`events`、`ActionUpgrade`、`designatorTypes`）＝「XML 引用 + DLL 提供 Type/方法」，資料可調但需要碼端先存在對應實作。
