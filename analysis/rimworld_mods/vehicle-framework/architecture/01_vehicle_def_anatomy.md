# 如何定義一台載具 — VehicleDef 逐欄拆解

> 框架本身**不附任何具體可玩載具**，但附了一組 `Base*` 抽象 Def 作為範本。本文以 `1.6/Defs/VehiclesDefs/VehiclePawnBase.xml`（抽象 `BaseVehiclePawn`）為主軸逐欄拆解，並對照反編譯型別（`projects/.../decompiled/Vehicles/Vehicles.decompiled.cs`，以下簡稱 `Vehicles.decompiled.cs`）。
>
> 一台載具實際由**兩個 Def 配對**構成：
> - `VehicleBuildDef`（建築藍圖，玩家在「載具」分類下建造它）→ 建好後依 `thingToSpawn` 生成
> - `VehicleDef`（真正的載具 Pawn 定義）

## 一、VehicleDef 是一種 ThingDef（category=Pawn）

`VehicleDef : ThingDef`（`Vehicles.decompiled.cs:11298`）。所以**所有原版 ThingDef 欄位都能用**（`statBases`、`comps`、`race`、`size`、`graphicData`…），再加上載具專屬欄位。

`VehiclePawnBase.xml` 關鍵骨架：

| XML 欄位 | 值 | 意義 / 對應型別 |
|---|---|---|
| `thingClass` | `Vehicles.VehiclePawn` | 執行期類別＝`VehiclePawn : Pawn`（`:13103`） |
| `category` | `Pawn` | **載具是一種 Pawn**（吃原版 pawn 的生成/選取/繪製管線） |
| `tickerType` | `Normal` | 每 tick 更新 |
| `passability` | `PassThroughOnly` / `pathCost` `250` | 別的東西能否穿過載具 |
| `useHitPoints` | `false` | 載具不用單一 HP，改用**部位健康**（見下） |
| `statBases` | PsychicSensitivity=0、Flammability=0… | 沿用 ThingDef，關閉不適用的原版機制 |
| `statEvents` | `MoveSpeed`/`Mass`/`BodyIntegrity`/`FlightSpeed` 綁 `HealthChanged`/`CargoAdded`… | 何時重算各 stat（`StatCache.EventLister`，`VehicleDef.statEvents`，`:11343`） |
| `inspectorTabs` | `ITab_Vehicle_Health` / `_Passengers` / `_Cargo` | 載具專屬 UI 分頁 |
| `race` | `body=emptyBody`、`thinkTreeMain=Vehicle`、`intelligence=ToolUser`、`fleshType=MetalVehicle`、`doesntMove=true` | 用空身體 + **載具專屬 ThinkTree**（`Defs/ThinkTree/ThinkTree_Vehicle.xml`）取代原版 pawn AI |
| `comps` → `CompAttachBase` | | 掛接基底 |
| `drawGUIOverlay` | `true` | 顯示頭頂資訊 |

> 海上載具範本 `VehicleSeaPawnBase.xml`：在 `properties` 裡用 `defaultImpassable`(Terrain/Biomes) + `customTerrainCosts AllowTerrainWithTag="Water" PathCost="1"` + `customBiomeCosts`(Ocean/Lake=1) 把「只能走水」表達為**純資料**。

## 二、載具專屬欄位群（VehicleDef 上的新欄位）

對應 `class VehicleDef`（`Vehicles.decompiled.cs:11298` 起）：

