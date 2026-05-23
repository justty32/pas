# 小門派 × 玩家勢力 — 調查批次索引

> 建立：2026-05-23。一批 5 個 subagent 平行調查，為「輕量小門派 + 太吾加入門派/城鎮取得身份權利並指揮 NPC」的 mod 構想打底。
> 原始碼為唯一事實來源：反編譯參考源 `~/dev/taiwu-src/`（較舊、供快速 grep）；實裝版 0.0.79.60 真身用 `ilspycmd -t <Type>` 對 `The Scroll of Taiwu_Data/Managed/Assembly-CSharp.dll`（前端）與 `Backend/GameData.dll`（後端）驗證。本資料夾僅為調查留檔，非權威。

## 使用者原始需求（7 點）
1. 產業視圖點地格建築（如民居）會「跳出東西」的機制，含非太吾村、跳交易視窗、觸發事件三種狀況。
2. 能否給遊戲物件加掛東西：想做**輕量小門派**，根據地可能是產業視圖中的特殊建築（如商會），其 NPC 的所屬/會用武功如何設置。
3. NPC 加入門派後如何被教會武功。
4. 如何給 NPC 設置特別身份（某小門派的某職位）。
5. 如何讓 NPC 依特定要求行動（長老命弟子跑去某地殺某人）。
6. mod：讓太吾加入某門派、獲得門派一定權利、進而指揮門派 NPC。
7. mod：讓太吾在城鎮取得身份、獲得權利，並給城鎮建設產業視圖。

## 五份調查（檔名 ↔ 涵蓋）
- [`01_building_production_view.md`](./01_building_production_view.md) — 產業視圖與建築系統（① 涵蓋 1 ＋ 7 的「建設產業視圖」）
- [`02_sect_member_npc_setup.md`](./02_sect_member_npc_setup.md) — 門派成員與 NPC 屬性設置（② 涵蓋 2 ＋ 4）
- [`03_npc_directed_action.md`](./03_npc_directed_action.md) — NPC 受命行動（③ 涵蓋 5）
- [`04_player_join_sect_command.md`](./04_player_join_sect_command.md) — 太吾加入門派、取得權利、指揮 NPC（④ 涵蓋 6）
- [`05_player_town_identity.md`](./05_player_town_identity.md) — 太吾在城鎮取得身份與權利（⑤ 涵蓋 7 的「城鎮身份/權利」）

## 綜述（5 份完成後彙整，2026-05-23）

### 一條脊椎貫穿全部：`OrganizationInfo`
5 個領域最大的共同發現是——**玩家與 NPC 共用同一套身份模型** `Character._organizationInfo`（型別 `OrganizationInfo`，在 **`Backend/GameData.Shared.dll`**，4 欄位 `OrgTemplateId / Grade / Principal / SettlementId`）。
- NPC 所屬門派（問題2）、NPC 職位（問題4）、玩家加入門派（問題6）、玩家城鎮身份（問題7）**全是改這同一個 struct**。`Grade`(0–8) 就是職位等級、`Principal=true`+`Grade8` 是領導/掌門。
- 後端 mod 直呼 `EventHelper.JoinOrganization / ChangeOrganization / ChangeOrganizationGrade`（`GameData.dll`），「加入門派＋給職位」原版就有現成 API。
- ⚠️ 硬約束：`JoinOrganization` 開頭 `if(SettlementId<0) return;`——NPC 要被門派系統認得必須有合法 `SettlementId`。

