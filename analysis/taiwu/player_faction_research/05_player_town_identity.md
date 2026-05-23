# 05 — 太吾在城鎮取得身份與權利（調查留檔）

> 任務：查清「讓太吾在某城鎮取得身份、獲得權利（再給城鎮建設產業視圖）」這一側的原版支撐。
> 事實來源：反編譯參考源 `~/dev/taiwu-src/backend/`（grep/瀏覽，舊版）；關鍵方法級結論已對實裝 0.0.79.60 DLL 反編譯驗證（前端 `Assembly-CSharp.dll`、後端 `GameData.dll`，並用 `/tmp/cjb_decomp/WorldMapModel.cs`/`BuildingModel.cs` 前端實裝反編譯交叉核對）。
> 本檔僅為調查留檔，非權威；結論逐項回原始碼覆核並標 path:line。
> 建築/產業視圖「建設端」細節由另一支 agent（`01_building_production_view.md`）負責；本檔聚焦「身份與權利」這一側，並指出它如何連到建設權。

---

## 0. 一句話總結

太吾繪卷**沒有獨立的「城鎮身份/官職/城主」資料模型**。城鎮治理＝「聚落綁一個 `OrgTemplateId`（門派/組織），由其 grade-8 `Principal` 成員當領導」。
玩家對城鎮的「身份」只能透過通用的 **`OrganizationInfo`（成員身份：哪個組織+位階+是否嫡傳+哪個聚落）** 表達——它是「成員身份」而非「擁有者身份」。
而玩家「在某地能建設/管理產業」這個**權利的真正承載，是後端 `BuildingDomain._taiwuBuildingAreas`（一個 `List<Location>`）**，原版只有「太吾村起始區那一格」會被加進去（`[0]` 即太吾村）。
⇒ 「取得城鎮身份 → 獲得建設權」在原版是**兩條獨立的軌**：身份走 `OrganizationInfo`，建設權走 `_taiwuBuildingAreas`/太吾村座標判定。要做這個 mod，最小切入＝**直接擴充建設權那條軌（把目標城鎮 location 塞進 `_taiwuBuildingAreas`）**，身份旗標只是用來「合理化/觸發」這件事的包裝。

---

## 1. 城鎮 / 聚落的治理模型

### 1.1 聚落本體 `Settlement`（抽象類）— 無「OwnerId / 城主」單一欄位
`GameData/GameData/Domains/Organization/Settlement.cs:27`（`abstract class Settlement : BaseGameDataObject`）。
持久化欄位（`:30-72`）只有：`Id`、`OrgTemplateId`（綁定的門派/組織模板）、`Location`、`Culture/MaxCulture`、`Safety/MaxSafety`、`Population/MaxPopulation`、`Members`（成員集合）、`LackingCoreMembers`、`ApprovingRateUpperLimitBonus`、`InfluencePowerUpdateDate`。
- **沒有 `OwnerId` / `ControllerId` / 城主欄位**。grep backend 全源「城主/治理/統治/領主/Governor/Ruler/Lord/OwnerId/ControllerId」只命中敏感詞表（`Config/SensitiveWords.cs`）與物品 owner（`ItemOwnerKey`），無聚落治理用法。
- 子類兩種：`Sect`（門派，`Sect.cs`）與 `CivilianSettlement`（民聚落＝城/鎮/村，`CivilianSettlement.cs`）。由 `OrganizationDomain.IsSect(orgTemplateId)` 區分。

### 1.2「主人/管理者/城主」＝ grade-8 Principal 成員（領導），非欄位
`Settlement.GetLeader()`（`Settlement.cs:173-184`）：取 `Members.GetMembers(8)`（最高位階 grade=8）中 `GetOrganizationInfo().Principal==true` 的那個角色當領導。
- grade 0–8 是位階（8 最高＝掌門/城主級）；`Principal` 表「嫡傳/正式核心」。
- 成為 grade-8 Principal 時會 `AddFeature(405)`（`OrganizationDomain.JoinOrganization`，`OrganizationDomain.cs:712-715`，僅 Sect 分支）。
- ⇒「城主/掌門」這個身份＝某角色的 `OrganizationInfo` 是「該聚落 + grade 8 + Principal」。它是**算出來的角色屬性**，不是聚落上的指針。

