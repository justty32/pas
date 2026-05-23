# 門派「武功列表＋好感度」UI 完整機制調查

> 目標：讓 mod 能從其他地方**程式化觸發**這個 UI，並在開啟時即時餵入（可能隨機生成的）資料。
>
> **版本綁定**：實裝版 **0.0.79.60**。
> - 反編譯參考源（較舊、可能漂移）：`~/dev/taiwu-src/Assembly-CSharp/`（前端）、`~/dev/taiwu-src/backend/`（後端）。
> - 核對基準（實裝 DLL，以 `ilspycmd -t` dump）：
>   - 前端 `…/The Scroll of Taiwu_Data/Managed/Assembly-CSharp.dll`
>   - 後端 `…/Backend/GameData.dll`
> - 下文每節標注「【實裝核對】」＝已對實裝 DLL 驗證；「【舊源】」＝僅看反編譯參考源。

---

## A. 鎖定這個 UI 是哪個類

### A-1. 真名：`UI_CombatSkillTree`（單一面板，含兩塊）
- 前端類：`UI_CombatSkillTree : UIBase`
  - 舊源：`~/dev/taiwu-src/Assembly-CSharp/UI_CombatSkillTree.cs:15`
  - 【實裝核對】`ilspycmd -t UI_CombatSkillTree`：類定義、欄位、`OnInit`/`OnNotifyGameData`/`InitSkillData`/`RefreshBaseData`/`RefreshExtraData` 全部與舊源一致（僅字串常數從整數 key 換成 `LanguageKey.*` 列舉，行為不變）。
- UI 資源路徑註冊：`UIElement.CombatSkillTree`，`_path = "UI_CombatSkillTree"`
  - `~/dev/taiwu-src/Assembly-CSharp/UIElement.cs:441-444`
- **`CombatSkillView` 不是這個面板**：它是 `Refers`（單一武功圖示小元件），被 UI 當作 list item 用（`UI_CombatSkillTree.RefreshSkillItem` 內 `refers.CGet<CombatSkillView>("CombatSkillView")`，舊源 `UI_CombatSkillTree.cs:337`）。背景脈絡踩到的 `static readonly string[] SectImg` 就掛在 `CombatSkillView`，被 `UI_CombatSkillTree` 借用。
  - `CombatSkillView.SectImg`：`~/dev/taiwu-src/Assembly-CSharp/CombatSkillView.cs:15-19`，型別 **`string[16]`**（id 0–15）。【實裝核對】`ilspycmd -t CombatSkillView` → `public static readonly string[] SectImg = new string[16]`，大小仍是 16。

### A-2. 一個面板同時顯示兩塊
`UI_CombatSkillTree` 是「一個面板含兩塊」，不是兩個分頁/兩個類：

1. **武功列表（武學樹）**：`SkillListView`（`InfinityScroll`），每格一個門派武功類型，內含至多 9 個 `SkillItem_i`（對應 9 階）。
   - 渲染：`OnTypeSkillItemRender`（舊源 `UI_CombatSkillTree.cs:304`）→ `RefreshSkillItem`（`:323`）。
   - 列表資料來源見 C-2。
2. **好感度（ApprovingRate）面板**：`ApprovePanel` + 進度條 `ProgressLineBar*`/`ProgressLevelIconHolder`(10 格) + `ApproveValue`/`ApproveValueLimit`/`AddAuthority`/`FameChange`。
   - 渲染：`RefreshExtraData`（舊源 `:137`，讀 `_data.ApprovingRate*` 等）。
   - 好感效果說明 tip（`SectApprovePowerBack_1..10`）：`RefreshApproveEffectTips`（`:383`）。

此外還顯示：門派名 `SectName`、門派圖示 `SectIcon`、門派描述 `SectDesc`/`SectDescExtra`、行為傾向插畫 `BehaviorImage`、好感主效果圖示/名 `ApproveSkillIcon`/`ApproveSkillDesc`（均在 `RefreshBaseData`，舊源 `:280-299`）。

---

## B. 原版的開啟入口（觸發鏈）

### B-1. 四個原版開啟點（皆只傳 `SectTemplateId`）
搜尋 `Set("SectTemplateId", …)` 得到四處：

