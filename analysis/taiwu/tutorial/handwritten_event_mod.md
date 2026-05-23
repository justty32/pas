# 教學：手寫一個事件 mod（不開編輯器）— 深淵崖底撿祕笈範例

> 日期：2026-05-23
> 成品：`~/repo/pas/projects/taiwu/AbyssManualEvent/`，已部署到 `<遊戲>/Mod/AbyssManualEvent/`。
> 需求：深淵地格過月，10% 機率在崖底撿到一本祕笈。
> 前置閱讀：[event_system_modding.md](../details/event_system_modding.md)（總覽）、[event_class_anatomy.md](../details/event_class_anatomy.md)（真實事件剖析）。

---

## 為什麼可以不開編輯器手寫

`TaiwuEventDomain.cs:391-393`：
```csharp
if (!ShowingEvent.TryExecuteScript(_scriptRuntime))   // 有 .twes 腳本就執行它
    ShowingEvent.EventConfig.OnEventEnter();            // 否則 fallback 呼叫 DLL 的 C# 覆寫
```
`TryExecuteScript` 在 `Script == null`（沒有 `.twes`）時回 false。條件也一樣：`CheckCondition()` = `CheckConditionList(Conditions, …) && OnCheckEventCondition()`，`Conditions` 來自 `.twes`、沒有就只看 C# 的 `OnCheckEventCondition()`。
→ **只要不產 `.twes`，遊戲就直接跑我們 DLL 裡的 C# 覆寫方法。** 而且 `LoadPackageScripts` 在 `.twes` 不存在時直接 return、不報錯（`EventScriptRuntime.cs:260`）。

## 載入鏈（後端）

`ModDomain.LoadAllEventPackages()`（ModDomain.cs:100）：
```
對每個已載入 mod：
  eventsDir = <mod>/Events
  對 Config.lua 的 EventPackages 每一項 name：
    載入 <mod>/Events/EventLib/<name>，反射建立 EventPackage 物件
    讀 <mod>/Events/EventScript/<去副檔名>.twes（沒有就略過）
    讀 <mod>/Events/EventLanguages/<去副檔名>_Language_CN.txt
    各 EventManager.HandleEventPackage(package)  ← ModEventManager 收 EEventType.ModEvent
```
重點：**`Config.lua` 的 `EventPackages` 必須列出 DLL 檔名**，否則完全不載。

## 資料夾佈局（部署到 `<遊戲>/Mod/AbyssManualEvent/`）
```
Config.lua                                              ← GBK（前端 Unity/Mono 讀）
Events/
  EventLib/Taiwu_EventPackage_AbyssManual.dll           ← 事件包
  EventLanguages/Taiwu_EventPackage_AbyssManual_Language_CN.txt  ← UTF-8（後端 net6 讀）
```
> **編碼陷阱**：`Config.lua` 由前端 Mono 以系統碼頁(GBK)讀 → 存 GBK；語言檔由**後端 GameData.exe(net6)** 以 UTF-8 讀 → 存 UTF-8。兩個不同進程、不同預設編碼。

## 三個原始碼檔

### 1. 事件包註冊類（`src/EventPackage_AbyssManual.cs`）
```csharp
public class Taiwu_EventPackage_AbyssManual : EventPackage {
    public Taiwu_EventPackage_AbyssManual() {
        NameSpace = "AbyssManual"; Author = "lorkhan"; Group = "AbyssManual";
        EventList = new List<TaiwuEventItem> { new TaiwuEvent_AbyssManual() };
    }
}
```

