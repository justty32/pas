# 教學：純 XML 擴充 RimCities（不寫 C#）

目標：示範三種「零編譯」即可達成的衍生，作為 create 模式起點。所有作法都用獨立 mod + `Patches/`（PatchOperation），不改動 RimCities 安裝檔。

## 前置：你的 mod 需在 loadAfter 加 RimCities

```xml
<!-- About/About.xml -->
<modDependencies><li><packageId>Cabbage.RimCities</packageId>...</li></modDependencies>
<loadAfter><li>Cabbage.RimCities</li></loadAfter>
```

## 範例 1：新增一種「軍械庫」建築（組合既有裝飾器）

新增一個 `GenStepDef`（沿用 C# class `Cities.GenStep_Buildings`），再把它 Patch 進城市管線。無需任何新 C#。

```xml
<Defs>
  <GenStepDef>
    <defName>City_Armory</defName>
    <order>304</order>
    <genStep Class="Cities.GenStep_Buildings">
      <count>1</count>
      <areaConstraints><min>80</min><max>160</max></areaConstraints>
      <wallChance>1.0</wallChance>
      <roomDecorators>
        <li Class="Cities.RoomDecorator_Storage">
          <maxArea>160</maxArea>
          <stockGenerators>
            <li Class="StockGenerator_Category">
              <categoryDef>WeaponsRanged</categoryDef>
              <thingDefCountRange><min>3</min><max>8</max></thingDefCountRange>
              <totalPriceRange><min>2000</min><max>5000</max></totalPriceRange>
            </li>
          </stockGenerators>
        </li>
      </roomDecorators>
      <buildingDecorators><li Class="Cities.BuildingDecorator_Sandbags"/></buildingDecorators>
    </genStep>
  </GenStepDef>
</Defs>
```

把它插進派系城市管線（原版 def 不可直接改，需 PatchOperationAdd）：

```xml
<!-- Patches/AddArmory.xml -->
<Patch>
  <Operation Class="PatchOperationAdd">
    <xpath>/Defs/MapGeneratorDef[defName="City_Faction"]/genSteps</xpath>
    <value><li>City_Armory</li></value>
  </Operation>
</Patch>
```

> 可用的 RoomDecorator：`RoomDecorator_Storage / Bedroom / Centerpiece / Batteries / PrisonCell / HospitalBed / FrozenStorage`；BuildingDecorator：`None / Patio / Sandbags`。範本見 `1.6/Defs/MapGeneration.xml` 既有條目。

## 範例 2：換掉城市裡會出現的傢俱/大型物件

針對既有 GenStepDef 的 `options` 清單做 Patch（加 modded 物件或移除原版）：

```xml
<Patch>
  <Operation Class="PatchOperationAdd">
    <xpath>/Defs/GenStepDef[defName="City_MainBuildings"]/genStep/roomDecorators/li[@Class="Cities.RoomDecorator_Centerpiece"][1]/options</xpath>
    <value><li>YourMod_FancyStatue</li></value>
  </Operation>
</Patch>
```

## 範例 3：改城市交易商品池

`TraderKindDef` 是標準原版 def，直接 Patch `Base_City`（定義於 `1.6/Defs/TraderKinds.xml`）：

```xml
<Patch>
  <Operation Class="PatchOperationAdd">
    <xpath>/Defs/TraderKindDef[defName="Base_City"]/stockGenerators</xpath>
    <value>
      <li Class="StockGenerator_SingleDef">
        <thingDef>YourMod_Goods</thingDef>
        <countRange><min>5</min><max>20</max></countRange>
      </li>
    </value>
  </Operation>
</Patch>
```

## 你「改不到」的（需 C#，見 details/extension_points.md）

- 世界上城市的數量/比例/尺寸 → 是 **mod 設定 UI**（`Config_Cities`），不是 def，玩家自行調或寫 C# 改預設。
- 新的擺放規則、新建築結構、新任務、讓**全新城市 defName 自動出現在世界** → 必須 C#（`WorldGenStep_Cities.GenerateFresh` 的城市清單寫死於 `RimCities.decompiled.cs:5686`）。
