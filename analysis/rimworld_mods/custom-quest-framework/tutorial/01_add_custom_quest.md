# 教學：在 CQF 上新增一個自訂任務 / 內容

> 目標讀者：要在 `HaiLuan.CustomQuestFramework`（CQF）基礎上做 create（衍生擴充）的人。
> 行號指 `decompiled/QuestEditor_Library/QuestEditor_Library.decompiled.cs`（簡寫 `:行`）。
> **權威 schema/defName**：先讀 `<MOD>/.QuestEditor_Library/Skill/` 下 4 份作者 SKILL.md（尤其 `cqf-def-catalog`：有效 defName 速查、`cqf-action-condition-dev`：每個 CQFAction 的 XML 欄位）。

## 0. 先決策：純 XML 還是 C#？

| 你要做的 | 路徑 | 證據 |
|---|---|---|
| 新地圖/子地圖、放既有交互物/箱子/陷阱/門、刷怪、對話、用既有效果做流程 | **純 XML**（最省力，90%+ 情況） | `CQFAction` 全可被 `DirectXmlToObject` 反序列化（`:100`）；自訂 Def 由 `CQFQuestDefBootstrap.LoadAll`:8503 載入 |
| 需要一個既有 `CQFAction`/`DialogCondition` 做不到的**新副作用/新判定**（多半是呼叫第三方 mod API） | **C#**（小樣板） | `CQFAndRS.decompiled.cs:29`、`HCFWithCQF.decompiled.cs:67` |

**結論：做擴充的最省力路徑是純 XML。** 只有當你要做一個框架沒有的新動作時才寫 C#，而且 C# 樣板只需 override 3 個方法。

---

## 路徑 A：純 XML 新增任務（推薦）

CQF 任務 = 原版 `QuestScriptDef` + `QuestNode_DoCQFActions`（裝 CQFAction 腳本）+ 可選的自訂地圖/群組 Def。一個獨立子 mod 的目錄：

```
MyQuestMod/
├── About/About.xml          # loadAfter: HaiLuan.CustomQuestFramework
├── LoadFolders.xml
├── 1.6/Defs/
│   ├── QuestScriptDef.xml    # 任務本體
│   ├── CustomMapDataDef.xml  # 任務地圖（選用）
│   └── GroupDataDef.xml      # 刷怪群組（選用）
└── Languages/...             # 翻譯 key
```

> 子 mod 把 Def 放在標準 `Defs/` 即可被 `DefDatabase` 載入；不必走 CQF 內建編輯器的 `Quests/` 存檔路徑（那是給遊戲內編輯器用的）。

### A1. 最小可行 QuestScriptDef（觸發即發消息 + 發信號）

```xml
<?xml version="1.0" encoding="utf-8" ?>
<Defs>
  <QuestScriptDef>
    <defName>MyMod_HelloQuest</defName>
    <rootSelectionWeight>1</rootSelectionWeight>
    <rootMinPoints>0</rootMinPoints>
    <questNameRules><rulesStrings><li>questName->我的第一個 CQF 任務</li></rulesStrings></questNameRules>
    <questDescriptionRules><rulesStrings><li>questDescription->這是用 CQF 純 XML 做的任務。</li></rulesStrings></questDescriptionRules>

    <root Class="QuestNode_Sequence">
      <nodes>

        <!-- 任務一開始就跑這串 CQFAction（inSignal 留空＝立即執行） -->
        <li Class="QuestEditor_Library.QuestNode_DoCQFActions">
          <actions>
            <!-- 顯示一則訊息 -->
            <li Class="QuestEditor_Library.CQFAction_Message">
              <message>任務開始！</message>
              <type>PositiveEvent</type>
            </li>
            <!-- 發一個帶任務前綴的信號，供後續 QuestPart 接收 -->
            <li Class="QuestEditor_Library.CQFAction_SentSignal">
              <signal>Stage1Done</signal>
              <addQuestPrefix>true</addQuestPrefix>
            </li>
          </actions>
        </li>

      </nodes>
    </root>
  </QuestScriptDef>
</Defs>
```

要點：
- `QuestNode_DoCQFActions`（`:32791`）的兩個欄位：`inSignal`（SlateRef，留空＝任務生成時立即跑）與 `actions`（CQFAction 列表）。
- 每個 action 的 `Class` 必填全限定名 `QuestEditor_Library.CQFAction_*`。
- 欄位名以該 class 的 `SaveToXElement()`/`ExposeData()` 為準（**勿憑直覺猜**）。`CQFAction_Message`（`:618`）欄位＝`message`,`type`；`CQFAction_SentSignal`（`:447`）＝`signal`,`signalIsOnlyValidInPart`,`addQuestPrefix`。

