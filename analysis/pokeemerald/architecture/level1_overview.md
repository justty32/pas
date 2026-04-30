# pokeemerald — Level 1 初始探索

## 專案基本資訊

| 項目 | 內容 |
|:---|:---|
| **專案名稱** | pokeemerald |
| **來源** | pret 組織（pret.github.io）的寶可夢 Emerald 反組譯專案 |
| **目標 ROM** | pokeemerald.gba（SHA1: `f3ae088181bf583e55daf962a92bb46f4f1d07b7`）|
| **原始編譯日期** | 2005-02-21 11:10（GameFreak 原廠時間戳）|
| **目標平台** | Game Boy Advance（GBA）|
| **主要語言** | C + ARM Assembly（`.s` 檔）|
| **建構系統** | Makefile + 自定義工具鏈（`tools/`）|

---

## 目錄結構總覽

```
pokeemerald/
├── src/          # C 源碼（315 個 .c 檔）— 核心遊戲邏輯
├── include/      # 標頭檔（.h）— 結構定義與函數宣告
├── asm/          # ARM 組語（.s）— 未完全反編譯的程式碼段
├── data/         # 遊戲資料（.s 組語格式）— 地圖、腳本、野生寶可夢等
├── graphics/     # 圖形資源（tile/sprite 原始資料）
├── sound/        # 音效與音樂資料
├── constants/    # 具名常數（.h + .inc）
├── tools/        # 建構輔助工具
├── docs/         # 安裝與開發文件
└── ld_script.ld  # 連結器腳本，定義記憶體佈局
```

---

## 技術棧

- **語言**：C（現代 gcc 或原始 agbcc 編譯器皆支援）、ARM Thumb Assembly
- **記憶體區段**：
  - `IWRAM`（32KB 快速內部 RAM）：用 `COMMON_DATA` 宏標記的關鍵資料
  - `EWRAM`（256KB 外部 RAM）：用 `EWRAM_DATA` 宏標記的大型資料
  - ROM：唯讀遊戲資料（圖形、腳本、地圖等）
- **中斷系統**：VBlank、HBlank、VCount、Serial、Timer0-3、DMA0-3 等 14 個中斷向量
- **音效**：M4A（m4aSoundInit）—— GameFreak 自研音效引擎

---

## Level 2：核心模組職責

### 1. 程式入口 — `src/main.c :: AgbMain()`

```
AgbMain()
├── 硬體初始化：InitGpuRegManager, InitKeys, InitIntrHandlers
├── 週邊初始化：m4aSoundInit, RtcInit, CheckForFlashMemory
├── 遊戲初始化：InitMainCallbacks, InitHeap(gHeap, HEAP_SIZE)
└── 主迴圈（無限）：
    ├── ReadKeys()              ← 讀取手把輸入
    ├── 軟重置偵測（A+B+Start+Select）
    ├── UpdateLinkAndCallCallbacks() 或 CallCallbacks()
    └── WaitForVBlank()         ← 同步垂直消隱
```

**雙 Callback 架構**（`include/main.h`，`struct Main`）：
- `gMain.callback1`：每幀必定執行（通常處理 VBlank 相關邏輯）
- `gMain.callback2`：當前遊戲狀態的主邏輯（稱 `CB2_*`），切換即換場景

---

### 2. Task 系統 — `src/task.c`

GBA 寶可夢的「協程」機制，用優先序鏈結串列管理所有並行邏輯。

```c
// src/task.c
struct Task gTasks[NUM_TASKS];   // 全域 Task 陣列

CreateTask(TaskFunc func, u8 priority)  // 建立並依優先序插入
RunTasks()                              // 每幀由主迴圈呼叫，依序執行所有 active task
DestroyTask(u8 taskId)                  // 停用 task
```

- 每個 Task 有自己的 `data[8]`（u16 陣列）作為局部狀態
- Priority 數字**越小越先**執行
- 內部用雙向鏈結串列（`prev`/`next` 欄位）按優先序串接

---

### 3. Script 系統 — `src/script.c`

類 bytecode 的事件腳本直譯器，驅動地圖事件、NPC 對話、劇情觸發。

```c
// 兩種執行模式：
SCRIPT_MODE_BYTECODE  // 讀取 .s 腳本資料中的 opcode 逐條執行
SCRIPT_MODE_NATIVE    // 呼叫 C 函數指標，等待其返回 TRUE

// 兩個全域 Context：
sGlobalScriptContext    // 主要腳本（地圖觸發等）
sImmediateScriptContext // 立即腳本（特殊場景）
```

腳本資料位於 `data/event_scripts.s`，opcode 表為 `gScriptCmdTable[]`（`src/scrcmd.c`）。

---

### 4. 大地圖（Overworld）— `src/overworld.c`

```
Overworld 主要組成：
├── fieldmap          地圖佈局（Tilemap + Metatile + Layout）
├── field_player_avatar  玩家移動、衝刺、騎自行車/衝浪
├── event_object_movement  NPC 路徑行走、面向
├── field_camera      視角追蹤玩家
├── field_weather     天氣效果（雨、雪、沙暴...）
├── metatile_behavior 地形行為（草叢、水面、岩石）
└── wild_encounter    野生寶可夢觸發邏輯
```

