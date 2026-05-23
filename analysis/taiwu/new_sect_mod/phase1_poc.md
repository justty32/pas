# 陳家堡 Mod — Phase 1：純資料 PoC（不上地圖）

> 目標：在 backend 注入一個新門派藍圖 `OrganizationItem`（TemplateId=42），讓世界生成時可被視為真正的 `Sect`。本階段**不處理上地圖**（屬 Phase 2，見 [`phase2_map_findings.md`](./phase2_map_findings.md)）。
> 產出：`~/repo/pas/projects/taiwu/ChenJiaBao/`（backend plugin，已對實裝 0.0.79.60 編譯通過）。
> 事實來源：反編譯原始碼 `~/dev/taiwu-src/backend/`。本檔所有 path:line 皆已回原始碼覆核。
> 狀態（2026-05-23）：**程式完成、`Build succeeded` 0 warning / 0 error；尚未實機測試**。

---

## 1. 一句話成果

backend plugin 在 `Initialize()` 反射克隆少林(id=1) 的 `OrganizationItem` → 覆寫成 id=42「陳家堡」(`IsSect=true`)，呼 `Organization.AddExtraItem` 注入。因為 `OrganizationDomain.IsSect()` 讀的是 config 旗標而非寫死 1..15，**零核心 Harmony 補丁**即可讓陳家堡被當真門派看待。

---

## 2. 專案結構

```
projects/taiwu/ChenJiaBao/
├── Backend/
│   ├── ChenJiaBao.Backend.csproj   # net6.0, 引用遊戲 Backend/ 下 GameData.* dll
│   └── Plugin.cs                   # TaiwuRemakePlugin，Initialize() 注入 id 42
├── Shared/
│   └── OrganizationItemFactory.cs  # 反射逐欄克隆 OrganizationItem 的工具
└── dist/
    └── Config.lua                  # manifest（UTF-8 原始檔；部署需轉 GBK）
```

編譯產物：`Backend/bin/Release/ChenJiaBao.Backend.dll`。

---

## 3. 注入機制與時機（已回原始碼覆核）

| 步驟 | 位置 | 作用 |
|---|---|---|
| config 灌列 | `GameData/Program.cs:46` `DomainManager.Global.ReloadAllConfigData()` → `Organization.Init()` | 重建 `_dataArray`，灌入 0..41 共 42 列（`Organization.cs:370` `new List<OrganizationItem>(42)`） |
| 載入 mod | `GameData/GameDataBridge/GameDataBridge.cs:184` `DomainManager.Mod.LoadAllMods(...)` | 載入 backend plugin、呼叫本 `Initialize()` → **此時注入 id 42** |
| 建門派池 | `OrganizationDomain.cs:187/189` `InitializeOnInitializeGameDataModule()` → `InitializeSectOrgTemplateIds()`（`:3730`），由 `OnInitializeGameDataModule()`（`:5214`）觸發 | 掃 config 建「可加入門派池」，**晚於 plugin Initialize** → 新派自動被掃入 |

⇒ 注入發生在「config 已就緒」之後、「門派池建立」之前，所以 `AddExtraItem` 安全、且新派自動進可加入池，無需補丁。

`Organization.AddExtraItem`（`Organization.cs:383`）要求 `id >= _dataArray.Count`（即 ≥ 42，`:387` 否則丟例外），寫入 `_extraDataMap`/`_refNameMap`；索引器 `Organization.Instance[42]`（`GetItem`，會 fallback `_extraDataMap`）可正常取回。

---

## 4. 為什麼選少林(id=1) 當克隆來源

`Organization.cs:124` 少林列：
```
new OrganizationItem(1, 4, 5, 125, 150, 700,
    new short[2] { 0, 1 },                                       // CharTemplateIds（掌門等關鍵角色）
    new short[9] { 323,322,321,320,319,318,317,766,316 },        // Members[9]：9 階皆合法 id ★
    arg8: true /*IsSect*/, arg9: false /*IsCivilian*/, ...,
    new List<sbyte> { 1, 8, 13 },                                // CombatSkillTypes
    ...)
```
- **★ 關鍵理由**：`CreateSettlementMembers`（phase0 §2.2）依 `Members[grade]`（grade 0..8）生人，要求 `Members` 為 `short[9]` 且每階為合法 member id。少林 9 階全是合法 id，是「成員/技藝最齊全」的安全範本。
- `CombatSkillTypes`/`CharTemplateIds`/`LargeSectFavorabilities(sbyte[15])` 等欄位完整，沿用即可不缺漏。

