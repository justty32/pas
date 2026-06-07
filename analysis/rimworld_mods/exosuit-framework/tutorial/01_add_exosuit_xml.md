# 教學：純 XML 新增一台機甲 (01_add_exosuit_xml)

## 結論：可以純 XML
新增一台機甲＋一個模組**不需要寫任何 C#**。框架提供了完整抽象範本（`ModuleApparel*` / `ModuleItem*`）、功能 Comp 與整備建築，你只要「繼承範本 + 填欄位 + 掛現成 Comp」。本教學做一台最小可玩機甲：**一個核心 + 一個動力模組**，讓殖民者能在維護坞登機並提升移速。

> 前置：你的 mod 須 `loadAfter` Exosuit Framework（並依賴 Harmony）。研究可沿用框架既有的 `WG_HeavyExoskeleton`。
> 行號依據：`projects/.../decompiled/Exosuit.decompiled.cs`；範本依據 `1.6/Defs/ModuleApparelBase.xml`、`ModuleItemBase.xml`、`FuelCellDefs.xml`。

---

## 心智模型（先記三件事）
1. **機甲＝穿在駕駛員身上的一組 Apparel。** 核心也是 Apparel（`Exosuit_Core`）。
2. **每個模組要寫兩個 ThingDef**：item 形態（搬運/放部件櫃）＋ apparel 形態（穿戴），兩者用 `CompProperties_ExosuitModule` 的 `ItemDef`/`EquipedThingDef` 互指。
3. **核心的 `SlotDef Core` 決定有哪些格**（已內建 Core）；模組用 `occupiedSlots` 占格，`uiPriority` 不可撞號。

---

## 步驟 1：核心模組（item 形態 + apparel 形態）

`MyMod/Defs/ThingDefs/MyExosuitCore.xml`：

```xml
<Defs>
  <!-- 核心：物品形態（造出來、放部件櫃、在維護坞裝上） -->
  <ThingDef ParentName="ModuleItemCore">
    <defName>MyMech_Module_Core</defName>
    <label>my mech core</label>
    <description>A basic exosuit core frame.</description>
    <statBases>
      <MaxHitPoints>300</MaxHitPoints>
      <MarketValue>2000</MarketValue>
      <Mass>40</Mass>
      <WorkToMake>30000</WorkToMake>
    </statBases>
    <costList>
      <Steel>200</Steel>
      <ComponentIndustrial>10</ComponentIndustrial>
    </costList>
    <comps>
      <li Class="Exosuit.CompProperties_ExosuitModule">
        <EquipedThingDef>MyMech_Apparel_Core</EquipedThingDef>
        <ItemDef>MyMech_Module_Core</ItemDef>
        <occupiedSlots><li>Core</li></occupiedSlots>
      </li>
    </comps>
    <recipeMaker>
      <researchPrerequisite>WG_HeavyExoskeleton</researchPrerequisite>
      <recipeUsers><li>FabricationBench</li></recipeUsers>
    </recipeMaker>
  </ThingDef>

  <!-- 核心：盔甲形態（穿在 Dummy/駕駛員身上，提供結構與外觀） -->
  <ThingDef ParentName="ModuleApparelCore">
    <defName>MyMech_Apparel_Core</defName>
    <label>my mech core</label>
    <description>A basic exosuit core frame.</description>
    <graphicData>
      <texPath>Things/MyMech/Core_apparel</texPath>   <!-- 你的機甲身體貼圖 -->
      <graphicClass>Graphic_Single</graphicClass>
    </graphicData>
    <statBases>
      <MaxHitPoints>300</MaxHitPoints>
      <ArmorRating_Sharp>0.6</ArmorRating_Sharp>
      <ArmorRating_Blunt>0.5</ArmorRating_Blunt>
      <Mass>40</Mass>
    </statBases>
    <comps>
      <li Class="Exosuit.CompProperties_ExosuitModule">
        <EquipedThingDef>MyMech_Apparel_Core</EquipedThingDef>
        <ItemDef>MyMech_Module_Core</ItemDef>
        <occupiedSlots><li>Core</li></occupiedSlots>
      </li>
    </comps>
    <modExtensions>
      <li Class="Exosuit.ExosuitExt">
        <BodySizeCap>1.25</BodySizeCap>
        <RequireAdult>true</RequireAdult>
        <minArmorBreakdownThreshold>0.25</minArmorBreakdownThreshold>
        <!-- 選用：要求駕駛服 / 植入物
        <RequiredApparelTag>PilotSuit</RequiredApparelTag>
        <RequiredHediff>MyNeuralLink</RequiredHediff> -->
      </li>
    </modExtensions>
  </ThingDef>
</Defs>
```

要點：
- item 與 apparel 兩個 Def **都掛同一份 `CompProperties_ExosuitModule`**，`EquipedThingDef`/`ItemDef` 互填（依據 `MechUtility.Conversion :11031`）。
- 核心占 `Core` 格（`SlotDef.xml` 的 `Core`，`isCoreFrame=true`）。
- `ExosuitExt` 設駕駛限制（檢查點 `:4951`-`:4984`）。
- 機甲外觀＝apparel 的 `graphicData` 貼圖＋範本內建的 render node（`ModuleApparelBase.xml:99`），框架已 Patch Humanlike render tree（`Patches/PatchRenderNode.xml`）。

---

## 步驟 2：一個動力模組（沿用框架 CompFuelCell）

