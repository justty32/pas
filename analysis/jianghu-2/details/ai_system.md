# AI 系統剖析

> 來源：`../../../../SourceCode/Assembly-CSharp/`  
> 日期：2026-05-22

## TL;DR

「AI」在這款遊戲分成三條互不相關的軌道：

1. **AIDialog（玩家可問答的「AI」聊天）** — **其實是 HTTP web 服務**，不是本機 LLM。串流回應、明文 HTTP、無加密。
2. **NPC 條件對話（NpcConditionalDialogueManager）** — 規則式優先級對話選擇，無 LLM 成分。
3. **NPC 戰鬥/行為 AI** — 沒有通用 BehaviorTree / FSM；行為散落在 `UnitController`（5357 行）、`NpcEntity`（3815 行）、各種 `*Spell*` 類別中，並以 CSV 表 (`NpcFight`) 餵資料。論道紙牌迷你遊戲有獨立的微型 AI（`LunDaoBattle.NpcAI`）。

## 1. AIDialog — 看似 AI，其實是後端 web 服務

### 1.1 核心類別與檔案

| 類別 | 檔案 | 行數 | 角色 |
|---|---|---:|---|
| `AIDialogManager` | `AIDialogManager.cs` | 169 | Singleton：歷史/配額狀態、本地持久化 |
| `AIDialogView` | `AIDialogView.cs` | 454 | UI Form：輸入框、訊息列表、實際發 HTTP |
| `AIDialogInfo` | `AIDialogInfo.cs` | 10 | DTO：`isPlayer / modelID / sendTime / message` |
| `AIDialogItem` | `AIDialogItem.cs` | 94 | 訊息氣泡 UI 元件 |
| `AIDialogPrototype` | `AIDialogPrototype.cs` | 42 | CSV 載入：歡迎詞、活動公告、超限提示文案 ID |

### 1.2 後端服務（關鍵發現）

`AIDialogView.cs:38`：
```csharp
private static string URL = "http://jh.inmotiongame.com/portal/dashuju/index?q=";
```

請求格式（`AIDialogView.cs:356 SendWebQuestion`）：
```
GET http://jh.inmotiongame.com/portal/dashuju/index?q=<question>&t=content[&ip=<extranet_ip>]
```

- **明文 HTTP**（沒有 HTTPS）。
- `q` = 玩家輸入；`t=content` 為固定參數。
- 若 `AppGame.Instance.GetExtranetIp()` 能拿到外網 IP，會附 `&ip=<ip>` 回傳服務端 — **這代表遊戲把玩家公網 IP 上報**，是隱私敏感點。
- 路徑 `dashuju`（大數據）暗示後端是中文 NLP/QA 服務或 LLM proxy。

### 1.3 串流回應協定

`SendWebQuestion` 用 `UnityWebRequest.Get()` 加 polling：

- timeout = `10000ms`（`AIDialogView.cs:40` `TIMEOUT_TIME`）
- 不等請求完成，每 frame 檢查 `connectRequest.downloadHandler` 已收到的內容
- **訊息分隔符是 `"\n\n\n\n"`（四個換行）**，類似 SSE 但自製
- 每收到新一段（`array[Length-2]` — 倒數第二段，避開未完成的最後段），就 update 對應 UI 氣泡的內容

```csharp
string[] array = downloadHandlerBuffer.text.Split("\n\n\n\n");
string text = array[Mathf.Clamp(array.Length - 2, 0, array.Length - 2)];
```

### 1.4 配額與每日重置

`AIDialogManager`：
- `totalSendCountPerDay = 20`（hard-coded 兩處：line 78 `LoadDialogHistory`、line 164 `CreateDialogData`）
- `curSendCount` 每送出一次遞增（`SendDialogToAI()`）
- `AIConnectError()` 在網路錯誤時遞減，並 clamp 在 [0, 20]
- **但客戶端從不阻擋送出**：`CanDialogWithAI()` 永遠 `return true`（line 134），UI 顯示 `20/20` 也照樣可發。`AIDialogView` 的 `!CanDialogWithAI()` 判斷因此永遠是 `false`（line 311），所謂的 `isOverAsk` 邏輯永不觸發。
- 跨日重置：`IsAnotherDay()` 用本地時區比對 `now.Date` 與 `lastLoginTime` 的日期。攻擊面：改系統時間可重置。

