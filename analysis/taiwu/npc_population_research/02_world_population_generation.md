# 整個世界的人口是如何生成的（數量／比例設定來源）

> 版本綁定：實裝版 **0.0.79.60**。
> 反編譯參考源：`~/dev/taiwu-src/backend/`（較舊、可能漂移）。
> 實裝核對 DLL：
> - 後端 `~/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/Backend/GameData.dll`
> - 後端共享 `…/Backend/GameData.Shared.dll`
> 工具：`~/.dotnet/tools/ilspycmd -t <型別> <DLL>`。
>
> **核對狀態圖例**：✅實裝DLL核對過 ／ 📄僅看反編譯舊源（語意級、低風險）。
> **重大版本漂移已標紅**（見 A／C 的 worldPopulationFactor 除數）。

---

## TL;DR（一句話）

開新世界時，全世界 NPC 由 `OrganizationDomain.CreateSettlementMembers` 逐「聚落 × 9 階位」批量生成；
**每階位生成幾個「核心人物」＝該階位的 `OrganizationMemberItem.Amount`**（再乘世界人口係數），
每個核心人物又會連帶生出兄弟姊妹／配偶／子女／情人。
性別由 `OrganizationMemberItem.Gender` 控制：`-1`＝50/50 隨機，否則強制該性別。
「人數」與「階位模板（稱謂／武學）」是**同一個結構** `OrganizationMemberItem`，由 `OrganizationItem.Members[grade]`（`short[9]`，存的是**模板 ID 不是人數**）指向。

---

## A. 世界人口生成的總機制

### A-1. 總入口與順序

開新世界總入口：`WorldDomain.CreateWorld(DataContext, WorldCreationInfo)`
- 反編譯：`backend/GameData/GameData/Domains/World/WorldDomain.cs:734`
- 實裝 ✅：`GameData.Domains.World.WorldDomain.CreateWorld`（GameData.dll）順序一致。

執行順序（`CreateWorld` 體內，:737~743）：
1. `SetWorldCreationInfo(...)` — 寫入玩家在開局選的世界設定（含**人口類型** `WorldPopulationType`，:750）。
2. `context.SwitchRandomSource(_worldId)` — 切到世界專屬隨機源（決定論種子）。
3. `DomainManager.Map.CreateAllAreas(context)` — **這一步生成全世界聚落與其常住 NPC**。
4. `DomainManager.Character.CreatePregeneratedCityTownGuards(context)` — 預生成「城鎮守衛」隨機敵人池。
5. `DomainManager.Character.CreatePregeneratedRandomEnemies(context)` — 預生成「隨機敵人」池。
6. `DomainManager.Extra.CreatePregeneratedFixedEnemies(context)` — 預生成「固定敵人」。

> 注意：4/5/6 是「模板池」（供日後隨機刷怪／鏢局守衛等引用），**不是常住人口**。常住人口全在第 3 步。

### A-2. 地圖→州→區→聚落的展開（第 3 步內部）

`MapDomain.CreateAllAreas`（`backend/.../Map/MapDomain.cs:3666`，實裝 ✅ 同型別同名）：
- 先 `CreateStateAreas`（:3782）建立 **15 個州 × 每州 3 個區**（:3802 `for stateId 0..15`，:3807 `for stateAreaIndex 0..3`）。
  - 每州 3 區的 areaTemplate：`0→MainAreaID(主城)`、`1→SectAreaID(門派區)`、`2→第三區`（:3810-3815，欄位來自 `MapStateItem`）。
- 各區呼叫 `CreateNormalArea`（:3858），其中：
  - `settlementCount = areaConfigData.OrganizationId.Length (+太吾村1)`（:3879）——**一個區裡有幾個聚落，由該 area 設定的 `MapAreaItem.OrganizationId[]` 陣列長度決定**。
  - 迴圈 :4093 `for i4 = settlementCount-1 .. 0`，逐聚落取 `orgTemplateId = areaConfigData.OrganizationId[i4]`（:4099；太吾村固定 16、劇情寨固定 38）。
  - `DomainManager.Organization.CreateSettlement(context, location, orgTemplateId)`（:4101）真正建立聚落。
- 之後另建 4 個特殊區：bornArea(135 出生地)、guideArea(136 引導)、secretVillageArea(137)、brokenPerformArea(138 破碎劇情寨)（:3731-3772）。