### 2. 事件本體（`src/TaiwuEvent_AbyssManual.cs`）關鍵
```csharp
// ctor
Guid = Guid.Parse("28a6b398-...");
IsHeadEvent = true;                      // 觸發必須掛 head 事件
EventType = EEventType.ModEvent;         // ModEventManager 只接 ModEvent
TriggerType = EventTrigger.NewGameMonth; // 過月觸發（每月一次）
EventOptions = new TaiwuEventOption[1]{ new(){ OptionKey="Option_1", OptionGuid="c210263c-..." } };

// 進入條件：太吾在「深淵」地格 + 10%
// ⚠️ 機率「每月只骰一次並快取」，不可直接 return CheckProbability(...)，見下方踩雷紀錄。
private int _rolledDate = int.MinValue; private bool _rolledResult;
public override bool OnCheckEventCondition() {
    var taiwu = DomainManager.Taiwu.GetTaiwu();
    if (taiwu == null) return false;
    Location loc = taiwu.GetLocation();
    MapBlockData block = EventHelper.GetMapBlockData(loc.AreaId, loc.BlockId);
    if (block.TemplateId != 124) return false;   // 124 = Abyss（確定性部分直接判）
    int d = DomainManager.World.GetCurrDate();    // 單調遞增；同一過月內兩次評估同值
    if (d != _rolledDate) { _rolledDate = d; _rolledResult = EventHelper.CheckProbability(10); }
    return _rolledResult;                          // 10%，但同月共用同一擲骰
}

// 進入事件：造祕笈、塞給太吾
public override void OnEventEnter() {
    var taiwu = DomainManager.Taiwu.GetTaiwu();
    // ⚠️ CreateSkillBook 參數是「書的物品 id（武學 BookId）」，不是武學 id！見踩雷 3。
    short bookId = Config.CombatSkill.Instance[538].BookId;   // 538=太極劍法 → BookId=682
    ItemKey book = EventHelper.CreateSkillBook(bookId);
    EventHelper.AddItemToRole(taiwu, book, 1);
}
```
其餘覆寫（`OnEventExit`/`GetReplacedContentString`/`GetExtraFormatLanguageKeys`）回空；選項 `OnOptionSelect` 回 `string.Empty`＝結束事件。

### 3. csproj
net6.0、引用 `Backend/` 下 `GameData.dll`/`GameData.Shared.dll`/`GameData.Utilities.dll`/`GameData.Combat.Math.dll`/`Redzen.dll`；`<AssemblyName>Taiwu_EventPackage_AbyssManual</AssemblyName>`。**對實裝版本編譯**（同 [[dual_assembly_type_conflict]] 鐵律）。

## 用到的關鍵 API（都在 `EventHelper`，共 2082 個）
| API | 用途 |
|---|---|
| `DomainManager.Taiwu.GetTaiwu()` | 取太吾 Character |
| `Character.GetLocation()` → `Location{AreaId,BlockId}` | 太吾當前位置 |
| `EventHelper.GetMapBlockData(areaId, blockId)` → `MapBlockData{TemplateId}` | 查地格 template |
| `EventHelper.CheckProbability(int)` | 百分比擲骰（10=10%） |
| `EventHelper.CreateSkillBook(short bookTemplateId)` → `ItemKey` | 造書；**參數是 SkillBook 物品 id ＝ `CombatSkill.Instance[skillId].BookId`，不是武學 id**（見踩雷 3） |
| `EventHelper.AddItemToRole(Character, ItemKey, int amount)` | 把物品給角色 |
| 常數 `Config.MapBlock.DefKey.Abyss = 124` | 深淵地格 |

## 結果
`dotnet build -c Release` → `0/0`，輸出 `Taiwu_EventPackage_AbyssManual.dll`，已部署。

## ⚠️ 踩雷紀錄（2026-05-23 實機）：別在 `OnCheckEventCondition` 放「會變的隨機」
**現象**：事件第一次真正觸發時，後端 log 出現
`event 28a6b398-... has triggered but failed to execute, removed trigger`，事件沒彈出。

**根因**：事件「進入條件」**會被框架評估不只一次**——觸發時一次（過了、進 `_triggeredEventList`），顯示前 `NextEvent()` 再呼一次 `CheckCondition()` 決定顯示哪個（`TaiwuEventDomain.cs:485` → `TaiwuEventItem.cs:82-89` → `OnCheckEventCondition()`）。初版把 `CheckProbability(10)` 直接放條件裡，**第二次重骰、約 90% 失敗** → 沒有事件通過 → 全被當「failed to execute」清掉（`TaiwuEventDomain.cs:496`）。

**修法（方案 2，已套用）**：條件的「確定性部分（深淵地格）」直接判；「隨機部分」以 `DomainManager.World.GetCurrDate()`（單調遞增）為 key **每月只骰一次並快取**，同一過月內多次評估共用同一結果（見上方 §2 程式）。重編部署後事件可正常顯示。

**通則**：`OnCheckEventCondition` 必須**對同一情境冪等**——不可放每次結果會變的東西（隨機、計時、外部可變狀態）。要隨機就「骰一次存起來」，或把隨機放進 `OnEventEnter`（事件已決定顯示後才跑、只跑一次）。

