# 新門派 Mod 調查與實作計畫 (plan.md)

> 範疇：調查《太吾繪卷》(0.0.79.60) 如何以 mod 新增一個「門派 / 組織」。
> 本檔為**規劃文件**，不改任何既有產出檔（為避免與另一個並行 session 搶寫，
> 本次刻意不寫入 `session_log.md`，也不碰 `details/`、`answers/` 下檔案）。
> 所有結論皆以反編譯原始碼為準（`~/dev/taiwu-src/`），analysis 既有文件僅作索引。

---

## 決策與狀態（2026-05-23 鎖定）

- **目標**：主題＝**陳家堡**，普通小型門派；**最小可行（路線 A）**；地圖**新增槽位**。不做大派、不做故事線。
- **Phase 0 補完調查：已完成** → 詳見同目錄 [`phase0_findings.md`](./phase0_findings.md)。
- **可行性上修**：Phase 0 推翻了初版「需跨兩道牆、屬大型 mod」的悲觀估計——**最小可行陳家堡預期零核心 Harmony 補丁**，降為「中型 mod」。本檔 §0/§3/§5/§6/§8 已被 `phase0_findings.md` 修正，以後者為準。

## 0. 一句話結論（已修正）

**`OrganizationItem.IsSect=true` 時，`CreateSettlement(42)` 直接生成真正的 `Sect`（讀 config 旗標，非寫死 1..15）；寫死 1..15 的只有「大派好感度網」且全有 `index>=0` 防護會自動略過——所以「第 16 個小派」就是預設行為，無需改核心判定。** 真正的工作集中在：①反射克隆 `OrganizationItem`（無 `Duplicate`）②backend `Initialize()` 注入 ③反射加長某 area 的 `OrganizationId[]`+`SettlementBlockCore[]` 一格上地圖（唯一較硬處）④前端同步注入名稱。

---

## 1. 「門派」在資料模型裡是什麼

太吾的「門派」= **Organization**（組織）。它是一個更大的概念，涵蓋門派、城鎮、聚落類型。

### 1.1 三層結構

| 層 | 型別 | 位置 | 角色 |
|----|------|------|------|
| Config 列（藍圖） | `OrganizationItem` | `backend/GameData/Config/OrganizationItem.cs` | 一個門派的靜態定義（38+ 個欄位） |
| Config 表 | `Organization`（單例 `Organization.Instance`） | `backend/GameData/Config/Organization.cs` | 所有組織列的容器 + 追加 API |
| 執行期實體 | `Sect` / `Settlement` / `CivilianSettlement` | `backend/GameData/GameData/Domains/Organization/` | 開新世界時依 config 生成的「活」門派、聚落、成員 |

> 注意：`OrganizationItem` 是**藍圖**，`Sect`/`Settlement` 是開局時依藍圖**生成的實體**。改 config 只影響「新世界生成時長什麼樣」，不會回頭改既有存檔。

### 1.2 既有 38 個 DefKey（`Organization.cs:13-91` 的 `DefKey`）

| TemplateId | 名稱 | 類別 |
|---|---|---|
| 0 | None | 佔位 |
| **1–15** | Shaolin/Emei/Baihua/Wudang/Yuanshan/Shixiang/Ranshan/Xuannv/Zhujian/Kongsang/Jingang/Wuxian/Jieqing/Fulong/Xuehou | **15 大派**（`IsSect=true`） |
| 16 | Taiwu | 太吾村（玩家） |
| 17–18 | Heretic / Righteous | 邪道 / 正道（陣營，非聚落） |
| 19–20 | XiangshuMinion / XiangshuInfected | 相щ（反派陣營） |
| 21–35 | Jingcheng…Yangzhou | 15 座城鎮（`IsCivilian=true`） |
| 36–38 | Village / Town / WalledTown | 民居聚落類型 |

實際 `_dataArray` 還灌到 TemplateId **41**（`CreateItems0()`，`Organization.cs:121-362`），共 **42 列**（0–41）。所以 mod 追加新門派的 TemplateId 必須 **≥ 42**。

### 1.3 一個門派由哪些欄位構成（`OrganizationItem.cs` 完整欄位）

關鍵欄位分組（源：`OrganizationItem.cs:10-78`）：

- **身份**：`TemplateId(sbyte)`、`Name`、`Desc`、`StoryName`、`OrganizationExtraDesc`
  - Name/Desc 在建構子裡走 `LocalStringManager.GetConfig("Organization_language", id)`（`OrganizationItem.cs:81-83`）→ 預設靠語言表；**mod 可用反射直接塞字串繞過語言表**。
