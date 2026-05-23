# NPC 生成 × 世界人口 — 調查批次索引

> 建立：2026-05-23。一批 2 個 subagent 平行調查，承接「輕量小門派」構想（[`../player_faction_research/`](../player_faction_research/)）——前一批解決「NPC 所屬/職位寫進 `OrganizationInfo`」，這批解決「人從哪來、屬性怎麼填、整個世界各種比例怎麼設」。
> 原始碼為唯一事實來源：反編譯參考源 `~/dev/taiwu-src/`（較舊、供快速 grep）；實裝版 0.0.79.60 真身用 `ilspycmd -t <Type>` 對 `Backend/GameData.dll`（後端）與 `The Scroll of Taiwu_Data/Managed/Assembly-CSharp.dll`（前端）核對。本資料夾僅為調查留檔、非權威。

## 使用者原始需求（2 點）
1. 龍島忠僕、比武招親如何生成 NPC？NPC 模板又該怎麼做？
2. 整個世界的人口生成、性別比例如何設置？門派人數 vs 普通人人數？九個階位的人數呢？

## 兩份調查（檔名 ↔ 涵蓋）
- [`01_dragonisland_servant_and_matchmaking_npc.md`](./01_dragonisland_servant_and_matchmaking_npc.md) — 龍島忠僕生成、比武招親、NPC 生成模板通則（涵蓋需求 1）
- [`02_world_population_generation.md`](./02_world_population_generation.md) — 世界人口生成總機制、性別比例、門派 vs 平民人數、九階位人數（涵蓋需求 2）

## 綜述（2 份完成後彙整）

### 一、NPC 生成只有一條正規入口
不論龍島忠僕、世界人口、或你的小門派成員，最終都走同一個工廠：
- `IntelligentCharacterCreationInfo`（struct，欄位齊全：`Location/OrganizationInfo/charTemplateId/Age/Gender/GrowingSectId/GrowingSectGrade/*SkillsLowerBound/InitializeSectSkills`）
- → `CharacterDomain.CreateIntelligentCharacter`（CharacterDomain.cs:26387，✅實裝核對）
- → 收尾必呼 `CompleteCreatingCharacter`（:27040，漏呼會拋例外）
- 最省事封裝：`EventHelper.CreateIntelligentCharacter(Location, gender, age, baseAttraction, settlementId, grade)`（EventHelper.cs:5735）。

**關鍵紅利**：生成收尾 `ComplementCreateIntelligentCharacter` 會**自動呼叫一次 `JoinOrganization`**——所以只要把 `OrganizationInfo` 設成你的門派（`orgTemplateId≥42`、`settlementId≥0`）就自動入籍，不必另外手動入派。但 `JoinOrganization`（OrganizationDomain.cs:692）開頭 `if(SettlementId<0) return;`，且對 `IsSect` 門派會把人加進 `_sects[SettlementId]`——**前置鏈「先有合法 Sect/Settlement」仍是必須**（接前一批小門派的佔位 sect 結論）。

### 二、龍島忠僕 = 伏龍(Fulong)系，動態生成 + 三層疊加綁主僕
- 原始碼無「龍島」直譯，對應 **`CreateFulongServant`**（EventHelper.cs:5685，✅實裝核對；實裝簽名漂移成 `(string nextEventGuid, EventArgBox argBox)`，可從 argBox 覆寫性別/外觀/行為）。是**事件觸發時 new 出來**，非世界生成既有。
- 「主僕關係」沒有單一關係表，是三件事疊加：① 特性 `199 = FulongServant`（CharacterFeature.cs:78）② 好感拉滿 10000 ③ `TaiwuDomain.JoinGroup`（TaiwuDomain.cs:6128）把忠僕 `LeaderId` 設成玩家、加入玩家隊伍。**「聽命」走的是隊伍系統**，月度行為由 `TeammateMonthAdvanceEvents.dll` 驅動。
- 同骨幹對照範例：`CreateForcedToFollowCharacter`（EventHelper.cs:2345，feature 198 + 好感 -10000）。
- ➜ **這是「憑空造一個帶指定屬性、綁定關係的 NPC」的現成教科書範本**。