| # | 來源 | 觸發 | 開啟方式 | 傳入 |
|---|------|------|----------|------|
| 1 | `MapElementSettlementBtn.OnClickSect` | 地圖上點門派駐地按鈕 | `CommandManager.AddCommandShowUI` | `SectTemplateId = _settlementInfo.OrgTemplateId` |
| 2 | `UI_Bottom`（`"SectSupportInfoBtn"`） | 底欄「勢力情報」鈕（玩家所在門派） | `SetOnInitArgs` + `UIManager.ShowUI` | `SectTemplateId = _currOrganizationId` |
| 3 | `UI_SettlementInformation`（`"…"` 駐地資訊內鈕） | 駐地資訊面板 | `SetOnInitArgs` + `UIManager.ShowUI` | `SectTemplateId = settlementData.OrgTemplateId` |
| 4 | `UI_NewGame`（`"ShowSectCombatSkills"`） | 開新檔選門派時看門派武功 | `SetOnInitArgs` + `UIManager.ShowUI` | `SectTemplateId = mapStateItem.SectID` ＋ `CallBack` |

原始碼位置（舊源）：
- `MapElementSettlementBtn.OnClickSect`：`~/dev/taiwu-src/Assembly-CSharp/MapElementSettlementBtn.cs:267-274`
  ```csharp
  ArgumentBox args = EasyPool.Get<ArgumentBox>().Set("SectTemplateId", _settlementInfo.OrgTemplateId);
  CommandManager.AddCommandShowUI(EPriority.ShowUINormal, UIElement.CombatSkillTree, args);
  ```
- `UI_Bottom`（"SectSupportInfoBtn"）：`~/dev/taiwu-src/Assembly-CSharp/UI_Bottom.cs:1055-1064`
  ```csharp
  box.Set("SectTemplateId", _currOrganizationId);
  UIElement.CombatSkillTree.SetOnInitArgs(box);
  UIManager.Instance.ShowUI(UIElement.CombatSkillTree);
  ```
- `UI_SettlementInformation`：`~/dev/taiwu-src/Assembly-CSharp/UI_SettlementInformation.cs:269-276`（先檢查 `Organization.Instance[orgTemplateId].IsSect` 才開）
- `UI_NewGame`（"ShowSectCombatSkills"）：`~/dev/taiwu-src/Assembly-CSharp/UI_NewGame.cs:363-372`（**唯一額外傳 `CallBack`，且在非 InGame 狀態開** → 見 C-3）

> 背景脈絡提到「產業視圖點建築鏈 `MapElementSettlementBtn.OnClickBuilding` / templateId 239~248 走門派 UI 分支」——實際打開這個 UI 的是同類的 `OnClickSect`（門派駐地按鈕，#1），參數同樣只有 org template id。

### B-2. UI 的「Open 方法」＝ `OnInit(ArgumentBox)`，**沒有自訂 Open 簽名**
這個 UI 沒有 `Open(...)`/`Show(...)` 帶參數的方法；它走通用 UI 框架：開窗時框架呼叫 `UIBase.OnInit(ArgumentBox argsBox)`。
- `UI_CombatSkillTree.OnInit`：舊源 `UI_CombatSkillTree.cs:50-76`。【實裝核對】簽名一致。
- 它從 `argsBox` 取兩個 key：
  - `"SectTemplateId"`（**`sbyte`**，門派 config template id；缺它則 `OnInit` 直接 return 不開）— `:55`
  - `"CallBack"`（`Action`，關閉時觸發；可選）— `:52`、關閉於 `OnDisable` 呼叫 `:47`

**結論：要從別處觸發，只需準備一個 `ArgumentBox`，`Set("SectTemplateId", (sbyte)orgId)`，再用下面任一管理器 API 開啟即可。**

### B-3. UI 管理器開窗 API（兩條等價）
1. **命令系統**（會排隊、含優先權）：
   - `CommandManager.AddCommandShowUI(EPriority priority, UIElement element, ArgumentBox argBox = null)`
   - 舊源 `~/dev/taiwu-src/Assembly-CSharp/FrameWork/CommandSystem/CommandManager.cs:46`
   - 內部：argBox 非 null → `AddCommand<CommandShowUIWithArgs,…>`（`:54`）
2. **直接開窗**：
   - `UIElement.CombatSkillTree.SetOnInitArgs(box)`（`UIElement.cs:2317`，會 `box.Clone()`）
   - `UIManager.Instance.ShowUI(UIElement.CombatSkillTree)`（`~/dev/taiwu-src/Assembly-CSharp/UIManager.cs:162`）

