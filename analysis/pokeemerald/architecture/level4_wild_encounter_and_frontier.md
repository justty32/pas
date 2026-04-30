# pokeemerald — Level 4：野生遭遇詳細機制 & 對戰設施

---

## 一、野生遭遇完整流程

### 1.1 主入口 — `StandardWildEncounter()`（`src/wild_encounter.c:552`）

```
StandardWildEncounter(curMetatile, prevMetatile)
│
├─ sWildEncountersDisabled? → FALSE 直接返回
├─ 取地圖 wildMonHeader ID
│
├─ [Battle Pike 地圖] → 特殊路徑：GetBattlePikeWildMonHeaderId()
├─ [Battle Pyramid 地圖] → 特殊路徑：依 curChallengeBattleNum 查表
│
└─ [一般地圖]
    ├─ IsLandWildEncounter(curMetatile)?
    │    ├─ prevMetatile 不同 + AllowWildCheckOnNewMetatile()=FALSE → 40%機率跳過
    │    ├─ WildEncounterCheck(encounterRate) → 判斷是否觸發
    │    ├─ TryStartRoamerEncounter() → 嘗試流浪寶可夢（Latias/Latios）
    │    ├─ DoMassOutbreakEncounterTest() → 嘗試大量出沒
    │    └─ TryGenerateWildMon(landMonsInfo, LAND, REPEL|KEEN_EYE)
    │
    └─ IsWaterWildEncounter(curMetatile)?
         ├─ AreLegendariesInSootopolisPreventingEncounters() → 傳說阻擋
         ├─ WildEncounterCheck(encounterRate)
         ├─ TryStartRoamerEncounter()
         └─ TryGenerateWildMon(waterMonsInfo, WATER, REPEL|KEEN_EYE)
```

---

### 1.2 遭遇率計算 — `WildEncounterCheck()`（`src/wild_encounter.c:502`）

```c
encounterRate *= 16;  // 基礎放大

// 騎自行車（輕裝/特技自行車均適用）
if (PLAYER_AVATAR_FLAG_MACH_BIKE | ACRO_BIKE)
    encounterRate = encounterRate * 80 / 100;  // ×0.8

// 笛子道具修正（白笛/黑笛 二選一）
ApplyFluteEncounterRateMod(&encounterRate);   // 白笛×0.5 or 黑笛×1.5

// 潔淨標籤（首只持有）
ApplyCleanseTagEncounterRateMod(&encounterRate); // ×2/3

// 首只特性修正（非蛋）：
ABILITY_STENCH     → ÷2（金字塔內×3/4）
ABILITY_ILLUMINATE → ×2
ABILITY_WHITE_SMOKE → ÷2
ABILITY_ARENA_TRAP → ×2
ABILITY_SAND_VEIL + 沙暴天氣 → ÷2

// 上限夾至 MAX_ENCOUNTER_RATE = 2880
// 最終判斷：
return Random() % 2880 < encounterRate;
```

---

### 1.3 槽位選取 — `ChooseWildMonIndex_*`（`src/wild_encounter.c:182`）

**陸地（12槽）** 機率分佈（Gen III 標準）：

| Slot | 出現率（%） | 備註 |
|:---:|:---:|:---|
| 0 | 20% | |
| 1 | 20% | |
| 2 | 10% | |
| 3 | 10% | |
| 4 | 10% | |
| 5 | 10% | |
| 6 | 5% | |
| 7 | 5% | |
| 8 | 4% | |
| 9 | 4% | |
| 10 | 1% | 稀有 |
| 11 | 1% | 極稀有 |

**水上 / 岩石（5槽）**：60% / 20% / 10% / 5% / 5%  
**釣魚（依釣竿，10槽共用）**：
- 舊釣竿（Old Rod）：槽 0-1
- 好釣竿（Good Rod）：槽 2-4
- 超級釣竿（Super Rod）：槽 5-9

---

### 1.4 寶可夢生成 — `TryGenerateWildMon()`（`src/wild_encounter.c:422`）

