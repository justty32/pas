# 教學：新增一個 outpost（純 XML）

> 本教學回答「想在 VOE 基礎上做一些 outpost」的最常見情形：**定時產出某資源、運回主基地**。這種完全不必寫 C#。
> 互動服務型（砲擊/攔截/科研/招募）才需 C# 子類，見文末。

## 觀念前提
- outpost 的引擎在 VEF 的 `Outposts.dll`；預設世界物件類別 `Outposts.Outpost` 已內建完整生產／配送。
- 你只要宣告一個 `WorldObjectDef ParentName="OutpostBase"`，掛一個 `Outposts.OutpostExtension` modExtension，框架就會：
  - 自動把它加進 caravan 的「建立 outpost」選單（Harmony patch，`decompiled-framework/Outposts.decompiled.cs:491`）；
  - 自動依條件檢查可否在該地形建立；
  - 自動每 `TicksPerProduction` 產出 `ResultOptions` 並配送回家。

## 最小可行範例
一個「香草園 outpost」：定時產出 `RawPotatoes`，數量隨在營人數與種植技能放大。
```xml
<?xml version="1.0" encoding="utf-8"?>
<Defs>
  <WorldObjectDef ParentName="OutpostBase">
    <defName>YourMod_Outpost_Garden</defName>
    <label>garden outpost</label>
    <description>一個自治菜園營地，定時把收成運回主基地。沙漠不可設置。</description>
    <expandingIconTexture>WorldObjects/OutpostFarming</expandingIconTexture>
    <!-- 不寫 worldObjectClass：沿用 OutpostBase 預設的 Outposts.Outpost -->
    <modExtensions>
      <li Class="Outposts.OutpostExtension">
        <DisallowedBiomes>
          <li>Desert</li>
          <li>ExtremeDesert</li>
        </DisallowedBiomes>
        <RequiresGrowing>true</RequiresGrowing>
        <TicksPerProduction>1800000</TicksPerProduction>  <!-- 約 30 天 -->
        <RequiredSkills>
          <Plants>6</Plants>
        </RequiredSkills>
        <ProvidedFood>MealSimple</ProvidedFood>
        <ResultOptions>
          <li>
            <Thing>RawPotatoes</Thing>
            <BaseAmount>100</BaseAmount>
            <AmountPerPawn>50</AmountPerPawn>
            <AmountsPerSkills>
              <Plants>3</Plants>   <!-- 每位 pawn 每點種植 +3 -->
            </AmountsPerSkills>
          </li>
        </ResultOptions>
      </li>
    </modExtensions>
  </WorldObjectDef>
</Defs>
```
- 放進你自己的 mod：`<yourmod>/1.6/Defs/WorldObjectDefs/YourOutposts.xml`。
- About.xml 加相依：`brrainz.harmony`、`OskarPotocki.VanillaFactionsExpanded.Core`、`vanillaexpanded.outposts`（後者選用——若你只要框架可只依賴 VEF；要沿用 VOE 的貼圖/事件才依賴 VOE），並 `loadAfter` 它們。
- `expandingIconTexture` 可重用 VOE 既有貼圖（如上 `WorldObjects/OutpostFarming`），或放自己的圖到 `Textures/`。

## 產量公式（記住這個就會調平衡）
> 來源：`ResultOption.Amount`，`decompiled-framework/Outposts.decompiled.cs:2058`
```
產量 = ( BaseAmount
        + AmountPerPawn × 在營人數
        + Σ(AmountsPerSkills 每技能: Count × 全員該技能等級總和) )
        × ProductionMultiplier(mod 設定，預設 1)
```
- 想要「人越多越多」→ 調 `AmountPerPawn`。
- 想要「技能越高越多」→ 用 `AmountsPerSkills`。
- 想要「高階產物需門檻」→ 該 ResultOption 加 `MinSkills`（未達門檻則此項不產）。

## 給玩家「選產出」的下拉（選用）
若想讓玩家在建立後切換產物（像 VOE 的 production/farming outpost）：
- `worldObjectClass` 改成 `Outposts.Outpost_ChooseResult`（`:2489`）。
- modExtension 改用 `Outposts.OutpostExtension_Choose`，多填 `ChooseLabel` / `ChooseDesc`，並把多個候選放進 `ResultOptions`。
- 範例見原 mod `Defs/WorldObjectDefs/Outposts.xml` 的 `Outpost_Production`。

## OutpostExtension 欄位速查
> 完整表見 `details/outpost_extension_fields.md`。最常用：

| 欄位 | 型別 | 作用 |
|---|---|---|
| `ResultOptions` | list | 產出清單（核心） |
| `TicksPerProduction` | int | 生產週期 tick；**-1＝不生產**（服務型） |
| `RequiredSkills` | AmountBySkill | 建立門檻（如 `<Plants>10</Plants>`） |
| `AllowedBiomes`/`DisallowedBiomes` | list BiomeDef | 地形白/黑名單 |
| `MinPawns` | int | 最少入駐人數 |
| `CostToMake` | ThingDefCountClass | 建立時消耗物資 |
| `ProvidedFood` | ThingDef | 餵養在營 pawn 的食物（預設 MealSimple） |
| `RequiresGrowing` | bool | 需可耕作季節/地形 |
| `TicksToPack` | int | 拔營打包耗時 |
| `Event` | HistoryEventDef | 加入時觸發的 ideology 事件 |

## 什麼時候非寫 C# 不可
當行為不是「產 Thing」而是互動服務時，需自訂 `worldObjectClass`（繼承 `Outposts.Outpost`）並覆寫對應方法，封進你自己的 DLL：
- 覆寫 `Produce()`（`:988`）：改寫每週期行為（如直接加研究點數，見 `VOE.Outpost_Science`）。
- 覆寫 `GetCaravanGizmos()`（`:1141`）：加自訂按鈕（如砲擊，見 `VOE.Outpost_Artillery`，`decompiled/VOE.decompiled.cs:60`）。
- `TicksPerProduction` 設 `-1` 讓框架不跑預設生產，全交給你的邏輯。
- 可參考 VOE 既有 10 個子類當範本（`projects/rimworld_mods/vanilla-outposts-expanded/decompiled/VOE.decompiled.cs`）。