`MyMod/Defs/ThingDefs/MyExosuitModule.xml`（仿 `FuelCellDefs.xml`）：

```xml
<Defs>
  <ThingDef ParentName="ModuleItemAttachment">
    <defName>MyMech_Module_Engine</defName>
    <label>thruster module</label>
    <statBases><MaxHitPoints>120</MaxHitPoints><Mass>8</Mass><WorkToMake>10000</WorkToMake></statBases>
    <costList><Steel>60</Steel><ComponentIndustrial>4</ComponentIndustrial><Chemfuel>30</Chemfuel></costList>
    <comps>
      <li Class="Exosuit.CompProperties_ExosuitModule">
        <EquipedThingDef>MyMech_Apparel_Engine</EquipedThingDef>
        <ItemDef>MyMech_Module_Engine</ItemDef>
        <occupiedSlots><li>Attachment</li></occupiedSlots>
      </li>
      <li Class="Exosuit.CompProperties_FuelCell">
        <fuelCapacity>150</fuelCapacity><fuelDef>Chemfuel</fuelDef>
        <fuelPerUnit>1</fuelPerUnit><moveSpeedOffset>2</moveSpeedOffset>
        <hediffDef>MF_FuelCellBoost</hediffDef>
      </li>
    </comps>
    <recipeMaker>
      <researchPrerequisite>WG_HeavyExoskeleton</researchPrerequisite>
      <recipeUsers><li>FabricationBench</li></recipeUsers>
    </recipeMaker>
  </ThingDef>

  <ThingDef ParentName="ModuleApparelAttachment">
    <defName>MyMech_Apparel_Engine</defName>
    <label>thruster module</label>
    <graphicData><texPath>Things/Item/Module_A</texPath><graphicClass>Graphic_Single</graphicClass></graphicData>
    <statBases><MaxHitPoints>120</MaxHitPoints><Mass>8</Mass></statBases>
    <equippedStatOffsets><CarryingCapacity>30</CarryingCapacity></equippedStatOffsets>
    <tickerType>Normal</tickerType>
    <comps>
      <li Class="Exosuit.CompProperties_ExosuitModule">
        <EquipedThingDef>MyMech_Apparel_Engine</EquipedThingDef>
        <ItemDef>MyMech_Module_Engine</ItemDef>
        <occupiedSlots><li>Attachment</li></occupiedSlots>
      </li>
      <li Class="Exosuit.CompProperties_FuelCell">
        <fuelCapacity>150</fuelCapacity><fuelDef>Chemfuel</fuelDef>
        <fuelPerUnit>1</fuelPerUnit><fuelConsumptionPerDay>50</fuelConsumptionPerDay>
        <moveSpeedOffset>2</moveSpeedOffset><hediffDef>MF_FuelCellBoost</hediffDef>
      </li>
    </comps>
  </ThingDef>
</Defs>
```

> 動力模組占 `Attachment` 格（`uiPriority=5`，與 Core 不撞號）。`MF_FuelCellBoost` Hediff 是框架內建（`FuelCellDefs.xml`），可直接用或自寫。

---

## 步驟 3（選用）：自訂插槽
若要新增框架沒有的部位插槽，加一個 `Exosuit.SlotDef` 並改核心的 `supportedSlots`（後者建議用 PatchOperation 或在自己的 SlotDef 引用）。最小機甲不需要——內建 6 格已足夠。

---

## 步驟 4：遊戲內驗收流程
1. 研究 `WG_HeavyExoskeleton`（或你的前置）。
2. 建造 **維護坞 `MF_Building_MaintenanceBay`** 並連一個 **模組櫃 `MF_Building_ComponentStorage`**（裝模組必須，`:5755`/`BuildingDefs.xml:188`）。
3. 在製造台造出 `MyMech_Module_Core` 與 `MyMech_Module_Engine`，放進模組櫃。
4. 點維護坞 → `ITab_Exosuit`（`:6011`）→ 先裝 Core 再裝 Engine（殖民者會跑 `WorkGiver_ModuleAtGantry` 把模組裝到內部 Dummy 上）。
5. 在維護坞指派駕駛員（`CompAssignableToPawn_Parking`）。
6. 駕駛員走到維護坞登機（`JobDriver_GetInWalkerCore :4915` → `GearUp :9556`）。畫面上人物變成機甲、移速提升、結構點血條出現（`Gizmo_HealthPanel`）。
7. 回維護坞下機（`GearDown :9578`）。

---

## 常見坑（ConfigError / 行為）
- **`occupiedSlots` 空** → ConfigError「No proper slot」（`:3617`）。每個模組必填。
- **同機甲內模組 `SlotDef.uiPriority` 撞號** → ConfigError「duplicated uiPriority」（`:3621`）。確保各模組占不同格。
- **`EquipedThingDef`/`ItemDef` 沒互填或填錯** → `Conversion()` 回 null，裝/拆模組會壞（`:11031`）。
- **核心 apparel 沒掛 `ExosuitExt`** → 仍可駕駛，但走 fallback 限制（BodySize≤1.25 且成年，`:4986`）。
- **沒連模組櫃** → 維護坞無法選模組安裝（只能選連接櫃中的模組）。
- **想要敵人駕駛機甲**：用 `ModExtForceApparelGen`（`:3969`）掛在 PawnKindDef 上強制生成整套機甲。