### ⚠️ 踩雷紀錄 2（2026-05-23 實機）：條件裡查地圖前要擋「太吾不在地圖上」
**現象**：100% 測試版下、在**秘境/探索/戰鬥中過月**時，後端**直接崩潰斷線**：
```
System.Exception: Failed to get block at -1 -1
  at MapDomain.GetBlock(-1,-1) → EventHelper.GetMapBlockData(-1,-1)
  at TaiwuEvent_AbyssManual.OnCheckEventCondition() → TaiwuEventItem.CheckCondition()
  at ModEventManager.OnEventTrigger_NewGameMonth()   ← NewGameMonth 每月都會檢查條件
```
**根因**：太吾不在世界地圖上（在秘境/探索/戰鬥）時，`taiwu.GetLocation()` 回 `{-1,-1}`；條件直接 `GetMapBlockData(-1,-1)` → `MapDomain.GetBlock` 找不到 block 丟例外 → 後端進程死亡。`NewGameMonth` 觸發器**每個月**都會呼叫所有 head 事件的條件，所以只要某次過月時太吾正好不在地圖上就會中。

**修法（已套用）**：查地圖前先擋無效位置——
```csharp
Location loc = taiwu.GetLocation();
if (loc.AreaId < 0 || loc.BlockId < 0) return false;   // 不在世界地圖上（秘境/戰鬥）→ 不觸發
MapBlockData block = EventHelper.GetMapBlockData(loc.AreaId, loc.BlockId);
```
**通則**：條件裡呼叫**任何依賴太吾「在地圖上」的 API（位置、地格、鄰格…）前，先確認位置有效**（`AreaId/BlockId >= 0`）。事件條件由後端在各種狀態下被掃描，別假設太吾一定站在世界地圖格上。後端 mod 拋未捕捉例外＝**整個 GameData 進程崩潰斷線**（比前端例外嚴重），務必對外部狀態防呆。

### ⚠️ 踩雷紀錄 3（2026-05-23 實機）：`CreateSkillBook` 的參數是「書 id」不是「武學 id」
**現象**：事件正常彈出、選項可選，但**沒拿到太極劍法**書。
**根因**：`EventHelper.CreateSkillBook(short templateId)` → `ItemDomain.CreateSkillBook`（`:2398`）第一行 `Config.SkillBook.Instance[templateId]`——`templateId` 是 **SkillBook 物品表 id**。初版傳 `538`（太極劍法的 **CombatSkill** id），而 SkillBook 表有 874 項、第 538 項是**別本書** → 造出錯的書（不崩、但不是太極劍法）。
**修法（已套用）**：用武學的 `BookId` 換成正確書 id——
```csharp
short bookId = Config.CombatSkill.Instance[538].BookId;  // 太極劍法 538 → BookId 682（CombatSkillItem.cs:35/276）
ItemKey book = EventHelper.CreateSkillBook(bookId);
EventHelper.AddItemToRole(taiwu, book, 1);
```
**通則**：要發「某武學的書」，先用 `Config.CombatSkill.Instance[skillId].BookId` 換成書 id，別把武學 id 當書 id（遊戲內部發武學書都走 `.BookId`，見 `EventHelper.cs:8530/25707`）。

## 待實機驗證 / 可能要調
- 事件已能觸發顯示（方案 2 修正後）；**`OnEventEnter` 的 `CreateSkillBook(538)`+`AddItemToRole` 仍待首次顯示後確認**——先前 failed to execute 發生在顯示前，OnEventEnter 從未執行過。
- 觸發機率低（每月在深淵 10%），可先把 `TriggerPercent` 暫改 100 快速測顯示與發書。
- 事件彈窗內文/選項顯示依賴語言系統（`SetLanguage` 順序：index0=EventContent、index1=Option_1），顯示空白再核對語言檔。
- 確認 base game「Abyss=124」是可被太吾踏上的地格；若不可進入，改用其他 template 或 `EMapBlockType`。

## 與「編輯器路線」的差異小結
手寫＝只產 DLL（C# 覆寫當邏輯）＋語言檔，省掉 `.twes`；適合「邏輯型/小事件」。編輯器路線＝視覺化＋`.twes` 腳本＋自動產膠水，適合大量對話/分支劇情。兩者都靠 `EventPackages` 註冊、都吃同一套 `EventHelper` API。