- **旗標**：`IsSect`（是不是門派）、`IsCivilian`（是不是民居）、`Hereditary`（世襲）、`GenderRestriction`（性別限制 -1/0/1）
- **屬性**：`Culture`（文化）、`Safety`（治安）、`Population`（人口）、`Goodness`（正邪）、`MainMorality`、`FiveElementsType`（五行）
- **成員/角色**：`CharTemplateIds(short[2])`（門派關鍵角色＝掌門等，指向 Character 模板）、`Members(short[])`（各職階成員模板，指向 `OrganizationMember` 表）、`RandomEnemyTemplateIds(short[9])`、`MemberFeature`
- **武學/技藝**：`CombatSkillTypes(List<sbyte>)`（教哪些武學類別）、`LearnLifeSkillTypes(List<sbyte>)`（生活技藝）、`SkillBreakBonusWeights`、`MartialArtistItemBonus`
- **職階**：`SeniorityGroupId`、`RetireGrade`（職階系統，grade 0–8 共 9 階，見 `OrganizationDomain.cs` 多處 `for (grade = 0; grade < 9)`）
- **關係**：`LargeSectFavorabilities(sbyte[15])` ← **固定長度 15，對應 15 大派**、`AbandonedBabyOrganizations`
- **故事/任務**：`TaskChains(int[])`、`TaskReadyWorldState`、`StoryGoodEndingsInformation`、`StoryBadEndingsInformation`、`StoryName`
- **其他**：`MerchantTendency/Level`、`LegendaryBookTendency`（殘卷）、`PunishmentFeature`、`PrisonBuilding`、`AllowPoisoning`、`NoMeatEating`、`NoDrinking`、`InfluencePowerUpdateInterval`、`TaiwuBeHunted`

---

## 2. 技術可行性：好消息

### 2.1 Config 追加有官方 API ✅

`Organization.AddExtraItem(identifier, refName, configItem)`（`Organization.cs:383-402`）：
- 要求 `TemplateId >= _dataArray.Count`（即 ≥ 42），否則丟例外；
- 寫入 `_extraDataMap` 與 `_refNameMap`；
- 索引器 `GetItem(sbyte)`（`Organization.cs:404-419`）會自動 fallback 到 `_extraDataMap`，故新派可正常被 `Organization.Instance[id]` 取到；
- `GetEnumerator`、`Iterate`、`GetAllKeys`（`Organization.cs:421-477`）都會把 extra 列一起吐出。

> `AddExtraItem` 是太吾**通用的 ConfigData 追加機制**（幾十個 config 表都有，見 `grep AddExtraItem`），與 MySwordArt 武學 mod 用的是同一條路。`OrganizationItem` 欄位雖全 `readonly`，但反射 `FieldInfo.SetValue` 照樣能寫（MySwordArt 的 `DataConfigAppender.ApplyChanges` 已驗證，`projects/taiwu/MySwordArt/Shared/DataConfigAppender.cs`）。

### 2.2 部分子系統會自動認新派 ✅

凡是「遍歷 `Config.Organization.Instance` 並看 `item.IsSect`」的程式碼，都會自動把 `IsSect=true` 的 extra 新派算進去。已確認的關鍵例子：
- **`InitializeSectOrgTemplateIds()`**（`OrganizationDomain.cs:3730-3756`）：掃 config 建 `_allSectOrgTemplateIds / _femaleSectOrgTemplateIds / _maleSectOrgTemplateIds`——新派會被納入「可加入的門派池」。
- 成員/技藝生成迴圈（`OrganizationDomain.cs:2010`、`2098-2114`）：`foreach (orgCfg ...) if (orgCfg.IsSect)`。

### 2.3 地圖擺放是資料驅動 ✅（但需介入）

世界生成時聚落由 `MapDomain` 放置（`MapDomain.cs:4092-4101`）：
```csharp
sbyte orgTemplateId = isTaiwuVillage ? 16
    : (isStoryStockade ? 38 : areaConfigData.OrganizationId[i4]);
short settlementId = DomainManager.Organization.CreateSettlement(context, location, orgTemplateId);
```
→ **哪個區塊生哪個門派，由 `MapArea` config 的 `OrganizationId[]` 陣列決定**（`Config/MapArea.cs` / `MapAreaItem.cs`）。
`CreateSettlement(context, Location{AreaId,BlockId}, orgTemplateId)` 是 public（`OrganizationDomain.cs:2023`），且 `DomainManager.Organization` 可達——**mod 也能自行呼叫**來放置聚落。

