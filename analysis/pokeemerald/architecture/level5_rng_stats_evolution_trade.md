# pokeemerald — Level 5：RNG / 能力值 / 招式 / 演化 / 連線交換

---

## 一、亂數生成器（RNG）— `src/random.c`

### 實作

```c
// IWRAM（快速存取）
COMMON_DATA u32 gRngValue = 0;   // 主亂數狀態
COMMON_DATA u32 gRng2Value = 0;  // 第二亂數狀態

// include/random.h
#define ISO_RANDOMIZE1(val) (1103515245 * (val) + 24691)  // LCG 常數
#define ISO_RANDOMIZE2(val) (1103515245 * (val) + 12345)  // 另一常數（僅宏層級，實際未使用）

u16 Random(void) {
    gRngValue = ISO_RANDOMIZE1(gRngValue); // 推進一步
    sRandCount++;                          // 計數（從未被讀取）
    return gRngValue >> 16;                // 取高 16 位輸出
}

u16 Random2(void) {
    gRng2Value = ISO_RANDOMIZE1(gRng2Value); // 同公式，獨立狀態
    return gRng2Value >> 16;
}
```

- **演算法**：Linear Congruential Generator（LCG），multiplier `1103515245`
- **週期**：`2^32`（32位元狀態）
- **初始化**：`SeedRng(seed)` 直接設 `gRngValue = seed`
  - `BUGFIX` 模式下，`SeedRngWithRtc()` 在 `AgbMain()` 啟動時從 RTC 取當前時間作種子
- **第二亂數 `gRng2Value`**：動畫效果專用（避免遊戲邏輯亂數被動畫消耗）
- **Feebas 亂數**（`sFeebasRngValue`）：完全獨立的第三組狀態，防止 Trend Word 種子影響主遊戲

---

## 二、等級升等招式系統

### 2.1 升等招式表格式

```c
// include/constants/pokemon.h
#define LEVEL_UP_MOVE_ID  0x01FF   // bits [8:0]  = 招式 ID
#define LEVEL_UP_MOVE_LV  0xFE00   // bits [15:9] = 解鎖等級
#define LEVEL_UP_END      0xFFFF   // 表格結尾哨兵

// include/pokemon.h
extern const u16 *const gLevelUpLearnsets[];
// 資料實體在 data/pokemon/leveling.h 等資料檔案
```

等級值以 `(level << 9)` 形式存入高位，比對時：
```c
if (moveLevel > (level << 9)) break;  // 超過當前等級就停止
```

### 2.2 初始招式分配 — `GiveBoxMonInitialMoveset()`（`src/pokemon.c:2991`）

```c
// 設定新寶可夢招式組（捕捉/孵化/創建時）
for each entry in gLevelUpLearnsets[species]:
    if (moveLevel ≤ current_level << 9):
        GiveMoveToBoxMon(boxMon, move)
            → 找第一個空位填入
            → 若已有4招：MON_HAS_MAX_MOVES
                → DeleteFirstMoveAndGiveMoveToBoxMon()
                   // 推掉最舊的，補上最新的
```

### 2.3 升等學招式 — `GiveMoveToMon()`（`src/pokemon.c:2934`）

```c
GiveMoveToMon / GiveMoveToBoxMon:
  → 找招式欄位中第一個 MOVE_NONE 填入，同時設 PP
  → 已知此招式 → MON_ALREADY_KNOWS_MOVE（不重複學）
  → 四格全滿 → MON_HAS_MAX_MOVES（觸發「遺忘/保留」選擇介面）
```

### 2.4 可重新學習招式 — `GetNumberOfRelearnableMoves()`

掃描 learnset，找出「等級已達到但目前未在技能欄中」的招式，用於招式學習機（Move Reminder）。

---

## 三、能力值計算公式 — `CalculateMonStats()`（`src/pokemon.c:2823`）

### HP 公式（Gen III）

```
HP = floor((2 × baseHP + HPIV + floor(HPEV / 4)) × Level / 100) + Level + 10
```

例外：`SPECIES_SHEDINJA`（脫殼忍者）固定 HP = 1。

### 其他五項能力值（CALC_STAT 宏）

```c
n = floor((2 × base + IV + floor(EV / 4)) × Level / 100) + 5
n = ModifyStatByNature(nature, n, statIndex)   // 個性修正
```

**個性修正**：每種個性讓 1 項能力 ×110%（無條件捨去），1 項 ×90%。中性個性不修正。

### 升等後 HP 更新

```c
// src/pokemon.c:2882
currentHP += newMaxHP - oldMaxHP;
// ⚠ BUG（Pomeg Berry 漏洞）：
// 若 Pomeg Berry 降低 HP EV 導致 newMaxHP < oldMaxHP，
// currentHP 可能變 ≤ 0，產生 HP=0 的「行走寶可夢（Ghost）」
// BUGFIX 模式下加入: if (currentHP <= 0) currentHP = 1;
```

---

## 四、演化系統 — `GetEvolutionTargetSpecies()`（`src/pokemon.c:5489`）

### 演化觸發模式

```c
// 三種呼叫模式（mode 參數）：
EVO_MODE_NORMAL    → 升等後觸發（大地圖升等/對戰升等）
EVO_MODE_TRADE     → 交換後觸發
EVO_MODE_ITEM_USE  → 使用道具後觸發
EVO_MODE_ITEM_CHECK → 僅查詢（選單檢視）
```

### EVO_MODE_NORMAL 各演化條件