---

## 5. 反射克隆做法（`OrganizationItemFactory.CloneFrom`）

`OrganizationItem` **無 `Duplicate()`**（不像 CombatSkillItem 走 `ConfigItem<,>.Duplicate`），故 MySwordArt 的 `DataConfigAppender` 不適用。改採：

1. `new OrganizationItem()`（無參建構子存在，`OrganizationItem.cs:144`）建空殼。
2. `GetFields(Instance|Public|NonPublic)` 逐一把來源派欄位 `SetValue` 到副本（readonly 欄位照樣可寫）。陣列 / `List<>` 做**淺拷貝**避免與來源派共用引用。
3. 套用 overrides（欄位名→值）覆寫指定欄位，並做數值縮窄轉換（int→sbyte/short）。

### 覆寫的欄位與依據

| 欄位 | 值 | 依據 |
|---|---|---|
| `TemplateId` | `(sbyte)42` | ≥ 42 才能 `AddExtraItem`（`Organization.cs:387`） |
| `Name` | `"陳家堡"` | 反射直接塞字串，繞過 `Organization_language` 語言表（phase0 §0/§6） |
| `Desc` | `"一座以家傳武學立足江湖的小型武林堡寨。"` | 同上 |
| `IsSect` | `true` | `OrganizationDomain.IsSect(42)`（`:3601` `return Config.Organization.Instance[id].IsSect;`）→ `CreateSettlement` 生成真正的 `Sect` |
| `IsCivilian` | `false` | 門派而非民居聚落 |
| `Population` | `100` | `CreateSettlementMembers` 在 `Population<=0` 時整段跳過（phase0 §2.2）；小派取小值 |
| `SeniorityGroupId` | `(sbyte)-1` | -1 走 `Sect` 建構子 else 分支（無職階稱謂範圍，最安全） |

其餘（`Members`/`CombatSkillTypes`/`CharTemplateIds`/`RetireGrade`/`LargeSectFavorabilities`…）沿用少林值。`GetLargeSectIndex(42) = -1`，所有大派好感度路徑皆有 `index>=0` 防護，自動略過、不崩（phase0 §0）。

---

## 6. 編譯結果（已驗證）

```
$ dotnet build -c Release   # projects/taiwu/ChenJiaBao/Backend
Build succeeded.
    0 Warning(s)
    0 Error(s)
```
csproj 採 0.0.79.60 的**普通引用**（不需 0.0.76.43 時代的 extern alias，見 `details/dual_assembly_type_conflict.md`），`**/*.cs` glob 已 `Exclude obj/**;bin/**`。引用：`GameData / GameData.Shared / GameData.Utilities / Redzen`（`$(Game)/Backend/`）＋ `0Harmony / TaiwuModdingLib`（`Managed/`）。

---

## 7. 使用者實機驗證步驟（待你開遊戲）

> 部署：把 `dist/Config.lua` **轉 GBK** 後與 `ChenJiaBao.Backend.dll` 放到 `<遊戲>/Mod/ChenJiaBao/{Config.lua, Plugins/ChenJiaBao.Backend.dll}`（編碼陷阱見 MySwordArt `BUILD_DEPLOY.md`）。

1. 啟動遊戲，看 backend log 是否出現 `ChenJiaBao.Plugin` 的 `陳家堡注入成功：Organization.Instance[42] Name='陳家堡', IsSect=True, ..., Members.Length=9, CombatSkillTypes.Count=...`。若見 `已存在，略過` 或 `注入失敗` 則需排查。
2. **開新世界**（注入只影響新世界生成，不回改既有存檔）。
3. 確認後端進程未崩、無 `OrganizationDomain` 例外。
4. 用 GM 指令 / 角色資訊面板嘗試確認 id=42 是否進入「可加入門派池」（`InitializeSectOrgTemplateIds` 應已納入）。

⚠️ Phase 1 **看不到陳家堡出現在地圖上**——上地圖是 Phase 2 的工作。本階段只驗證「config 注入成功、後端不崩、進入門派池」。

---

## 8. 已知風險 / 待 Phase 2

