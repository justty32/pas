# pokeemerald — Level 9：競技大會（Contest）系統

---

## 一、整體架構

```
src/contest.c（6125 行）— 競技大會主邏輯
src/contest_effect.c    — 各招式效果函數（gContestEffectFuncs[]）
src/contest_ai.c        — AI 招式選擇腳本引擎
src/contest_util.c      — 工具函數（ContestMon 設定、結果保存）

競技大會 5 種類別（gSpecialVar_ContestCategory）：
  CONTEST_CATEGORY_COOL   = 0  （帥氣）
  CONTEST_CATEGORY_BEAUTY = 1  （美麗）
  CONTEST_CATEGORY_CUTE   = 2  （可愛）
  CONTEST_CATEGORY_SMART  = 3  （聰明）
  CONTEST_CATEGORY_TOUGH  = 4  （強壯）

4 個排名等級（whichRank）：
  CONTEST_RANK_NORMAL → SUPER → HYPER → MASTER

CONTESTANT_COUNT = 4（每場4位參賽者）
CONTEST_NUM_APPEALS = 5（共5回合表演）
```

---

## 二、核心資料結構（`include/contest.h`）

### 2.1 參賽寶可夢資料 — `struct ContestPokemon`（line 87）

```c
struct ContestPokemon {
    u16 species;
    u8 nickname[POKEMON_NAME_LENGTH + 1];
    u8 trainerName[PLAYER_NAME_LENGTH + 1];
    u8 trainerGfxId;
    u32 aiFlags;            // AI 行為旗標
    u8 whichRank:2;         // 當前挑戰等級
    u8 aiPool_Cool:1;       // 此 AI 能選酷招式嗎？
    // ...其他4個 aiPool 旗標
    u16 moves[MAX_MON_MOVES]; // 4個招式
    u8 cool, beauty, cute, smart, tough; // 五項特徵值（Condition）
    u8 sheen;               // 光澤（影響道具效果上限）
    u8 highestRank;         // 歷史最高等級
};

// EWRAM 全域陣列
extern struct ContestPokemon gContestMons[CONTESTANT_COUNT];
```

### 2.2 每回合參賽者狀態 — `struct ContestantStatus`（line 167）

```c
struct ContestantStatus {
    s16 baseAppeal;         // 招式基礎魅力值
    s16 appeal;             // 本回合實際得分（含修正）
    s16 pointTotal;         // 累計總分
    u16 currMove, prevMove; // 本回合/上回合使用的招式
    u8 moveCategory;        // 招式所屬競技類別
    u8 ranking:2;           // 目前排名 (0=1st)
    u8 moveRepeatCount:3;   // 連續使用相同招式次數
    bool8 noMoreTurns:1;    // 已使用「只能用一次」的招式？
    bool8 nervous:1;        // 緊張狀態（強制得0分）
    u8 numTurnsSkipped:2;   // 剩餘跳過回合數
    s8 condition;           // 本回合有效特徵加成（Context bonus）
    u8 jam;                 // 受到的干擾值
    u8 jamReduction;        // 干擾減免值
    bool8 resistant:1;      // 抗干擾？
    bool8 immune:1;         // 免疫干擾？
    bool8 hasJudgesAttention:1; // 評審注目？（Combo 前置條件）
    bool8 completedComboFlag:1; // 完成組合技？
    bool8 usedComboMove:1;
    u8 comboAppealBonus;    // 組合技額外得分（= baseAppeal × completedCombo）
    u8 repeatJam;           // 重複招式懲罰（= (repeatCount+1) × 10）
    u8 nextTurnOrder;       // 下回合出場順序（0~3）
    u8 attentionLevel;      // 觀眾注意度（0~5，影響UI心形滑塊）
};
```

### 2.3 競技大會全域狀態 — `struct Contest`（line 133）