| 演化方法 | 條件 | 典型例子 |
|:---|:---|:---|
| `EVO_FRIENDSHIP` | 好感度 ≥ 220 | 皮丘→皮卡丘 |
| `EVO_FRIENDSHIP_DAY` | 好感度 ≥ 220 + RTC 12:00-23:59 | 夜巡鹿→晨巡鹿 |
| `EVO_FRIENDSHIP_NIGHT` | 好感度 ≥ 220 + RTC 00:00-11:59 | 伊布→月精靈 |
| `EVO_LEVEL` | 等級 ≥ param | 多數基礎演化 |
| `EVO_LEVEL_ATK_GT_DEF` | 等級 + ATK > DEF | 雙截龍A |
| `EVO_LEVEL_ATK_EQ_DEF` | 等級 + ATK == DEF | 雙截龍B |
| `EVO_LEVEL_ATK_LT_DEF` | 等級 + ATK < DEF | 雙截龍C |
| `EVO_LEVEL_SILCOON` | 等級 + `(personality>>16) % 10 ≤ 4` | 天蠶→白蝴蛹 |
| `EVO_LEVEL_CASCOON` | 等級 + `(personality>>16) % 10 > 4` | 天蠶→鐵繭殼 |
| `EVO_LEVEL_NINJASK` | 等級條件（`evolution_scene` 另生成脫殼忍者）| 飛天螳螂 |
| `EVO_BEAUTY` | 美麗度 ≥ param | 美麗魚→天藍鸚鵡魚 |
| `EVO_TRADE` | 交換 | 怪力→火暴獸等 |
| `EVO_TRADE_ITEM` | 持有特定道具交換（道具消失）| 鬼斯通→耿鬼 |
| `EVO_ITEM` | 使用進化石 | 火石→九尾 |

**常青石（Everstone）**：持有時 `HOLD_EFFECT_PREVENT_EVOLVE` → 跳過所有演化（ITEM_CHECK 模式例外）。

### 演化場景 — `EvolutionScene()`（`src/evolution_scene.c:209`）

```
EvolutionScene(mon, postEvoSpecies, canStopEvo, partyId)
  └─ Task_EvolutionScene(taskId)   ← Task 狀態機驅動
      ├─ 播放演化動畫（調色板閃爍/縮放效果）
      ├─ canStopEvo = TRUE → 監聽 B 鈕取消
      ├─ 演化完成 → SetMonData(MON_DATA_SPECIES, postEvoSpecies)
      ├─ CalculateMonStats(mon)    ← 重算能力值
      ├─ MonTryLearningNewMove()   ← 嘗試學習演化後招式
      └─ TryCreateNincadaEgg()     ← 忍者蜥 Lv20 時創造脫殼忍者
```

---

## 五、連線交換系統 — `src/trade.c`

### 架構

```
CB2_LinkTrade()（`src/trade.c:2827`）
  使用 gMain.state 狀態機（而非 Task 系統）

連線方式：
  Cable Link（Link Cable）→ `src/link.c`
  無線（RFU）              → `src/AgbRfu_LinkManager.c` + librfu
```

### 連線建立流程（`CB2_LinkTrade` state 機）

```
state 0: 初始化記憶體（AllocZeroed sTradeAnim, ResetTasks, ResetSpriteData）
state 1: 判斷是否已有 RemoteLinkPlayers
          有 → state 4（已建立連線）
          無 → OpenLink(), state 2
state 2: 等待 60 幀（Cable 硬體握手時間）
state 3: IsLinkMaster() 等待玩家數達到 GetSavedPlayerCount()
          → CheckShouldAdvanceLinkState()（同步進度）
state 4: 等待 IsLinkPlayerDataExchangeComplete()（完整玩家資料交換）
state 5+: 進入交換 UI（選擇寶可夢、確認、動畫）
```

### 資料傳輸

```c
SendBlock(BitmaskAllOtherLinkPlayers(), linkData, sizeof(linkData));
// linkData 包含：
// - 玩家選擇的 Pokemon（完整 struct Pokemon）
// - 確認旗標（playerFinishStatus）
// - 通訊封包類型（CB2_* 枚舉）

IsLinkMaster()  // Master 節點負責同步雙方狀態機
```

### 交換驗證規則

```c
// src/trade.c（RunTradeMenuCallback）
MSG_MON_CANT_BE_TRADED   // 有些寶可夢有交易限制
MSG_EGG_CANT_BE_TRADED   // 蛋不可交換
CB_PARTNER_MON_INVALID   // 對方的寶可夢無效（ROM 版本不相容等）
```

交換完成後：
1. 雙方的 `Pokemon` 資料互換
2. 對收到的寶可夢呼叫 `GetEvolutionTargetSpecies(EVO_MODE_TRADE)`
3. 若可演化 → 立即啟動 `EvolutionScene`
4. 訓練師資料（OT Name/ID）保留原主人資訊
5. 更新好感度（交換獎勵）

---

## 附錄：寶可夢資料讀寫 — `GetMonData()` / `SetMonData()`

```c
// src/pokemon.c — 通用資料存取介面
GetMonData(mon, field, buffer)
// field 枚舉（MON_DATA_*）決定讀取哪個子結構的哪個位元欄位
// BoxPokemon 的 4 個 substruct 需先 Decrypt 後讀取，讀完 Encrypt

SetMonData(mon, field, value)
// 寫入後重新 Encrypt
// 某些欄位寫入後自動觸發 CalculateMonStats()
```

BoxPokemon 子結構 × 4（排列由 `personality % 24` 決定）：
| 子結構 | 內容 |
|:---|:---|
| Substruct 0 | 物種、持有道具、EXP、好感度、技能、特性 |
| Substruct 1 | 招式 × 4、PP × 4、PP Up |
| Substruct 2 | HP/Atk/Def/Speed/SpAtk/SpDef 努力值（EV）|
| Substruct 3 | 個性值（IV）、屬性、Pokérus、捕獲地點、球種 |