- 地圖擺放尚未做 → 世界裡還生不出陳家堡聚落（Phase 2：反射加長某 area 的 `OrganizationId[]`/`SettlementBlockCore[]`）。
- 成員職階稱謂 `GradeName` 目前沿用少林（複用其 `Members`）；要自訂得用 `OrganizationMember.AddExtraItem` 追加 9 列（進階）。
- 前端是否需同步注入名稱（UI 顯示）：本 PoC 只做 backend，前端顯示待 Phase 2/3 實測（武學 mod 是前後端各載一次）。
- 名稱亂碼風險：`Config.lua` 的 `Title` 走遊戲讀檔（GBK 陷阱）；門派 `Name` 走反射塞字串（後端 UTF-8），兩者來源不同，需實機確認顯示。

---

## §前端 org 注入（修 `NameRelatedData.GetMonasticTitle` NRE）

> 2026-05-23 增補。對應上文「前端是否需同步注入名稱」待辦 — 實機證實**必須做**，且 phase0 §6 早提醒「Organization 名稱注入前後端都要做一次」。

### 事實：前後端各一份 `Config.Organization.Instance`

- `Config.Organization` / `Config.OrganizationItem` 型別定義在 **`GameData.Shared.dll`**（不在 `Assembly-CSharp.dll`、也不在 `GameData.dll`）。
  - 實裝路徑驗證：`Managed/GameData.Shared.dll` 與 `Backend/GameData.Shared.dll` **md5 完全相同**（`0645496f76e0e39a381e440a075d72d3`）→ 同一份型別定義，前後端共用、**型別綁定一致、不需 extern alias**（與 `analysis/taiwu/details/dual_assembly_type_conflict.md` 0.0.79.60 結論一致）。
- 但「型別相同」不等於「實例相同」：前端與後端是不同進程／組件，**各自持有一份 `Config.Organization` 單例**。`Organization.Init()` 各自灌 0..41。Backend plugin 的 `InjectChenJiaBao()` 只 `AddExtraItem` 進 backend 那份；**前端那份仍只有 0..41**。

### NRE 根因（path:line）

- 觸發鏈：顯示陳家堡成員法號 → `MapBlockCharNormal.RefreshName` → `NameCenter.GetMonasticTitleOrName`（`~/dev/taiwu-src/Assembly-CSharp/NameCenter.cs:154` → :160 `data.GetMonasticTitleOrDisplayName`）→ `GameData.Domains.Character.Display.NameRelatedData.GetMonasticTitle`（struct，定義在 `GameData.Shared.dll`；反編譯 IL 見 `GameData.Shared.dll` `NameRelatedData::GetMonasticTitle`）。
- `GetMonasticTitle` 內部以 `ConfigData<,>.get_Item(orgId)` 取 `Config.Organization.Instance[42]`。前端那份沒有 42：
  - 先噴 `[Config.Organization]: index 42 is not in range [0, 42)`（count 0）。
  - 取回 null → 後續讀該 `OrganizationItem` 欄位（法號字庫由 `SeniorityGroupId` 決定、`Members` 等）→ `System.NullReferenceException`。

### 做法

- 新增**前端 plugin**：`projects/taiwu/ChenJiaBao/Frontend/`
  - `ChenJiaBao.Frontend.csproj`：net48、`AssemblyName=ChenJiaBao.Frontend`、`Compile Include ../Shared/*.cs`（**重用同一份 `OrganizationItemFactory`，不複製**）。引用照 `MySwordArt.Frontend`：`Assembly-CSharp`/`0Harmony`/`TaiwuModdingLib`/`System.Core` 從 `Managed/`，`GameData.Shared`/`GameData.Utilities` 從 `Backend/`，net48 reference assemblies 用 `Microsoft.NETFramework.ReferenceAssemblies` 1.0.3。
  - `Plugin.cs`：基類 `TaiwuRemakePlugin`（**非** Harmony 版；前端**不做任何地圖／世界生成 patch**）。`Initialize()` 用**與 backend 完全相同的 overrides**（`TemplateId=42`/`Name=陳家堡`/`Desc`/`IsSect=true`/`IsCivilian=false`/`Population=100`；**不覆寫 `SeniorityGroupId`** → 法號字庫沿用少林、`GetMonasticTitle` 才取得到字庫）克隆少林(1)→ id=42 → `AddExtraItem("ChenJiaBao","ChenJiaBao_42",item)` 進**前端**的 `Organization.Instance`。加冪等（`Instance[42]!=null` 則略過）＋ try-catch（前端例外不崩後端，仍防呆只記 log）＋ log。