```c
struct Contest {
    u8 playerMoveChoice;    // 玩家選擇的招式索引
    u8 appealNumber;        // 當前第幾回合（0~4）
    u8 turnNumber;          // 當前回合中第幾位出場（0~3）
    u8 currentContestant;   // 當前正在表演的參賽者 ID
    s8 applauseLevel;       // 掌聲表（0~4，=5時觸發溢出動畫）
    u8 prevTurnOrder[4];    // 上回合出場順序（用於反轉邏輯）
    u16 moveHistory[5][4];  // 歷史招式記錄
    u8 excitementHistory[5][4]; // 歷史興奮度記錄
    // ... 各種旗標（waitForLink, isShowingApplauseMeter...）
};
```

---

## 三、評分核心 — `CalculateAppealMoveImpact()`（line 4425）

每位參賽者出場時的評分流程：

```
1. 基礎魅力值 = gContestEffects[effect].appeal
   appeal = baseAppeal

2. 執行招式效果函數
   gContestEffectFuncs[effect]()
   （effect 由 gContestMoves[move].effect 決定）

3. Condition 加成（特徵值bonus）
   if (conditionMod == CONDITION_GAIN):
       appeal += condition - 10
   elif (appealTripleCondition):
       appeal += condition × 3
   else:
       appeal += condition  （通常狀況，condition 作為直接加分）

4. Combo 組合技系統
   前置招式：gContestMoves[move].comboStarterId != 0
     → hasJudgesAttention = TRUE（評審注目）
   後續招式：AreMovesContestCombo(prevMove, currMove) == TRUE
     且持有 hasJudgesAttention
     → completedCombo = TRUE
     → comboAppealBonus = baseAppeal × completedCombo
     → hasJudgesAttention = FALSE（消耗注目）

5. 重複招式懲罰（repeatJam）
   if (currMove == prevMove):
       moveRepeatCount++
       repeatJam = (moveRepeatCount + 1) × 10
       → 在後續 jam 計算中扣除其他競賽者的 appeal

6. 緊張（Nervous）
   if (nervous): appeal = 0; baseAppeal = 0
   → 且取消 hasJudgesAttention
```

---

## 四、觀眾興奮度（Excitement）系統 — `Contest_GetMoveExcitement()`（line 4748）

```c
// 5×5 興奮度查表（sContestExcitementTable[競技類別][招式類別]）
// 當前競技大會類別 vs 招式類別：

         Cool Beauty Cute Smart Tough
Cool  → [ +1,   0,  -1,  -1,   0]
Beauty→ [  0,  +1,   0,  -1,  -1]
Cute  → [ -1,   0,  +1,   0,  -1]
Smart → [ -1,  -1,   0,  +1,   0]
Tough → [  0,  -1,  -1,   0,  +1]

// +1 = 與當前大會類別相符 → 提高掌聲
// -1 = 類別衝突 → 降低掌聲
//  0 = 中性

// 興奮度加分邏輯（line 4515）：
if (moveExcitement > 0):
    if (applauseLevel + moveExcitement > 4):
        excitementAppealBonus = 60   // 掌聲溢出，大加分
    else:
        excitementAppealBonus = 10   // 普通加分
else:
    excitementAppealBonus = 0

// applauseLevel > 4 觸發 StartApplauseOverflowAnimation()
// → Task_ApplauseOverflowAnimation：紅色閃爍（混白色漸層每幀切換）
```

---

## 五、回合排名與下回合順序

### 5.1 回合內排名 — `RankContestants()`（line 3414）

```c
// 1. 累計本回合 appeal 到 pointTotal
pointTotal += appeal;

// 2. Bubble Sort（降序）
for i..CONTESTANT_COUNT-1:
    for j = CONTESTANT_COUNT-1 downto i+1:
        if arr[j-1] < arr[j]: swap

// 3. 找每位參賽者的最佳名次（允許同分同名次）
// 例：[100, 80, 80, 50] → ranking = [0, 1, 1, 3]（0-indexed）
// 同分者「取最佳名次」，非平均名次

// 4. SortContestants(TRUE) → 重新排列顯示框順序
// 5. ApplyNextTurnOrder() → 設定下回合出場順序
```

