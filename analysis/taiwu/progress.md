# 太吾繪卷 Mod 開發 — 進度快照 (progress.md)

> 更新：2026-05-23。詳細流水帳見 [`session_log.md`](./session_log.md)；本檔為高階現況快照。
> 實裝版 **0.0.79.60**（分支 test）。反編譯源 `~/dev/taiwu-src/`（前端 `Assembly-CSharp/`、後端 `backend/`）為唯一事實來源。
> mod 工作區 `projects/taiwu/`（**依 `.gitignore` 不入庫**；本 repo 僅託管 `analysis/` 留檔）。部署目標 `~/.local/share/Steam/steamapps/common/The Scroll Of Taiwu/Mod/`。

## 五個 mod 現況

| Mod | 功能 | 狀態 | 備註 |
|---|---|---|---|
| **MySwordArt** | 自製劍法「流光劍法」（劇意堆疊特效） | ✅ 實機全綠 | 早先完成；技能顯示/可學/戰鬥特效皆正常 |
| **MonthlyAiDemo** | 過月補滿太吾全部 8 種資源（含金錢） | ✅ 實機驗證 | `AdvanceMonthFinish` 鉤；原為 +50 金錢，依需求改補滿 |
| **AbyssManualEvent** | 深淵地格過月撿祕笈（手寫事件） | ✅ 彈窗＋發書已驗 | `TriggerPercent` 仍 **100（測試值）**，待確認後改回 10 |
| **ChenJiaBao 陳家堡** | 新增第 16 個門派（克隆少林） | ✅ 過月/名稱/武學樹圖示/**產業（append→取代槽）皆實機驗過** | 見下方專節 |
| **QolCheats** | 無限行動點 ＋ 開局解鎖驛站 | ⏳ 已部署待實機 | 行動點 Harmony patch `ConsumeActionPoint`；驛站 `OnEnterNewWorld` 設旗標＋逐區 UnlockStation |

## 陳家堡（第 16 派）— 重點與「三類修正」

落點：**太吾村起始區**（runtime Harmony patch `MapDomain.CreateNormalArea`，在玩家選定的太吾村那一格**取代原城鎮槽**；非靜態，因起始州開局才定）。克隆少林(org 1)→ org **42**。

> ⚠️ **不可 append（2026-05-23 產業 crash 根因）**：太吾村「家園」block/settlement 被前端寫死在 `SettlementInfos[1]`（`WorldMapModel.GetTaiwuVillageBlock`/`GetTaiwuVillageSettlementId`）。起始區聚落順序＝org 填 `[0..Length-1]`、家園永遠 append 最後（原版 Length==1 → 家園恰在 `[1]`）。append 陳家堡使 Length 變 2 → 家園被擠到 `[2]`、`SettlementInfos[1]` 變陳家堡 → 家園身分被劫持，點陳家堡產業時 `BuildingModel.GetBuildingLevel` 誤入家園分支、字典查無 → NRE crash。**修法＝取代 `OrganizationId[0]`（長度維持 1）→ 家園仍在 `[1]`**，代價是原城鎮被取代。詳見 `new_sect_mod/phase2_map_findings.md §10`。

**核心心得：把「新增第 16 個門派」做成功，要對付遊戲各處「只給 15 大派、按門派 id 索引的固定結構」。分三類修：**

1. **ConfigData（有 `AddExtraItem`）→ 注入克隆少林的 extra item**（**前後端各一次**，因前後端各持一份 `Instance` 單例）
   - `Organization`（key=orgTemplateId → 注入 TemplateId **42**）— 否則生不出/顯示 NRE。
   - `SectApprovingEffect`（key=orgTemplateId-1 → 注入 TemplateId **41**）— 否則開武學樹崩。
   - 工具：`Shared/ConfigExtraItemInjector.cs`（泛型反射）。
2. **後端裸陣列/方法 → Harmony guard 回安全值**
   - `WorldDomain.GetSectMainStoryTaskStatus`（`_stateTaskStatuses=sbyte[15]`）→ 非大派回 0、跳過；否則過月成員更新崩。
3. **前端 UI 靜態陣列 → 反射 enlarge**
   - `CombatSkillView.SectImg`（`static readonly string[16]`）→ enlarge 到 43、[42]=少林圖示；修武學樹＋勢力情報圖示。
   - 工具：`Shared/StaticArrayPatcher.cs`。

**其他關鍵踩雷（皆已修，依據見 `new_sect_mod/`）**：
- `SeniorityGroupId` **不可設 -1**（克隆少林＝僧侶派，成員生成要法號字庫；-1→空→`Random.Next(0)` 開新世界崩）。沿用少林值。
- `MapAreaData.SettlementInfos` 硬限 **3 格**：不能把 3 聚落區加長到 4（崩＋壞存檔）。
- 「死地」機制：config TemplateId≥31 的第三區隨機抽 1 生成、其餘變破碎之地不生聚落 → 落點要選必生區（門派區/太吾村區）。

**殘留風險**：`TaskGroup.SectImg`（instance readonly，僅門派主線任務鏈會踩，本 mod 無此任務鏈→目前無風險）；其他極冷門、實機才冒出的「按門派 id 索引 ≤42 結構」依上述三類之一補。

## 通用技術備忘（跨 mod）

- **前後端分離**：backend 是獨立 net6 進程（`<遊戲>/Backend/`），frontend net48（`Managed/`），各持一份 Config 單例 → config 注入/名稱顯示要前後端各做。
- **編碼（2026-05-24 更正，推翻先前「GBK」）**：`Config.lua` 前端 `ModManager.ReadModInfo` 以 `File.ReadAllText` **無編碼＝UTF-8** 讀（已對實裝 Assembly-CSharp.dll 核對，.NET/Mono 預設 UTF-8 與 OS locale 無關）→ **Config.lua 須 UTF-8**；先前轉 GBK 正是 mod 啟用界面中文顯示**方塊(□)** 的主因（GBK byte UTF-8 解碼失敗→U+FFFD）。已把 Mod/ 下全部 mod 的 Config.lua 轉回 UTF-8（待視覺確認）。YAML / 事件語言檔由後端 net6 以 UTF-8 讀（不變）。
- **型別綁定**：0.0.79.60 普通引用、不需 extern alias（舊版 0.0.76.43 才需）。`**/*.cs` glob 要 Exclude obj/bin。
- **後端 mod 未捕捉例外＝整個 GameData 進程崩潰斷線**（比前端例外嚴重）；所有 patch/反射務必 try-catch＋防呆。
- **事件條件 `OnCheckEventCondition` 會被多次評估**：勿放隨機（要骰一次快取）、查地圖前先驗位置有效（太吾在秘境時 GetLocation 回 {-1,-1}）。
- 武學書：`CreateSkillBook` 參數是 SkillBook 物品 id（`CombatSkill.Instance[skillId].BookId`），非武學 id。
- 需求屬性用造詣（Attainment）非資質（Qualification，後端 GetPropertyValue 不支援會崩）。

## 中小門派 mod（dynamic_sect_mod）— 開工進度（2026-05-24）

完整設計＝[`dynamic_sect_mod/design_vision.md`](./dynamic_sect_mod/design_vision.md)（六項基礎實驗 mod，已結構化＋§六全拍板＋首期 MVP 彙整）。起手＝**experiment #1（收徒與傳授）**，採**調查優先**。

**接點調查（5 份平行 subagent，皆對實裝 0.0.79.60 DLL 核對）**：[`dynamic_sect_mod/research/`](./dynamic_sect_mod/research/) `01-05.md` ＋ `README.md`（綜述＋訂正漂移表＋各實驗備料狀態）。**核心結論：experiment #1 不需門派 / 不需 Harmony / 不需新美術。**
- **01 師徒**＝獨立雙向 bitflag(Mentor=2048/Mentee=4096)；建立 `AddRelation(ctx,弟子,師父,2048)`；收徒封裝 `EventHelper.ApplyRelationBecomeMentor(弟子,師父)` `:6215`；查徒弟 `GetRelatedCharIds(id,4096)`；NPC 不自發收徒須 mod 驅動。
- **02 傳授**＝`CharacterDomain.LearnCombatSkill(ctx,charId,skillId,readingState)` `:4248`（通用、無祕笈/造詣門檻、已學會丟例外須先防重）；原版另有 `TeachCombatSkillAction` 現成語義。
- **03 變異**＝`Config.CombatSkillItem`(Shared.dll，欄位 readonly 靠反射)；五行=`FiveElements`(0-5)、威力=`TotalHit` 等；改五行只染色不換 sprite；變異須新 TemplateId 注入(`AddExtraItem` 前後端各一次)；MVP 零美術但造詣門檻須自查；風險＝運行期動態注入＋跨存檔持久化未證。
- **04 互動選項**＝官方事件系統 `NpcInteractEvent`+CharacterClicked（純前端 patch 加不了動作選項）；條件式選項現成(創派=是太吾弟子 AND NOT CharacterInSect(21)；據點=CharacterIsCastellan(33))；承載動作全有 EventHelper API；缺口＝「委託請師傅派人」。
- **05 動態誕生**＝「預生池＋認領」(注入空門派 config id≥42 克隆世俗派→`CreateEmptySects` 自動生佔位 sect AreaId=-1→`JoinSect` 認領)，**不要 runtime 新建**；升格＝過月鉤數 `GetMembers().GetCount()`＋據點走 mod 私有表；釘死＝`RemoveSettlementCache` 從不被呼叫→小派不上地圖 count 恆 1。
- **訂正既有調查漂移**：LearnCombatSkill `:3984→:4248`、`CharacterDomainHelper.MethodCall→CharacterDomainMethod.Call`(id 92→91)、`RelationType.AllowAdding*→RelationTypeHelper`、`CombatSkillItem→Config.CombatSkillItem`(Shared)、接點表「據點→_taiwuBuildingAreas」是太吾家園專屬軌**不適合小派**。

**4 個驗證 spike mod**（`projects/taiwu/`，各獨立目錄）。下表為 **2026-05-24 收尾後的磁碟實況**：

| spike | 對應實驗 | 狀態 |
|---|---|---|
> **2026-05-24 全部 4 spike 已部署（UTF-8 Config.lua）、實機一輪：mod 名顯示正常；過月曾崩於 DirectedActionSpike（已修，見表下）。待再開新世界複測。**

| **MentorSpike** | #1 收徒/傳授 | ✅ build 過＋**已部署**（`Mod/MentorSpike/{Config.lua(UTF-8)、Plugins/…dll}`）。過月鉤造測試 NPC→拜太吾為師→傳一招；驗證看後端 log `[MentorSpike]` ＋「人物關係」面板。具 try-catch＋安全 NPC 模板來源。 |
| SkillMutationSpike | #6 武功變異 | ✅ 前後端 build＋VERIFY＋**已部署**。載入期注入「－水（變異測試）」→過月 `TaiwuLearnCombatSkill` 送太吾（實機 log 確認前端注入成功 id=4710）。**2026-05-24 補過月鉤 try-catch**（原缺）。 |
| DirectedActionSpike | #2 命弟子 | ✅ **已部署＋2026-05-24 修過月 NRE**（見表下）。`AdvanceMonthBegin` 維護指派表每月重放 `TakeRevengeAction`，執行者逐月移向目標動手。 |
| DynamicSectSpike | #5 動態創派 | ✅ 親寫＋Release 0/0＋VERIFY＋**已部署**。見下方專節。 |

**DirectedActionSpike 過月 NRE 修正（2026-05-24 實機踩到）**：過月後端崩斷線。根因＝`CreateOne` 用「太吾自己的 OrgTemplateId（開局＝太吾村 16）」算 `GetCharacterTemplateId`→走 fallback 配開局早期 state→無效 charTemplateId→`new Character(無效id)` 取 `Config.Character.Instance[id]=null`→ctor NRE（`GameData.dll:21659`）；且 `OnAdvanceMonthBegin` **無 try-catch**→直接崩整個後端。三點修：①改 `GetRandomSectOrgTemplateId(random,gender)` 算 growingSect/charTemplate（真門派 1-15→模板必有效，同 MentorSpike 證實做法）；②加 `location.IsValid()` 防呆；③整段 try-catch、`TrySpawn` 回傳 bool 只成功才標 _spawned。**通則：`CreateIntelligentCharacter` 的 charTemplateId 一律用真門派(1-15) 算、勿用太吾 org(16)；每個過月後端鉤必 try-catch（4 spike 共用後端，任一未捕捉例外拖垮全部）。**

### DynamicSectSpike(#5) — 重做完成（2026-05-24）

依 research/05「**預生池＋認領**」配方，全部關鍵 API **對實裝 0.0.79.60 DLL `ilspycmd -t` 逐字核對**（行號與研究 05 完全吻合：`CreateEmptySects:2086`／`GetSettlementByOrgTemplateId:637`〔count!=1 回 null〕／`GetSettlementIdByOrgTemplateId:677`／`JoinSect:702`／`Settlement.GetMembers:1799`／`OrgMemberCollection.GetCount`）。流程：
- **Initialize**：注入 1 個空門派 config（id **50**，避開陳家堡 42；克隆少林、`IsSect`、`Population=0`、`Hereditary=false`、`InfluencePowerUpdateInterval=0`、**保留 SeniorityGroupId**）＋ `SectApprovingEffect[49]` 注入（同陳家堡防越界）＋ `base.Initialize()` 掛 Harmony guard。
- **核實命脈**：`CreateEmptySects` 本體**不呼 CreateSettlementMembers** → 佔位 sect 天生空成員；只要不上地圖 count 恆 1 → `GetSettlementByOrgTemplateId(50)` 穩回。
- **必帶 Harmony guard**：id 50 是真 Sect，過月 `UpdateOrganizationMembers` **無條件**對每個 `_sects`（含 AreaId=-1 佔位）呼 `UpdateMemberGrades`→`GetExpectedCoreMemberAmount`→`GetSectMainStoryTaskStatus(50)` 越界 → 沿用陳家堡 guard（非大派回 0）。
- **過月鉤**：首月認領佔位 sect（造創派者 grade8 principal＋2 弟子 grade0 **principal=false 繞過 `CheckPrincipalMembersAmount`**，`JoinSect` 進 `GetSettlementIdByOrgTemplateId(50)`）→ 後續每月補人並 `GetMembers().GetCount()` 數人，達 10 顯示升格中型。
- **安全決策依據（皆實裝核對）**：`TryBecomeSectMonk:1595` 僅 `ProbOfBecomingMonk>0 且命中` 才變僧（克隆少林沿用 SeniorityGroupId → 變僧不崩）；`CheckPrincipalMembersAmount:1840` 僅 `Principal && RestrictPrincipalAmount && 該階principal數>Amount` 才 throw（掌門 1 人≤Amount 1、弟子非 principal）。
- **前提**：只能在「啟用本 mod 後**新建**」的世界驗（舊存檔當初沒注入 50 → 無佔位，plugin 防呆 log warning 不崩）。**只驗 NPC 版**（不碰太吾自身 org，副作用未證）。

**下一步**：① 把可用 spike 部署實機——**MentorSpike 已部署，待使用者開新世界驗**（看 log `[MentorSpike]` ＋人物關係面板）；其餘三個（DirectedActionSpike/SkillMutationSpike/DynamicSectSpike）視 MentorSpike 結果再逐一部署。② DynamicSectSpike 須**開新世界**驗（log `[DynamicSectSpike.Plugin]`：佔位空→認領後成員 3＋`GetSettlementByOrgTemplateId(50)` 仍穩回→逐月成長→升格；過月不因 `GetSectMainStoryTaskStatus` 越界崩）。③ 依結果決定 experiment #1 往「太吾版互動選項 UX」或「NPC 版自然收徒」長。**延後項**：experiment #3 外交/階級（依賴 sect 成立）尚未開調查。

## 待辦 / 下一步
- [x] ~~開新世界驗證產業 crash 修復~~ **✅ 實機正常（2026-05-23）**：取代槽修法生效，點陳家堡產業不再 crash、家園身分不被劫持。
- [ ] **（使用者要求，下一步要做）給陳家堡添加自製武功並在 UI（武學樹/勢力情報）顯示**。
- [ ] （非致命，順手觀察）後端 `Organization.CivilianSettlements.7.Members` 監控 WARN 是否仍在（克隆少林多聚落殘留）。
- [ ] 實機確認陳家堡武學樹可開、整套順（生成/加入/過月/成員名/武學樹/勢力情報/產業）。
- [ ] QolCheats 實機驗證（行動點不掉、開局驛站可用）；觀察開局極早期解鎖驛站是否干擾引導。
- [ ] AbyssManualEvent `TriggerPercent` 100 → 改回 10。
- [ ] 其餘陳家堡殘留大派結構：實機踩到再依三類修。

## 物件資料解壓縮（非 mod，2026-05-24）

把遊戲六大類物件的「名稱＋品級」整批抽出，留檔 [`object_data_dump/`](./object_data_dump/)（含 README、6 份 md、taiwu_objects.json、抽取工具）。

- **架構**：config 資料硬編在反編譯 `Assembly-CSharp/Config/<Table>.cs`（`new <Table>Item(arg0,…)` 靜態初始化）；`<Table>Item.cs` 建構子本體記「欄位=argN」。品級／數值＝.cs 字面值；**名稱權威來源＝安裝版 `StreamingAssets/ConfigRefNameMapping/<Table>.ref.txt`（name↔TemplateId，版本同步）**。語言檔 `Language_CN/*_language.txt` 行號索引在部分表（BuildingBlock/Organization）相對反編譯版漂移，故棄用，改 ref。
- **成果**：武功 919 · 物品 4210（12 類，Grade 0~8）· 職稱/身份 244（`OrganizationMember`，Grade 0~8）· 建築 319（`BuildingBlock`，MaxLevel）· 城鎮種類 6（`EOrganizationSettlementType`）。工具：`extract_objects.py` + `render_markdown.py`，唯讀可重現。