### 1.5 持久化（**檔名偽裝**）

`AIDialogManager.cs:35`：
```csharp
private static string DialogHistoryPath = GameSaving.GetLocalPath() + "unitypackage.json";
```

- 路徑：`<persistentDataPath>/Local/unitypackage.json`
- 命名偽裝成 Unity 系統檔，**這是刻意的**（推測：避免玩家輕易看到自己問了什麼）
- 格式：`JsonMapper.ToJson(AIDialogData)`，內容包含完整對話歷史
- **隱私敏感**：玩家輸入過的所有問題都保留在這

### 1.6 Mod 介入點建議

| 目的 | 方法 |
|---|---|
| **改 endpoint**（指向自架 LLM）| Reflection 改 `AIDialogView` private static `URL` 欄位 |
| **去掉 IP 上報** | Harmony Prefix `AIDialogView.SendWebQuestion`，把 `extranetIp` 強制設為空，或重寫請求 |
| **解開 20/day 顯示** | 已經沒在擋了，但若 UI 想顯示無限：reflection 改 `dialogData.totalSendCountPerDay = int.MaxValue` |
| **清歷史隱私** | 刪 `Local/unitypackage.json` 或啟動時 patch `LoadDialogHistory` 跳過 |
| **解析串流換成 SSE/JSON** | Patch `SendWebQuestion` IEnumerator（用 transpiler，因為是 coroutine） |

## 2. NPC 條件對話 — 規則式優先級選擇

### 2.1 流程（`NpcConditionalDialogueManager.cs`）

每 `0.2s` 跑一個 step（`ManagedUpdate` line 28）：

| Step | 動作 |
|---|---|
| 0 | `GetMeetTheConditionDatas` — 掃所有 `NpcConditionalDialogueData`，把 condition 通過、ignoreCondition 不通過的加入 `m_MeetConditionDatas` |
| 1 | `ExcludeLowPriorityDatas` — 對每個 `groupId` 只保留最高 `priority` |
| 2 | `GetUnexpiredDatas` — `m_ExcludeLowPriorityDatas` 與 `m_UnexpiredDatas` swap，配合 `m_Stats` 處理過期 |

條件評估委派給 `AnswerViewNew.IsMatchMultCondition(condition, null)`（在 ModSpace 的 `AnswerViewNew.cs`）。

### 2.2 為什麼這算 AI？

嚴格說不是 AI。但對玩家而言這套系統讓「NPC 主動冒出符合當前狀態的話」，產生「NPC 有情境感知」的錯覺。是 RPG 業界標準的 **scripted contextual barks**。

### 2.3 Mod 介入點

- 新增條件對話：直接擴 `NpcConditionalDialogueData.npcConditionalDialogueDatas`
- 改評估邏輯：patch `AnswerViewNew.IsMatchMultCondition`
- 提高/降低觸發頻率：`updateInterval`（預設 0.2f）

## 3. 戰鬥 / NPC 行為 AI

### 3.1 「沒有通用 AI 框架」這件事

掃過程式碼後**沒找到**：
- Behavior Tree（無 `BTNode`、`IBehaviourNode` 等基類）
- Utility AI（無 score-based selector）
- 通用 FSM（雖然 `*State.cs` 很多，但是各系統各做各的，不是統一框架）

戰鬥行為實際上 **由 spell/skill 資料驅動 + 硬編碼決策**。

### 3.2 關鍵類別

| 類別 | 檔案 | 行數 | 職責 |
|---|---|---:|---|
| `UnitEntity` | `SweetPotato/UnitEntity.cs` | 360 | 所有 entity 基類 |
| `NpcEntity` | `SweetPotato/NpcEntity.cs` | 3815 | NPC 屬性/技能/裝備/門派/初始化/Save/Load — **沒有 Update 行為迴圈** |
| `UnitController` | `SweetPotato/UnitController.cs` | **5357** | NPC 與玩家共用的 controller，含移動、戰鬥觸發、動畫狀態 — **真正的 AI 行為入口** |
| `PlayerController` | `SweetPotato/PlayerController.cs` | (大) | 玩家版本，繼承/類似 UnitController |
| `NpcFight` | `SweetPotato/NpcFight.cs` | 252 | CSV-loaded：每個 NPC 配備什麼 spell list、fightScript、難度 |
| `NpcSpellContainer` | `SweetPotato/NpcSpellContainer.cs` | 61 | 執行期持有 spell 集合 |
| `SpellManager` | `SweetPotato/SpellManager.cs` | (大) | 招式發動/結算 |
| `WorldManager` | `SweetPotato/WorldManager.cs` | (大) | 全域 entity 字典、行為 tick 派發 |

