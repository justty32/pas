# pokeemerald — Level 3：戰鬥傷害計算管線

## 概述

戰鬥腳本以指令集（`Cmd_*`）的形式驅動一場攻擊從「使出招式」到「扣血完畢」的完整流程。  
共有 **498 個 `Cmd_*` 指令**（`src/battle_script_commands.c`，10326 行）。

---

## 一回合出招的指令執行順序

```
battle_scripts_1.s / gBattleScriptsForMoveEffects[]
  ↓ 每幀 RunTurnActionsFunctions() 呼叫 BattleScriptExecute()
  ↓ RunScriptCommand(ctx) → ctx->cmdTable[opcode]()

主要 Cmd_ 執行順序（普通物理/特殊招式）：
  Cmd_attackcanceler       ← 檢查先制行動取消（金屬音、封印...）
  Cmd_accuracycheck        ← 命中率判定
  Cmd_attackstring         ← 印出「使出 XXX！」文字
  Cmd_ppreduce             ← 扣 PP
  Cmd_critcalc             ← 計算是否暴擊
  Cmd_damagecalc           ← 計算基礎傷害
  Cmd_typecalc             ← 套用 STAB + 屬性相剋
  Cmd_adjustnormaldamage   ← 亂數修正（85~100%）
  Cmd_attackanimation      ← 播放招式動畫
  Cmd_waitanimation        ← 等待動畫結束
  Cmd_healthbarupdate      ← 更新 HP 血條
  Cmd_datahpupdate         ← 實際扣 HP
  Cmd_critmessage          ← 印「要害一擊！」文字
  Cmd_effectivenesssound   ← 播放效果音
  Cmd_resultmessage        ← 印「效果絕佳！」等文字
  Cmd_seteffectwithchance  ← 附加效果（燒傷/麻痺，按機率）
  Cmd_tryfaintmon          ← 判斷是否昏厥
  Cmd_getexp               ← 分配 EXP
```

每個 `Cmd_*` 結尾將 `gBattlescriptCurrInstr` 推進（等同 bytecode PC）。  
遇到 `Cmd_waitstate` 時暫停等待控制器回應，下幀繼續。

---

## 命中率計算 — `Cmd_accuracycheck`（`src/battle_script_commands.c:1099`）

```c
buff = attacker.statStages[STAT_ACC] + DEFAULT_STAT_STAGE - defender.statStages[STAT_EVASION];
// 夾到 [MIN_STAT_STAGE, MAX_STAT_STAGE]

calc = sAccuracyStageRatios[buff].dividend * moveAcc / divisor;
```

**特性 / 道具修正（依序乘除）**：

| 條件 | 效果 |
|:---|:---|
| 複眼（Compound Eyes）| ×130% |
| 沙塵遮蔽（Sand Veil）+ 沙暴 | ×80%（防禦方）|
| 速攻（Hustle）+ 物理招式 | ×80%（攻擊方）|
| 持有迴避類道具 | ×(100-param)% |
| 晴天 + 雷電（Thunder）| 固定 moveAcc = 50 |

最終：`if (Random() % 100 + 1) > calc → MOVE_RESULT_MISSED`

---

## 暴擊判定 — `Cmd_critcalc`（`src/battle_script_commands.c:1253`）

```c
critChance  = 2 * (STATUS2_FOCUS_ENERGY)   // 精力充沛 +2
            + (EFFECT_HIGH_CRITICAL)         // 高暴擊技能 +1
            + (EFFECT_SKY_ATTACK)
            + (EFFECT_BLAZE_KICK)
            + (EFFECT_POISON_TAIL)
            + (HOLD_EFFECT_SCOPE_LENS)       // 照準鏡 +1
            + 2*(HOLD_EFFECT_LUCKY_PUNCH && SPECIES_CHANSEY)  // +2
            + 2*(HOLD_EFFECT_STICK && SPECIES_FARFETCHD);     // +2

// 查表 sCriticalHitChance[]，Random() % table_value == 0 時暴擊
gCritMultiplier = 2; // 或 1
```