| XML 欄位 | C# 型別 / 行號 | 說明 |
|---|---|---|
| `type` | `VehicleType`(Sea/Air/Land/Universal)，`:11321`/列舉`:50413` | 行駛域；舊名 `vehicleType`（LoadAlias） |
| `vehicleCategory` | `VehicleCategory`(Transport/Trader/Combat/Work, Flags)，`:11318`/`:50326` | 用途分類（影響 AI 取用） |
| `navigationCategory` | `NavigationCategory`(Manual/Opportunistic/Automatic)，`:11324`/`:50308` | 自動駕駛程度 |
| `enabled` | `VehicleEnabled.For`(Player/Raiders/Everyone)，`:11303`/`:50354` | 誰能擁有此載具 |
| `nameable` | bool，`:11306` | 可否命名 |
| `combatPower` | float，`:11311` | 襲擊點數權重（敵方載具） |
| `canCaravan` | bool，`:11316` | 可否加入商隊/世界地圖 |
| `vehicleStats` | `List<VehicleStatModifier>`，`:11313`/類別`:10364` | 載具專屬 stat（如 CargoCapacity、FlightSpeed） |
| `buildDef` | `VehicleBuildDef`，`:11326` | 反向指回建造藍圖 |
| `graphicData` | `GraphicDataRGB : GraphicDataLayered`，`:11329`/`:38157` | 多層 RGB 著色貼圖（支援 pattern 重染色） |
| `properties` | `VehicleProperties`，`:11333`/類別`:16950` | **行駛/地形/碰撞/座位**核心束（見三） |
| `npcProperties` | `VehicleNPCProperties`，`:11335`/`:7328` | 敵方 NPC 使用設定 |
| `drawProperties` | `VehicleDrawProperties`，`:11338`/`:11965` | 繪製細節（圖示路徑、overlay、座位 pawn 繪製位置） |
| `fishingProperties` | `FishingProperties`，`:11340` | 釣魚（MayRequire odyssey/VCEF，選用） |
| `kindDef` | `PawnKindDef`，`:11358` | 載具作為 pawn 的 kind |
| `components` | `List<VehicleComponentProperties>`，`:11360`/類別`:8850` | **部位健康清單**（見四） |
| `soundOneShotsOnEvent` / `soundSustainersOnEvent` | `:11345`/`:11347` | 事件音效（IgnitionOn→DraftOn…） |
| `events` | `SimpleDictionary<VehicleEventDef, List<DynamicDelegate<VehiclePawn>>>`，`:11349` | **資料驅動的事件鉤**（XML 綁方法名） |
| `designatorTypes` | `List<Type>`，`:11351` | 自訂 designator（需 C# 類別存在） |

## 三、VehicleProperties — 行駛/地形/座位核心束

`class VehicleProperties`（`Vehicles.decompiled.cs:16950`），是 `<properties>` 標籤內容：

- **地形/路徑成本（純資料）**：`customTerrainCosts` / `customBiomeCosts` / `customRoadCosts` / `customHillinessCosts` / `customRiverCosts` / `customWeatherCosts` / `customThingCosts`（皆 `SimpleDictionary`，`:16993–17011`）、`offRoadMultiplier`(`:17001`)、`winterCost`(`:17017`)、`worldSpeedMultiplier`(`:17021`)、`defaultImpassable`(`:16991`)。
- **碰撞**：`pawnCollisionMultiplier`(`:16962`)、`pawnCollisionRecoilMultiplier`(`:16966`)。
- **行為**：`diagonalRotation`(`:16970`)、`manhunterTargetsVehicle`(`:16973`)、`canFish`(`:16956`)、`empStuns`/`canAdaptToEmp`(`:16978/16985`)、`restrictToFactions`(`:17023`)。
- **座位（重點）** `roles`：`List<VehicleRole>`（`:17026`）。

### VehicleRole — 一個座位角色
`class VehicleRole`（`:17141`）：

| 欄位 | 行號 | 說明 |
|---|---|---|
| `key` | 17143 | 角色識別字串 |
| `label` | 17145 | 顯示名 |
| `handlingTypes` | 17147 | `HandlingType`(None/Movement/Turret, Flags，`:50302`)＝此座位負責駕駛還是操砲 |
| `slots` | 17149 | 座位數 |
| `slotsToOperate` | 17151 | 需幾人才能讓此功能運作（如駕駛至少 1 人才能動） |
| `turretIds` | 17155 | 此座位可操作的砲塔 id 清單（對應 `CompProperties_VehicleTurrets.turrets` 的 turret key） |
| `hitbox` | 17157 | 座位在載具上的受擊範圍（被打中時傷害此座位乘客） |
| `exposed` / `chanceToHit` | 17159/17161 | 是否暴露在外、被命中機率 |
| `pawnRenderer` | 17164 | 乘客在載具上如何繪製 |