### A2. 加上條件分支（技能檢定 → 給獎勵）

```xml
<li Class="QuestEditor_Library.QuestNode_DoCQFActions">
  <actions>
    <li Class="QuestEditor_Library.CQFAction_Condition">
      <conditions>
        <li Class="QuestEditor_Library.DialogCondition_Skill">
          <targetText>Trigger</targetText>   <!-- 對觸發者檢定 -->
          <skill>Intellectual</skill>
          <level>8</level>
        </li>
      </conditions>
      <actions>
        <li Class="QuestEditor_Library.CQFAction_Spawn">
          <targetsText><li>Position</li></targetsText>
          <datas>
            <li>
              <things>
                <li Class="QuestEditor_Library.CQFThingDefCount">
                  <thing>Gold</thing>
                  <count>200~400</count>   <!-- IntRange 用波浪號，勿用 (min,max) -->
                </li>
              </things>
            </li>
          </datas>
        </li>
      </actions>
    </li>
  </actions>
</li>
```

要點：
- `CQFAction_Condition`（`:336`）只有「滿足才執行」，**沒有 else**；要做失敗分支就再寫一個互斥的 `CQFAction_Condition` 配 `DialogCondition_Reversal`（`:5850`）。
- `targetText`（單目標，條件用）vs `targetsText`（多目標，動作用）。常用 target key：`Trigger`（觸發 Pawn）、`CustomThing`（交互物本體）、`Position`（位置）、`Inner`（容器內）、`Target`（群組成員）。
- `Spawn` 的 `count` 用 `min~max`（`CQFThingDefCount`）。技能名見 `cqf-def-catalog` 第八節。

### A3. 加上自訂地圖站點

用 `CustomMapDataDef`（schema 見 `../architecture/01_framework_lifecycle.md` 第三節）定義一張地圖，任務節點用 `QuestNode_RandomCustomMap`（`:33090`）或 `QuestNode_Root_CustomMap`（`:33215`）生成站點。地圖骨架（直接取自作者 `cqf-def-catalog/SKILL.md` 第九節）：

```xml
<QuestEditor_Library.CustomMapDataDef>
  <defName>MyMod_Cellar</defName>
  <size>(47,1,47)</size>
  <fogged>true</fogged>
  <terrainsRect>
    <li><key>Concrete</key><value><li>(2,2,44,44)</li></value></li>
  </terrainsRect>
  <thingDatas>
    <li>
      <def>Wall</def><stuff>Steel</stuff>
      <allRect>
        <li>(2,2,2,44)</li><li>(44,2,44,44)</li>
        <li>(2,44,44,44)</li><li>(2,2,44,2)</li>
      </allRect>
    </li>
  </thingDatas>
  <customThings>
    <li Class="QuestEditor_Library.CustomThingData_CustomMapEntrance">
      <def>QE_SubMap_Burrow</def><position>(23,0,3)</position>
    </li>
    <li Class="QuestEditor_Library.CustomThingData_CustomMapExit">
      <def>QE_Exit</def><position>(23,0,42)</position>
    </li>
  </customThings>
</QuestEditor_Library.CustomMapDataDef>
```

CellRect 格式＝`(minX,minZ,maxX,maxZ)`（左上+右下，**不是** x,z,w,h）。`<stuff>` 規則：石材用砖块名（`BlocksMarble`）、金屬用基礎名（`Steel`）、木用 `WoodLog`；有 `<stuffCategories>` 的 ThingDef 必填 `<stuff>`。既有 `QE_*` 物件 defName 速查見 `cqf-def-catalog` 第五節。

### A4. 必填/常用欄位參照表