---

## 3. 技術風險：兩道牆

### 牆 A：「門派 = 1..15」寫死

存在**兩種**門派判定，必須區分：

1. `OrganizationItem.IsSect`（config 旗標）—— 多數邏輯用它，遍歷會掃到 extra 列 ✅
2. **`OrganizationDomain.IsSect(sbyte orgTemplateId)`**（`OrganizationDomain.cs:1317`）：
   ```csharp
   return orgTemplateId >= 1 && orgTemplateId <= 15;
   ```
   以及緊接的大派索引（`OrganizationDomain.cs:1322`）：
   ```csharp
   return (orgTemplateId >= 1 && orgTemplateId <= 15) ? (orgTemplateId - 1) : -1;
   ```

新派 TemplateId ≥ 42 → **過不了第 2 種判定**。受影響：`LargeSectFavorabilities[15]` 索引、幫派領袖斷言（`OrganizationDomain.cs:2949` 對非 [1,15] 組織會丟例外）、影響力更新、大派專屬機制（比武大會主辦、好感度網等）。

牽連檔案（`grep LargeSectFavorabilities`）：`GlobalConfig.cs`、`RandomEnemyItem.cs`、`OrganizationDomain.cs`、`OrganizationDomainHelper.cs`、`CharacterDomain.cs`、`Character.cs`、`WorldDomain.cs`、`HuntFugitiveAction.cs`、`VillagerRoleLiterati/SwordTombKeeper.cs`、`ExtraDomain.cs`。

> 結論：要把新派做成「**第 16 個大派**」，得 Harmony patch `IsSect()`/大派索引並擴大 `sbyte[15]` 為 [16]——但這會改變既有 15 大派的索引基礎，連鎖風險高（與 MySwordArt 擴大 `EquipAddPropertyDict` 容量是同一類「固定容量」陷阱，見 `details/martial_arts_mod_anatomy.md` §6）。

### 牆 B：相依資源鏈很長

一個「能玩」的門派不只一列 config，還需要：

| 相依 | 來源/表 | 難度 |
|------|---------|------|
| **成員模板** `Members[]` | `OrganizationMember` 表（`Config/OrganizationMember.cs`，**15625 行**，每職階一個模板；`Members[grade]` 取用見 `OrganizationDomain.cs:2314/2450/2512`） | 高（要嘛複用既有、要嘛追加） |
| **關鍵角色** `CharTemplateIds[2]` | Character/CharacterTemplate config（掌門等） | 中（可複用既有角色模板） |
| **武學** `CombatSkillTypes` | CombatSkill 類別（MySwordArt 已能新增武學） | 低（已有經驗） |
| **地圖位置** | `MapArea.OrganizationId[]` 或自呼 `CreateSettlement` | 中高（要找空 block、避開既有派） |
| **建築** | `DomainManager.Building.PlaceBuildingAtBlock`（`OrganizationDomain.cs:319/332`）、`PrisonBuilding` | 中 |
| **本地化名稱** | `Organization_language` 表 / 反射塞字串 | 低 |
| **故事/任務** | `TaskChains`、`Story*Endings`、`TaiwuEvent` 系統 | 高（可留空） |
| **職階/退休** | `SeniorityGroupId`、`RetireGrade` | 中（可複用既有派數值） |

---

## 4. 哪些東西「自動會動」 vs「要手動補」

| 機制 | 新派(IsSect=true, id≥42) 是否自動運作 | 依據 |
|------|------|------|
| 被 `Organization.Instance[id]` 取到 | ✅ | `GetItem` fallback `_extraDataMap` |
| 進入「可加入門派池」 | ✅ | `InitializeSectOrgTemplateIds` 掃 config |
| 成員/技藝生成迴圈納入 | ✅（若有 Members/CombatSkillTypes） | `OrganizationDomain.cs:2010/2098` |
| 大派好感度網 `[15]` | ❌ | `IsSect(id)` 寫死 1..15 |
| 自動出現在地圖上 | ❌（需改 `MapArea.OrganizationId[]` 或自呼 `CreateSettlement`） | `MapDomain.cs:4101` |
| 幫派領袖系統 | ❌（id 不在 1..15 會丟例外） | `OrganizationDomain.cs:2949` |
| 比武大會 / 影響力大派專屬 | ❌ | 多處 1..15 判定 |

