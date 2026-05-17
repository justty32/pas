# pokeemerald — Level 8：日間照料中心 / 孵蛋系統 / 訓練師視線偵測

---

## 一、日間照料中心（Daycare）— `src/daycare.c`

### 1.1 資料結構（儲存於 SaveBlock1）

```c
// include/daycare.h（由 gSaveBlock1Ptr->daycare 存取）
struct DaycareMon {
    struct BoxPokemon mon;   // 完整 BoxPokemon（含加密）
    struct DaycareMail mail; // 寄存時隨附的郵件備份
    u32 steps;               // 累積走步數（等同 EXP 增加量）
};

struct DayCare {
    struct DaycareMon mons[DAYCARE_MON_COUNT]; // 2 個槽位
    u32 offspringPersonality;  // 0 = 無蛋；非0 = 蛋已決定 personality
    u16 stepCounter;           // 0~255，達255觸發孵蛋週期檢查
};
```

`DAYCARE_MON_COUNT = 2`，兩隻寶可夢各有獨立步數計數器。

---

### 1.2 寶可夢存取/領取

**存入** `StorePokemonInDaycare()`（line 160）：
```
1. 備份郵件（MonHasMail → 複製至 daycareMon->mail，TakeMailFromMon）
2. daycareMon->mon = mon->box   ← 複製 BoxPokemon
3. BoxMonRestorePP(&daycareMon->mon)  ← 恢復 PP（在daycare中不消耗）
4. daycareMon->steps = 0
5. ZeroMonData(mon) + CompactPartySlots()
```

**取出** `TakeSelectedPokemonFromDaycare()`（line 243）：
```c
// 累積步數當 EXP 加回去
experience = GetMonData(&pokemon, MON_DATA_EXP) + daycareMon->steps;
SetMonData(&pokemon, MON_DATA_EXP, &experience);
ApplyDaycareExperience(&pokemon);  // 逐級升等 + 學招式（自動推掉最舊的）

// 費用計算（line 319）
cost = 100 + 100 * numLevelsGained;  // 基礎100 + 每升一級100
```

---

### 1.3 相性（Compatibility）評分 — `GetDaycareCompatibilityScore()`（line 1015）

```c
// 回傳值（對應 NPC 台詞）：
PARENTS_INCOMPATIBLE      = 0  // 「似乎不太對盤...」
PARENTS_LOW_COMPATIBILITY = 20  // 「似乎不太感興趣」
PARENTS_MED_COMPATIBILITY = 50  // 「相處還算好」
PARENTS_MAX_COMPATIBILITY = 70  // 「非常合得來！」

// 判斷邏輯：
if (EGG_GROUP_NO_EGGS_DISCOVERED) → INCOMPATIBLE
if (兩隻都是 Ditto) → INCOMPATIBLE

if (其中一隻是 Ditto):
    同訓練師 → LOW；不同訓練師 → MED

else (一般配對):
    不同性別 + 相同蛋群 是前提條件
    同種 + 同訓練師 → MED
    同種 + 不同訓練師 → MAX   ← 異國寶可夢的意義
    異種 + 不同訓練師 → MED
    異種 + 同訓練師 → LOW
```

---

### 1.4 蛋的產生觸發 — `TryProduceOrHatchEgg()`（line 879）

每走一步，呼叫一次：

```c
// 步數計數（每隻寶可夢獨立）
daycare->mons[i].steps++

// 嘗試產蛋條件（每走 256 步的邊界才檢查，判斷式：(steps & 0xFF) == 0xFF）
if (offspringPersonality == 0       // 目前沒有待領的蛋
 && validEggs == 2                  // 兩槽都有寶可夢
 && (mons[1].steps & 0xFF) == 0xFF) // 每 256 步一次機會
{
    compatibility = GetDaycareCompatibilityScore();
    // 比較相性值與隨機數：
    if (compatibility > (Random() * 100u) / USHRT_MAX)
        TriggerPendingDaycareEgg();  // 設定 offspringPersonality + FlagSet(FLAG_PENDING_DAYCARE_EGG)
}

// 孵蛋週期（stepCounter 0→254，每 255 步觸發一次）
if (++daycare->stepCounter == 255):
    toSub = GetEggCyclesToSubtract()  // Magma Armor/Flame Body 特性 → toSub = 2，否則 = 1
    eggCycles -= toSub
    if (eggCycles == 0) → 回傳 TRUE（觸發孵蛋動畫）
```

---

### 1.5 個性遺傳（Everstone）— `_TriggerPendingDaycareEgg()`（line 455）