兩者最後都會驅動 `UIElement.Show()`（`UIElement.cs:2322`）→ 載資源 → 呼 `OnInit`。

---

## C. 資料來源：UI 開啟時從哪裡拿「武功列表＋好感度」

**這個 UI 是 data-driven 的，但兩塊資料來源不同：**

### C-1. 好感度 / 已習得武功 → 即時向後端要（InGame 時）
`OnInit` 在拿到 `GameDataListenerId` 後發一筆 domain method call：
- 舊源 `UI_CombatSkillTree.cs:64-67`：
  ```csharp
  if (NeedDataListenerId)
      OrganizationDomainHelper.MethodCall.GetOrganizationCombatSkillsDisplayData(Element.GameDataListenerId, _sectTemplateId);
  ```
- 【實裝核對】實裝版類名漂移：呼叫的是
  `GameData.Domains.Organization.OrganizationDomainMethod.Call.GetOrganizationCombatSkillsDisplayData(int listenerId, sbyte organizationTemplateId)`
  （`ilspycmd -t OrganizationDomainMethod`，內部 `GameDataBridge.AddMethodCall(listenerId, 3, 3, organizationTemplateId)`，即 DomainId=3、MethodId=3）。
  - 另有 async 版：`OrganizationDomainMethod.AsyncCall.GetOrganizationCombatSkillsDisplayData(IAsyncMethodRequestHandler, sbyte, AsyncMethodCallbackDelegate)`。

回應走 `OnNotifyGameData`（舊源 `:93-108`，【實裝核對】一致）：當 `DomainId==3 && MethodId==3` → 反序列化成 `OrganizationCombatSkillsDisplayData _data` → `RefreshExtraData()`。

**後端建資料的方法（version-sensitive，已實裝核對）：**
`GameData.Domains.Organization.OrganizationDomain.GetOrganizationCombatSkillsDisplayData(sbyte organizationTemplateId)`
- 舊源 `~/dev/taiwu-src/backend/GameData/GameData/Domains/Organization/OrganizationDomain.cs:2626`
- 【實裝核對】`ilspycmd -t …OrganizationDomain GameData.dll` 行 2705，邏輯逐行相同：
  1. `Settlement s = GetSettlementByOrgTemplateId(organizationTemplateId)`（**會回 null / 越界，見 D-3**）
  2. `data.ApprovingRate = s.CalcApprovingRate()`、`ApprovingRateTotal`、`ApprovingRateUpperLimit = GetApprovingRateUpperLimit()`、`ApprovingRateUpperLimitBonus = s.GetApprovingRateUpperLimitBonus()+s.GetApprovingRateUpperLimitTempBonus()`
  3. `data.LearnedSkills`：取**太吾自己**已學武功 `DomainManager.Taiwu.GetTaiwu().GetLearnedCombatSkills()`，篩 `Config.CombatSkill.Instance[id].SectId == organizationTemplateId`，再 `DomainManager.CombatSkill.GetCombatSkillDisplayData(taiwuCharId, ids)`。

資料模型 `OrganizationCombatSkillsDisplayData`（欄位）：
- `~/dev/taiwu-src/backend/GameData.Shared/GameData/Domains/Organization/Display/OrganizationCombatSkillsDisplayData.cs:8-26`
- 欄位：`sbyte OrganizationTemplateId`、`short ApprovingRate`、`short ApprovingRateTotal`、`short ApprovingRateUpperLimit`、`short ApprovingRateUpperLimitBonus`、`List<CombatSkillDisplayData> LearnedSkills`。
- 前端有同名鏡像類（`~/dev/taiwu-src/Assembly-CSharp/GameData/Domains/Organization/Display/OrganizationCombatSkillsDisplayData.cs`），UI 直接 `new` 它並反序列化。

**好感度怎麼算（重要：不是單一可寫欄位）**：`Settlement.CalcApprovingRate()`（舊源 `Settlement.cs:273-289`）是**遍歷該駐地成員角色的 `GetApprovingRate()` 加總後 clamp 到上限**算出來的——沒有「設一個數就好」的後端欄位。要靠後端真實算出某個好感度，得有真實成員且各自有好感值，**不切實際**。

