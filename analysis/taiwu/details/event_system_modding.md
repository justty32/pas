# 調查：如何做「添加新事件」的 mod

> 日期：2026-05-23
> 問題：想做一個「添加新事件」的 mod，該怎麼做？
> 一句話結論：**走官方「遊戲內事件編輯器」路線**——以 `--enable-event-editor` 啟動參數開啟編輯器，視覺化建事件＋寫 C# 腳本片段，編輯器自動產生並編譯成事件包 DLL、註冊到 `Config.Lua` 的 `EventPackages`。**這跟武學 mod（手寫 YAML＋C# 特效類）是完全不同的兩條路。**
> 來源：`~/dev/taiwu-src/Assembly-CSharp/EventEditor/*`、`~/dev/taiwu-src/backend/GameData/GameData/Domains/TaiwuEvent/*`、`~/dev/taiwu-src/Assembly-CSharp/ModManager.cs`、實裝 `<遊戲>/Event/`、`<遊戲>/.../StreamingAssets/EventScriptsTemplates/`。
> ⚠ 反編譯源為 0.0.76.43，實裝為 0.0.79.60；本文為架構性說明，動手做時具體型別/欄位仍需對實裝 DLL 核對（見 [[dual_assembly_type_conflict]] 的版本綁定教訓）。

---

## 1. 為什麼是「用編輯器」而不是手寫

太吾繪卷內建一套**官方視覺化事件編輯器**（`Assembly-CSharp/EventEditor/` 下數十個 UI 類：`UI_EventEditor`、`EventEditorEventList`、`EventEditorScript`、`Export`、`Load`…）。它把事件做成一套 DSL：

- 一個**事件群組**＝一個事件包（EventPackage），編譯成一個 DLL。
- 每個**事件**＝一個 `TaiwuEventItem` 子類（C# class）。
- 編輯器負責把你拉的圖＋寫的腳本，套 template 產生 C# 並呼叫遊戲自帶的編譯器（`<遊戲>/Event/EventCompiler/`）編成 DLL，還會自動生一堆膠水碼（`EventManagerBase.cs`、`EventTrigger.cs`、`TaiwuEventDomain_TriggerDistribute.cs`、`EventOption/ConditionId.cs`、`OptionConditionMatcher.cs`——見 `EventEditor/Export.cs:847-1155`）。

> 結論：**手寫不切實際**（膠水碼很多且彼此關聯），請用編輯器。編輯器才是官方支援、也是基礎遊戲自己用來做主線/門派故事的工具。

## 2. 啟用事件編輯器

`Game.cs:366` 解析啟動參數 `--enable-event-editor`；啟用後 `Game.EnableEventEditor=true`、版本號加 `-event-editor` 後綴（`Game.cs:393-395`）。

- **Steam**：遊戲 → 內容 → 啟動選項，填 `--enable-event-editor`（或用 `TaiwuLauncher.exe` 對應選項）。
- 啟用後主選單會出現事件編輯器入口（`AdventureEventEditorHelper.cs`、`UI_EventEditor.cs`）。

## 3. 事件系統的資料模型（後端 `GameData.Domains.TaiwuEvent`）

- **`EventPackage`**（`backend/GameData/Config/EventConfig/EventPackage.cs`）：抽象類，欄位 `NameSpace / Author / Group / ModIdString`，`Key = "{NameSpace}_{Author}_{Group}"`，內含 `List<TaiwuEventItem>`，並有 `InitLanguage(語言檔)`。
- **`TaiwuEventItem`**（事件本體，C# class，繼承見 template）：一個事件 = 進入條件 + 進入腳本 + 一組**選項 `EventOption`**；每個選項有「可見條件 / 可選條件 / 選項腳本 / 消耗（`_cost.twe`）」。
- **腳本片段種類** `EScriptType`（`EventEditor/EScriptType.cs`）：`GlobalScript`、`EventEnterScript`、`EventConditionList`、`OptionScript`、`OptionAvailableConditionList`、`OptionVisibleConditionList`。
- **執行期**：後端有 `EventScriptRuntime`、`ScriptExecutionInstance`、`EventCondition(List)`、`EventTrigger`、甚至 `Decompiler/`——事件腳本在後端進程執行。

### 事件種類 `EEventType`（`backend/GameData.Shared/.../TaiwuEvent/Enum/EEventType.cs`）
`MainStoryEvent / GlobalCommonEvent / SkillTaskEvent / IdentityEvent / NpcInteractEvent / AdventureEvent / **ModEvent** / TutorialEvent / NoneType`
→ mod 自製事件主要用 **`ModEvent`**（`TaiwuEvent.cs:264` 有對 ModEvent 的專門處理），也可做 `AdventureEvent`（奇遇）、`NpcInteractEvent`（NPC 互動）等。