### 1.3 聚落「所屬組織」＝ `OrgTemplateId`（建構時綁定）
`Settlement(short id, Location location, sbyte orgTemplateId, ...)`（`Settlement.cs:141-157`）把 `OrgTemplateId` 寫死。聚落的文化/治安/人口上限全從 `Config.Organization.Instance[orgTemplateId]` 來（`:146-154`）。
- 世界生成時：`MapDomain.CreateSettlement(context, location, orgTemplateId)` 用 area config 的 `OrganizationId[i]` 當 `orgTemplateId`（見 `phase2_map_findings.md §1.2`，`MapDomain.cs:4099/4101`）。
- ⇒ **一個城鎮 = 一個 location 上、綁一個 `OrgTemplateId`、由該組織 grade-8 principal 領導、有一群 Members 的 `Settlement` 物件**。這就是治理模型的全部。

### 1.4 執行期映射：`MapAreaData.SettlementInfos` ↔ `Settlement`
`SettlementInfo`（`GameData.Shared/.../Map/SettlementInfo.cs:7`）是 struct：`SettlementId / BlockId / OrgTemplateId / RandomNameId`，序列化 8 bytes。
- 一個 area 的 `SettlementInfos[3]`（硬限 3，見 `phase2_map_findings.md §6.0`）記該 area 上每個聚落落在哪格（BlockId）、是哪個 org。
- 前端據此渲染地圖上的聚落、查名稱（`WorldMapModel.cs`）。
- ⚠️ **太吾村被前端寫死讀 `SettlementInfos[1]`**（見 §2.3），這是 mod 改起始區時的大坑（`phase2_map_findings.md §10` 已踩過）。

### 1.5 治理相關的「軟指標」：民望(ApprovingRate)、威望(InfluencePower)、金庫(Treasury)
這些是聚落運作的數值，不是「身份」，但與「權利」概念相關：
- `CalcApprovingRate()`（`Settlement.cs:273-288`）＝聚落「贊同率/民望」，由成員 `GetApprovingRate()` 加總，有上限（`OrganizationDomain.GetApprovingRateUpperLimit()` + bonus）。
- `InfluencePower`（成員的影響力/威望，`UpdateInfluencePowers`，`Settlement.cs:821-868`）：決定金庫資源分配、誰升任領導（`GetOrganizationMemberPotentialSuccessorsInSet` 比 influencePower，`:755-783`）。
- `Treasury`（金庫，`SettlementTreasury`）：聚落的物資/資源庫；太吾可存取（`StoreItemInTreasury`/`TakeItemFromTreasury`，對 `isTaiwu` 有特判記錄，`:1035/1134/1192`）。
- **太吾特判**：`UpdateInfluencePowers` 中 `approvingRate >= 600` 時，成員對太吾的好感會加成其 influencePower（`Settlement.cs:854-859`）——這是原版唯一一處「太吾在聚落內有特殊地位影響力」的數值鉤，但仍是「外人影響」而非「身份」。

---

## 2. 玩家在城鎮的「身份/地位」現況

### 2.1 玩家身份的唯一資料模型 = `OrganizationInfo`（角色屬性，非城鎮屬性）
`GameData/GameData/Domains/Character/OrganizationInfo.cs:7`（struct）：
- `OrgTemplateId`（哪個門派/組織，0 = 無 / None）
- `Grade`（位階 0–8）
- `Principal`（是否嫡傳/正式核心成員）
- `SettlementId`（屬於哪個聚落，-1 = 無）
- `None = (0,0,principal,-1)`（`:17`）。
角色透過 `Character.GetOrganizationInfo()`（`Character.cs:18970`）持有這份身份。
⇒ **「玩家在某城鎮的身份」在原版就等於「太吾的 `OrganizationInfo` 指向該城鎮的 Settlement，帶某個 grade」**。沒有「聲望條/官職表/地位等級」這種獨立 UI 系統——grep「聲望/威望/Reputation/Prestige/官職/Identity/Title/地位」散落在 config 欄位與 InteractionEventOption，無集中的玩家身份系統。