```c
SeedRng2(gMain.vblankCounter2);   // ← 用幀計數器當種子（可 RNG 操作）

parent = GetParentToInheritNature(daycare);
// 優先找母方（MON_FEMALE）；有 Ditto 就選 Ditto；兩隻都是 Ditto 則丟硬幣
// 若持有道具 ≠ ITEM_EVERSTONE → 返回 -1（不遺傳個性）
// 若持有 Everstone → 50% 機率遺傳（再丟一次硬幣）

if (parent < 0):
    // 完全隨機 personality
    offspringPersonality = (Random2() << 16) | ((Random() % 0xfffe) + 1)
else:
    // 重複嘗試（最多 2400 次），直到 personality % 25 == wantedNature
    do { personality = (Random2() << 16) | Random(); } while (natureTries++ <= 2400);
```

---

### 1.6 個體值遺傳（IV Inheritance）— `InheritIVs()`（line 527）

```c
// 遺傳 INHERITED_IV_COUNT = 3 項 IV
// ⚠️ BUG（Gen III 共有，Emerald 未修正）：
// 應從 availableIVs[Random() % (NUM_STATS - i)] 取 index，然後 RemoveIVIndexFromList(index)
// 但實際程式碼每次固定移除 i（0, 1, 2 = HP, ATK, DEF 位置）而非隨機選出的位置
// 結果：HP 和 DEF 的遺傳機率低於理論值

#ifndef BUGFIX
selectedIvs[i] = availableIVs[Random() % (NUM_STATS - i)];
RemoveIVIndexFromList(availableIVs, i);  // ← 移除固定位置，非選中位置
#else
u8 index = Random() % (NUM_STATS - i);
selectedIvs[i] = availableIVs[index];
RemoveIVIndexFromList(availableIVs, index); // 正確版本
#endif

// 每個遺傳 IV 的親代：各自獨立 Random() % 2（隨機選父或母）
```

---

### 1.7 蛋的招式組合 — `BuildEggMoveset()`（line 632）

```
蛋招式優先序（由低到高，後者覆蓋前者）：
1. 孵化招式（Level 1 升等學習的招式）
2. 遺傳招式（Egg Moves）：父方的招式 ∈ gEggMoves[species] → 加入
3. TM/HM 遺傳：父方招式是 TM/HM 且子方可學 → 加入
4. 雙親共有招式（父母都會 + 出生時可學）→ 加入

特殊處理：
- 皮丘（SPECIES_PICHU）：若任一親代持有 ITEM_LIGHT_BALL → 加入 MOVE_VOLT_TACKLE
- 無需持有 Light Ball；只要帶著就能傳遞
```

---

### 1.8 蛋種類決定（物種回溯）— `GetEggSpecies()`（line 381）

```c
// 從當前物種往演化樹根部回溯（最多 EVOS_PER_MON = 5 次，但實際3次系最多）
// 遍歷 gEvolutionTable[j][k].targetSpecies == species → species = j
// 直到找不到前驅為止

// 特例：
// Nidoran♀ + personality & EGG_GENDER_MALE → SPECIES_NIDORAN_M
// Illumise  + personality & EGG_GENDER_MALE → SPECIES_VOLBEAT

// 香精道具（Incense）：
AlterEggSpeciesWithIncenseItem():
  SPECIES_WYNAUT  → 若無 LAX_INCENSE  → 改為 SPECIES_WOBBUFFET
  SPECIES_AZURILL → 若無 SEA_INCENSE  → 改為 SPECIES_MARILL
```

---

## 二、孵蛋動畫系統 — `src/egg_hatch.c`

### 2.1 資料結構

```c
struct EggHatchData {
    u8 eggSpriteId;          // 蛋 Sprite ID
    u8 monSpriteId;          // 孵化後寶可夢 Sprite ID
    u8 state;                // CB2_EggHatch 狀態機 (0~10)
    u8 delayTimer;           // 延遲計數
    u8 eggPartyId;           // 蛋在隊伍中的 index
    u8 eggShardVelocityId;   // 蛋殼碎片速度組合 index
    u16 species;
    u8 textColor[3];
    u8 windowId;
};

static struct EggHatchData *sEggHatchData;  // EWRAM 動態分配
```

### 2.2 孵蛋流程