| 物件 | 必填 | 常用 | class:行 |
|---|---|---|---|
| `QuestScriptDef` | `defName`, `root` | `rootSelectionWeight`, `questNameRules` | 原版 |
| `QuestNode_DoCQFActions` | `actions` | `inSignal` | `:32791` |
| `CQFAction_Message` | `message` | `type`(MessageTypeDef) | `:618` |
| `CQFAction_SentSignal` | `signal` | `addQuestPrefix`(預設 true), `signalIsOnlyValidInPart` | `:447` |
| `CQFAction_Condition` | `conditions`, `actions` | — | `:336` |
| `CQFAction_Spawn` | `targetsText`, `datas`(LootData) | — | `:1473` |
| `CQFAction_RecordToDatabase` | `targetsText`, `recordKey` | `recordToQuestBase`/`recordToTemporaryBase`/`recordToGlobalBase` | `:4864` |
| `LootData` | — | `chance`, `things`, `categorys`, `pawnDatas`, `specialThingDatas` | `:15175` |
| `CustomMapDataDef` | `defName`, `size` | `fogged`, `terrainsRect`, `thingDatas`, `customThings`, `pawns` | `:18435` |
| `GroupDataDef` | `lord`, `pawns` | — | `:20117` |
| `DialogCondition_Skill` | `skill` | `targetText`, `level` | `:6426` |

> 全量 CQFAction 清單（流程/信號/記錄/生成/Pawn/傳送/伤害…共 100+ 個）與逐欄位說明見作者 `cqf-action-condition-dev/SKILL.md`。

---

## 路徑 B：C# 新增一個全新 CQFAction（只在 XML 做不到時）

最小樣板（對照 `CQFAndRS.decompiled.cs:29` / `HCFWithCQF.decompiled.cs:67`）：

```csharp
using System.Collections.Generic;
using QuestEditor_Library;   // 引用 QuestEditor_Library.dll
using RimWorld; using Verse; using UnityEngine;

namespace MyMod {
    public class CQFAction_MyEffect : CQFAction_Target {
        public string myParam;   // 自訂欄位

        // (選用) 編輯器 UI；若不在遊戲內編輯器裡編可省略
        public override void Draw(ref float y, Rect inRect, float x) {
            base.Draw(ref y, inRect, x);
            CQFEditorTools.DrawLabelAndText_Line(y, "MyParam".Translate(), ref myParam, x, 60f);
            y += 30f;
        }

        // (必填) 實際邏輯：targets 已由 CQFAction_Target.Work 用 targetsText 解析好
        public override void RealWork(Dictionary<string, TargetInfo> targets, Quest quest) {
            foreach (var kv in targets) {
                Thing t = kv.Value.Thing;
                // ... 對目標做事，可呼叫任何 mod 的 API ...
            }
        }

        // (有自訂欄位時必填) 序列化
        public override void ExposeData() {
            base.ExposeData();
            Scribe_Values.Look(ref myParam, "myParam");
        }
    }
}
```

建置：
- 目標框架 `net48`（或 1.4 用 net472），輸出 DLL 放子 mod `Assemblies/`。
- 引用 `<MOD>/1.6/Assemblies/net48/QuestEditor_Library.dll` + RimWorld 的 `Assembly-CSharp.dll`、`UnityEngine.*`。
- 子 mod `About.xml` `loadAfter` CQF（必要時用 `LoadFolders.xml` 的 `IfModActive` 條件掛載，仿 `<MOD>/LoadFolders.xml`）。

之後在 XML 用 `<li Class="MyMod.CQFAction_MyEffect"><myParam>...</myParam>...</li>` 即可，和內建 action 一視同仁。

### 同理可擴充的其他 C# 接點
- 新判定：subclass `DialogCondition`（`:5439`）/ `DialogCondition_Target`（`:6005`），override `IsMet`/判定方法。
- 新物件行為：subclass `InteractableThing`（`:14062`）/ `CustomTrap`（`:13397`）/ `LootBox`（`:14763`），或給普通 ThingDef 掛 `CompActionWorker`（`:12616`，被動觸發）。

---

## 快速校驗清單

- [ ] 每個 action/condition 的 `Class` 是全限定名且存在
- [ ] 欄位名對照 `SaveToXElement()`/`ExposeData()`，不憑直覺猜
- [ ] `IntRange` 用 `min~max`；`CellRect` 用 `(minX,minZ,maxX,maxZ)`
- [ ] 有 `<stuffCategories>` 的 ThingDef 都寫了正確 `<stuff>`
- [ ] defName/skill/category 對照 `cqf-def-catalog`，無 `SteelWall`/`TileFine` 類臆造名
- [ ] 信號有發也有接（`addQuestPrefix` 一致）；記錄目標用同一 `recordKey`
- [ ] 顯示文本走翻譯（`message`/`label`），內部 key（`signal`/`targetsText`/`recordKey`）不翻譯
- [ ] 子 mod `About.xml` `loadAfter` 了 CQF