### 2.2 加入組織取得成員身份 = `OrganizationDomain.JoinOrganization`（通用入口）
`OrganizationDomain.cs:692-755`：給角色一份 `destOrgInfo`，把它加進對應 Sect 或 CivilianSettlement 的 `Members`：
- Sect 分支（`:701-718`）：建 `SectCharacter`、`members.Add(charId, grade)`、設師徒、`grade==8&&Principal` 時 `AddFeature(405)`。
- Civilian 分支（`:720-747`）：建 `CivilianSettlementCharacter`、`members.Add(...)`；若 `OrgTemplateId==16`（太吾村）則 `AddTaiwuVillageResident`（`:730-740`）。
- `ChangeOrganization`（`:829-836`）= `Leave` + `Join` + `SetOrganizationInfo` + 發事件，是「轉換身份」的完整原子操作。
⇒ **太吾完全可以被設成任一城鎮（含民聚落）的成員，甚至 grade-8 principal（城主）**——這條路在資料層完全通。可由事件腳本直接呼叫（見 §5.1）。

### 2.3 原版唯一的「玩家擁有/管理一塊地」機制 = 太吾村，且靠座標寫死判定
太吾村是一個 `OrgTemplateId==16` 的 `CivilianSettlement`（`TaiwuDomain.TaiwuVillage` 屬性，`TaiwuDomain.cs:614`）。**判定「這是玩家的地」全靠座標等於太吾村座標**，無身份旗標：
- 前端（實裝 `/tmp/cjb_decomp/WorldMapModel.cs`）：
  - `GetTaiwuVillageAreaId()`（`:2052`）＝ `(TaiwuVillageStateTemplateId-1)*3+2`（起始州的第三區）。
  - `GetTaiwuVillageBlock()`（`:2057-2062`）＝ `Areas[村區].SettlementInfos[1].BlockId` 的座標。**寫死 index 1**。
  - `IsAtTaiwuVillage(areaId,blockId)`（`:2078-2082`）＝ 當前座標是否等於 `GetTaiwuVillageBlock()`。
  - `GetTaiwuCharOnSettlement()`（`:2308-2325`）＝ 太吾當前站的聚落 id（純座標查 `SettlementInfos`），無身份概念。
- 後端：`GetTaiwuVillageLocation()` ＝ `GetTaiwuBuildingAreas()[0]`（`TaiwuDomain.cs:10565-10567`）。
⇒ **太吾村 ≠「玩家身份」，而是「玩家當前是否站在那個寫死座標 / 那個 location 是否在玩家建設區清單裡」**。原版沒有「玩家擁有第二塊地」的機制（清單恆只 push 太吾村那一格，§3.2）。
> ⚠️ 改起始區聚落數會劫持 `SettlementInfos[1]` 太吾村身分 → crash（已踩雷，`phase2_map_findings.md §10`）。

---

## 3.「取得身份後獲得權利」——權利的真正承載

### 3.1 建設權的最終 gate = `BuildingDomain.CanBuild`：location 必須在 `_taiwuBuildingAreas`
`GameData/GameData/Domains/Building/BuildingDomain.cs:865-908`：
```csharp
public bool CanBuild(BuildingBlockKey blockKey, short buildingTemplateId = -1)
{
    Location location = new Location(blockKey.AreaId, blockKey.BlockId);
    if (!DomainManager.TutorialChapter.InGuiding && !GetTaiwuBuildingAreas().Contains(location))
        return false;   // ← 核心 gate：不在「太吾建設區清單」就不能建
    ...
}
```
- `_taiwuBuildingAreas`（`BuildingDomain.cs:97`，`private List<Location>`）就是**「玩家可建設地」的完整承載**。`GetTaiwuBuildingAreas()` 回它。
- 其餘檢查：非 MainBuilding（`:886`）、isUnique 未重複（`:891`）、依賴建築齊（`AllDependBuildingAvailable`）、資源夠（`:894-903`）。引導期一律放行（`:887-890`）。