### 五個問題的可行性總表
| # | 問題 | 結論 | 最省力切入 |
|---|---|---|---|
| 1 | 產業視圖點建築跳東西 | 已釐清：`UI_BuildingArea.OpenBuildingManage` 依 templateId 段三分流（管理彈窗／事件／倉庫）；交易分「自營商店(`ShopEvent`)」與「商會(`MerchantType`)」；事件型 17/20/22 `allowExternal:true` **可掛 mod** | — |
| 2 | 輕量小門派＋NPC 屬性 | **可行（高）**：克隆**世俗**門派→id42、`IsSect=true`、`SeniorityGroupId=-1`、不上地圖（靠 `CreateEmptySects` 佔位 sect `AreaId=-1`） | 注入 `Organization` extra item＋`new OrganizationInfo(42,grade,true,settlementId)` 生成/`JoinSect` |
| 3 | 入派後學武功 | 已釐清：武學掛在**各職位** `OrganizationMemberItem.CombatSkills`(`PresetOrgMemberCombatSkill{SkillGroupId,MaxGrade}`)，生成時 `info.InitializeSectSkills` 控制 | 設好職位 config 即自動學 |
| 4 | NPC 特殊職位身份 | 已釐清：`Grade` 索引 `Members[]→OrganizationMemberItem`(含稱謂 `GradeName`)；`ChangeGrade` 改職位 | — |
| 5 | 長老命弟子去某地殺人 | **完全可行、有現成範本**：＝既有**復仇行動 `TakeRevenge`(id8)**。`CharacterDomain.StartCharacterPrioritizedAction(ctx, 弟子, new TakeRevengeAction{Target=new NpcTravelTarget(victimId,n)})` | 在 `AdvanceMonthBegin` 事件鉤（主執行緒）植入，免 patch |
| 6 | 太吾加入門派/取得權利/指揮 NPC | 加入＋職位＝**現成**；「指揮 NPC」原版**只有太吾村村民差遣**現成，對既有門派 NPC 需自造（接問題5） | `SetTaiwuAsLeaderOfTaiwuVillage`(30724) 是「入勢力→當掌門→指揮村民」近乎現成範本 |
| 7 | 太吾城鎮身份＋建產業視圖 | **無「城主/官職」獨立模型**；身份走 `OrganizationInfo`、建設權走另一條軌 `_taiwuBuildingAreas`(List\<Location\>) | 後端 `AddTaiwuBuildingArea(目標location)` 開建設權＋前端開面板；身份只是包裝 |

### 跨領域關鍵接點
1. **問題5 是問題6「指揮 NPC」的底層引擎**：玩家側（問題6）只負責「給太吾門派職位＋提供差遣入口（自訂事件選項/UI）」，按下去就呼問題5 的 `StartCharacterPrioritizedAction` 對目標 NPC 植入行動。
2. **問題7 身份 vs 建設權是兩條獨立軌**：原版 `OrganizationInfo`（身份）**不**直接解鎖 `_taiwuBuildingAreas`（建設權），mod 要自己把兩者綁起來（身份事件成功 → 呼 `AddTaiwuBuildingArea`）。
3. **商會不是門派**：商會＝`MerchantType` 商人系統（問題1）／「平民聚落+Grade4+IdentityInteractConfig 含4」的身份（問題2），**無法照搬當小門派根據地**；小門派根據地實體一律是 `Settlement`（綁地圖 Location），但可用佔位 sect 不上地圖。

### ⚠️ 重要修正（推翻舊記憶一條）
舊記憶記「`SeniorityGroupId` 不可設 -1、-1 會崩」——**過度概括**。實裝核對：`Sect` 建構子有 `if(SeniorityGroupId>=0)` 防護（`Sect.cs:151`），**-1 建構不崩**。崩潰只發生在「生成僧侶成員」走 `CreateSectMemberMonasticTitle→GetMonasticTitleSuffixRange(-1)`，而該路徑被 `ProbOfBecomingMonk>0` 門檻擋著。**做世俗派（全職位 `ProbOfBecomingMonk=0`/`MonkType=0`）時 `SeniorityGroupId=-1` 完全安全**——陳家堡會崩只因克隆少林繼承了僧侶屬性。➜ 輕量小門派應克隆**世俗派**，可省掉法號字庫問題。

### 共同待釐清（需實機/再讀 config）
- 佔位 sect `AreaId=-1` 對 NPC 過月/AI 是否走異常路徑、前端對「無據點門派」的顯示（問題2）。
- `AddTaiwuBuildingArea` 用在「已有聚落的成熟城鎮」上 `InitializeResidences` 是否與既有 NPC/建築衝突；前端如何讓非太吾村座標安全開建設面板而不誤觸家園/主線/BGM 判定（問題7，皆讀 `GetTaiwuVillageBlock`）。
- `TakeRevenge` 的 `BasePriority` 是否會被下月更高優先行動打斷（問題5，建議每月重放）。
- 太吾 `GetInteractionGrade()` 對本人回 0，靠 grade 開特權對玩家失效，mod 較穩自掛 feature 旗標（問題6）。