- `OrganizationItemFactory` **不需任何微調**即可在前端編譯／執行：它只依賴 `Config` 與 `GameData.Utilities.AdaptableLog`；`AdaptableLog`（含 `TagInfo/TagWarning/TagError`）在 `Managed/GameData.Utilities.dll` 與 `Backend/GameData.Utilities.dll` 皆存在，且 `MySwordArt/Shared/DataConfigAppender.cs` 已在前端實際用過 `AdaptableLog.Info`，證明前端可用。
- 編譯：`Build succeeded 0 Warning(s) 0 Error(s)`。
- 部署：
  - `Frontend/bin/Release/ChenJiaBao.Frontend.dll` → `Mod/ChenJiaBao/Plugins/`。
  - `dist/Config.lua` 加 `FrontendPlugins = { [1] = "ChenJiaBao.Frontend.dll" }`（保留 `BackendPlugins`），`iconv -f UTF-8 -t GBK` 寫入 `Mod/ChenJiaBao/Config.lua`。

### 重點教訓

- 「Organization（門派）名稱／config 注入」前後端各要做一次：後端管成員生成／過月，前端管 UI 顯示（法號、成員名）。只做後端 → 後端正常但前端取 `Instance[42]` 回 null → 顯示時 NRE。
- backend 行為完全未動（前端是獨立 plugin、獨立 dll、獨立進程那份 config）。

---

## §大派固定 config 系統性補丁（2026-05-23）

### 問題模式

太吾繪卷有一批「只開 15 格給 15 大派」的 `ConfigData`（`_dataArray = new List<XxxItem>(15)`），呼叫端用 `Instance[orgTemplateId - 1]`（少林那批 TemplateId=0..14）或 `Instance[orgTemplateId]` 索引。陳家堡是第 16 派（`orgTemplateId=42`），踩到這類 config 會越界 / 取得 null → IndexOutOfRange / NRE。

**當前阻斷器（實機 2026-05-23）**：開武學樹 UI →
`UI_CombatSkillTree.RefreshBaseData`（`~/dev/taiwu-src/Assembly-CSharp/UI_CombatSkillTree.cs:279`、`:392`）取
`SectApprovingEffect.Instance[_sectTemplateId - 1]`，`_sectTemplateId=42` → index 41 →
前端那份 `SectApprovingEffect` 只有 0..14 → `[Config.SectApprovingEffect]: index 41 is not in range [0,15)` → IndexOutOfRange、武學樹開不出。

### 系統性掃描方法與結論

掃描指令：在 `Assembly-CSharp/Config/`、`backend/GameData.Shared/Config/`、`backend/GameData/Config/` grep `new List<.*Item>(15)`；再在前後端全樹 grep `Instance[... - 1]` / `Instance[orgTemplateId` / `Instance[_sectTemplateId`。

掃到的 15-長度 config 與分類（**鐵則：以實裝 0.0.79.60 的 DLL 為唯一事實，反編譯源僅當索引；用 `ikdasm <dll>` 驗型別歸屬**）：

| Config | size | 索引語意 | 15 大派 TemplateId | DefKey 是否門派 | 實裝是否存在 | 有無被陳家堡踩到的取用 | 處置 |
|---|---|---|---|---|---|---|---|
| **SectApprovingEffect** | 15 | `Instance[orgTemplateId-1]` | 0..14（少林=0） | 是（Shaolin..Xuehou） | 是（`GameData.Shared.dll`） | **有**（見下） | **注入 TemplateId=41、克隆 index 0** |
| SectMainStory | 15 | `Instance[TemplateId-1]`（`OrganizationItem.SectMainStory` getter） | 0..14 | 是 | **否**（`Config.SectMainStory` 型別 + getter 在實裝 DLL 已移除；反編譯源為陳舊副本） | 無（型別不存在） | 不注入（無風險） |
| TaiwuBeHuntedEvent | 15 | 無 `Instance[..-1]` 取用 | 0..14 | 是 | 是 | **無**（全樹只在 `ConfigCollection`（Init 登記）出現；實際只經 `OrganizationItem.TaiwuBeHunted` 這個 `short` 欄位，克隆少林時已帶值，非索引） | 不注入（理論安全；留意） |
| WorldCreation | 15 | — | — | 否（遊戲難度選項 CharacterLifeSpan 等） | — | — | 排除（非門派） |
| EnemyNest | 15 | — | — | 否（敵巢類型 ViciousBeggarsNest 等） | — | — | 排除（非門派） |
| CombatSkeleton | 15 | — | — | 否（無 DefKey，戰鬥骨架） | — | — | 排除（非門派） |
| MysteryEffect | 15 | — | — | 否（無 DefKey，key=int） | — | — | 排除（非門派） |
| AdvancingMonthState | 15 | — | — | 否（過月階段 NotInProcess 等） | — | — | 排除（非門派） |