```c
TryGenerateWildMon(wildMonInfo, area, flags):

1. 特性優先選種：
   ABILITY_MAGNET_PULL → 優先選鋼系（陸地）
   ABILITY_STATIC      → 優先選電系（陸地/水上）
   ↓ 若無符合則走機率槽位選取

2. ChooseWildMonLevel():
   level = minLevel + (Random() % (maxLevel - minLevel + 1))

3. Repel 檢查（WILD_CHECK_REPEL）：
   若 level < gPlayerParty[0] 等級 → 不觸發

4. Keen Eye 檢查（WILD_CHECK_KEEN_EYE）：
   首只有 Keen Eye/Intimidate → 降低低等級寶可夢遭遇率

5. CreateWildMon(species, level)
```

---

### 1.5 大量出沒（Mass Outbreak）

```c
// 資料儲存於 SaveBlock1（由廣播節目觸發）
gSaveBlock1Ptr->outbreakPokemonSpecies   // 出沒種類
gSaveBlock1Ptr->outbreakPokemonLevel     // 等級
gSaveBlock1Ptr->outbreakPokemonMoves[4] // 固定招式
gSaveBlock1Ptr->outbreakPokemonProbability // 機率（0-100）
gSaveBlock1Ptr->outbreakLocationMapGroup/Num // 觸發地圖

// 條件：在正確地圖 + Random() % 100 < probability → 觸發
// 生成後強制設定招式組合（覆蓋正常學習招式）
```

---

### 1.6 Feebas 特殊機制

```c
// src/wild_encounter.c
// Route 119 共 NUM_FISHING_SPOTS = 131+167+149 = 447 個釣魚點
// 其中 6 個為 Feebas 點，由 Trend Word 種子決定

FeebasSeedRng(seed)    // 初始化獨立 sFeebasRngValue（≠ 主遊戲 RNG）
FeebasRandom()         // 產生下一個 Feebas 亂數（LCG 計算）

// 判斷當前釣魚點是否為 Feebas 點：
GetFeebasFishingSpotId(x, y, section)  // 計算此點的全域索引
// 用 FeebasRandom() 依序生成 6 個不重複索引，比對是否命中
```

Trend Word（時尚語）改變後，Feebas 點重新亂數洗牌。

---

## 二、流浪寶可夢（Roamer）機制

```c
// src/roamer.c（Latias/Latios）
// 儲存於 gSaveBlock1Ptr->roamer：
struct Roamer {
    u32 ivs;
    u32 personality;
    u16 species;
    u16 hp;    // 剩餘 HP（逃跑後保留）
    u16 maxHP;
    u8  level;
    u8  status; // 異常狀態（逃跑後保留）
    u8  caught;
};

// 每次轉換地圖時，Roamer 移動到相鄰地圖
// TryStartRoamerEncounter()：
// 若 Roamer 在當前地圖 + 草叢觸發 → 1/4 機率替換普通遭遇
```

---

## 三、對戰設施（Battle Frontier）架構

### 3.1 共用框架 — `frontier_util.c` + `battle_tower.c`

```c
// 共用道具白名單（17種）
const u16 gBattleFrontierHeldItems[] = {
    ITEM_KINGS_ROCK, ITEM_SITRUS_BERRY, ITEM_CHOICE_BAND,
    ITEM_SCOPE_LENS, ITEM_LUM_BERRY, ITEM_LEPPА_BERRY, ...
};

// 設施訓練師資料（ROM 唯讀）
const struct BattleFrontierTrainer gBattleFrontierTrainers[];
// 每個訓練師有固定隊伍 ID 清單

FillTrainerParty(trainerId, firstMonId, monCount)
// 依訓練師 ID 從資料表填充 gEnemyParty
// 設施寶可夢有固定 IV（依難度：50組=31IV，Open組=視等級）

// 設施進度儲存在 SaveBlock2.frontier（struct BattleFrontier）
// 包含各設施的：連勝數、Record連勝、獎品、挑戰次數
```