### 3.2 誰把地加進建設權清單 = `AddTaiwuBuildingArea`，原版只在太吾村那格呼叫
`BuildingDomain.AddTaiwuBuildingArea(context, location)`（`BuildingDomain.cs:6582-6588`）：
```csharp
_taiwuBuildingAreas.Add(location);
SetTaiwuBuildingAreas(_taiwuBuildingAreas, context);
InitializeResidences(context, location);        // 初始化住宅
InitializeComfortableHouses(context, location); // 初始化舒適屋
```
原版呼叫處（grep 全 backend）：
- `MapDomain.cs:4140`：世界生成時，當該格 `IsCityTown()` 且 **`orgTemplateId == 16`（太吾村）** 才 `AddTaiwuBuildingArea(new Location(areaId, blockId9))`。
- `MapDomain.cs:3645`：另一處世界生成路徑（同為太吾相關 area）。
⇒ **原版「玩家擁有建設權的地」恆等於「太吾村起始區那一格」，`_taiwuBuildingAreas[0]` 就是它。** 這是「身份→權利」的權利端唯一承載。

### 3.3 前端建設/管理 UI 的開放條件（與後端一致）
前端 `UI_BuildingArea`（實裝 `Assembly-CSharp.dll`，舊源 `Assembly-CSharp/UI_BuildingArea.cs` 行號對位）：
- `_isTaiwuVillage = WorldMapModel.IsAtTaiwuVillage(_areaId, _blockId)`（實裝 `:507`，舊 `:485`）。
- `BuildingBlockCanInteractable`（實裝 `:790`，舊 `:777`）：
  ```csharp
  return _isTaiwuVillage
      || (configData.CanOpenManageOutTaiwu && _canUseBuilding)  // ← 太吾村外的口子
      || canGetOfferUpSupport
      || templateId == 48 || templateId == 49;
  ```
- `_canUseBuilding`（`:526/530`）＝ 太吾當前站在該建築/其根 block 上。
⇒ 前端開放建設/管理面板的條件也是「在太吾村」或「建築 config 設了 `CanOpenManageOutTaiwu` 且人站在上面」。

### 3.4 原版唯一「非太吾村也能管理」的旗標 = `BuildingBlockItem.CanOpenManageOutTaiwu`
`GameData.Shared/Config/BuildingBlockItem.cs:30`（`public readonly bool CanOpenManageOutTaiwu`，建構子第 11 參，`:138/150`）。
設 `true` 的建築（`BuildingBlock.cs`）：id **48 倉庫**(`:1064`)、**49 緣集社**(`:1073`)、**52 練功坊**(`:1100`)、各工坊 129/139/149/159/169/179/203、以及各**門派主殿 239-248**(`:3317-3402`，`EBuildingBlockType.MainBuilding`)。
⇒ 這是原版「在門派/特定建築裡開管理視窗」的既有機制，但**只開「管理」面板（看/操作既有建築），不等於「能蓋新建築」**——蓋新建築仍要過後端 `CanBuild` 的 `_taiwuBuildingAreas` gate（§3.1）。

### 3.5 建築 config 暗藏的「組織/民望」欄位（潛在接點，原版未用於玩家城鎮）
`BuildingBlockItem` 還有：`BelongOrganization`（sbyte，`:124`）、`AvailableOrganization`（List<short>，`:134`）、`ApprovingRate`（short，`:136`）。
- 這些是「建築綁哪個組織 / 哪些組織可用 / 所需民望」的 config，主要服務門派/聚落自身的建築配置與 NPC 建築效果，**不是玩家身份權利系統**。grep `BuildingDomain` 未見用它們 gate 玩家建設權（玩家端只認 `_taiwuBuildingAreas` 與太吾村座標）。列為「若要做更精緻的城鎮身份分級，可掛靠的既有欄位」。

