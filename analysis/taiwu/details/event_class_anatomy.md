# 真實事件類剖析 + 事件腳本 API 速查

> 日期：2026-05-23
> 依據：反編譯 base game 三個事件包到 `~/dev/taiwu-src/events/`：
> - `MapPickup`（最簡單，純流程：撿拾→觸發戰鬥）
> - `NewSecretInformationEvent`（中型）
> - `SectMainStoryZhujianPrelude`（鑄劍山莊門派故事，142 檔，帶選項/對話/角色）
> 工具：`ilspycmd -p --nested-directories -o <out> <dll>`。
> 配合 [[event_system_modding]]（總覽：用 `--enable-event-editor` 編輯器路線）一起看。

---

## 1. 一個事件包反編譯後長怎樣

`Taiwu_EventPackage_<Group>.dll` → 命名空間 `<Author>.EventConfig.<NameSpace>`（base game ＝ `ConchShip.EventConfig.Taiwu`）：
- **`Taiwu_EventPackage_<Group>.cs`**：事件包註冊類，繼承 `EventPackage`，ctor 設 `NameSpace/Author/Group` 並把所有事件塞進 `EventList`：
  ```csharp
  public class Taiwu_EventPackage_MapPickup : EventPackage {
      public Taiwu_EventPackage_MapPickup() {
          NameSpace = "Taiwu"; Author = "ConchShip"; Group = "MapPickup";
          EventList = new List<TaiwuEventItem> {
              new TaiwuEvent_261641bf...(),   // 每個事件一個 GUID 命名的類
              new TaiwuEvent_831d1726...(), ...
          };
      }
  }
  ```
- **`TaiwuEvent_<guid>.cs`** × N：每個事件一個類，類名 = `TaiwuEvent_` + GUID（去橫線）。

> 編輯器用 GUID 當事件識別，所以類名是 GUID；事件間用 GUID 互跳。

## 2. `TaiwuEventItem` 解剖（事件本體）

來源：`backend/GameData/Config/EventConfig/TaiwuEventItem.cs`。

**ctor 設定的欄位**（在編輯器裡就是事件的屬性面板）：
| 欄位 | 型別 | 說明 |
|---|---|---|
| `Guid` | Guid | 事件唯一識別 |
| `EventGroup` | string | 所屬群組（=包的 Group） |
| `EventType` | `EEventType` | 事件種類（見下） |
| `TriggerType` | short | 觸發點，取自 `EventTrigger` 常數（見 §5）；`None=0` 表示只能被其他事件 `ToEvent` 跳入 |
| `IsHeadEvent` | bool | 是否為群組「入口事件」（觸發點實際掛載的那個） |
| `ForceSingle` | bool | 是否強制單獨顯示（對話/劇情常 true） |
| `EventSortingOrder` | short | 同觸發點多事件時的優先序 |
| `MainRoleKey`/`TargetRoleKey` | string | 事件涉及的角色槽（如 "Child1"/"Child2"），對應立繪/名字替換 |
| `EventBackground` | string | 背景圖（如 `tex_sectstory_jingang_10`） |
| `EventAudio`/`MaskControl`/`MaskTweenTime`/`EscOptionKey` | — | 演出相關 |
| `EventOptions` | `TaiwuEventOption[]` | 玩家選項陣列（見 §3） |

**5 個可覆寫方法**（abstract/virtual）＝事件的「腳本」：
| 方法 | 時機 | 典型用途 |
|---|---|---|
| `bool OnCheckEventCondition()` | 觸發前 | 回 true 才會出現此事件（**進入條件腳本**） |
| `void OnEventEnter()` | 進入事件 | 主邏輯：發道具、開戰、設參數、跳事件（**進入腳本**） |
| `void OnEventExit()` | 離開事件 | 收尾 |
| `string GetReplacedContentString()` | 顯示內文時 | 動態替換內文（回空＝用語言檔原文） |
| `List<string> GetExtraFormatLanguageKeys()` | — | 內文格式化用的額外語言鍵 |

### 真實範例（MapPickup 的 OnEventEnter，**有實質邏輯**）
`events/MapPickup/.../TaiwuEvent_831d1726....cs`：
```csharp
public override void OnEventEnter() {
    Location val = default;
    if (!ArgBox.Get<Location>("Location", ref val))       // 從參數箱取觸發地點
        throw new Exception("failed to get parameter: Location");
    int num = EventHelper.TriggerLocationFirstPickup(val, false);  // 撿拾，回敵人id或<0
    if (num < 0) { EventHelper.ToEvent(string.Empty); return; }     // 無事→結束
    ArgBox.Set("EnemyCharId", num);                                 // 存參數
    EventHelper.StartCombat(num, 1, "dd66138e-...", ArgBox, true);  // 開戰，戰後跳指定事件
    EventHelper.ToEvent(string.Empty);                              // 流程結束
}
```
入口事件（IsHeadEvent=true）通常很短，只 `EventHelper.ToEvent("<下個事件guid>")` 把流程導到實際內容事件。

## 3. `TaiwuEventOption` 解剖（玩家選項）

