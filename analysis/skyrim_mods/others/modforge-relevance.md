# 綜合：ModForge 能從這七個 mod 借鏡什麼

把七個參考 mod 對照 **ModForge**（`~/repo/ModForge`，程式化生成 Skyrim plugin 的工具）目前的能力，整理出「已對齊 / 可短期補 / 範式級缺口」三層。本檔是綜合層，個別細節見各 `architecture/*.md` 與 `details/dialogue-targeting-technique.md`。

> ModForge 現況（摘自其 `CLAUDE.md`「已落地功能」）：QuestSpec/storyEvent+SM 掛載、SceneSpec(autoStart 在場偵測)/ScenePhaseSpec(Dialog/Package/Timer action)、五種 alias fill、10 個 PACK template、NpcSpec(items/essential/protected)、GlobalSpec(GLOB)、Light/Projectile/Explosion builder、可複用 trigger 庫、dialogue 鏈(SNAM/Hello/DLVW/ENAM+CNAM)。

## 一、ModForge 已對齊的（參考 mod 印證設計正確）

| 能力 | 印證來源 | 說明 |
|---|---|---|
| Scene = phase 序列、每 phase 綁 dialog topic | Sofia `JJSofiaMainQuestDialogueScene`（1 actor/17 phase/17 action） | ModForge 的 ScenePhaseSpec 結構與真實隨從 mod 完全同型 |
| scene action 三型 Dialog/Package/Timer | Sofia `JJSofiaDrunkScene`、`SofiaWeddingScene`（多 actor 走位+對拍） | ModForge「NPC 做動作走 Package action」的設計被 Sofia 驗證 |
| uniqueActor alias 指向 vanilla NPC | Sofia 8 個 *Comment quest（`alias uniqueActor -> Skyrim.esm`） | ModForge 的 `uniqueActor:<ref>` fill 正是這個用法 |
| GLOB 當 runtime 旗標/設定 | Sofia 57 個 GLOB（CatchUpDistance/CommentFrequency…） | 少量狀態用 GLOB 是業界常態，ModForge 方向正確 |
| storyEvent 掛 vanilla SM 根 | RDO override SM 節點 + 新增節點嫁接 | ModForge 的 SMBN→SMQN 掛載與 RDO 手法同源 |
| condition 投放（GetInFaction/RelationshipRank/RandomPercent） | RDO condition 前段（已在 ModForge `SupportedConditionFunctions`） | 基礎 condition dispatch 已具備 |
| Relationship record | Sofia/RDO 都用 | ModForge 已有 RelationshipSpec |

→ 結論：ModForge 的**劇情演出（scene）與 SM 掛載**設計，與工業級隨從/對話 mod 高度一致，無需大改。

## 二、可短期補的（地基已在，補 case / 補欄位即可）

### 1. condition 函式擴充（高 ROI、低成本）
RDO 投放的頭號 condition **ModForge 目前不支援**：
- `GetIsVoiceType`（RDO 用 9245 次，第 1 名）— 規模化投放的根本（投給一整類嗓音=一群 NPC）
- `IsInList`（936 次）— 配 FormList 做「目標名單/排除名單」
- `GetPlayerTeammate` / `LocationHasKeyword` / `GetVMQuestVariable` 也缺

ModForge 的 `BuildCondition` dispatch（`Generator.Build.Conditions.cs`）已是可擴充結構，補這幾個 case 即可。**這是讓 ModForge 從「指名單一 NPC」進化到「按類投放」的關鍵第一步**。細節見 `details/dialogue-targeting-technique.md`。

### 2. FormList builder + condition 批次模板（中成本）
RDO 用 18 個 `aaa_RDOVoices*` FormList 集中管理目標名單。ModForge 目前 condition 逐句手寫、無 FormList builder。補上後可做「一組 condition 套 N 句台詞」。