```
EggHatch()（由 overworld 呼叫）
  LockPlayerFieldControls()
  CreateTask(Task_EggHatch, 10)   ← 等待淡出完成後切換 CB2
  FadeScreen(FADE_TO_BLACK, 0)

CB2_LoadEggHatch（gMain.state 0~8）：
  0: 重置 BG/Sprite/任務/掃描線；Alloc sEggHatchData
  1: InitWindows
  2: 載入 BattleTextbox 圖格/調色板
  3: LoadSpriteSheet（蛋 + 蛋殼碎片）
  4: AddHatchedMonToParty(eggPartyId)   ← 將蛋轉為正式寶可夢
  5: EggHatchCreateMonSprite(FALSE, 0)  ← 載入寶可夢前視圖圖形
  6: EggHatchCreateMonSprite(FALSE, 1)  ← 建立寶可夢 Sprite（初始隱藏）
  7: 載入交換背景（Trade Platform）
  8: SetMainCallback2(CB2_EggHatch)

CB2_EggHatch（state 0~10）：
  0: 淡入 + 建立蛋 Sprite + CreateTask(Task_EggHatchPlayBGM)
     BGM: t=0→停地圖音樂；t=1→MUS_EVOLUTION_INTRO；t>60→MUS_EVOLUTION
  1: 等待淡入完成
  2: 延遲 30 幀後啟動搖晃動畫 SpriteCB_Egg_Shake1
  3: 等待動畫結束（SpriteCB_Egg_Shake1 → Shake2 → Shake3 → WaitHatch → Hatch → Reveal）
     SpriteCB_Egg_Hatch：播放蛋殼爆裂 + 隨機生成多個 EggShard Sprite（彈射物理）
     SpriteCB_Egg_Reveal：顯示寶可夢 Sprite + 隱藏蛋 Sprite
  4: 等待寶可夢前視圖動畫（DoMonFrontSpriteAnimation）
  5: 顯示「{名字} 從蛋裡孵化了！」+ PlayFanfare(MUS_EVOLVED)
  6~7: 等待 Fanfare 結束（IsFanfareTaskInactive 判斷兩次）
  8: 顯示「要為它取個暱稱嗎？」
  9: 等待文字列印完成 → 建立 Yes/No 選單
  10: Yes → DoNamingScreen(NAMING_SCREEN_NICKNAME)
       No/B → SetMainCallback2(CB2_ReturnToField)
```

### 2.3 蛋圖形動畫幀序列

```
蛋 Sprite 動畫索引：
  EGG_ANIM_NORMAL    = frame(0,  5)  // 完整蛋
  EGG_ANIM_CRACKED_1 = frame(16, 5)  // 一道裂縫
  EGG_ANIM_CRACKED_2 = frame(32, 5)  // 兩道裂縫
  EGG_ANIM_CRACKED_3 = frame(48, 5)  // 三道裂縫

搖晃 Callback 鏈：
  SpriteCB_Egg_Shake1 → Shake2 → Shake3 → WaitHatch → Hatch → Reveal
  每次 Shake 以 x2 偏移模擬左右晃動 + 切換裂縫動畫幀
```

---

## 三、訓練師視線偵測系統 — `src/trainer_see.c`

### 3.1 架構概覽

```
CheckForTrainersWantingBattle()（每幀在 Overworld 呼叫）
  遍歷所有 gObjectEvents[]（OBJECT_EVENTS_COUNT = 16）
  篩選 trainerType == TRAINER_TYPE_NORMAL || TRAINER_TYPE_BURIED
  呼叫 CheckTrainer(objectEventId) → 驗證旗標 + 計算接近距離

  結果：
  gNoOfApproachingTrainers == 1 → ConfigureAndSetUpOneTrainerBattle()
  gNoOfApproachingTrainers == 2 → ConfigureTwoTrainersBattle() + SetUpTwoTrainersBattle()
  → 雙打只在玩家隊伍有兩隻可用寶可夢時觸發
```

---

### 3.2 視野距離計算 — `GetTrainerApproachDistance()`（line 301）

```c
// 四方向距離計算函數表
static u8 (*const sDirectionalApproachDistanceFuncs[])(
    struct ObjectEvent *trainerObj, s16 range, s16 x, s16 y) = {
    GetTrainerApproachDistanceSouth,  // 訓練師面向南，看向下方的玩家
    GetTrainerApproachDistanceNorth,
    GetTrainerApproachDistanceWest,
    GetTrainerApproachDistanceEast,
};

// 以南向為例（line 327）：
GetTrainerApproachDistanceSouth():
    if (trainerObj->currentCoords.x == x           // 同列（X 軸對齊）
     && y > trainerObj->currentCoords.y            // 玩家在訓練師南方
     && y <= trainerObj->currentCoords.y + range)  // 在視野範圍內
        return (y - trainerObj->currentCoords.y);  // 接近距離
    return 0;

// 普通訓練師（TRAINER_TYPE_NORMAL）：
//   只看面向的單一方向（trainerObj->facingDirection）
// 特殊訓練師（TRAINER_TYPE_SEE_ALL_DIRECTIONS / BURIED）：
//   遍歷四個方向，任一方向看到即觸發
```

---

### 3.3 視線路徑檢查 — `CheckPathBetweenTrainerAndPlayer()`（line 370）