### 三、比武招親 = 篩既有人口，不生成 NPC
- 內建「月度行動 + 歷練」系統（非單一事件）。觸發 `EventHelper.TriggerBrideOpenContest`（EventHelper.cs:2400），城市對應 `OrgTemplateIdToContestForTaiwuBride`（ConfigMonthlyActionDefines.cs:7）。
- 候選者全是**地圖現役 NPC**，用 `MatchParticipateCharacter_ContestForTaiwuBride`（CallCharacterPredefinedRules.cs:11）布林篩選（未婚、16~50歲、世俗所屬、非僧侶），**完全沒有 `Create*`**。⚠️ 此規則類別標 `[Obsolete]`，僅看舊源未對實裝核細節。
- ➜ 對「造 NPC」幫助低；但「需從現役人口挑人」時，`CharacterMatchers` 過濾器是現成參考。

### 四、世界人口生成（數值幾乎全在 config 表，不在 C# 常數）
- 流程：`WorldDomain.CreateWorld`（WorldDomain.cs:734，✅）→ `MapDomain.CreateAllAreas`（:3666，**15 州 × 每州 3 區**：主城/門派區/第三區）→ 每聚落 `OrganizationDomain.CreateSettlement`（:2023）→ 常住人口全在 **`CreateSettlementMembers`**（GameData.dll :2227）。
- 「是否生常住人口」閘＝`OrganizationItem.Population > 0`；總量再被世界係數縮放。

| 子問題 | 結論（✅=實裝核對） | mod 改法 |
|---|---|---|
| 性別比例 | **硬性 50/50**：`gender = CoreMemberConfig.Gender==-1 ? Gender.GetRandom(random) : CoreMemberConfig.Gender`（✅ :2337）；`Gender.GetRandom`＝`random.Next(2)`，**全遊戲無偏斜比例參數**。情境差異只是「強制某性別 or 50/50」二選一 | 改個別模板 `OrganizationMemberItem.Gender`＝config 注入；改全局 50/50＝必須 Harmony patch `Gender.GetRandom` |
| 門派 vs 平民人數 | 兩者**走同一套 `CreateSettlementMembers`**，只差 config 參數。核心人物數 = `Math.Max(1, OrganizationMemberItem.Amount × worldPopulationFactor / 125)`（🔴版本漂移：舊源 `/100` 無下限，實裝 0.0.79.60 `/125 + Max(1,…)`，✅核對）。`worldPopulationFactor` 來自 `WorldCreation[5].InfluenceFactors[人口類型]`（玩家開局選的設定，✅:7462）。每個核心人物還連帶生兄弟姊妹(1~3)/配偶/子女，故總人口遠大於 Amount 之和 | 改 Amount/人口係數＝config 注入；改除數 125 或家庭規模＝Harmony patch |
| 九階位人數 | 每階位人數＝該階位 `OrganizationMemberItem.Amount`（門派劇情上/下行時改用 `Up/DownAmount`）。**人數與階位模板(GradeName/CombatSkills)是同一個 `OrganizationMemberItem` 結構**，`Members[grade]`(short[9]) 存的是**各階位模板 ID、不是人數**。掌門 1 人**非引擎寫死**，是 Grade8 config `Amount=1 + RestrictPrincipalAmount=true`（定額不乘係數） | 改各階位 Amount＝config 注入 |
- 過月維持人數：`WorldDomain.cs:8279` → `UpdateOrganizationMembers` → `UpdateMemberGrades` → `RecruitOrCreateLackingMembers`，逐階位算「`GetExpectedCoreMemberAmount`(✅，依劇情狀態在 Amount/Up/Down 間切換) − 現有正式成員」補缺額。

### 五、對「造輕量小門派」的可行性結論
- **憑空造帶指定屬性/所屬的 NPC：高** — `CreateFulongServant` 是現成、已核對的完整範本；正規入口 `CreateIntelligentCharacter` 生成時自動 `JoinOrganization`。
- **塞進 id≥42 自訂門派：中** — 路徑清楚（OrgInfo 設好就自動入籍），門檻在前置鏈「先把 Sect/Settlement(`SettlementId≥0`) 建出來」（接前一批佔位 sect，未端到端實測 `_sects[SettlementId]` 是否存在）。
- **小門派各階位人數/武功/性別** — 全靠 `OrganizationMemberItem` config（`Amount`/`Gender`/`CombatSkills`/`GradeName`），用 ConfigData 注入即可，**不需 Harmony**。

## 待補（需實機/再 dump config）
- 各門派 Grade8 `Amount` 是否真為 1、`InfluenceFactors` 具體百分比（數值在資源檔，本批未逐筆 dump）。
- 自訂門派 Sect/Settlement 端到端、`AddExtraItem` 注入角色模板、精準發特定武學的 API。
- 比武招親實裝版的 `characterFilterRulesId` 新走法（舊規則類別已 `[Obsolete]`）。