`InitOptions()` 內對每個選項掛委派（鑄劍山莊事件 `TaiwuEvent_2936224a...` 實例）：
```csharp
base.EventOptions = new TaiwuEventOption[1] {
    new TaiwuEventOption { OptionKey = "Option_-1532369974", OptionGuid = "3c0fab94-..." }
};
EventOptions[0].OnOptionVisibleCheck    = OnOption1VisibleCheck;     // Func<bool> 是否顯示
EventOptions[0].OnOptionAvailableCheck  = OnOption1AvailableCheck;   // Func<bool> 是否可選(可灰掉)
EventOptions[0].GetReplacedContent      = OnOption1GetReplacedContent;// 動態選項文字
EventOptions[0].OnOptionSelect          = OnOption1Select;           // 選擇後執行(回傳下一事件guid或空)
EventOptions[0].GetExtraFormatLanguageKeys = Option1GetExtraFormatLanguageKeys;
EventOptions[0].DefaultState = 0;
EventOptions[0].OneTimeOnly  = false;                                // 是否只能選一次
```
→ 一個選項 = 文字（語言檔，鍵 `OptionKey`）＋ 可見條件 ＋ 可選條件 ＋ 選擇後腳本（`OnOptionSelect`，回傳要跳的事件 GUID）。

## 4. 內文/文字怎麼來（重要）

事件類裡腳本回傳大多是 `string.Empty`、條件回 `true`——**因為對話內文與選項文字不在 C# 裡，而在語言檔**（`EventLanguages/`，以 `OptionKey`、事件 Guid 為鍵）。`SetLanguage(string[])`（TaiwuEventItem.cs:105）把語言陣列灌進事件內文與各選項。
→ 做 mod 時：C# 管「邏輯與流程」，語言檔管「文字」。編輯器會幫你同時產生兩者。

## 5. `EventTrigger` 觸發類型（事件掛在哪觸發）

`backend/GameData/GameData/Domains/TaiwuEvent/EventTrigger.cs`（short 常數，節選）：
| 值 | 名稱 | 觸發時機 |
|--:|---|---|
| 0 | None | 不自動觸發，只能被 `ToEvent` 跳入 |
| 1 | TaiwuBlockChanged | 太吾移動到新格 |
| 2 | CharacterClicked | 點擊角色 |
| 3–6 | AdventureReach*/EnterNode | 奇遇地圖節點 |
| 12 | TeammateMonthAdvance | 隊友過月 |
| 13 | SameBlockWithTaiwuWhenMonthAdvance | 過月時與太吾同格 |
| 16 | SectBuildingClicked | 點門派建築 |
| 19 | NewGameMonth | 新一月 |
| 23 | CombatOpening | 戰鬥開始 |
| 33 | NpcTombClicked | 點 NPC 墳 |
| …（共 40+，另有 `TriggerMapPickupEvent` 等具名常數） | | 完整見原始碼 |

## 6. `EEventType`（事件種類）
`MainStoryEvent / GlobalCommonEvent / SkillTaskEvent / IdentityEvent / NpcInteractEvent / AdventureEvent / **ModEvent** / TutorialEvent / NoneType`（值依序 0–8）。
> 注意：反編譯看到 base game 事件多寫 `EventType = (EEventType)1` = `GlobalCommonEvent`。mod 自製可用 `ModEvent` 或對應種類。

## 7. 事件腳本 API：`EventHelper`（共 **2082** 個 static 方法）

來源：`backend/GameData/GameData/Domains/TaiwuEvent/EventHelper/EventHelper.cs`（＋同目錄多檔）。數量極大、且很多是特定劇情專用（Baihua*/Fulong*/Wuxian* 等）。**用法：在反編譯源裡 grep 關鍵字找對應 API**，例如：
- 流程：`ToEvent(guid)`、`StartCombat(charId, combatType, afterGuid, argBox, ...)`、`SimulateNpcCombat(...)`
- 參數箱：`ArgBox.Get<T>("key", ref v)` / `ArgBox.Set("key", v)`（跨事件傳值）
- 角色/關係/道具/特徵：`AddFeature`、`ChangeRelation*`、`CheckCharCombatSkill`、`CharacterHasItem*`、`Get*Char*` 等（grep `GiveItem`/`AddItem`/`Relation`/`Taiwu`）
- 條件判斷：大量 `bool Is.../Can.../Check...`（給 `OnCheckEventCondition` 與選項可見/可選用）

> 速查指令：
> `grep -rhE "public static " ~/dev/taiwu-src/backend/GameData/GameData/Domains/TaiwuEvent/EventHelper/*.cs | grep -i <關鍵字>`

## 8. 動手做新事件的對應關係（編輯器欄位 ↔ 反編譯碼）
| 編輯器裡你做的事 | 反編譯碼對應 |
|---|---|
| 新建事件群組 | 一個 `EventPackage` 子類 + 一包 DLL |
| 設事件觸發點/種類/角色/背景 | `TaiwuEventItem` ctor 欄位 |
| 寫「進入條件」 | `OnCheckEventCondition()` 內呼 EventHelper 條件 API |
| 寫「進入腳本」 | `OnEventEnter()`（發物/開戰/跳事件） |
| 加選項＋條件＋腳本 | `TaiwuEventOption` + `OnOptionVisibleCheck/AvailableCheck/OnOptionSelect` |
| 打對話/選項文字 | 語言檔（`EventLanguages/`） |
| 事件互跳 | `EventHelper.ToEvent("<guid>")` |

## 9. 最佳學習法
反編譯任一個結構接近你目標的 base game 事件包當骨架對照：
- 純流程/觸發戰鬥：`MapPickup`
- 門派劇情/對話/多選項/角色：`SectMainStoryZhujianPrelude`（鑄劍山莊，與本專案的流光劍法同門派）
- 其餘 246 個包在 `<遊戲>/Event/EventLib/`，依檔名（MainStory/SectMainStory/Adventure/Marry/Find…）挑。