地圖資料儲存於 `data/maps/<MapName>/` 子目錄（事件、腳本、連接資料）。

---

### 5. 戰鬥系統 — `src/battle_main.c`（核心）

**架構：CB2 狀態機 + 多 Controller**

```
CB2_InitBattleInternal
  └─ BattleStartClearSetData
       └─ BattleMainCB1（每幀）
            ├─ HandleTurnActionSelectionState  ← 選擇行動（招式/物品/換寶可夢/逃跑）
            ├─ SetActionsAndBattlersTurnOrder  ← 計算速度，決定出招順序
            ├─ RunTurnActionsFunctions         ← 執行各 Battler 的行動
            └─ HandleEndTurn_*                 ← 回合結束處理（繼續/勝利/失敗/逃跑）
```

**多 Controller 架構**（`src/battle_controllers.c`）：
| Controller | 檔案 | 用途 |
|:---|:---|:---|
| `battle_controller_player.c` | 玩家本機 | 接受玩家輸入 |
| `battle_controller_opponent.c` | AI 對手 | 呼叫 AI 腳本引擎 |
| `battle_controller_link_*.c` | 通訊對戰 | 通過 Link Cable/RFU 同步 |
| `battle_controller_safari.c` | 野生大地 Safari | 特殊規則 |
| `battle_controller_wally.c` | Wally 教學戰 | 劇情特化 |

---

### 6. 戰鬥 AI — `src/battle_ai_script_commands.c`

採用**腳本評分制**：

```
BattleAI_DoAIProcessing()
  ├── 讀取 gBattleAI_ScriptsTable[] 中對應腳本
  ├── 逐條執行 AI opcode（if_hp_less_than, if_status, score...）
  └── 累計各招式的 score，選出最高分招式
```

AI 行為腳本位於 `data/battle_ai_scripts.s`，分為多個策略層（基礎、進階、換寶可夢判斷等）。

---

### 7. 寶可夢資料結構 — `src/pokemon.c`

```c
// 核心資料結構（include/pokemon.h）
struct BoxPokemon {           // PC Box 中的寶可夢（80 bytes）
    u32 personality;          // 個性值（PID），決定性別、招式等
    u32 otId;                 // 訓練師 ID
    // ... 加密子結構 × 4（技能/努力值/特性/條件）
};

struct Pokemon {              // 戰鬥中使用（100 bytes）
    struct BoxPokemon box;    // 內含 BoxPokemon
    // + 非持久化戰鬥資料（HP、等級、狀態）
};
```

**加密機制**：BoxPokemon 的 4 個子結構（Substruct 0~3）以 PID XOR OTID 加密，排列順序由 `personality % 24` 決定（防止存檔作弊）。

---

### 8. 野生寶可夢遭遇 — `src/wild_encounter.c`

```c
// 四種遭遇區域
WILD_AREA_LAND    // 行走於草叢
WILD_AREA_WATER   // 衝浪於水面
WILD_AREA_ROCKS   // 使用岩石破碎於岩石
WILD_AREA_FISHING // 釣魚

// 特殊：Feebas 專屬機制
// Route 119 有固定 6 個 Feebas 釣魚點（FeebasRandom 另起亂數種子）
```

遭遇率受 Repel、Keen Eye 特性、笛子道具、潔淨標籤等修正。

---

## 記憶體分佈圖（概要）

```
GBA 位址空間：
0x02000000  EWRAM（256KB）  ← EWRAM_DATA 宏的變數（gPlayerParty, gEnemyParty...）
0x03000000  IWRAM（32KB）   ← COMMON_DATA 宏的變數（gMain, gTasks...）
0x08000000  ROM（最大 32MB）← 所有 const 資料、程式碼
0x05000000  Palette RAM     ← BG/OBJ 調色板（gMain 初始化時設白色）
0x06000000  VRAM            ← Tile/Map 資料
0x07000000  OAM（1KB）      ← Sprite 屬性（gMain.oamBuffer[128]）
```

---

## 關鍵全域變數速查

| 變數 | 位置 | 用途 |
|:---|:---|:---|
| `gMain` | IWRAM | 主結構（callback、按鍵、OAM buffer）|
| `gTasks[NUM_TASKS]` | IWRAM | 全域 Task 陣列 |
| `gPlayerParty[6]` | EWRAM | 玩家的寶可夢隊伍 |
| `gEnemyParty[6]` | EWRAM | 對手的寶可夢隊伍 |
| `gBattleMons[4]` | EWRAM | 場上戰鬥中的寶可夢（最多 4 體雙打）|
| `gBattleTypeFlags` | EWRAM | 戰鬥類型旗標（野生/訓練師/連線/對戰設施）|
| `gMapHeader` | — | 當前地圖標頭（佈局、事件、連接）|