---

## 4. 與「玩家自建/管理產業」的接點

把上面串起來，「城鎮身份 → 可在城鎮建設產業」的原版接線是：

```
太吾村 = OrgTemplateId 16 的 CivilianSettlement（座標在起始區）
   └─ 世界生成 MapDomain.cs:4140  → AddTaiwuBuildingArea(太吾村location)
        └─ _taiwuBuildingAreas.Add(location) + InitializeResidences/ComfortableHouses
             ├─ 後端 CanBuild(BuildingDomain.cs:868)：location ∈ _taiwuBuildingAreas → 可蓋
             └─ 前端 IsAtTaiwuVillage(WorldMapModel.cs:2078)：站在該座標 → 開建設/管理面板
```

對「另一支 agent 的建設端」而言，**身份這一側只需交付一件事：把目標城鎮的 `Location` 弄進後端 `_taiwuBuildingAreas`，並讓前端 `IsAtTaiwuVillage`/`CanOpenManageOutTaiwu` 對該座標回 true。** 這就是身份→建設權的全部接點。

「身份」（`OrganizationInfo` 指向該城鎮、給個 grade）在原版**不直接解鎖建設權**——它只影響成員互動/門派功能。但它是給玩家「為什麼能在這裡建設」一個合理化包裝（劇情/旗標），mod 可自行把「身份取得事件」與「擴充建設區」綁在一起。

---

## 5. 可行性與最小切入路徑

### 5.1 原版已支撐 vs 需新造
| 需求 | 原版支撐 | 位置 |
|------|----------|------|
| 太吾成為某城鎮「成員/掌門」身份 | ✅ 完全支撐 | `OrganizationDomain.JoinOrganization/ChangeOrganization`（`OrganizationDomain.cs:692/829`）；事件可直呼（§5.3） |
| 城鎮治理「所屬組織+領導」模型 | ✅ 既有 | `Settlement`（綁 OrgTemplateId + grade-8 principal） |
| 玩家「擁有/能建設一塊地」 | ✅ 但只綁太吾村一格 | `_taiwuBuildingAreas`（`BuildingDomain.cs:97`），`AddTaiwuBuildingArea`（`:6582`） |
| 「城鎮身份」與「建設權」自動關聯 | ❌ 需新造 | 原版兩條軌獨立；要 mod 自行把「身份事件」連到「擴充建設區」 |
| 收稅/徵召/調度等其他「權利」 | ⚠️ 部分 | 金庫存取（太吾已可，`Settlement.Store/TakeFromTreasury`）；無「向城鎮收稅/徵召兵」這種玩家專屬權利系統 |
| 玩家身份「聲望/官職」等級條 | ❌ 無此系統 | grep 無集中的玩家身份分級；只有 `OrganizationInfo.Grade` 與聚落 `ApprovingRate`（聚落級非玩家級） |

### 5.2 最小可行路徑（建議：權利端切入，身份做包裝）
**核心動作 = 把目標城鎮的 `Location` 加進 `_taiwuBuildingAreas`**（這是建設權的唯一硬 gate）：
1. **後端**：在某觸發點（事件鉤 / Harmony / DomainMethod 呼叫）對目標城鎮 location 呼 `DomainManager.Building.AddTaiwuBuildingArea(context, location)`（`BuildingDomain.cs:6582`）。它會自動 `SetTaiwuBuildingAreas` 存檔 + 初始化住宅。此後後端 `CanBuild`（`:868`）對該地放行。
2. **前端開面板**：前端 `IsAtTaiwuVillage` 寫死只認太吾村座標（`WorldMapModel.cs:2078`）；要讓「目標城鎮」也開建設面板，最乾淨是讓目標建築走 `CanOpenManageOutTaiwu` 那條口子（§3.4，把該城鎮的某建築 config `CanOpenManageOutTaiwu` 設 true，或 Harmony 讓 `IsAtTaiwuVillage`/`BuildingBlockCanInteractable` 對該座標回 true）。**此點需前端介入，列為實測項。**
3. **身份包裝（可選但符合需求）**：用事件給太吾一個「城鎮身份」——可直接設 `OrganizationInfo` 指向該城鎮聚落（透過事件 `JoinOrganization`，§5.3），或自定義一個旗標。把「身份取得事件」的成功動作綁上步驟 1 的 `AddTaiwuBuildingArea`，即達成「取得身份 → 解鎖該城鎮建設」。