### A-3. 單一聚落的建立：`OrganizationDomain.CreateSettlement`

`backend/.../Organization/OrganizationDomain.cs:2023`（實裝 ✅ GameData.dll 同名 :2102 附近）：
```
if (IsSect(orgTemplateId))  → new Sect(...);            AddElement_Sects;  CreateSettlementMembers(...)
else                        → new CivilianSettlement(...); AddElement_CivilianSettlements; CreateSettlementMembers(...)
```
- **門派與平民聚落走同一條人口生成函式** `CreateSettlementMembers`，只是 org 設定不同（見 C）。
- 另有 `CreateEmptySects`（:2007）：對**每個 IsSect 的 OrganizationItem** 建一個「Location=(-1, index)」的空殼 sect 物件（不在地圖上、無成員），這是「門派實體先佔位」的機制，與地圖上實際生成成員的 sect 不同；由 `MapDomain.cs:3560` 呼叫。

### A-4. 人口總量／各聚落人口數的來源

- 「世界要不要在這個 org 生成常住人口」的開關：`OrganizationItem.Population`（`int`，config 欄位）。
  `CreateSettlementMembers` 開頭 :2174（反編譯）／實裝 ✅ `if (organizationItem.Population <= 0) return;`——`Population <= 0` 的 org 不生成常住成員（例如 None=0、敵人模板 org 等）。
  - 欄位定義：`backend/GameData/Config/OrganizationItem.cs:21 public readonly int Population;`
  - ⚠️ 注意：這個 `Population` 在生成階段**只當「是否生成」的布林閘**用，**不是直接決定生成幾人**；實際人數看各階位的 `OrganizationMemberItem.Amount`（見 C/D）。聚落執行期的 `CivilianSettlement.Population / MaxPopulation / StandardOnStagePopulation`（`CivilianSettlement.cs:220/232/244` 的 setter）是另一組執行期統計欄位，由 `RecordSettlementStandardPopulations`（實裝 GameData.dll OrganizationDomain :950 附近）在生成後統計實際在場人數寫入，而非反向決定生成數。
- **全世界人口縮放係數**：`WorldDomain.GetWorldPopulationFactor()`
  - 反編譯 :6993／實裝 ✅ `GameData.dll WorldDomain :7462`：
    `return WorldCreation.Instance[(byte)5].InfluenceFactors[_worldPopulationType];`
  - 即：人口係數＝config 表 **`WorldCreation` 第 5 號項目的 `InfluenceFactors[人口類型]`**。人口類型 `_worldPopulationType` 是玩家開局選的設定（`SetWorldPopulationType`，WorldDomain.cs:8795；預設 0，見 :8487）。
  - 數值（各人口類型對應的百分比係數）**不在 C# 常數，而在 `WorldCreation` config 表**（ConfigData 資源，見最後「數值來源」一節）。

---

## B. 性別比例

### B-1. 決定性別的那一行

核心人物的性別：`OrganizationDomain.CreateCoreCharacter`
- 反編譯 `backend/.../Organization/OrganizationDomain.cs:2258`
- 實裝 ✅ `GameData.dll OrganizationDomain :2337`：
```csharp
sbyte gender = ((info.CoreMemberConfig.Gender == -1) ? Gender.GetRandom(random) : info.CoreMemberConfig.Gender);
```
- 讀的設定欄位：**`OrganizationMemberItem.Gender`（sbyte）**
  - 欄位定義反編譯 `backend/GameData/Config/OrganizationMemberItem.cs:29 public readonly sbyte Gender;`
  - 實裝 ✅ `GameData.Shared.dll Config.OrganizationMemberItem :29`。
- 語意：
  - `Gender == -1`（`Gender.Unknown`）→ 呼叫 `Gender.GetRandom(random)`。
  - 否則 → **強制**為該值（0=女 / 1=男）。

### B-2. 隨機時是不是 50/50？→ 是，硬性 50/50

`Gender.GetRandom`：
- 反編譯 `backend/GameData.Shared.Enum/GameData/Domains/Character/Gender.cs:20`：
```csharp
public static sbyte GetRandom(IRandomSource random) => (sbyte)random.Next(2);
```
- 常數定義同檔 :9 `Female = 0`、:11 `Male = 1`、:7 `Unknown = -1`。
- **沒有任何機率/比例參數**——`random.Next(2)` 即 0/1 等機率，固定 50/50。**沒有 `GenderProb` 之類的可調欄位**（已搜尋確認無）。