### 5.2 下回合出場順序 — `ApplyNextTurnOrder()`（line 4602）

```
預設邏輯：本回合最後出場 → 下回合最先出場（順序反轉）
例：本回合出場順序 [A, B, C, D] → 下回合 [D, C, B, A]

特殊覆蓋：
  各招式效果可設定 eContestantStatus[i].nextTurnOrder（0~3）
  → 強制此參賽者排在指定出場順序
  → 已排定者不參與剩餘反轉邏輯
```

### 5.3 注意度等級 — `SetAttentionLevels()`（line 3463）

```c
// 決定滑塊心形動畫的顯示格數
attentionLevel =
    currMove == MOVE_NONE ? 5    // 跳過回合 → 特殊
    appeal <= 0           ? 0    // 0分以下
    appeal < 30           ? 1
    appeal < 60           ? 2
    appeal < 80           ? 3
                          : 4    // 80分以上 → 滿格
```

---

## 六、最終評分計算 — `CalculateFinalScores()`（line 3557）

```
競技大會採兩輪計分制：

Round 1（審查，由 NPC 評審員依 Condition 評分）
  → gContestMonRound1Points[i]
  基準：寶可夢的5項 Condition + Sheen（光澤）

Round 2（表演，5回合 appeal 累計）
  gContestMonRound2Points[i] = gContestMonAppealPointTotals[i] × 2
  （表演得分 × 2 後算入最終）

totalPoints = round1Points + round2Points

排名決定（DetermineFinalStandings()，line 3571）：
  1. 主排序：totalPoints（高者優先）
  2. 次排序：round1Points（高者優先）
  3. 最終排序：randomOrdering（4個不重複亂數，確保無完全平局）
  → 賦值 gContestFinalStandings[contestant] = placing（0=1st）
```

---

## 七、掌聲表（Applause Meter）— `UpdateApplauseMeter()`（line 4728）

```c
// eContest.applauseLevel：0~4（整數），5+ 觸發溢出
// 視覺：8段 Sprite，前 applauseLevel 格顯示「亮」圖格，其餘「暗」圖格
// 直接寫 VRAM OBJ 區（OBJ_VRAM0 + tileNum offsets）

// 觸發時機：
ShowAndUpdateApplauseMeter(-1)  // 在競賽者干擾行動後顯示（興奮度降低）
ShowAndUpdateApplauseMeter(+1)  // 在成功表演後顯示（興奮度提高）

// 溢出動畫：applauseLevel > 4
StartApplauseOverflowAnimation()
  → BlendPalette(紅色 ↔ 白色，每隔1幀切換，來回16步)
  → 直到 applauseLevel < 5 才停止
```

---

## 八、AI 系統 — `struct ContestAIInfo`（line 226）

```c
struct ContestAIInfo {
    u8 aiState;         // AI 評估狀態機
    u16 nextMove;       // AI 決定使用的招式
    u8 nextMoveIndex;   // 招式在 moves[] 中的索引
    u8 moveScores[MAX_MON_MOVES]; // 各招式評分（0~255）
    u8 aiAction;        // 當前 AI 腳本動作
    u8 currentAIFlag;   // 正在評估的 AI 旗標
    u32 aiFlags;        // AI 行為旗標組合
    s16 scriptResult;   // 腳本返回值
    s16 vars[3];        // AI 腳本局部變數
    const u8 *stack[8]; // AI 腳本呼叫堆疊（8層深度）
    u8 stackSize;
    u8 contestantId;    // 目前評估哪位 AI
};

// AI 腳本引擎（contest_ai.c）：
// 類似 Battle AI — 以 gContestAIScriptsTable[] 腳本位元組碼
// 對每個招式評分，最終選 moveScores 最高的
// 高難度 AI 有更多 aiFlags（啟用更多評估腳本）
```