### C-2. 武功列表（整棵武學樹）→ 全部走前端 ConfigData，不靠後端
- `InitSkillData()`（舊源 `UI_CombatSkillTree.cs:110-135`；【實裝核對】行 121 一致）：
  ```csharp
  CombatSkill.Instance.Iterate(item => { if (item.SectId == _sectTemplateId) { …按 item.Type 分組… } });
  ```
  即整棵樹來自 **`Config.CombatSkill`（ConfigData）依 `SectId == _sectTemplateId` 過濾**，與後端無關。
- 後端只回 `LearnedSkills`，用來在樹上標「已習得 / 已破解」（`RefreshSkillItem`，舊源 `:323-381`，`_data.LearnedSkills.Find(...)`）。

### C-3. 非 InGame（如新遊戲選門派）→ 完全不要後端
- `OnInit`：`NeedDataListenerId = Game.Instance.GetCurrentGameStateName() == EGameState.InGame`（舊源 `:59`）。
- 非 InGame 時（`UI_NewGame` 的 #4 入口）：`ApprovePanel` 保持隱藏（`:63`），不發 domain call，只 `RefreshApproveEffectTips()` + 直接 `ShowAfterRefresh()`（`:69-72`）。`_data` 維持 null。
- 此模式下整個面板只靠前端 ConfigData（武學樹 + 門派 config + SectApprovingEffect config），**完全 data-driven、零後端依賴**。

### C-4. 關鍵判斷
- **武學樹**：100% data-driven。先用 ConfigData 注入某 org id 的武功（`CombatSkill` 設 `SectId=該id`）＋ `Organization`／`SectApprovingEffect` config，再開這個 UI，**武學樹就會顯示注入的內容**。
- **好感度**：data-driven 但資料來自後端 `CalcApprovingRate`（成員加總），**不能單純注入一個 config 數字**讓它顯示某好感百分比。要顯示自訂好感，得攔截前端資料（見 D）。

---

## D. mod 如何「從其他地方觸發 + 即時餵隨機資料」

### D-1. 從任意 mod 程式碼觸發 Open，可行嗎？
**可行（高）**。從事件選項回呼 / 自訂按鈕 / Harmony patch 任意處，照 B-3 開即可：
```csharp
var box = EasyPool.Get<ArgumentBox>();   // 或 new ArgumentBox()
box.Set("SectTemplateId", (sbyte)orgId);
// box.SetObject("CallBack", someAction);  // 可選
UIElement.CombatSkillTree.SetOnInitArgs(box);
UIManager.Instance.ShowUI(UIElement.CombatSkillTree);
```
前置條件（不滿足就崩，見 D-3）：`orgId` 必須對應到**合法存在的 `Organization` config 與（InGame 時）一個真實 Settlement**，且 `orgId ∈ [0,15]`（SectImg）、`SectApprovingEffect[orgId-1]` 存在。

### D-2. 「即時填入隨機生成的東西」三種注入點比較

#### (a) 開啟前先用 ConfigData 注入臨時門派的武功/好感 config
- **做什麼**：在 `Config.CombatSkill` 注入若干 `SectId=tmpOrgId` 的武功（→ 餵武學樹）、在 `Config.Organization` 注入 `OrganizationItem(tmpOrgId)`、在 `Config.SectApprovingEffect` 注入 `[tmpOrgId-1]`、在 `CombatSkillView.SectImg` 補槽（見 D-3）。
- **餵得到什麼**：✅ **武學樹（含隨機武功）**、門派名/描述/圖示/好感主效果說明。❌ **好感「百分比」餵不到**（那來自後端 `CalcApprovingRate`，無真實成員時無意義）。
- **可行性**：武學樹部分 **高**；好感百分比部分靠這招 **無法**。
- **風險**：ConfigData 注入須在進遊戲前/正確時機（mod 載入點）；新增 org config 會讓後端 `_orgTemplateId2Settlements` 陣列依 `maxOrgTemplateId+1` 自動擴容（見 D-3），但**不會自動建 Settlement**，所以 InGame 開仍會在 C-1 後端步驟 1 拿到 null 而崩 → InGame 想用這招得搭配「真的有一個掛該 org id 的 Settlement」或走 (b)。

#### (b) Harmony patch UI 的資料讀取方法，直接回傳隨機內容（**推薦**）
最穩、最可控。兩個層級可選：
- **patch 前端 `UI_CombatSkillTree.OnNotifyGameData` 或 `RefreshExtraData`**：在 `_data` 被填好/使用前，把 `_data`（`OrganizationCombatSkillsDisplayData`）整個換成你 `new` 的隨機物件（自訂 `ApprovingRate`/`ApprovingRateTotal`/`ApprovingRateUpperLimit*`/`LearnedSkills`）。這樣**好感百分比＋已習得標記都能餵任意值**。
  - patch 點：`UI_CombatSkillTree.OnNotifyGameData`（舊源 `:93`）postfix／或 prefix `RefreshExtraData`（`:137`）。