```c
// 從訓練師位置出發，逐步往玩家方向移動，檢查碰撞
for (i = 0; i < approachDistance - 1; i++, MoveCoords(direction, &x, &y)):
    collision = GetCollisionFlagsAtCoords(trainerObj, x, y, direction)
    // 忽略 COLLISION_OUTSIDE_RANGE（超出自身移動範圍），但其他碰撞（牆壁、物件）阻擋視線

// 最後一格（玩家所在格）：
GetCollisionAtCoords(trainerObj, x, y, direction)
if (collision == COLLISION_OBJECT_EVENT) → 確認命中玩家 → return approachDistance
```

---

### 3.4 訓練師接近動畫狀態機 — `sTrainerSeeFuncList[]`（line 89）

```
enum TrainerSeeState:
  TRSEE_NONE               = 0  // 閒置
  TRSEE_EXCLAMATION        = 1  // 顯示「!」Sprite + 訓練師面向玩家
  TRSEE_EXCLAMATION_WAIT   = 2  // 等待「!」動畫結束
  TRSEE_MOVE_TO_PLAYER     = 3  // 走向玩家（tTrainerRange 步，每幀走一格）
  TRSEE_PLAYER_FACE        = 4  // 命令玩家轉向面對訓練師
  TRSEE_PLAYER_FACE_WAIT   = 5  // 等待玩家轉向完成 → SwitchTaskToFollowupFunc
  TRSEE_REVEAL_DISGUISE    = 6  // 擬態訓練師（樹/山）：MOVEMENT_ACTION_REVEAL_TRAINER
  TRSEE_REVEAL_DISGUISE_WAIT = 7 // 等待擬態動畫 → 跳回 MOVE_TO_PLAYER
  TRSEE_REVEAL_BURIED      = 8  // 埋入地下訓練師：面向玩家
  TRSEE_BURIED_POP_OUT     = 9  // 灰燼噴出效果（FieldEffectStart(FLDEFF_ASH_PUFF)）
  TRSEE_BURIED_JUMP        = 10 // 彈跳動畫（等 ash puff animCmdIndex == 2）
  TRSEE_REVEAL_BURIED_WAIT = 11 // 等待灰燼效果結束 → 跳回 MOVE_TO_PLAYER

Task_RunTrainerSeeFuncList()（line 438）：
    while (sTrainerSeeFuncList[task->tFuncId](taskId, task, trainerObj));
    // 回傳 TRUE 時連續推進（同幀執行多個狀態）
```

---

### 3.5 感嘆號圖示 Sprite — `FldEff_ExclamationMarkIcon()`（line 696）

```c
// 建立 16x16 感嘆號（或問號、愛心）Sprite
CreateSpriteAtEnd(&sSpriteTemplate_ExclamationQuestionMark, 0, 0, 0x53);

SpriteCB_TrainerIcons（Sprite callback）：
  sprite->x = objEventSprite->x     // 跟隨訓練師 Sprite 橫座標
  sprite->y = objEventSprite->y - 16 // 在頭頂上方 16px
  sprite->y2 += sYVelocity           // 初始 -5（向上彈起），重力 +1 每幀
  // 動畫結束（animEnded）或物件消失 → FieldEffectStop()
```

---

### 3.6 雙打訓練師配對邏輯

```c
// gNoOfApproachingTrainers 陣列最多儲存 2 位訓練師
// 第一位訓練師接近完成後：
TryPrepareSecondApproachingTrainer()（line 666）：
    if (gNoOfApproachingTrainers == 2 && gApproachingTrainerId == 0):
        gApproachingTrainerId++
        UnfreezeObjectEvents()
        FreezeObjectEventsExceptOne(gApproachingTrainers[1].objectEventId)
        gSpecialVar_Result = TRUE   ← 腳本繼續讓第二位訓練師接近

// 腳本識別雙打格式（scriptPtr[1]）：
TRAINER_BATTLE_DOUBLE              // 普通雙打
TRAINER_BATTLE_REMATCH_DOUBLE      // 重賽雙打
TRAINER_BATTLE_CONTINUE_SCRIPT_DOUBLE // 帶後續腳本的雙打
```

---

## 附錄：Daycare 相性評分觸發蛋機率

```
蛋觸發公式（每 256 步一次機會）：
  出蛋概率 = compatibility / 100
  具體：compatibility > Random() × 100 / 65535

相性值 → 概率對照：
  PARENTS_INCOMPATIBLE (0)  → 絕不產蛋
  LOW  (20)                 → 約 20% 機率（每 256 步有 20% 的機會）
  MED  (50)                 → 約 50% 機率
  MAX  (70)                 → 約 70% 機率

實際產蛋週期預期步數（期望值）：
  LOW  → 256 / 0.20 = 1280 步
  MED  → 256 / 0.50 = 512 步
  MAX  → 256 / 0.70 ≈ 366 步
```