### B-3. 不同情境的性別差異

性別差異**完全來自各情境讀哪個 `Gender` 欄位**，機率仍是「強制 or 50/50」二選一，沒有中間比例：

| 情境 | 函式 / 位置 | 性別決定 |
|---|---|---|
| 門派核心成員 / 平民核心人物 | `CreateCoreCharacter`（反編 :2258 ／實裝 ✅ :2337） | 讀**該階位** `OrganizationMemberItem.Gender`；`-1`→50/50，否則強制 |
| 兄弟姊妹 | `CreateBrothersAndSisters`（反編 :2323 ／實裝 :2402） | 讀**兄弟階位**(`BrotherGrade`)的 `OrganizationMemberItem.Gender`；同上規則 |
| 配偶 | `CreateSpouse`（反編 :2403） | `Gender.Flip(核心人物性別)`——配偶必為異性 |
| 情人 | `CreateLover`（反編 :2447） | `Gender.Flip(核心人物性別)`——必為異性 |
| 子女 | `CreateChildren` | 子女性別走遺傳/隨機（在 CreateChildren 內，未逐行展開） |

> 結論：**全遊戲只有「強制某性別」與「50/50 隨機」兩種**，沒有可調的偏斜比例。
> 「某門派全是女性/男性」是靠該門派各階位 `OrganizationMemberItem.Gender` 設成 0 或 1（亦可參考 `OrganizationItem.GenderRestriction`，`OrganizationItem.cs:37`，用於入門限制與石碑分配 `GetBestMatchingOrgTemplateId` :2100）。

---

## C. 門派人數 vs 普通人人數

### C-1. `OrganizationItem.Members` 是 short[9]，但存的是「模板 ID」不是「人數」（重要澄清）

- 欄位：`backend/GameData/Config/OrganizationItem.cs:71 public readonly short[] Members;`（實裝 ✅ 同名）。
- 用法見 `CreateSettlementMembers` :2192：`short orgMemberId = orgConfig.Members[grade];` 接著 `OrganizationMember.Instance[orgMemberId]` 取出 `OrganizationMemberItem`。
- **所以 `Members[grade]` ＝「第 grade 階位該用哪個 `OrganizationMemberItem` 模板」的索引**，不是該階位人數。人數另在模板的 `Amount` 欄位（見 D）。
  - （補充：`OrgMemberCollection Members`——`Settlement.cs:60 protected OrgMemberCollection Members;`——才是「執行期實際成員集合」，與 config 的 `OrganizationItem.Members[9]` 同名但完全不同物。）

### C-2. 一個門派／聚落生成多少人

主流程 `OrganizationDomain.CreateSettlementMembers`：
- 反編譯 `backend/.../Organization/OrganizationDomain.cs:2148`
- 實裝 ✅ `GameData.dll OrganizationDomain :2227`

核心迴圈（實裝 ✅ 版本）：
```csharp
sbyte b2 = (sbyte)((orgTemplateId != 16) ? 8 : 7);     // 太吾村(16)最高階7，其餘到8
for (sbyte b3 = b2; b3 >= 0; b3--) {                    // 9 階位由高到低
    short index = organizationItem.Members[b3];
    OrganizationMemberItem organizationMemberItem = OrganizationMember.Instance[index];
    if (organizationMemberItem.Amount > 0) {
        int num = organizationMemberItem.Amount;
        if (!organizationMemberItem.RestrictPrincipalAmount) {
            num = Math.Max(1, num * worldPopulationFactor / 125);   // ★實裝版
        } else if (members2.Count > 0) {
            num -= members2.Count;
        }
        for (int i = 0; i < num; i++) {
            CreateCoreCharacter(context, info);          // 1 個核心人物
            CreateBrothersAndSisters(context, info);     // + 兄弟姊妹
            CreateSpouseAndChildren(context, info);      // + 配偶 + 子女(+情人)
            info.CompleteCreatingCharacters();
        }
    }
}
```

> 🔴 **重大版本漂移**：
> - 反編譯舊源（:2201）：`coreMembersAmount = coreMembersAmount * worldPopulationFactor / 100;`（除 100、無下限）
> - **實裝 0.0.79.60（✅ GameData.dll :2227 體內）：`num = Math.Max(1, num * worldPopulationFactor / 125);`（除 125、且至少 1 人）**
> 兩者不同！要算實際人數務必用 **/125** 並套 `Math.Max(1,…)`。