**免疫暴擊**：對手有 `ABILITY_BATTLE_ARMOR` / `ABILITY_SHELL_ARMOR`，或攻擊方有 `STATUS3_CANT_SCORE_A_CRIT`（Wally 教學戰）。

---

## 傷害計算公式 — `CalculateBaseDamage`（`src/pokemon.c:3106`）

**輸入**：攻擊方 `BattlePokemon`、防禦方 `BattlePokemon`、招式、場地狀態、威力覆蓋值、屬性覆蓋值。

### 修正順序（物理招式為例）

```
attack_stat
  ×2   若 ABILITY_HUGE_POWER / ABILITY_PURE_POWER
  ×1.1 若已獲第1徽章（Boulder Badge）
  ×1.5 若 ABILITY_HUSTLE
  ×1.5 若 ABILITY_GUTS + 異常狀態
  ×(type_boost_item)  持有加成同類型道具

defense_stat
  ×1.1 若已獲第5徽章（Balance Badge）
  ×1.5 若 ABILITY_MARVEL_SCALE + 異常狀態
  ÷2   若防禦方 ABILITY_THICK_FAT + 火/冰屬性

move_power（gBattleMovePower）
  ÷2   若 Mud Sport（電屬性）/ Water Sport（火屬性）場地效果
  ×1.5 若起始特性（Overgrow/Blaze/Torrent/Swarm）+ HP≤1/3 + 對應屬性
  ... 其他特殊道具/特性修正

// 最終公式（Gen III 標準）：
damage = (2 * level / 5 + 2) * power * attack / defense / 50 + 2;
```

---

## 屬性相剋計算 — `Cmd_typecalc`（`src/battle_script_commands.c:1355`）

```c
// 1. STAB（同屬性加成）
if (IS_BATTLER_OF_TYPE(attacker, moveType))
    damage = damage * 15 / 10;  // ×1.5

// 2. 飄浮特性免疫地面
if (defender.ability == ABILITY_LEVITATE && moveType == TYPE_GROUND)
    → MOVE_RESULT_MISSED | DOESNT_AFFECT_FOE

// 3. 查屬性相剋表（TYPE_EFFECT_ATK_TYPE / DEF_TYPE 三元組）
while (TYPE_EFFECT_ATK_TYPE(i) != TYPE_ENDTABLE):
    ModulateDmgByType(multiplier):
        ×0  (TYPE_MUL_NO_EFFECT)    → MOVE_RESULT_DOESNT_AFFECT_FOE
        ×5  (TYPE_MUL_NOT_EFFECTIVE) → MOVE_RESULT_NOT_VERY_EFFECTIVE
        ×20 (TYPE_MUL_SUPER_EFFECTIVE) → MOVE_RESULT_SUPER_EFFECTIVE
        (* 均以 /10 為基底，即 ×0.5 / ×2)
```

雙屬性對手需走完全表，效果可疊加（×4 或 ×0.25）。

---

## 戰鬥腳本控制流指令

| 指令 | 功能 |
|:---|:---|
| `Cmd_goto` | 無條件跳轉（同 JMP）|
| `Cmd_call` | 呼叫子腳本（push 返回地址到 BS stack）|
| `Cmd_return` | 返回（pop BS stack）|
| `Cmd_end` / `Cmd_end2` | 結束腳本 |
| `Cmd_jumpifbyte/halfword/word` | 比較值後跳轉 |
| `Cmd_jumpifstatus/status2/status3` | 依狀態旗標跳轉 |
| `Cmd_jumpifability` | 依特性跳轉 |
| `Cmd_jumpifstat` | 依能力等級跳轉 |
| `Cmd_pause` | 暫停 N 幀 |
| `Cmd_waitstate` | 等待控制器回應（多幀協作）|

---

## 附加效果施加

```c
// Cmd_seteffectwithchance：
// 讀取 gBattleScripting.moveEffect，依機率套用
// 機率由招式資料 gBattleMoves[move].secondaryEffectChance 決定

// Cmd_seteffectprimary / Cmd_seteffectsecondary：
// 強制套用主要/次要效果（不走機率判定）
```

效果 ID 定義於 `constants/battle_move_effects.h`（EFFECT_BURN、EFFECT_SLEEP...）。