---

### 3.2 五大設施各自特色

#### Battle Tower（`src/battle_tower.c`，3548行）
- 連續7場/5場（50組/Open組）訓練師對決
- 連勝記錄可透過 **Record Mixing**（混合記錄）傳播：5筆 `towerRecords[]`
- **學徒（Apprentice）系統**：玩家可訓練徒弟，徒弟的隊伍/招式/戰術由玩家設定後轉為 NPC 使用
- 敗陣後連勝歸零（但Record保留）

#### Battle Dome（`src/battle_dome.c`，6176行，最大設施）
- **16人單淘汰錦標賽**（`DOME_TOURNAMENT_TRAINERS_COUNT = 16`）
- Tournament Tree UI 視覺化（`Task_ShowTourneyTree`）
- **Info Card**（資訊卡）：可查看對手的招式屬性相剋分析
  - `EFFECTIVENESS_MODE_AI_VS_AI`：模擬 AI 對 AI 計算勝率
- `DOME_MONS[16][3]`：各訓練師的 3 隻寶可夢 ID 快取於存檔

#### Battle Palace（`src/battle_factory.c`部分 + `frontier_util`）
- 寶可夢依**個性**自主選擇招式（非玩家/AI控制）
- 不同個性群組偏好不同招式類型（攻擊/支援/防守）

#### Battle Arena（`battle_arena.c`）
- 每回合計算 **Mind/Skill/Body** 三項評分
- 三回合後比較分數決定勝負（非 HP）
- 特殊判定規則：閃躲/防禦扣分，攻擊加分

#### Battle Factory（`src/battle_factory.c`，919行）
- 玩家**出借**隨機寶可夢組隊
- 每場勝後可選擇**換牌**（與對手的某隻寶可夢交換）
- `rentalMons[6]` 儲存目前出借中的寶可夢 + 訓練師的寶可夢

#### Battle Pike（`src/battle_pike.c`，1656行）
- 7×14 連續通關，每節 14 個房間
- **房間類型（`sRoomType`）**：
  - 訓練師戰、野生戰（固定招式的特定寶可夢）、回復（HP/PP/異常）
  - NPC 施加異常狀態（燒傷/麻痺/睡眠）、提示房間、雙訓練師連戰
- `pikeHintedRoomIndex/Type`：「預言者 NPC」給出後方房間提示
- `pikeHeldItemsBackup[3]`：進入時備份持有道具，防止 Pike 機制剝奪
- `pikeHealingRoomsDisabled`：特定挑戰中禁用回復房

#### Battle Pyramid（`src/battle_pyramid.c`，1984行）
- **程序生成地圖**（`GenerateBattlePyramidFloorLayout()`，暗黑迷宮）
- `pyramidLightRadius`：光照半徑（初始1格，找到特定物品可擴大）
- `pyramidRandoms[4]`：樓層生成種子
- `pyramidTrainerFlags`（8-bit）：最多8個訓練師的戰鬥狀態旗標
- `pyramidBag`：設施專用道具袋（與一般背包分離）
- 到達頂層前需找到出口旗標，Boss 在第7層

---

### 3.3 對戰設施資料存放總覽

```
gSaveBlock2Ptr->frontier（struct BattleFrontier，約 0x300 bytes）：
  offset 0x000  Battle Tower 玩家記錄
  offset 0x0EC  Battle Tower 5筆 Record Mixing 記錄
  offset 0x588  挑戰狀態（lvlMode, challengePaused, selectedPartyMons）
  offset 0x5A2  curChallengeBattleNum（各設施進度房號/層數）
  offset 0x5A4  trainerIds[20]（當前挑戰的對手 ID 序列）
  offset 0x5CC  各設施連勝 / Record 數據
  offset 0x6E8  Battle Pike 房間提示 / 道具備份
  offset 0x700  Battle Pyramid 種子 / 光照 / 道具袋
  ...
  offset 0xEBE  battlePoints（BP）
```