所以「核心人物數」公式（非 RestrictPrincipalAmount 的階位）：
```
核心人物數 = max(1,  OrganizationMemberItem.Amount × worldPopulationFactor ÷ 125)
```
- `worldPopulationFactor` 是百分比（預設人口下會是某個基準值，來自 `WorldCreation[5].InfluenceFactors`）。
- `RestrictPrincipalAmount == true` 的階位（如掌門等「定額職位」）**不乘係數**，固定 `Amount`（若已有既存成員則補差額），見 :2199-2206。

而且每個核心人物還會「滾雪球」生出一家人：
- `CreateBrothersAndSisters`（:2305）：兄弟姊妹數 = `RedzenHelper.NormalDistribute(random, 1, 1, 1, 3)`（常態分布，1~3 人；太吾村上限 2），階位用 `OrganizationMemberItem.BrotherGrade`。
- `CreateSpouseAndChildren`（:2364）：婚配率 `min((年齡-20)×10, 90)%`；成婚則 `CreateSpouse`（+10% 機率 `CreateLover`），再依生育力機率 `CreateChildren`。
- **因此實際總人口遠大於各階位 `Amount` 之和**（一個核心人物可帶出配偶＋1~3 兄弟姊妹＋若干子女）。

### C-3. 平民／散人的數量 vs 門派成員——同一套還是分開？

**同一套**。`CreateSettlement` 對 sect 與 civilian 都呼叫 `CreateSettlementMembers`（:2032 / :2039），同樣走「9 階位 × Amount」迴圈。差異只在 config：
- 平民聚落 org（如 `OrganizationItem.IsCivilian`，:29）也有 `Members[9]` 指向各自的 `OrganizationMemberItem`，各階位 `Amount` 決定平民人數。
- 平民聚落沒有「門派劇情階位升降」（`GetExpectedCoreMemberAmount` 對非 sect 直接回 `orgMemberCfg.Amount`，見 D-3），生成邏輯與門派一致只是參數不同。
- 「真正無門派的散人」：地圖上每個常住 NPC 都掛在某個 settlement 的 org 下（包含平民聚落 org=平民身份）；劫匪/隨機敵人等非常住者走 A-1 的第 4/5/6 步「預生成池」與後續刷怪，不屬 `CreateSettlementMembers`。

---

## D. 九個階位的人數

### D-1. 每階位生成幾個人＝該階位 `OrganizationMemberItem.Amount`

- 由 C-2 迴圈可見：階位 `grade` 的核心人物數，就是 `OrganizationItem.Members[grade]` 指向的 `OrganizationMemberItem.Amount`（再依非定額階位乘 `worldPopulationFactor/125`）。
- `OrganizationMemberItem` 欄位（反編譯 `backend/GameData/Config/OrganizationMemberItem.cs`，實裝 ✅ `GameData.Shared.dll Config.OrganizationMemberItem`）：
  - :19 `sbyte Grade` — 屬於哪一階位（0~8）。
  - :21 `sbyte Amount` — **平時人數**。
  - :23 `sbyte UpAmount` — 門派劇情任務「上行」狀態時的人數。
  - :25 `sbyte DownAmount` — 「下行」狀態時的人數。
  - :27 `bool RestrictPrincipalAmount` — true＝定額職位（不乘人口係數、不超額）。
  - :15 `string GradeName` — 階位稱謂。
  - :79 `List<PresetOrgMemberCombatSkill> CombatSkills` — 預設武學。
  - 還有 :29 `Gender`、:33 `DeputySpouseDowngrade`、:35 `ChildGrade`、:37 `BrotherGrade`、:71 `InitialAges` 等。

### D-2. 「人數」與「階位模板（稱謂/武學）」是同一個結構

**是同一個 `OrganizationMemberItem`**。它同時承載：
- 階位身份模板：`GradeName`、`CombatSkills`、`Equipment`、`InitialAges`、性別…
- 該階位人數：`Amount` / `UpAmount` / `DownAmount`。

`OrganizationItem.Members[9]`（short[9]）只是「9 個階位各指向一個 `OrganizationMemberItem` 模板 ID」的對照表。人數**沒有另設別處**，就在模板的 `Amount` 系列欄位。

