# 教學：用 FFF 做一個最小新內容（純 XML）

目標：示範「掛一個 FFF 的 Comp 就獲得新機制」的最小可行路徑。選用**塗裝/迷彩（Painting）子系統**，因為它對玩家可見、純 XML、所需資產 FFF 已內建（shader＋花紋 png）。

> 前置：你的 mod 要 `About.xml` 宣告 `loadAfter`/`modDependencies` 指向 `AOBA.Framework`，確保 FFF 先載入、其型別與 shader 可用。

## 步驟 1：讓一個建築可上色＋切迷彩

在你的 mod `Defs/` 放一個 ThingDef（或對既有建築 patch 加 comp）：

```xml
<?xml version="1.0" encoding="utf-8"?>
<Defs>
  <ThingDef ParentName="BuildingBase">
    <defName>MyMod_PaintableBunker</defName>
    <label>paintable bunker</label>
    <description>A bunker you can repaint and apply camo to.</description>
    <thingClass>Building</thingClass>
    <category>Building</category>
    <graphicData>
      <texPath>Things/Building/Wall</texPath>   <!-- 換成你的貼圖 -->
      <graphicClass>Graphic_Single</graphicClass>
    </graphicData>
    <statBases><MaxHitPoints>300</MaxHitPoints><Mass>20</Mass></statBases>
    <comps>
      <!-- 引用 FFF 的塗裝 Comp，零 C# -->
      <li Class="Fortified.CompProperties_Paintable">
        <enableCamoSwitch>true</enableCamoSwitch>
        <allowGizmoForBuilding>true</allowGizmoForBuilding>   <!-- 建築要顯示塗裝按鈕 -->
        <defaultCamo>FFF_Camo_Digital</defaultCamo>           <!-- 用 FFF 內建迷彩 -->
      </li>
    </comps>
  </ThingDef>
</Defs>
```

對應型別欄位來源：`CompProperties_Paintable`（`Fortified.decompiled.cs:10942`，含 `defaultColor` / `useFactionColor` / `enableCamoSwitch` / `allowGizmoForBuilding` / `defaultCamo`）。`FFF_Camo_Digital` 是 FFF 內建迷彩（`1.6/Defs/CamoDefs.xml`）。

## 步驟 2（選用）：加一個自訂迷彩花紋

把一張 png 放到 `你的mod/Textures/MyPatterns/Tiger.png`，再宣告：

```xml
<Defs>
  <Fortified.FFF_CamoDef>
    <defName>MyMod_Camo_Tiger</defName>
    <label>tiger camo</label>
    <texPath>MyPatterns/Tiger</texPath>
  </Fortified.FFF_CamoDef>
</Defs>
```

型別：`FFF_CamoDef`（`Fortified.decompiled.cs:12823`，欄位即 `texPath`）。然後可把步驟 1 的 `<defaultCamo>` 換成 `MyMod_Camo_Tiger`。塗裝 shader 由 FFF 的 `FFF_AssetLoader`（`:4190`）自動載入，無需自帶。

## 步驟 3：驗證

1. 啟用 Harmony → AOBA.Framework → 你的 mod（順序）。
2. 開發者模式 → spawn `MyMod_PaintableBunker`。
3. 選取建物，應出現塗裝 gizmo（`CompPaintable` 在 `:10643` 提供），點開 `Dialog_PaintConfig`（`:28646`）可選顏色/迷彩/疊圖。

## 進一步：純 XML 做一座敵營（結構子系統）

若要更進階的純 XML 內容，改走結構生成（見 `architecture/01_structure_generation.md`）：

1. 寫 `Fortified.SymbolDef` 字典（字元 → ThingDef/TerrainDef/PawnKind）。
2. 寫 `Fortified.StructureLayoutDef`：用 `layouts`/`terrainGrid`/`roofGrid` 等字元網格畫出一棟建物。
3. （選用）寫 `Fortified.FFF_CompoundStructureDef` 把多棟組成聚落＋自動加砲塔/守衛（`DefenseConfig`）。
4. 掛到 `GenStepDef`（class `Fortified.Structures.GenStep_FFFStructureGen`）或 `FFF_SettlementDef` 讓它在地圖生成時出現。
5. 加速技巧：遊戲內用 FFF 的匯出工具（`Dialog_ExportStructure` `:35107`）框選現有建物，反向產生 `StructureLayoutDef` XML。

全程零 C#。只有「放置後要跑自訂演算法」時才需新增 `IFFF_GenerationTask` 子類（C#，見 extension_points C 區）。
