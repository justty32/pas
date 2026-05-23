# 陳家堡 Mod — Phase 0 補完調查結果

> 目標：小派、最小可行、地圖**新增槽位**、主題＝**陳家堡**（普通小型門派）。
> 本檔回答 `plan.md` §8 的 7 條未解問題，並修正初版計畫對「需 Harmony 補丁」的過度估計。
> 來源全部以反編譯原始碼 `~/dev/taiwu-src/` 為準。
> 留檔位置：`analysis/taiwu/new_sect_mod/`（與並行 session 零交集，未動 session_log.md）。

---

## 0. 最重要的修正：最小可行門派**不需要**改核心門派判定

初版計畫擔心「`IsSect` 寫死 1..15」會逼我們 Harmony patch 才能生成門派。**這是誤判**。實際上存在兩個名字相近、語意不同的方法：

| 方法 | 位置 | 內容 | 用途 |
|------|------|------|------|
| `IsSect(sbyte)` | `OrganizationDomain.cs:3601` | `return Config.Organization.Instance[id].IsSect;`（**讀 config 旗標**） | `CreateSettlement` 用它決定生 `Sect` 還是 `CivilianSettlement`；幫派領袖斷言、成員邏輯等也用它 |
| `IsLargeSect(short)` / `GetLargeSectIndex(sbyte)` | `OrganizationDomain.cs:1316 / 1320` | 寫死 `1..15` | **只**服務「15 大派好感度網」與大派專屬機制（比武大會等） |

**結論**：陳家堡的 `OrganizationItem.IsSect = true` 時，`CreateSettlement(42)`（`:2026`）走的是 config 旗標分支 → **生成真正的 `Sect` 實體**，自動具備：可加入、收徒、傳武、職階、幫派系統。

而 `IsLargeSect`/大派好感度只把它當「非大派」略過，且**所有相關路徑都有 `index >= 0` 防護**，不會崩：
- `Sect` 建構子（`Sect.cs`）：`largeSectIndex = GetLargeSectIndex(42) = -1` → `if (largeSectIndex >= 0)` 跳過大派好感度初始化。
- 好感度查詢 `GetLargeSectFavorabilityBetween`（`:3497-3501`）：`if (largeSectIndex >= 0 && relatedLargeSectIndex >= 0)` 才查。
- `CreateSettlement` 內 `SetLargeSectFavorabilities(_largeSectFavorabilities, context)`（`:2030`）只是把既有 `sbyte[64]` 陣列存檔，**不按新 id 索引**，無越界。

> 換句話說：「小派」在太吾沒有專屬分級，但「**第 16 個 Sect + 不進大派好感度網**」恰好就是小派的效果，且這正是預設行為——**零核心補丁**。

---

## 1. 太吾沒有「小派/大派」分級，只有 Sect vs CivilianSettlement

- 門派(`IsSect=true`)：原版就 15 個（TemplateId 1–15），全是「大派」。執行期實體 = `Sect`。
- 民居(`IsCivilian=true`)：城鎮/村莊（21–38），執行期 = `CivilianSettlement`，**不可加入為武林門派**。
- 「陳家堡是小派」= 我們做**第 16 個 `Sect`**，靠 config 把規模調小（低 `Population`、各職階低 `Amount`、不設 faction、不進大派網）。

---

## 2. 成員系統（`OrganizationMember`）

### 2.1 結構
- 表 `OrganizationMember.Instance`：244 基礎列（`Init`: `new List<OrganizationMemberItem>(244)`），鍵為 `short`，**有自己的 `AddExtraItem`**（`OrganizationMember.cs:15527`）。
- 藍圖 `OrganizationMemberItem`（`OrganizationMemberItem.cs`）關鍵欄位：
  - `Organization(sbyte)`、`Grade(sbyte)`：這列屬於哪個組織的哪個職階（元資料）。
  - `Amount / UpAmount / DownAmount`：該職階生成幾人。
  - `GradeName`：職階稱謂（走 `OrganizationMember_language` 語言表）。
  - `Gender`、`SurnameId`、`InitialAges[4]`。
  - `ChildGrade / BrotherGrade / TeacherGrade / RejoinGrade`：職階家族關係。
  - `Neili / ConsummateLevel / ExpPerMonth / ContributionPerMonth / Fame`。
  - `CombatSkills(List<PresetOrgMemberCombatSkill>)`、`CombatSkillsAdjust[14]`、`LifeSkillsAdjust[16]`、`MainAttributesAdjust`、`ExtraCombatSkillGrids[5]`。
  - `Equipment[8] / Clothing / Inventory / DropResources / PreferProfessions`。