### D-3. 掌門(Grade8)固定 1 人嗎？階位人數是寫死還是公式？

- **不是引擎硬寫死「掌門=1」**，而是該門派 Grade8 的 `OrganizationMemberItem.Amount` 在 config 設為 1、且 `RestrictPrincipalAmount=true`（定額、不乘係數）。各階位人數**全部來自 config 表的 `Amount`/`UpAmount`/`DownAmount`**，不是 C# 算式。
- 唯一的「公式」是門派劇情狀態切換 `GetExpectedCoreMemberAmount`：
  - 反編譯 `backend/.../Organization/Settlement.cs:634`，實裝 ✅ `GameData.dll Settlement.GetExpectedCoreMemberAmount`（逐行一致）：
  ```csharp
  if (!orgCfg.IsSect || orgMemberCfg.RestrictPrincipalAmount) return orgMemberCfg.Amount;
  result = GetSectMainStoryTaskStatus(OrgTemplateId) switch {
      1 => orgMemberCfg.UpAmount,    // 門派任務「上行」
      2 => orgMemberCfg.DownAmount,  // 「下行」
      _ => orgMemberCfg.Amount,      // 平時
  };
  ```
  即「期望人數」會隨門派主線任務狀態在 `Amount/UpAmount/DownAmount` 間切換，**值仍全來自 config**。
  - （注意：初次世界生成 `CreateSettlementMembers` 用的是裸 `Amount × factor/125`；劇情升降的 `Up/DownAmount` 主要在過月維護階段才透過 `GetExpectedCoreMemberAmount` 生效。）

### D-4. 過月時如何維持各階位人數（UpdateOrganizationMembers）

過月總入口 `WorldDomain.AdvanceMonth` → 在 `WorldDomain.cs:8279`（實裝 ✅ 同型別）呼叫 `OrganizationDomain.UpdateOrganizationMembers`。
- `UpdateOrganizationMembers`（反編譯 OrganizationDomain.cs:1393）：對每個 sect / civilian 呼叫 `settlement.UpdateMemberGrades(context)`（:1404 / :1425）。
- `Settlement.UpdateMemberGrades`（`Settlement.cs:305`）內 :443 呼叫 `RecruitOrCreateLackingMembers(context)` —— **這才是逐階位補人的地方**：
  - `Sect.RecruitOrCreateLackingMembers`（`Sect.cs:253`）／`CivilianSettlement.RecruitOrCreateLackingMembers`（`CivilianSettlement.cs:108`）：
  ```
  for grade 8..0:
      orgMemberCfg = OrganizationMember.Instance[organizationCfg.Members[grade]];
      expectedAmount = GetExpectedCoreMemberAmount(orgMemberCfg);   // D-3 公式
      recruitCount  = expectedAmount - GetPrincipalAmount(grade);   // 缺額
      重複 recruitCount 次：CreateCoreCharacter(...)（招募或新生）
  ```
  （`CivilianSettlement.cs:122-139`、`Sect.cs:263-304` 為對應段落。）
- 維持方式＝**每月對每階位算「期望人數 − 現有正式成員」，缺多少補多少**（招募現有 NPC 或新建）。期望人數仍由 D-3 的 config `Amount/Up/Down` 決定。

---

## 數值設定的來源（C# 常數？config 表？）

- **生成「演算法／流程」在 C#**（上述全部方法體，已對實裝 DLL 核對）。
- **所有「數量／比例的數值」在 ConfigData 資源表，不是 C# 常數**：
  - `Config.Organization : ConfigData<OrganizationItem, sbyte>`（實裝 ✅ `GameData.Shared.dll Config.Organization:11`）——各 org 的 `Population`、`Members[9]`、`GenderRestriction` 等。
    具名存取器確認 TemplateId 對照：1=少林…15=雪後、16=太吾、17=Heretic、18=Righteous（Shared DLL :100~134）。
  - `Config.OrganizationMember : ConfigData<OrganizationMemberItem, short>`——各階位的 `Amount/UpAmount/DownAmount/Gender/Grade/CombatSkills/GradeName…`。
  - `Config.WorldCreation`——`[5].InfluenceFactors[人口類型]` 即世界人口係數百分比。