---

## 5. 兩條實作路線

### 路線 A — 最小可行門派（建議先做）
**目標**：世界裡真的出現一個能被看見、能加入、有成員、教自訂武學的「組織」，但不強求它享有 15 大派的全部待遇。

策略：
- 新派 `IsSect=true`、TemplateId=42、`Members`/`CombatSkillTypes`/`CharTemplateIds` **複用某既有大派的值**（克隆其列再覆寫 Name/Desc/武學）。
- **地圖**：Harmony 後置補丁 `MapDomain` 世界生成，或改 `MapArea.OrganizationId[]` 把某個區塊的一個聚落槽改成 42；先做「取代地圖上某個城鎮/民居槽」最省事。
- **不碰** `IsSect(1..15)` / `LargeSectFavorabilities`——接受新派暫不進大派好感度網、不辦比武。
- 避開會丟例外的路徑（幫派領袖：新派暫不設 Faction）。

風險最低，能最快驗證「config 追加 + 上地圖 + 成員生成」整條鏈是否通。

### 路線 B — 完整第 16 大派
在 A 的基礎上再 Harmony patch：
- `OrganizationDomain.IsSect()` 放寬上界、大派索引函式、`LargeSectFavorabilities` 擴容到 16；
- 補比武大會、影響力、好感度初始化；
- 補故事線 `TaskChains` / 結局。
工作量大、連鎖風險高，**等 A 驗證成功再評估**。

---

## 6. 分階段實作計畫

- **Phase 0 — 補完調查 ✅ 已完成**（結果見 [`phase0_findings.md`](./phase0_findings.md)）
  - [x] `OrganizationMember` 結構：`Members` 必須 `short[9]`（職階 0..8），各階靠 `Amount>0` 才生人；最小可行**複用既有派 Members 陣列**。
  - [x] `MapArea`：`settlementCount = OrganizationId.Length`（`MapDomain.cs:3879`）；`OrganizationId[i]` 與 `SettlementBlockCore[i]` 平行對應 → 「新增槽位」＝反射把兩陣列同步加長一格。
  - [x] 注入時機：backend `Initialize()`（MySwordArt 已驗證 config `Init()` 先於 plugin `Initialize()`）。
  - [x] `OrganizationItem` **無 `Duplicate()`** → 需反射逐欄複製（不能直接套 MySwordArt appender）。
  - [x] `SeniorityGroupId=-1` 最安全（`Sect` 建構子走 else 分支）；`RetireGrade` 沿用來源派。
  - [x] 核心結論：**最小可行不需 Harmony patch 核心門派判定**（`IsSect` 讀 config 旗標）。

- **Phase 1 — 純資料 PoC（不上地圖）**
  - [x] backend plugin：克隆少林(1) 的 `OrganizationItem` → id 42、覆寫 `Name`/`Desc`（反射塞字串）、保留其餘欄位 → `AddExtraItem`。**✅ 程式完成、`Build succeeded 0/0`**，見 [`phase1_poc.md`](./phase1_poc.md)、`projects/taiwu/ChenJiaBao/`。
  - [ ] 啟動遊戲，確認後端不崩、log 出現新組織、`Organization.Instance[42]` 可取。（實機待測）
  - [ ] 用 GM 指令 / 角色資訊面板驗證新派是否進入「可加入門派池」。（實機待測）

- **Phase 2 — 上地圖（路線 A 核心）**
  - [x] **調查完成**，見 [`phase2_map_findings.md`](./phase2_map_findings.md)。平行對應 `SettlementBlockCore[i]`↔`OrganizationId[i]` 等長確立；`SettlementBlockCore[i]` 是 **block 模板 id**（引擎自動找空位）；注入時機放 `Initialize()` 安全。
  - [x] **⚠️ 重大修正（推翻本檔 §3.2 / phase0 §3「任意 area 加長一格」）**：`MapAreaData.SettlementInfos` 硬寫死長度 3（`MapAreaData.cs:70/141/182`），把 3 聚落區加長到 4 → IndexOutOfRange 崩潰＋序列化斷言失敗壞存檔。**修正策略**＝在常規野外區（1 聚落，如 area 31）加長到 2（方案①，建議）；或取代既有 3 聚落區的一個槽（方案②，少一原版聚落）。
  - [x] 把 `PlaceOnMap()`（目標 area 31、block 模板 19、含 >3 防呆）整合進 ChenJiaBao `Plugin.cs` 的 `Initialize()`（org 注入後呼叫），`Build succeeded 0/0`，已部署到 `<遊戲>/Mod/ChenJiaBao/`。
  - [ ] 開新世界，確認地圖上出現該聚落、可進入、成員依 `Members`/職階生成、不崩；存讀檔往返正常。（實機待測）