- **patch 後端 `OrganizationDomain.GetOrganizationCombatSkillsDisplayData`（postfix）**：直接 return 你造好的 `OrganizationCombatSkillsDisplayData`，繞過 `GetSettlementByOrgTemplateId`（避開 null/越界）。這同時解決 D-3 後端越界問題。
  - patch 點：`GameData.Domains.Organization.OrganizationDomain.GetOrganizationCombatSkillsDisplayData(sbyte)`（實裝 `GameData.dll` 行 2705）。
- **可行性**：**高**。武學樹仍由前端 `InitSkillData` 走 ConfigData（所以武學樹仍需 (a) 的 `CombatSkill` config，或另 patch `InitSkillData`/`_sectSkillList`），好感與已習得則由 patch 完全掌控。
- **風險**：前端武學樹的圖示/門派名仍會在 `RefreshBaseData` 讀 `SectImg`/`Organization.Instance`/`SectApprovingEffect.Instance`，**那段在 domain call 回來前就跑了**（`OnInit` 末尾直接 `RefreshBaseData()`，`:75`），所以 D-3 的固定結構越界**無法靠 patch 資料方法迴避**，仍要備好或 patch `RefreshBaseData`。

#### (c) 直接 new 一個 data model 傳給 Open 方法
- **不可行（低）**：`OnInit` 只吃 `SectTemplateId`/`CallBack` 兩個 key，**沒有接受 `OrganizationCombatSkillsDisplayData` 的入口**；`_data` 是 private、只由 `OnNotifyGameData` 反序列化填入。想「傳 model 進去」等同於要改 `OnInit`（即還是得 Harmony patch）。故 (c) 實質退化成 (b)。

**三者結論**：用 **(b) Harmony patch（前端 `OnNotifyGameData`/`RefreshExtraData` 或後端 `GetOrganizationCombatSkillsDisplayData`）餵好感＋已習得**，搭配 **(a) ConfigData 注入武學樹/門派 config**，是「從別處觸發＋即時餵（隨機）資料」的最佳組合。(c) 不成立。

### D-3. 需要防的「按門派 id 索引的固定結構」越界清單
（沿用陳家堡的兩個修正＝其中前兩項；以下皆【實裝核對】過索引點）

| # | 結構 | 位置（實裝） | 索引方式 | 越界/null 後果 | 防法 |
|---|------|------|----------|----------------|------|
| 1 | `CombatSkillView.SectImg`（`string[16]`） | `UI_CombatSkillTree.RefreshBaseData` 行 292：`SectImg[_sectTemplateId]` | 陣列下標 `[orgId]` | orgId≥16 → `IndexOutOfRange` | 反射 enlarge 陣列到 ≥orgId+1，填一個合法 sprite 名（陳家堡：[42]=少林圖示） |
| 2 | `Config.SectApprovingEffect`（ConfigData，key=orgId-1） | 行 290＆403：`SectApprovingEffect.Instance[_sectTemplateId-1]` | `GetItem`：缺則回 **null** | `.Icon`/`.Name`/`.Desc` → **NPE** | ConfigData 注入 `[orgId-1]`（陳家堡作法），或 patch `RefreshBaseData`/`RefreshApproveEffectTips` |
| 3 | `Config.Organization`（ConfigData，key=orgId） | 行 289：`Organization.Instance[_sectTemplateId]`；行 233：`Organization.Instance[_sectTemplateId].Goodness` | `GetItem`：缺則回 **null** | `.Name`/`.Desc`/`.Members`/`.MainMorality`/`.Goodness` → **NPE** | 注入合法 `OrganizationItem(orgId)`（含 `IsSect` 等欄位） |
| 4 | 後端 `_orgTemplateId2Settlements`（`List<Settlement>[]`） | `OrganizationDomain.GetSettlementByOrgTemplateId` 行 639：`_orgTemplateId2Settlements[orgTemplateId]` | **陣列下標** | orgId ≥ `CalcOrgTemplateCount()`(=maxOrgTemplateId+1) → `IndexOutOfRange`；陣列槽為 null/0 或 >1 → 回 **null** | 註：陣列大小依 Organization config 自動擴容（行 1720-1731 `maxOrgTemplateId+1`），故注入 org config 後不會下標越界；但「該 org 沒有恰好 1 個 Settlement」→ 回 null → C-1 步驟 2 `s.CalcApprovingRate()` **NPE**。InGame 想安全：(b) postfix patch 後端方法繞過，或保證該 org 真有一個 Settlement |
| 5 | `ApproveEffectDesc`（`string[8]`）／`ProgressLevelIconHolder` 子物件 10 格 | `RefreshApproveEffectTips`/`RefreshExtraData` | 固定迴圈 `i<10`、`i-2` | 與 orgId 無關，固定大小；只要 prefab 結構正常即安全 | 不需特別防 |