### 事件 C# 骨架（template）
`<遊戲>/.../StreamingAssets/EventScriptsTemplates/TaiwuEventTemplate.template`：
```csharp
${BaseUsing}${AdvancedUsing}${CustomUsings}
namespace ${ModAuthor}.EventConfig.${ModNamespace} {
    public class ${EventName} : TaiwuEventItem {
        ${Ctor}
        ${CustomFields}
        #region EventAPI
        ${EventAPI}
        #endregion
        #region Options
        ${Options}
        #endregion
    }
}
```
腳本可用的 API 命名空間（`Export.cs:16` BaseUsing/AdvancedUsing）很廣：`GameData.Domains.TaiwuEvent.EventHelper`、`Character`、`Combat`、`CombatSkill`、`Item`、`World`、`Map`、`Adventure`、`Relation`、`SectMainStory` 等——幾乎能讀寫整個遊戲狀態。

## 4. 檔案佈局（mod 端）

`ModManager.cs:108-112, 1449-1499` 定義路徑常數：
- 編輯器專案資料：`<mod>/EventEditorData/`（含 `EventEditorConfig/`、`EventCore/`、`GlobalScripts/`、`EventTextures/`、`SimulateEnvironment/`、`ExportCacheFiles/{ExportEvents, EventLanguages}/`）。
- 匯出來源：`EventScript/`（`.cs`、`.twes` 事件群組專案、`_cost.twe` 選項消耗）。
- **編譯產物：`EventLib/Taiwu_EventPackage_<Group>.dll`**（`EventCompileDllFilesFolder="EventLib"`）。
- 執行期核心：`Events/`。
- **`Config.Lua` 的 `EventPackages`**（`ModManager.cs:947`）：列出此 mod 提供的事件包 Key；遊戲據此載入 `EventLib/` 下對應 DLL。

## 5. 直接可學的真實範例（最有價值）

基礎遊戲**自己**就是用這套做的，事件包 DLL 全在 `<遊戲>/Event/EventLib/Taiwu_EventPackage_*.dll`（數十個），例如：
- `Taiwu_EventPackage_SectMainStoryZhujianPrelude.dll` / `...ZhujianEpitasis.dll`（**鑄劍山莊**門派故事——正好跟你的流光劍法同門派）
- `Taiwu_EventPackage_AdventureEvent`、`...FindTreasureEvents`、`...MarryQingZhou`、`...FindBlackBear` 等奇遇/婚姻/探索事件。

→ 用 `ilspycmd` 反編譯任一個來學「事件類怎麼寫、腳本怎麼呼叫 EventHelper API」，是最快的學法（與 [[feedback-analysis-docs-not-authoritative]] 一致：讀真實碼，不要只靠文件）。
另：`<遊戲>/Event/EventCompiler/`＝遊戲自帶的事件編譯器；`StreamingAssets/EventScriptsTemplates/*.template`＝產碼模板。

## 6. 建議工作流程

1. Steam 啟動選項加 `--enable-event-editor`，進遊戲開事件編輯器。
2. 新建（或選現有）mod → 建事件群組（= 一個 EventPackage）。
3. 加事件：設觸發/種類（`ModEvent` 等）、進入條件、進入腳本、選項（文字＋可見/可選條件＋腳本＋消耗）。
4. 用編輯器的「模擬環境(SimulateEnvironment)」測試。
5. 匯出/編譯 → 產生 `EventLib/Taiwu_EventPackage_<Group>.dll`，編輯器自動寫入 `Config.Lua` 的 `EventPackages`。
6. 正常啟動遊戲、開啟該 mod 實測。

## 7. 與武學 mod 的對比 / 注意事項

| 面向 | 武學 mod（已完成的 MySwordArt） | 事件 mod |
|---|---|---|
| 作法 | 手寫 YAML + C# 特效類，自己 `dotnet build` | 用遊戲內編輯器視覺化 + C# 腳本片段，編輯器產碼/編譯 |
| 產物 | `Plugins/*.dll` + YAML | `EventLib/Taiwu_EventPackage_*.dll` + `EventEditorData/` |
| Config.Lua | `BackendPlugins`/`FrontendPlugins` | `EventPackages` |
| 入門難度 | 中（要懂 backend/frontend 雙 assembly、型別漂移） | 低～中（編輯器代勞膠水碼，但腳本仍是 C#） |

注意：
- 事件腳本＝C#，在**後端進程**跑，可呼叫的 API 與武學特效同源（`GameData.Domains.*`）。
- 版本綁定一樣重要：事件包 DLL 由遊戲自帶編譯器對**當前版本**編；換版本可能要重匯出/重編。
- 仍可手寫（不開編輯器）硬刻 `TaiwuEventItem` 子類塞進 backend plugin，但要自己補 EventManager/Trigger/ConditionMatcher 膠水，極不划算——除非只是想在既有事件上掛 Harmony patch 微調。

## 8. 待釐清（若要實際動手再深入）
- 編輯器匯出的 `.twes` 專案檔精確 JSON 結構（`EventEditor/Export.cs`、`Load.cs`、`EventGroupData.cs`）。
- `EventPackages` 在 Config.Lua 內每一項的精確寫法（字串 Key 還是物件）——動手前讀一個現成事件 mod 或 base game 的 Config 對照。
- `EventTrigger` 如何把事件掛到觸發點（過月/進地圖/互動），與各 `EEventType` 的觸發條件 API。
- 事件語言/本地化檔（`EventLanguages/`）格式。