**`ikdasm` 驗證關鍵發現（覆蓋反編譯源）**：
- 實裝 `Backend/GameData.dll` **不**定義 `Config.SectApprovingEffect`；唯一定義在 `Backend/GameData.Shared.dll`（型別為 `ConfigData<SectApprovingEffectItem, sbyte>` 子類，**非**反編譯 `Assembly-CSharp/Config/SectApprovingEffect.cs` 那份手寫 `IConfigData`）。
- 前端 `Managed/Assembly-CSharp.dll` 對 `Config.SectApprovingEffect` 的 typeref/IL 全綁 `[GameData.Shared]`（`ldsfld [GameData.Shared]Config.SectApprovingEffect::Instance` / `get_Item(int32)`）。
- ⇒ 全遊戲只有**一個** `Config.SectApprovingEffect` 型別（在 `GameData.Shared.dll`），但前後端各進程載入各自的 `GameData.Shared.dll` → 兩個獨立 `Instance` 物件 → 故仍須**前後端各注入一次**。
- `Config.SectMainStory` 在實裝 `GameData.Shared.dll` 完全不存在（只剩無關的 `Config.AccessoryItem` 的 `SectMainStoryShaolinWellWornShoe` 等 DefValue），`OrganizationItem.get_SectMainStory` 也已移除 → 確認無風險、不需注入。

### SectApprovingEffect 取用點（path:line 依據，皆 `Instance[orgTemplateId - 1]`）

- 前端（`Assembly-CSharp`，實際綁 `GameData.Shared` 型別）：
  - `~/dev/taiwu-src/Assembly-CSharp/UI_CombatSkillTree.cs:279`（武學樹基礎資料）
  - `~/dev/taiwu-src/Assembly-CSharp/UI_CombatSkillTree.cs:392`（武學樹 tips Desc）
  - `~/dev/taiwu-src/Assembly-CSharp/CommonUtils.cs:2378`
- 後端：
  - `~/dev/taiwu-src/backend/GameData.Shared/GameData/Domains/Taiwu/SharedMethods.cs:18`（`.RequirementSubstitutions`）
  - `~/dev/taiwu-src/backend/GameData/GameData/Domains/Taiwu/TaiwuDomain.cs:10216 / :10235 / :10254 / :10275 / :10311`

### 注入做法與 path:line

- 新增泛型工具 `~/repo/pas/projects/taiwu/ChenJiaBao/Shared/ConfigExtraItemInjector.cs`：
  把既有 `OrganizationItemFactory`（OrganizationItem 專用）的「反射逐欄克隆 → 改 TemplateId → AddExtraItem」手法 generalize 成**任意 `ConfigData` + 任意 `ConfigItem`**（全反射）：
  - `TryGetItem`：反射呼叫 `GetItem(key)`（自動把 int 縮窄成 sbyte/short/int 參數型別），退回 `get_Item(int)`；越界吞例外回 null。
  - `CloneItem`：用無參數建構子建空殼 → 逐 instance field 複製（陣列/List 淺拷貝避免別名）→ 反射 `SetValue` 覆寫 readonly `TemplateId`。
  - `Inject(...)`：冪等（目標 id 已取得到 non-null 則略過）＋ 反射呼叫 `AddExtraItem(string,string,object)`（前後端同簽名，皆 `ConfigData<,>` 基類）＋ 取回驗證 ＋ log。
  - 既有 `OrganizationItemFactory` **未動**（org 注入行為不變）。