### 5.3 給玩家身份的原生接口（事件腳本可直呼）
`GameData/GameData/Domains/TaiwuEvent/FunctionDefinition/OrganizationFunctions.cs`：
- `JoinOrganization(runtime, character, settlement, grade)`（`:18-27`）：建 `OrgInfo{ OrgTemplateId=settlement org, Grade=grade, SettlementId=settlement.Id, Principal=true }` → `ChangeOrganization`。**這是事件腳本直接把太吾設成某聚落成員/掌門的原生函數。**
- `ChangeSafetyForSettlement` / `ChangeCultureForSettlement`（`:40/46`）：事件可改聚落治安/文化（治理數值的權利雛形）。
- `SetSectAllowLearning`（`:9`）：事件可設聚落允許學習。
⇒ 「用事件給玩家城鎮身份」有原生函數可用，無需自造身份系統的資料層。

### 5.4 風險與限制
- **`_taiwuBuildingAreas` 是後端持久化清單**（`SetTaiwuBuildingAreas` 存檔）；mod 加入的地會進存檔，需做冪等防呆（避免重複 add）。
- **太吾村座標寫死 `SettlementInfos[1]`**（§2.3）：任何改起始區聚落數的做法都會劫持太吾村身分 → crash（`phase2_map_findings.md §10` 已證）。新城鎮應**新增聚落槽或取代非太吾村槽**，絕不動起始區 `SettlementInfos[1]`。
- **建設區 `[0]` 假設**：多處程式碼直接取 `GetTaiwuBuildingAreas()[0]` 當太吾村（`TaiwuDomain.cs:2597/10567`、`BuildingDomain.cs:2365`）。**新地必須 append 在尾端，[0] 永遠是太吾村**，否則太吾村相關邏輯全錯位。
- 前端 `IsAtTaiwuVillage` gate 需另解（步驟 2），是本路徑最不確定的一環，須實機驗證。
- 「收稅/徵召」等權利原版無系統，要做得另立資料與 UI，屬「新造」範圍，建議 mod 一期不碰，先做「身份旗標 → 解鎖建設」最小閉環。

---

## 6. 待釐清問題（交給後續/實測）
1. **前端如何讓「非太吾村座標」開建設/管理面板**：Harmony patch `IsAtTaiwuVillage` 對目標座標回 true 是否安全？會否誤觸 BGM/主線進度/家園判定（這些都讀 `GetTaiwuVillageBlock`，§2.3）？→ 必須讓「目標城鎮」與「太吾村」走不同判定，避免身分混淆。
2. `AddTaiwuBuildingArea` 在「非起始區、已有聚落的成熟城鎮 location」上呼叫，`InitializeResidences/ComfortableHouses`（`:6586-6587`）是否與該聚落既有 NPC/建築衝突？→ 實機驗證。
3. `CanOpenManageOutTaiwu=true` 的建築（如門派主殿）在玩家「取得身份」後，前端是否真能開「建設新建築」而非僅「管理既有」？（§3.4 推測只開管理面板）→ 實機驗證。
4. 是否存在 `[DomainMethod]`/前後端橋讓前端主動觸發 `AddTaiwuBuildingArea`，或只能後端事件/Harmony 觸發？→ 查 `GameDataBridge` 對 BuildingDomain 的暴露面。
5. `BelongOrganization`/`AvailableOrganization`/`ApprovingRate`（§3.5）能否被改造成「玩家城鎮身份分級」的承載，讓不同身份開不同建築？→ 進階設計選項，需查 `BuildingDomain` 是否在玩家路徑讀這些欄位。