- **Phase 3 — 內容填充**
  - [ ] 接上 MySwordArt 自訂武學作為門派 `CombatSkillTypes`。
  - [ ] 調 `Culture/Safety/Population/Goodness/五行`、`CharTemplateIds`（掌門）。
  - [ ] 本地化名稱顯示驗證（注意 `Config.lua` 的 GBK 編碼陷阱，見 `projects/taiwu/MySwordArt/BUILD_DEPLOY.md`）。

- **Phase 4（可選）— 升格為大派（路線 B）**
  - [ ] Harmony patch `IsSect()` / 大派索引 / `LargeSectFavorabilities` 擴容。
  - [ ] 比武大會、影響力、好感度、故事線。

- **Phase 5 — 收尾**
  - [ ] 寫 `tutorial/add_new_sect.md`、更新 `index.md`。
  - [ ] 整理 BUILD/DEPLOY、編碼、需求陷阱。

---

## 7. 可直接復用的既有資產

| 資產 | 來源 | 用途 |
|------|------|------|
| 通用 config 追加器 | `projects/taiwu/MySwordArt/Shared/DataConfigAppender.cs` + `DataConfigAppenderHelpers.cs` | 改造成 `AddOrganizationItemToConfig`（呼 `Organization.AddExtraItem`） |
| 雙組件型別衝突解法 | `details/dual_assembly_type_conflict.md` | Config 型別綁定（0.0.79.60 已不需 extern alias） |
| 編譯/部署/編碼流程 | `projects/taiwu/MySwordArt/BUILD_DEPLOY.md` | net6 backend + net48 frontend、`Config.lua` 轉 GBK、YAML 維持 UTF-8 |
| 屬性 ID 對照 | `details/property_ids.md` | 需求屬性、五行等數值 |
| Mod 載入機制 | `architecture/mod_loader.md` | plugin 生命週期、backend 進程位置 |
| backend 事件/動詞 API | `details/backend_combat_events.md` | 若門派要綁事件 |
| 參考 mod | `~/dev/taiwu-src/mods/MoreFactionCombatSkills*` | 已證實 backend appender helper 寫法 |

---

## 8. 未解問題清單（丟給 Phase 0 / 後續）

1. `OrganizationMember` 表一個 entry 的真正語意？`Members[]` 長度與職階(grade 0–8)如何對應？能否整段複用既有派？
2. `MapArea.OrganizationId[]` 每個 area 的聚落槽數量與分配規則？安插 id 42 會不會擠掉既有派或越界？
3. 開新世界時 mod 呼叫 `CreateSettlement` 的正確時機與 context 取得方式（哪個生命週期 hook / 哪個事件）？
4. `CharTemplateIds` 指向的 Character 模板能否複用既有掌門？新角色模板要不要也追加？
5. `Faction`（幫派）系統：新派若不設 faction，是否安全（避開 `OrganizationDomain.cs:2949` 例外）？
6. 存檔相容：新派只影響「新世界」還是也能注入既有存檔（`OnLoadedArchiveData` / `FixAbnormalDomainArchiveData`，`OrganizationDomain.cs:199/210`）？
7. 前後端是否都要載入這份 Organization config（武學 mod 是兩邊各載一次，見 `details/martial_arts_mod_anatomy.md` §6）？

---

## 9. 給使用者的決策點

1. **目標等級**：先做「路線 A 最小可行門派」還是直攻「路線 B 完整大派」？（強烈建議 A 先行）
2. **地圖安插策略**：取代既有某聚落槽（省事、但少一個原版聚落）vs 新增聚落槽（保留原版、但要改 MapArea/補丁）？
3. **門派主題**：名稱、正邪、五行、性別限制、主修武學（可接 MySwordArt 的劍法）。
4. 是否要我接著做 **Phase 0 補完調查**（讀 OrganizationMember / MapArea 兩個大檔），把未解問題逐一釘死後再給更細的施工圖。