### 2.2 `OrganizationItem.Members[]` 如何被消費
`CreateSettlementMembers`（`OrganizationDomain.cs:2148-2215`）：
```csharp
sbyte maxGrade = (orgTemplateId != 16) ? 8 : 7;          // 非太吾村 = 9 階 (0..8)
for (sbyte grade = maxGrade; grade >= 0; grade--) {
    short orgMemberId = orgConfig.Members[grade];        // ← 依職階索引
    OrganizationMemberItem cfg = OrganizationMember.Instance[orgMemberId];
    if (cfg.Amount > 0) { ...生成 cfg.Amount 個核心成員 + 兄弟姐妹 + 配偶子女... }
}
```
- **`Members` 必須是 `short[9]`（索引 0..8 都要有合法 member id）**，否則 `Members[grade]` 越界或 `OrganizationMember.Instance[id]` 回 null。
- 各職階是否真的生人，由該 member 列的 `Amount > 0` 決定。
- 生成的角色歸屬用 settlement 的 `orgTemplateId`（`info = new SettlementMembersCreationInfo(orgTemplateId, ...)`），**不是** member 列的 `Organization` 欄位。
- `Population <= 0` 時整段跳過（`:2173`）→ 陳家堡 `Population` 必須 > 0。

### 2.3 對陳家堡的選擇（最小可行）
**複用某個既有門派的 `Members` 陣列**（直接抄一個風格相近的小規模派，例如人數少的派），最省事。代價：成員職階稱謂 `GradeName` 會顯示被抄派的稱謂。
- 進階（之後）：用 `OrganizationMember.AddExtraItem` 追加 9 個自訂職階列（自訂稱謂/武學/屬性），`Members` 指向它們。

---

## 3. 地圖「新增槽位」機制（已釘死）

### 3.1 槽位數 = `OrganizationId[]` 長度
`MapDomain.cs:3879`：
```csharp
int settlementCount = areaConfigData.OrganizationId.Length + (taiwuVillageInArea ? 1 : 0);
```
世界生成迴圈（`MapDomain.cs:4093-4101`）：
```csharp
for (int i4 = settlementCount - 1; i4 >= 0; i4--) {
    short blockId = staticBlockIdList[i4];
    Location location = new Location(areaId, blockId);
    sbyte orgTemplateId = isTaiwuVillage ? 16 : (isStoryStockade ? 38 : areaConfigData.OrganizationId[i4]);
    short settlementId = DomainManager.Organization.CreateSettlement(context, location, orgTemplateId);
}
```
- `staticBlockIdList` 由 `PlaceStaticBlocks`（`:4509`）依 `areaConfigData.SettlementBlockCore`（`:4519`）填。
- **`OrganizationId[i]`（哪個門派）與 `SettlementBlockCore[i]`（擺哪個區塊核心）平行對應、等長。**

### 3.2 做法
**用反射把某既有 area 的兩個陣列同步加長一格**：
- `MapAreaItem.OrganizationId[]` 尾端 append `42`（陳家堡）。
- `MapAreaItem.SettlementBlockCore[]` 尾端 append 一個該 area 內**合法、未被佔用**的區塊 id。

`settlementCount` 自動 +1（`:3879`），世界生成就會在新區塊呼叫 `CreateSettlement(ctx, Location(areaId, newBlock), 42)` 生出陳家堡。

- `MapArea` 表：138 基礎列，欄位 `readonly` → 反射替換陣列引用（建新陣列複製舊值 + 追加）。
- **這是「修改既有 area 的 config」，不是新增 area**（不需 `MapArea.AddExtraItem`）。

### 3.3 主要風險 / 待 Phase 2 釘死
- 必須挑一個目標 area 內**空閒且 passable** 的區塊 id 當 `SettlementBlockCore` 新成員，否則與既有聚落/不可走區塊衝突 → 生成失敗或重疊。需檢視該 area 的 `BlockAtlas` / `MapBlock` 佈局，或先用既有派所在 area 試。
- 各 area `Size` 與可用區塊數不同；建議選一個地廣、聚落少的 area。
- 替代方案：Harmony postfix 世界生成迴圈，自行 `CreateSettlement` 一格——同樣要解決選空閒區塊問題，且較侵入，故**優先用反射改 config 陣列**。

---

## 4. 注入時機（已確認安全）

- `Organization.Init()`（`:365`）會 `_extraDataMap.Clear()` 並重建 `_dataArray` → **注入必須在 Init 之後**。
- MySwordArt 在 `TaiwuRemakePlugin.Initialize()`（`projects/taiwu/MySwordArt/Backend/Plugin.cs:23`）注入 CombatSkill **已驗證成功** → 證明 config 表的 `Init()` 在 plugin `Initialize()` **之前**完成。
- ⇒ 陳家堡的 `Organization.AddExtraItem`、`OrganizationMember`（若追加）、`MapArea` 陣列反射改寫，**全部放在 backend plugin 的 `Initialize()`** 即可。
- ⚠️ Phase 1 仍需驗證：`MapArea.Init` 是否也在 plugin `Initialize()` 前完成（理應如此，但要實測）。
- 世界生成在「開新世界」時才跑，遠晚於 `Initialize()`，所以注入後資料已就位。

