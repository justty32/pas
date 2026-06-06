# RimWorld Mods 分析群組

對既有 RimWorld 1.6 Workshop mod 做 Analysis，目標導向皆為「在此基礎上 create（擴充/衍生）」。每個 mod 一個子目錄，反編譯/原始碼放在 `projects/rimworld_mods/<mod>/`。

> 共同方法：`ilspycmd <dll> -o <out>` 反編譯（或讀自帶原始碼）→ 追框架相依 DLL → 釐清「純 XML 可做 vs 必須 C#」的二分 → 以 tutorial/extension_points 當核心交付。

## 已分析 mod

| Mod | packageId / workshop | 本質 | 「做擴充」最省力路徑 | 入口文件 |
|---|---|---|---|---|
| **Vanilla Outposts Expanded** | `vanillaexpanded.outposts` / 2688941031 | 世界地圖自治營地：定時產資源/提供服務。引擎在 VEF 的 `Outposts.dll` | **產資源型＝純 XML**（繼承 `OutpostBase`＋`OutpostExtension.ResultOptions`）；互動服務型才需 C# | `vanilla-outposts-expanded/tutorial/01_add_outpost_xml.md` |
| **Custom Quest Framework** | `HaiLuan.CustomQuestFramework` / 2978572782 | 遊戲內視覺化任務/地圖/物件編輯器＋領域腳本（`QuestScriptDef`＋`CQFAction`） | **純 XML 覆蓋 90%+**：`QuestNode_DoCQFActions` 裝既有 100+ 個 `CQFAction`；新副作用才繼承 `CQFAction_Target` 寫 C# | `custom-quest-framework/tutorial/01_add_custom_quest.md` |
| **SpeakUp 畅所欲言** | `cn.speakup.ttyet` / 3445623063（依賴 Interaction Bubbles `Jaxe.Bubbles` / 1516158345） | 純本地 `GrammarResolver` 語法規則驅動的動態對話，**不接 LLM/網路**；與 Bubbles 經原版 `PlayLog` 解耦 | **A 純資料**（`1.6/Patches/` 加 `PatchOperation` 注入對話）／**B 改碼**（`ExtraGrammarUtility.cs::ExtraRules` 加情境變數） | `speakup/details/extension_points.md` |

## 重要備註
- **CQF 自帶權威 schema**：mod 目錄內 `<MOD>/.QuestEditor_Library/` 有作者原始碼樹＋4 份 `Skill/*/SKILL.md`（`cqf-overview`/`cqf-def-catalog`/`cqf-action-condition-dev`/`cqf-map-dev`），做 create 時優先參考。
- **SpeakUp 不是 AI 對話**：目前完全是模板規則；若想「接 LLM 讓對話更聰明」是全新對話來源接點（B 類改碼），非改 XML 模板。
- **VOE outpost 現行不會被襲擊**：`raidPoints`/`raidFaction` 是死欄位，About 描述過時；唯一的「襲擊設計」是反向（`Outpost_Defensive` 削減打主基地的 raid）。詳見 `vanilla-outposts-expanded/details/raid_and_attack_design.md`。

## 衍生（create）產物
> 放 `derived/rimworld_mods/<項目>/`。測試用複本已複製到 `…/common/RimWorld/Mods/`。

| 衍生項目 | 基於 | 內容 | 狀態 |
|---|---|---|---|
| `cqf-caravan-redemption` | CQF | 最小可運行 CQF 純 XML 任務（`QuestScriptDef` 跳訊息＋發信號，獎勵走原版 DropPods）。獎勵不用 `CQFAction_Spawn`（任務生成階段空 targets 不生成）。未來長成「流民商隊的償還」四章故事 | XML 健檢綠；遊戲內實測待人工 Execute quest |
| `speakup-context-expansion` | SpeakUp | C# 加 3 個殖民地層級情境變數（`COLONY_DANGER`/`COLONY_FOOD_DAYS`/`COLONY_DAYS_SINCE_DEATH`＋drafted），Harmony Postfix 掛 `ExtraGrammarUtility.ExtraRules`，外掛式不改原 mod | **DLL 編譯通過**；遊戲內掃 log 實測待人工 |

### 流民商隊四章故事（CQF 未來擴充設計，已定）
一條主線 QuestScriptDef 串 4 自足章節，章節間僅靠信號鏈＋共享 DB key 耦合：Ch1 探索被洗劫商隊營地（CustomMapDataDef）→ Ch2 生還商人對話委託護送（DialogTreeDef）→ Ch3 途中匪幫來襲防守（GroupDataDef，須保護商人存活）→ Ch4 送達結算聲望/白銀。待最小切片實測過再以「我建骨架＋多 agent 各做一章」並行實作。