- 後端 `~/repo/pas/projects/taiwu/ChenJiaBao/Backend/Plugin.cs`：
  - `Initialize()` 在 `InjectChenJiaBao()`（org 42）之後、`base.Initialize()`（Harmony PatchAll）之前呼叫新增的 `InjectSectFixedConfigs()`。
  - `InjectSectFixedConfigs()`：`ConfigExtraItemInjector.Inject(SectApprovingEffect.Instance, "SectApprovingEffect", sourceTemplateId:0, newTemplateId:41, "ChenJiaBao", "ChenJiaBao_SectApprovingEffect_41")`。
- 前端 `~/repo/pas/projects/taiwu/ChenJiaBao/Frontend/Plugin.cs`：
  - `Initialize()` 在 `InjectChenJiaBaoFrontend()`（org 42）之後呼叫新增的 `InjectSectFixedConfigsFrontend()`，內容同上（前端那份 `Instance`）。
- 兩個 Plugin 既有 try-catch 保護維持不變；injector 內任何失敗只記 error log、不外拋。

### 與 Harmony guard 的分工

- 「按 `orgTemplateId-1` 索引、且該 config item 型別仍存在」者 → 用 **extra item 注入**（本節，SectApprovingEffect）。
- 「不是 `ConfigData` 而是裸 `sbyte[15]` 等內部狀態陣列」者 → 無 `AddExtraItem` 可用，須 **Harmony guard**。已知例：`WorldDomain._stateTaskStatuses = new sbyte[15]`（`GetSectMainStoryTaskStatus`/`SetSectMainStoryTaskStatus`，索引 `orgTemplateId-1`），已由 `Backend/Plugin.cs` 的 `GetSectMainStoryTaskStatus_Patch` / `SetSectMainStoryTaskStatus_Patch`（非大派回 0 / 略過）處理。

### 編譯 / 部署

- 後端、前端皆 `Build succeeded 0 Warning(s) 0 Error(s)`。
- 部署 `ChenJiaBao.Backend.dll` / `ChenJiaBao.Frontend.dll` → `Mod/ChenJiaBao/Plugins/`（`Config.lua` 不需改）。

### 殘留風險（需實機才會冒出）

- 本次只實證修好「武學樹越界」這條鏈；其餘 SectApprovingEffect 取用點（過月 `SharedMethods`/`TaiwuDomain`、`CommonUtils`）注入後理應一併解決，但未逐一實機驗證。
- `TaiwuBeHuntedEvent` 雖被列為門派 config，但目前無任何 `Instance[orgTemplateId-1]` 取用、僅經 `OrganizationItem.TaiwuBeHunted` 欄位（克隆少林時已帶值）→ 評估無風險、未注入；若日後改版新增直接索引，須補注入 TemplateId=41。
- 仍可能存在「未在反編譯源出現、或經其他間接路徑」按門派索引 15-長度陣列的取用（尤其過月平行段、戰鬥、特定 UI），實機踩到時依本節同模式（先 `ikdasm` 確認型別與索引語意 → 注入或 Harmony guard）處理。

## §前端門派靜態陣列補丁（SectImg 等）

### 背景

除了「按門派 id 索引的 ConfigData.Instance」外，前端 UI 程式碼還有一批「**寫死長度 15/16、按門派 orgTemplateId 索引的 static readonly 陣列**」。陳家堡 orgTemplateId=42 取 `Arr[42]` 直接 `IndexOutOfRange`，前端例外（不崩後端，但該 UI 開不出）。

實機阻斷器：開陳家堡武學樹 → `UI_CombatSkillTree.RefreshBaseData`（`Assembly-CSharp/UI_CombatSkillTree.cs:281`）`CombatSkillView.SectImg[_sectTemplateId]`，`_sectTemplateId=42` → `SectImg` 為 `public static readonly string[16]`（`Assembly-CSharp/CombatSkillView.cs:15`）→ `[42]` 越界。

### 已 enlarge 的陣列

| 陣列 | 型別 | 原長度 | 索引語意 | 少林來源 index | 宣告 path:line | 消費端 path:line |
|------|------|--------|----------|----------------|----------------|------------------|
| `CombatSkillView.SectImg` | `static readonly string[]` | 16 | `[orgTemplateId]`（圖示名 `charactermenu3_19_menpai_N`，N=orgTemplateId）→ 少林 orgTemplateId=1 對應 index 1 | **1** | `CombatSkillView.cs:15` | `UI_CombatSkillTree.cs:281`（`[_sectTemplateId]`）＋ `InformationUtils.cs:291`（`[settlementInfo.OrgTemplateId]`） |