### 3. MCM 設定選單生成（中成本、隨從品類高 ROI）
Sofia 的 `JJSofiaMCM` 與 SkyUI 的 `SKI_ConfigBase` 機制：生成一個 `extends SKI_ConfigBase` 的 Start-Game-Enabled quest + script，GLOB 可自動推導控制項（bool→toggle、float→slider）。ModForge 已會生成 `extends Quest/TopicInfo` 的 Papyrus（`Generator.QuestFragments.cs`），生成繼承 SKI_ConfigBase 是同型工作。**代價**：產物多一個 SkyUI 依賴 → 做成 opt-in `mcm` spec 區塊。

## 三、範式級缺口（與 ModForge 當前「新增導向」是兩種範式）

### A. override vanilla record（致命缺口，若要做「對話包」）
RDO 的本質不是新增劇情，而是**覆寫 1612 個 vanilla record**（51 個 vanilla Quest、1304 個 vanilla INFO…）再塞進新 response。ModForge 的 dialogue builder 只把 condition 掛**自建** INFO（`WireDialogueConditions` 用 `dialogResponsesByEd`），沒有「取 vanilla record 覆寫」的路徑。Mutagen 的 `GetOrAddAsOverride` ModForge 已在 world 路徑用過、但 dialogue 未暴露。
→ 要做 RDO 式「對話包」，需在 dialogue/quest 層開放 override 入口。

### B. 批次 per-NPC 內容展開（中缺口）
Sofia 手寫了 8 個 per-NPC comment quest（Nazeem/Carlotta/Braith…），每個結構幾乎相同。ModForge 若要量產隨從的「對特定 NPC 吐槽」內容，需要一個「給一張 (NPC, 台詞) 表，批次展開成 N 個 quest+scene+alias」的高階 spec。目前要逐個手寫 spec。

### C. 進階狀態儲存後端（低急迫、需求驅動）
GLOB 做不到 per-actor 狀態表（如每個 NPC 各自的好感度）。兩個候選：
- **PapyrusUtil StorageUtil**：`(Form, key)` 扁平 KV，**入門成本低、扁平結構比容器生命週期更容易機器生成** → ModForge 首選後端。
- **JContainers JFormDB**：路徑定址 + 容器，功能更強但概念重。
- **PapyrusUtil JsonUtil**：把「生成時就決定的資料表」寫成外部 .json 隨 mod 出貨、runtime 唯讀載入 → 對「資料驅動生成」特別契合，不佔 FormID 又可外部檢視。
→ 三者皆 native 依賴，做成 opt-in；真要選預設後端，PapyrusUtil 優先於 JContainers。

### D. runtime 互動 UI（小缺口、可選）
UIExtensions 提供清單/文字輸入/輪盤選單，補 ModForge「對話分支以外」的玩家即時選擇（命名、目標指定、命令輪盤）。需生成呼叫其 menu script 的 Papyrus，且為 native+SWF 依賴 → 可選增強。

## 四、橫貫原則：依賴策略

五個 library（JContainers / PapyrusUtil / powerofthree / SkyUI / UIExtensions）對 ModForge 的共同結論一致：

- **它們都是 native DLL 或 SWF 依賴**，ModForge 若產出依賴它們的 plugin，等於要求終端使用者額外安裝。
- 全部都應做成 **opt-in spec 區塊**，預設維持 ModForge 的「零外部依賴、純 vanilla 引擎機制」取向（Sofia 就是零 SKSE 資料結構依賴、純 GLOB+quest 撐起整個隨從的反例證明——**單一隨從用 vanilla 機制就夠**）。
- **powerofthree's Tweaks 是例外方向**：它修的是引擎 bug（Load EditorIDs / Projectile Range Fix / Distant Ref Load Crash…），ModForge 不依賴它、但可在文檔假設「進階使用者多半裝了它」，且 `Load EditorIDs` 對 ModForge 的 console debug 流程有實質幫助。

## 五、若要排優先級（建議序）

1. **condition 函式擴充**（GetIsVoiceType / IsInList…）— 最低成本、解鎖規模化投放。
2. **MCM 生成（opt-in）** — 隨從品類最大缺口（Sofia 印證）。
3. **批次 per-NPC 內容展開 spec** — 把手寫 8 個 quest 變成一張表。
4. **dialogue override 入口** — 開啟「對話包」範式（較大工程）。
5. **PapyrusUtil 狀態後端（opt-in）** — 需求出現再做。