---

## 5. `OrganizationItem` 沒有 `Duplicate()` —— 克隆方式

- `OrganizationItem` 是純資料類，**無 `Duplicate` 方法**（不像 `CombatSkillItem`/`SpecialEffectItem` 走 `ConfigItem<,>.Duplicate`）。MySwordArt 的 `DataConfigAppender` 依賴 `Duplicate` → **不能直接套用**到 Organization。
- 兩條克隆路：
  1. **反射逐欄複製**：讀某來源派所有 `readonly` 欄位 → 用 42 引數建構子或 `new OrganizationItem()` + 反射 `FieldInfo.SetValue` 寫入副本 → 覆寫 `TemplateId=42`、`Name/Desc`（直接塞字串繞過語言表）、`IsSect=true`、`Population`、`CombatSkillTypes` 等。
  2. **直接呼 42 引數建構子**：把每個欄位明確列出（可讀性差、易錯，但無歧義）。
- 建議走（1），寫一個 `OrganizationItemFactory.CloneFrom(sourceId, overrides)` 小工具，沿用 MySwordArt `ApplyChanges` 的反射覆寫邏輯（`DataConfigAppender.cs`）。

---

## 6. 其餘問題

- **faction（幫派）**：陳家堡**不設 faction** 即安全。`OrganizationDomain.cs:2949` 的斷言只在「某 faction 的領袖所屬組織非 sect」時丟例外；只要不給陳家堡指派 faction，就不觸發。
- **存檔相容**：陳家堡靠世界生成擺放 → **只出現在新開的世界**。既有存檔不會自動長出它（除非另寫 `OnLoadedArchiveData` 注入聚落，屬進階）。最小可行＝開新世界測試，可接受。
- **前後端各載一次**：`Organization` config 前後端都有（backend `GameData.dll` + 前端用於 UI 顯示）。世界生成/成員生成在 **backend**；門派名稱/UI 顯示在 **frontend**。⇒ `Organization.AddExtraItem` 與名稱注入**前後端都要做一次**（與 MySwordArt YAML 兩邊各載一次同理，見 `details/martial_arts_mod_anatomy.md` §6）。`MapArea` 改寫主要影響 backend 世界生成；前端地圖顯示是否需同步改，Phase 2 實測。
- **`SeniorityGroupId`**：~~設 **-1** 走 else 分支（無 monastic title），對小派最安全省事~~ **← 此結論已被實機推翻（2026-05-23）**。若克隆**僧侶派（如少林）**，成員生成會走 `TryBecomeSectMonk → CharacterDomain.CreateSectMemberMonasticTitle`（`CharacterDomain.cs:15328`），需用 `SeniorityGroupId` 灌的法號字庫；設 -1 → 字庫空 → `context.Random.Next(0)` 例外、**開新世界崩潰**。**正解：沿用來源派的 `SeniorityGroupId`（不要覆寫成 -1）**。`RetireGrade` 沿用來源派數值即可。

---

## 7. 修正後的可行性結論

| 項目 | 初版估計 | Phase 0 修正後 |
|------|---------|---------------|
| 生成真．門派 | 需 Harmony patch `IsSect` | **不需要**（config 旗標即可） |
| 大派好感度越界 | 高風險，需擴容 `[15]` | **無風險**（路徑皆有 `index>=0` 防護，自動略過） |
| 成員 | 不明 | `Members[9]` 複用既有派即可；可選追加 |
| 上地圖 | 不明 | **反射加長 `OrganizationId[]`+`SettlementBlockCore[]` 一格** |
| 克隆 config | 套 MySwordArt Duplicate | OrganizationItem 無 Duplicate，需**反射逐欄複製** |
| 注入時機 | 不明 | backend `Initialize()`（已由 MySwordArt 驗證） |

➡️ **最小可行陳家堡的真正工作量**：
1. 寫 `OrganizationItem` 反射克隆工具（中）。
2. backend `Initialize()` 注入 org 42（低）。
3. 反射改某 area 的 `OrganizationId[]`/`SettlementBlockCore[]`、挑空閒區塊（**中高，唯一較硬處**）。
4. frontend 同步注入名稱顯示（低）。
5. 開新世界實測：聚落出現、可進入、成員生成、可加入、傳武（驗證）。

**全程預期零核心 Harmony 補丁**（除非地圖選區塊不得不用 postfix）。比初版評估的「大型 mod」樂觀許多，接近「中型 mod」。
