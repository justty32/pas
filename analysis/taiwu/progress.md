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
- **編碼**：`Config.lua` 前端以 GBK 讀（中文 Title 須轉 GBK）；YAML / 事件語言檔由後端 net6 以 UTF-8 讀。
- **型別綁定**：0.0.79.60 普通引用、不需 extern alias（舊版 0.0.76.43 才需）。`**/*.cs` glob 要 Exclude obj/bin。
- **後端 mod 未捕捉例外＝整個 GameData 進程崩潰斷線**（比前端例外嚴重）；所有 patch/反射務必 try-catch＋防呆。
- **事件條件 `OnCheckEventCondition` 會被多次評估**：勿放隨機（要骰一次快取）、查地圖前先驗位置有效（太吾在秘境時 GetLocation 回 {-1,-1}）。
- 武學書：`CreateSkillBook` 參數是 SkillBook 物品 id（`CombatSkill.Instance[skillId].BookId`），非武學 id。
- 需求屬性用造詣（Attainment）非資質（Qualification，後端 GetPropertyValue 不支援會崩）。

## 待辦 / 下一步
- [x] ~~開新世界驗證產業 crash 修復~~ **✅ 實機正常（2026-05-23）**：取代槽修法生效，點陳家堡產業不再 crash、家園身分不被劫持。
- [ ] **（使用者要求，下一步要做）給陳家堡添加自製武功並在 UI（武學樹/勢力情報）顯示**。
- [ ] （非致命，順手觀察）後端 `Organization.CivilianSettlements.7.Members` 監控 WARN 是否仍在（克隆少林多聚落殘留）。
- [ ] 實機確認陳家堡武學樹可開、整套順（生成/加入/過月/成員名/武學樹/勢力情報/產業）。
- [ ] QolCheats 實機驗證（行動點不掉、開局驛站可用）；觀察開局極早期解鎖驛站是否干擾引導。
- [ ] AbyssManualEvent `TriggerPercent` 100 → 改回 10。
- [ ] 其餘陳家堡殘留大派結構：實機踩到再依三類修。