### 3.3 NPC 戰鬥資料流

```
CSV (策劃表)
  └─ NpcFight.LoadCSV → NpcFight.mTemplateList
       └─ GetSpellList(npcFight) → long[] spell ids
       └─ GetFightScript(npcFight) → 戰鬥腳本 id（推測指向 ScriptEntity）
       └─ GetNpcSpell(npcFight, SpellType) → 分類後的 spell list
NpcEntity.InitNpcSpell / InitNpcFight (line 1255, 1309)
  └─ 把 NpcFight 配給 NPC 的 NpcSpellContainer
UnitController（NPC 掛 controller）
  └─ 依據 spell list + fightScript 決定何時用何招（具體邏輯散落，待深 trace）
```

### 3.4 論道（LunDao）紙牌迷你遊戲 AI

唯一寫得比較像「AI 程式」的地方 — `LunDaoBattle.cs:505 NpcAI`：

- 對每張 NPC 牌依序跑 `SingleAI`
- `ai_CastValue` 初始 60，依據 HP%、MP 量動態加減：
  - HP < 50% → +10
  - HP < 30% → +20（注意：因為連續 `if/else if`，30%/10% 永遠進不去這個 branch，**bug 還是設計**？）
  - MP ≤ 3 → -10；否則 `+= m_Mp * 5`
- 用 `Random.Range(0, 100) <= ai_CastValue` 二元決定 Wait / CastSkill
- CastSkill 後遞迴 `SingleAI`（如還有可用招就再來一次）

非常陽春的「機率 + 狀態 bias」AI，但揭露了一個重點：**這款遊戲的 AI 設計哲學是「資料驅動 + 簡單腳本」，而非 ML/規劃**。Mod 可以做出明顯比原版聰明的對手。

### 3.5 Mod 介入建議

| 目的 | 方法 |
|---|---|
| 改特定 NPC 用什麼招 | patch CSV-loaded `NpcFight.mTemplateList`（建議用 `BepInEx` 載自訂 mod CSV） |
| 改 NPC 出招頻率/決策 | patch `UnitController` 的 spell 觸發點（要先 trace 哪個 method 決定出招時機） |
| 改論道 AI | Postfix `LunDaoBattle.SingleAI`，改寫 `ai_CastValue` 計算 |
| 注入 ML AI / 外部 AI agent | 替換 `UnitController` 的 tick；把當前局面序列化送到外部 AI server，再以指令回灌 |

## 4. 三軌 AI 對 mod 設計的啟示

- **想做 LLM 接入**：最自然的切入點是 **AIDialogView**（換 endpoint 指向自架 LLM/Claude 代理），或乾脆做新的 Form 並繞過原配額。
- **想做更聰明的 NPC**：要深入 `UnitController` 與 `SpellManager` 的觸發點，工作量比 dialog 大很多。
- **想做動態劇情/上下文 NPC barks**：擴 `NpcConditionalDialogueData` + 接 LLM 在條件對話 trigger 時調用，效果最高 CP 值。

## 5. 待深入（之後可以挖）

- [ ] **`UnitController` 5357 行的結構地圖** — 找出 NPC 戰鬥決策的實際 tick 點。
- [ ] **`AnswerViewNew.IsMatchMultCondition`** — 條件 DSL 語法，了解可以表達什麼條件（影響「動態劇情」mod 可行性）。
- [ ] **`SpellManager` + spell 執行管線** — 從 NPC 「想用招」到「實際發出 effect」的完整鏈路。
- [ ] **AIDialog 後端實測**：用 `curl http://jh.inmotiongame.com/portal/dashuju/index?q=hello&t=content` 看真實回應格式（小心：可能會被服務端紀錄 IP）。
