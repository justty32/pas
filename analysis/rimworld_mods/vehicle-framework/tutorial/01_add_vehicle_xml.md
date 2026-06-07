# 教學：用純 XML 新增一台載具

> 目標：在不寫任何 C# 的前提下，做出一台「外觀/數值不同」的可建造載具。
> 前提：你的 mod 把 Vehicle Framework 設為相依（About.xml `modDependencies` 列 `SmashPhil.VehicleFramework`、`loadAfter` 列之）。
> 參考範本：`1.6/Defs/VehiclesDefs/VehiclePawnBase.xml`、`VehicleSeaPawnBase.xml`、`Buildable_Vehicle.xml`。
> 型別/行號依據見 `analysis/.../architecture/01_vehicle_def_anatomy.md`。

## 心智模型
一台載具＝**兩個 Def 配對**：
1. `VehicleBuildDef`（玩家在「載具」建造分類下蓋的藍圖建築）
2. `VehicleDef`（建好後生成的真正載具 Pawn）
兩者透過 `VehicleBuildDef.thingToSpawn` ↔ `VehicleDef.buildDef` 互指。

## 最小步驟清單

### 步驟 0：準備資產
- 載具主體貼圖（放 `Textures/Things/Vehicle/MyTruck/...`），以及至少能用內建 `Default` PatternDef 染色的圖層。
- （選用）建造完成圖示、cargo 圖示。

### 步驟 1：寫 VehicleBuildDef（建造藍圖）
繼承內建 `VehicleBaseBuildable`（陸）或 `VehicleBoatBaseBuildable`（海）：
```xml
<Vehicles.VehicleBuildDef ParentName="VehicleBaseBuildable">
  <defName>MyTruck_Blueprint</defName>
  <label>my truck (build)</label>
  <description>A small cargo truck.</description>
  <thingToSpawn>MyTruck</thingToSpawn>            <!-- 指向下面的 VehicleDef -->
  <graphicData>
    <texPath>Things/Vehicle/MyTruck/MyTruck</texPath>
    <graphicClass>Graphic_Single</graphicClass>
  </graphicData>
  <costList><Steel>200</Steel><ComponentIndustrial>4</ComponentIndustrial></costList>
  <researchPrerequisites><li>Smithing</li></researchPrerequisites>
  <soundBuilt>Standard_Build</soundBuilt>
</Vehicles.VehicleBuildDef>
```

### 步驟 2：寫 VehicleDef（載具本體）
繼承 `BaseVehiclePawn`（陸）或 `BaseSeaVehicle`（海）：
```xml
<Vehicles.VehicleDef ParentName="BaseVehiclePawn">
  <defName>MyTruck</defName>
  <label>my truck</label>
  <description>A small cargo truck.</description>
  <buildDef>MyTruck_Blueprint</buildDef>
  <type>Land</type>
  <vehicleCategory>Transport</vehicleCategory>
  <enabled>Everyone</enabled>
  <size>(2,3)</size>

  <graphicData>                                    <!-- GraphicDataRGB，多層染色 -->
    <texPath>Things/Vehicle/MyTruck/MyTruck</texPath>
    <graphicClass>Vehicles.Graphic_Vehicle</graphicClass>
    <drawSize>(2,3)</drawSize>
  </graphicData>

  <vehicleStats>                                   <!-- VehicleStatModifier -->
    <MoveSpeed>4.5</MoveSpeed>
    <CargoCapacity>300</CargoCapacity>
    <BodyIntegrity>1</BodyIntegrity>
  </vehicleStats>

  <properties>                                     <!-- VehicleProperties -->
    <visibilityWeight>1.0</visibilityWeight>
    <roles>                                        <!-- 座位 VehicleRole -->
      <li>
        <key>driver</key>
        <label>Driver</label>
        <handlingTypes>Movement</handlingTypes>     <!-- 駕駛 -->
        <slots>1</slots>
        <slotsToOperate>1</slotsToOperate>          <!-- 要 1 人才能動 -->
      </li>
      <li>
        <key>passenger</key>
        <label>Passenger</label>
        <slots>3</slots>                            <!-- 純乘客，不需 handlingTypes -->
      </li>
    </roles>
  </properties>

  <components>                                     <!-- 部位健康 VehicleComponentProperties -->
    <li>
      <key>engine</key>
      <label>Engine</label>
      <health>120</health>
      <depth>Internal</depth>
      <categories><li>MoveSpeed</li></categories>   <!-- 引擎壞→影響移速 -->
    </li>
    <li>
      <key>body</key>
      <label>Body</label>
      <health>300</health>
      <depth>External</depth>
    </li>
  </components>

  <comps>
    <li Class="Vehicles.CompProperties_FueledTravel">  <!-- 燃料行駛 -->
      <fuelType>Chemfuel</fuelType>
      <fuelCapacity>200</fuelCapacity>
      <fuelConsumptionRate>1.2</fuelConsumptionRate>
    </li>
  </comps>
</Vehicles.VehicleDef>
```

### 步驟 3（選用）：武裝
在 `<comps>` 加 `Vehicles.CompProperties_VehicleTurrets`，內含 `turrets`（每個 `VehicleTurret` 給 `key`），再在某個 `VehicleRole` 的 `<turretIds>` 列出該 key，讓某座位能操砲。砲塔細節另定 `Vehicles.VehicleTurretDef`。

### 步驟 4（選用）：升級樹
- 寫 `Vehicles.UpgradeTreeDef`（含 `UpgradeNode` 清單，用內建 `StatUpgrade`/`TurretUpgrade`/`VehicleUpgrade` 等）。
- 在 `<comps>` 加 `Vehicles.CompProperties_UpgradeTree` 並把 `def` 指向它（框架會自動掛出 `ITab_Vehicle_Upgrades` 分頁）。

### 步驟 5（選用）：新塗裝
新增 `Vehicles.PatternDef`（`defName`/`label`/`path`），玩家即可在載具上選用，純資料。

## 驗收
- 進遊戲後在建造選單「載具」分類找到 `MyTruck_Blueprint`，蓋好後變成可駕駛載具。
- 派 pawn 進 driver 座位 → 可徵召移動；無燃料則動不了。
- 引擎部位被打壞 → 移速下降（驗證 `components.categories` 生效）。

## 什麼時候會撞牆（要改 C#）
- 想要砲塔有「非標準開火行為」、全新 comp 系統、特殊部位 Reactor、自訂尋路 → 見 `details/extension_points.md` B 節。