---

## 九、干擾（Jam）傳遞機制

```
每個招式效果函數（gContestEffectFuncs[effect]）執行後：

eContestAppealResults.jam  = 基礎干擾值
eContestAppealResults.jam2 = 副要干擾值

干擾對象：eContestAppealResults.jamQueue[]（最多5個目標）
干擾計算：
  實際 jam = jam × (1 - jamReduction/100)
  若 contestant.resistant: jam 減半
  若 contestant.immune: jam = 0
  target.appeal -= jam
  → 導致目標此回合失分

干擾文字（SetStartledString，line 4553）：
  jam >= 60 → "TRIPPED_OVER"（絆倒）
  jam >= 40 → "LEAPT_UP"（跳起來）
  jam >= 30 → "UTTER_CRY"（發出叫聲）
  jam >= 20 → "TURNED_BACK"（轉過去）
  jam >= 10 → "LOOKED_DOWN"（低下頭）

對手緊張（MakeContestantNervous，line 4586）：
  nervous = TRUE → appeal = 0, currMove = MOVE_NONE
```

---

## 十、大會流程（CB2_ContestMain 任務鏈）

```
初始化
  AllocContestResources()        ← EWRAM 動態分配所有子結構
  SetupContestGraphics()         ← 載入 BG/Sprite/調色板
  Task_WaitToRaiseCurtainAtStart ← 等待淡入
  Task_RaiseCurtainAtStart       ← 幕起動畫

每回合（CONTEST_NUM_APPEALS = 5 次）：
  Task_DisplayAppealNumberText   ← 顯示「第N次表演」
  Task_TryShowMoveSelectScreen   ← 顯示招式選擇畫面（玩家）
  Task_HandleMoveSelectInput     ← 等待玩家選招式
  Task_EndCommunicateMoveSelections ← 連線同步所有人選招式
  [對每位參賽者按出場順序]
    Task_AppealSetup             ← 設定動畫資料
    Task_DoAppeals               ← 執行招式動畫（借用 battle_anim）
      CalculateAppealMoveImpact() ← 評分計算
  Task_FinishRoundOfAppeals      ← 結算本回合
    RankContestants()            ← 更新排名
    SetAttentionLevels()         ← 更新注意度
  Task_UpdateHeartSliders        ← 動態更新心形滑塊（UI 動畫）
  Task_WaitPrintRoundResult      ← 顯示回合結果文字
  Task_DropCurtainAtRoundEnd     ← 幕落動畫

最終：
  Task_EndAppeals
  Task_DropCurtainAtAppealsEnd
  CalculateFinalScores()         ← 計算 Round1+Round2 總分
  DetermineFinalStandings()      ← 決定排名
  Task_TryCommunicateFinalStandings ← 連線同步最終結果
  Task_ContestReturnToField      ← 返回大地圖

記憶資料（成功後）：
  gSaveBlock2Ptr->contestLinkResults[category][place]++
  gCurContestWinner 存儲優勝資料（用於 TV 節目播送）
```

---

## 附錄：招式分類興奮度矩陣（完整）

```
競技大會當前類別（縱）× 招式類別（橫）→ 興奮度修正
        Cool Beauty Cute Smart Tough
Cool    [ +1,   0,  -1,  -1,   0 ]
Beauty  [  0,  +1,   0,  -1,  -1 ]
Cute    [ -1,   0,  +1,   0,  -1 ]
Smart   [ -1,  -1,   0,  +1,   0 ]
Tough   [  0,  -1,  -1,   0,  +1 ]

同類別恆 +1（對角線）
Cool↔Cute、Cool↔Smart 對稱 -1
Beauty↔Smart、Beauty↔Tough 對稱 -1
Cute↔Cool、Cute↔Tough 對稱 -1
Smart↔Cool、Smart↔Beauty 對稱 -1
Tough↔Beauty、Tough↔Cute 對稱 -1
```