> 額外注意：`Organization.Instance` 與 `SectApprovingEffect.Instance` 的 `GetItem` **不丟例外、回 null**（`~/dev/taiwu-src/backend/GameData.Shared/Config/Common/ConfigData.cs:104-121`），所以症狀是「開 UI 時 NullReference」而非下標例外——和陳家堡崩潰特徵吻合。

### D-4. 最務實的「臨時/隨機門派」配方（InGame）
1. **載入期 ConfigData 注入**：
   - `Config.Organization` 加 `OrganizationItem(tmpId)`（`IsSect=true`、`Name/Desc/Goodness/MainMorality/Members` 等齊全）。
   - `Config.SectApprovingEffect` 加 `[tmpId-1]`（`Icon/Name/Desc`）。
   - `Config.CombatSkill` 加若干 `SectId=tmpId` 的武功（→ 武學樹內容；可隨機）。
   - 反射 enlarge `CombatSkillView.SectImg` 到 ≥tmpId+1 並填合法 sprite。
   - 確保 `tmpId ≤ 15`（否則 SectImg 即使 enlarge，也要注意它本只 16 槽——enlarge 是唯一解）。
2. **好感/已習得**：Harmony **postfix** `OrganizationDomain.GetOrganizationCombatSkillsDisplayData`（或前端 `OnNotifyGameData`），對 `tmpId` 回傳隨機 `OrganizationCombatSkillsDisplayData`（自填 `ApprovingRate` 等＋隨機 `LearnedSkills`），**避開 `GetSettlementByOrgTemplateId` 拿 null**。
3. **觸發開窗**：B-3 任一 API，`Set("SectTemplateId",(sbyte)tmpId)`。
4. （更省事的替代）若可接受**不顯示好感面板**：以**非 InGame 行為**或 patch 讓 `NeedDataListenerId=false`，則只需第 1 步的 config，連後端都不碰（C-3）。但 InGame 狀態下 `NeedDataListenerId` 恆為 true，要改它得 patch `OnInit`。

---

## 附：實裝核對清單（哪些已對 DLL 驗證）
- 【實裝核對 ✅】`UI_CombatSkillTree` 全類（`OnInit`/`OnNotifyGameData`/`InitSkillData`/`RefreshBaseData` 索引點/`RefreshExtraData`）— `Assembly-CSharp.dll`。
- 【實裝核對 ✅】`CombatSkillView.SectImg` = `string[16]` — `Assembly-CSharp.dll`。
- 【實裝核對 ✅】前端呼叫類名為 `OrganizationDomainMethod.Call.GetOrganizationCombatSkillsDisplayData(int,sbyte)`（舊源寫 `OrganizationDomainHelper.MethodCall`，**已漂移**）— `Assembly-CSharp.dll`。
- 【實裝核對 ✅】後端 `OrganizationDomain.GetOrganizationCombatSkillsDisplayData`（行 2705）與 `GetSettlementByOrgTemplateId`（行 637-643，`_orgTemplateId2Settlements` 為 `List<Settlement>[]`）— `GameData.dll`。
- 【舊源（未逐行對 DLL，但邏輯穩定）】`UIElement.cs` 開窗 API、`CommandManager.AddCommandShowUI`、`UIManager.ShowUI`、四個開啟入口的 click handler、`Settlement.CalcApprovingRate`、`ConfigData.GetItem`/`CalcOrgTemplateCount`、`SectApprovingEffectItem`/`OrganizationCombatSkillsDisplayData` 欄位。這些屬框架/結構性程式碼，跨版漂移風險低；若 mod 實作要綁簽名，建議再對 DLL 點對點核一次。