> 執行期對應 `VehicleRoleHandler`（`:17448`，IThingHolder，真正裝乘客的容器）。

## 四、VehicleComponentProperties — 部位健康（取代單一 HP）

`class VehicleComponentProperties`（`Vehicles.decompiled.cs:8850`），是 `<components>` 內每個 `<li>`：

| 欄位 | 行號 | 說明 |
|---|---|---|
| `key` / `label` | 8853/8855 | 部位識別與顯示名 |
| `health` | 8859 | 該部位血量 |
| `depth` | 8861 | `VehiclePartDepth`（外層/內層） |
| `hitbox` | 8873 | 部位佔載具哪塊區域（決定被哪個方向擊中） |
| `armor` | 8867 | `List<StatModifier>` 各傷害類型護甲 |
| `empSeverity` | 8869 | EMP 影響等級 |
| `categories` | 8875 | `List<VehicleStatDef>`：此部位損壞影響哪些 stat（如引擎壞了 MoveSpeed 降） |
| `efficiency` | 8877 | `LinearCurve`：血量比例→功能效率曲線 |
| `reactors` | 8880 | `List<Reactor>`：被擊中時的反應（爆炸/起火等，**內建 Reactor 子類即可純 XML，特殊反應需 C#**） |

執行期對應 `VehicleComponent`（`:8542`，IExposable），每個部位獨立記血量、算效率。

## 五、可加掛的 VehicleComp（功能 comp，寫在 `<comps>`）

皆繼承 `VehicleCompProperties : CompProperties`（`:21906`），對應 comp `VehicleComp : ThingComp`（`:21817`）。在 `<comps>` 內以 `<li Class="...">` 加入：

| CompProperties | 行號 | 提供功能 | 關鍵欄位 |
|---|---|---|---|
| `CompProperties_FueledTravel` | 19495 | 燃料/電力行駛 | `fuelType`、`fuelCapacity`、`fuelConsumptionRate`、`electricPowered`/`dischargeRate`/`chargeRate` |
| `CompProperties_VehicleTurrets` | 19853 | 武裝 | `turrets`(`List<VehicleTurret>`)、`deployTime`、deploy 音效 |
| `CompProperties_VehicleLauncher` | 17770 | 飛行/空降世界移動 | `rateOfClimb`、`maxAltitude`、`landingAltitude`、`fuelConsumptionWorldMultiplier` |
| `CompProperties_UpgradeTree` | 21047 | 升級樹 | `def`(`UpgradeTreeDef`) |

> `VehicleDef.ResolveReferences`（`:11455`）會把這些 comp 快取成具名屬性 `CompPropsFueledTravel`/`CompPropsVehicleTurrets`/`CompPropsVehicleLauncher`/`CompPropsUpgradeTree`（`:11381–11387`）。有 UpgradeTree 時自動加上 `ITab_Vehicle_Upgrades` 分頁（`:11459-11462`）。

## 六、升級樹（純資料即可，內建效果類別豐富）

- `CompProperties_UpgradeTree.def` → `UpgradeTreeDef : Def`（`:34361`）→ `List<UpgradeNode>`。
- `UpgradeNode`（`:34057`）：`key`/`gridCoordinate`(節點座標)/`researchPrerequisites`/`prerequisiteNodes`/`ingredients`(成本)/`upgrades`(`List<Upgrade>`)。
- `Upgrade`(abstract，`:33552`) 內建子類**多為純資料**：
  - `StatUpgrade`(`:33250`)：改 stat（Add/Set）
  - `CompUpgrade`(`:32967`)、`SettingsUpgrade`(`:33045`)、`SoundUpgrade`(`:33148`)
  - `TurretUpgrade`(`:33463`)：加/換砲塔
  - `VehicleUpgrade`(`:33587`)：含 `RoleUpgrade`(`:33636`) 可改座位
  - `ActionUpgrade`(`:32933`)：觸發行為（較需 C# 配合）

→ 多數「升級樹」內容（加血、加速、加砲）可**純 XML** 用內建 Upgrade 子類完成。