- ConfigData 載入機制（實裝 ✅ `GameData.Shared.dll Config.Common.ConfigData\`2`）：
  - `Init()`（:34）只 `_refNameMap.Load(GetType().Name)`；實際 `_dataArray`（:14）由外部序列化資源反序列化（`OrganizationItem` 的多參數建構式被資料填入），數值在資源檔不在程式碼。
  - 提供 mod 注入點：`AddExtraItem(identifier, refName, configItem)`（:50）、`AddOrModifyItem(configItem)`（:71）、`_extraDataMap`（:16）。

---

## mod 若要調整這些比例／人數，該改哪裡（初步判斷）

| 目標 | 改法 | 切入點 |
|---|---|---|
| 改某門派/平民某階位**人數** | **config 注入**：`AddOrModifyItem` 替換該 `OrganizationMemberItem`，調 `Amount`（及 `UpAmount/DownAmount`） | `Config.OrganizationMember.AddOrModifyItem`（ConfigData :71）。沿用既有 `ConfigData.AddExtraItem` 注入模式 |
| 改**全世界人口縮放** | config：改 `WorldCreation[5].InfluenceFactors`；或開局 `SpecifyWorldPopulationType` | `WorldDomain.GetWorldPopulationFactor`／`SpecifyWorldPopulationType`(WorldDomain.cs:6954) |
| 改**性別**（讓某階位偏某性別） | config：把該階位 `OrganizationMemberItem.Gender` 設 0/1（強制）或 -1（50/50） | `OrganizationMemberItem.Gender` |
| 想要**非 50/50 的隨機性別偏斜** | **必須 Harmony patch**（config 無此參數）：patch `OrganizationDomain.CreateCoreCharacter` 改寫 `Gender.GetRandom(random)` 那行（實裝 GameData.dll :2337） | Harmony，因為機率寫死在 C# `random.Next(2)` |
| 改**人口公式本身**（除數 125、是否乘係數、雪球家庭規模） | **Harmony patch** `OrganizationDomain.CreateSettlementMembers` / `CreateBrothersAndSisters` / `CreateSpouseAndChildren` | Harmony，公式在方法體內 |
| 新增**自訂門派並控制其人數/階位** | config 注入新 `OrganizationItem`（含 `Members[9]` 指向新建 `OrganizationMemberItem`）＋對應 area 的 `OrganizationId` | 參考既有陳家堡作法（player_faction_research/） |

> 一句話：**「數量/比例的數值」幾乎都能用 ConfigData 注入（AddOrModifyItem）改；只有「50/50 寫死」「除數 125 公式」「雪球家庭規模」這些寫在 C# 方法體內的，要 Harmony patch。**

---

## 核對狀態總表

| 項目 | 反編譯位置 | 實裝核對 |
|---|---|---|
| `CreateWorld` 流程順序 | WorldDomain.cs:734 | ✅ |
| `CreateSettlementMembers` 9階位迴圈 | OrganizationDomain.cs:2148 | ✅ GameData.dll :2227 |
| 人口係數除數 | 舊源 `/100` | 🔴 實裝為 `Math.Max(1, … /125)`（✅） |
| 性別決定行 | OrganizationDomain.cs:2258 | ✅ GameData.dll :2337 |
| `Gender.GetRandom`=Next(2) | Gender.cs:20 | 📄（語意極穩，未單獨反編；常數已見） |
| `GetWorldPopulationFactor` | WorldDomain.cs:6993 | ✅ GameData.dll :7462 |
| `GetExpectedCoreMemberAmount` | Settlement.cs:634 | ✅ GameData.dll 同名 |
| `OrganizationMemberItem` 欄位 | OrganizationMemberItem.cs | ✅ GameData.Shared.dll |
| `OrganizationItem.Members=short[]` 模板ID | OrganizationItem.cs:71 | ✅（Members[grade] 用法 + ConfigData 結構） |
| 過月補人 `UpdateOrganizationMembers→RecruitOrCreateLackingMembers` | OrganizationDomain.cs:1393 / Settlement.cs:443 / 8279 | 📄（語意級；流程錨點未逐行重核） |
| ConfigData 載入/注入 (`AddOrModifyItem`/`AddExtraItem`) | — | ✅ GameData.Shared.dll ConfigData\`2 |

> 待補（若要更精確）：把實際 config 數值（各門派 Grade8 `Amount` 是否=1、`WorldCreation[5].InfluenceFactors` 的具體百分比）從 ConfigData 資源 dump 出來核對——本次只確認了「數值在 config 表、不在 C#」，未逐筆 dump 數值。