- 補法：enlarge 到長度 43，`[42] = 舊[1]`（少林圖示名 `charactermenu3_19_menpai_1`），新增空位 16..41 保留 null。
- **一個 enlarge 同時修好兩個消費端**（武學樹 UI + 勢力情報 settlement icon），因兩者都按 orgTemplateId 索引同一陣列、語意一致。
- 空位 16..41 為 null：目前無門派 orgTemplateId 落在該區間，且 `CImage.SetSprite(null)` 不崩 → 安全。

### Helper

抽出 `ChenJiaBao/Shared/StaticArrayPatcher.cs`（`internal static class StaticArrayPatcher`）：
- `EnlargeAndSet(Type declaringType, string fieldName, int targetIndex, int sourceIndex)`：反射取 static 欄位 → 確認為陣列、現值非 null → **冪等**（length>targetIndex 則略過）→ `Array.CreateInstance(elementType, targetIndex+1)` ＋ `Array.Copy` 舊內容 → `newArray[targetIndex]=oldArray[sourceIndex]` → `field.SetValue(null, newArray)`（static readonly 仍可反射寫）。
- 全程 try-catch，失敗只記 `AdaptableLog.TagError`（前端例外不可外溢）。
- 由 `Frontend/Plugin.cs` 的 `PatchSectStaticArraysFrontend()`（在 org / SectApprovingEffect 注入之後）呼叫，傳 `typeof(CombatSkillView), "SectImg", targetIndex:42, sourceIndex:1`。
- 既有前端 org / SectApprovingEffect 注入完全保留、不受影響。

### 排除（掃到但不適合本手法 / 與門派無關）

逐一 grep `Assembly-CSharp/` 全域 `new ...[15]/[16]` 與「按 orgTemplateId/sectId/_sectTemplateId 索引」確認，全前端**唯一**按門派 template id 索引的 static 陣列就是 `CombatSkillView.SectImg`。其餘：

- `TaskGroup.SectImg`（`TaskGroup.cs:64`，`string[16]`）：被 `GetTaskIcon` 以 `SectImg[sect]`（`TaskGroup.cs:287`，`sect=TaskChain.Sect`）索引。但這是 **private instance readonly**（非 static、每實例 inline 初始化各一份）→ static 反射手法不適用；且僅「門派主線任務鏈」會走 `ETaskChainGroup.SectMainStory` 分支，本 mod 未新增任何 `Sect=42` 的 TaskChain → **不會踩到 [42]**，故不處理（列殘留風險）。
- `UI_LifeSkillCombat.EffectTaiwuScoreRemoved` / `EffectEnemyScoreRemoved`（`UI_LifeSkillCombat.cs:60/66`，`static string[16]`）：按 `Model.LifeSkillType`（活計類型 0..15）索引（`:799/:806/:866/:877`），**與門派無關** → 排除。
- 其餘 `Assembly-CSharp/` 內 15-43 長度 static 陣列（`SpineAnimationUtils`、`GlobalConfig.SecretInformationDisplay_*`、`CricketView`、`UI_CharacterMenuEquipCombatSkill.ConsummateBarFillAmount`、各 `GameData/Domains/.../FieldId2FieldName`/`MethodId2MethodName`/`DataId2FieldName` 序列化映射表等）：非門派索引 → 排除。

### 殘留風險（需實機才會冒出）

- `TaskGroup.SectImg`（instance readonly）：若日後替陳家堡新增「門派主線任務鏈」（`TaskChain.Sect=42`、`Group=SectMainStory`），則 `GetTaskIcon` 會踩 `SectImg[42]` 越界。因非 static 無法用本 helper 反射替換，屆時需改 Harmony patch `TaskGroup.GetTaskIcon`（或建構後逐實例 enlarge）。目前未新增此類任務鏈 → 無風險。
- 仍可能存在「未在反編譯源直接出現、或經其他 UI 間接路徑」按門派索引 ≤42 長度 static 陣列的取用（尤其其他 `UI_*` 面板、地圖 UI），實機踩到時依本節同模式（grep 確認型別/索引語意/少林來源 index → `StaticArrayPatcher.EnlargeAndSet`）處理。
