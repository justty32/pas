# pokeemerald — Level 7：腳本指令集 / 事件系統 / 天氣效果 / 自行車物理

---

## 一、腳本指令集（Event Script VM）— `src/scrcmd.c`

### 1.1 概覽

共 **220 個 `ScrCmd_*` 指令**，2307 行，為事件腳本（`data/event_scripts.s`）的虛擬機實現。

每個指令函數簽名為 `bool8 ScrCmd_xxx(struct ScriptContext *ctx)`：
- 返回 `FALSE`：繼續執行下一條指令（同一幀）
- 返回 `TRUE`：暫停腳本（等待外部事件，下幀繼續）

### 1.2 指令分類速覽

#### 流程控制
```
goto(ptr)           → ScriptJump(ctx, ptr)
call(ptr)           → ScriptCall(ctx, ptr)  ← push 返回地址
return              → ScriptReturn(ctx)      ← pop 返回地址
end                 → StopScript()
goto_if(cond, ptr)  → sScriptConditionTable[cond][comparisonResult] 決定是否跳轉
waitstate           → ScriptContext_Stop() + return TRUE  ← 暫停等待
```

#### 動態定址（用於 Mystery Event 相對位址）
```
vgoto   → 從 sAddressOffset 偏移計算目標地址後跳轉
vcall   → 同上但呼叫子腳本
setvaddress → 設定 sAddressOffset（讀 u32）
```

#### 標準腳本庫呼叫
```
gotostd(id)   → 跳轉到 gStdScripts[id]（常用流程如 msgbox、yesnobox）
callstd(id)   → 呼叫 gStdScripts[id] 子腳本
```

#### 特殊函數橋接
```c
// ScrCmd_special（src/scrcmd.c:118）
index = ScriptReadHalfword(ctx);
gSpecials[index]();         // 無返回值

// ScrCmd_specialvar
*var = gSpecials[index]();  // 有返回值，存入指定 Var

// ScrCmd_callnative
func = (NativeFunc)ScriptReadWord(ctx);
func();                     // 直接呼叫 C 函數指標（4字節ROM地址）
```

`gSpecials[]`：`data/specials.inc` 定義的函數指標表，包含各種遊戲功能（治療、Pokédex 操作、地形變更...）。

#### 旗標 / 變數操作

```c
ScrCmd_setflag   → FlagSet(ScriptReadHalfword(ctx))
ScrCmd_clearflag → FlagClear(...)
ScrCmd_checkflag → comparisonResult = FlagGet(...)

ScrCmd_setvar(var, val)    → *GetVarPointer(var) = val
ScrCmd_copyvar(dst, src)   → *GetVarPointer(dst) = *GetVarPointer(src)
ScrCmd_compare_local_to_value → comparisonResult 設定（供 goto_if 使用）
```

**Flag 儲存**：`gSaveBlock1Ptr->flags[]`（位元陣列，數千個旗標）  
**Var 儲存**：`gSaveBlock1Ptr->vars[]`（u16 陣列，300+ 個變數）

#### 對話 / UI
```
message(textptr)        → 開始顯示訊息框（SetupNativeScript 等待輸入）
messageautoscroll       → 自動捲動訊息
msgbox（gotostd）       → 標準訊息框+等待確認
yesnobox（gotostd）     → 是/否選擇框
waitmessage             → 等待訊息框關閉
```

#### 傳送 Warp
```
warp(mapGroup, mapNum, warpId, x, y)    → 一般門傳送（黑屏切換）
warpsilent                              → 無音效傳送
warpdoor                                → 開門動畫後傳送
warphole                                → 落坑（洞窟洞口）傳送
warpteleport                            → 瞬間移動招式傳送
warpspinenter                           → 旋轉進入（秘密基地）
warpwhitefade                           → 白屏淡出後傳送（聖地等）
```

#### 訓練師戰鬥
```
trainerbattle(type, trainerId, varFlag, ...)
dotrainerbattle     → 實際啟動戰鬥（設置 CB2_InitBattleInternal）
checktrainerflag    → 查訓練師是否已被擊敗（TRAINER_FLAGS 位元陣列）
settrainerflag      → 設「已擊敗」
cleartrainerflag    → 重置為可再戰
```

#### 其他關鍵指令
```
setmetatile(x, y, metatileId, collision)  → 動態修改地圖格子（如解謎後改變地形）
opendoor / closedoor / waitdooranim       → 門開關動畫管理
dofieldeffect(effectId)                   → 觸發場地效果（如切草、水波紋...）
playmoncry / waitmoncry                   → 播放寶可夢叫聲 + 等待
setberrytree(treeId, species, stage)      → 設定樹莓樹狀態
initrotatingtilepuzzle                    → 初始化旋轉磁磚謎題（磁力道館）
```

---

## 二、天氣效果系統 — `src/field_weather.c`

### 2.1 天氣類型與對應實作

```c
// include/constants/weather.h
WEATHER_NONE               = 0
WEATHER_SUNNY_CLOUDS       = 1  // 雲朵移動
WEATHER_SUNNY              = 2  // 日照（調色板偏黃）
WEATHER_RAIN               = 3  // 雨滴 Sprite + 調色板暗化
WEATHER_SNOW               = 4  // 雪花 Sprite（未使用）
WEATHER_RAIN_THUNDERSTORM  = 5  // 暴風雨 + 閃電
WEATHER_FOG_HORIZONTAL     = 6  // 水平霧（BG blend）
WEATHER_VOLCANIC_ASH       = 7  // 火山灰 Sprite（Mt. Chimney）
WEATHER_SANDSTORM          = 8  // 沙塵暴 Sprite + 螺旋效果
WEATHER_FOG_DIAGONAL       = 9  // 斜霧（未使用）
WEATHER_UNDERWATER         = 10 // 水中（未使用，等同水平霧）
WEATHER_SHADE              = 11 // 陰天（原名 OVERCAST）
WEATHER_DROUGHT            = 12 // 乾旱（烈日 LUT 調色板）
WEATHER_DOWNPOUR           = 13 // 豪雨（暴風雨 Main + 豪雨 Init）
WEATHER_UNDERWATER_BUBBLES = 14 // 水下氣泡（天空之柱）
WEATHER_ABNORMAL           = 15 // 交互異常天氣（古雷/蓋歐卡衝突）
WEATHER_ROUTE119_CYCLE     = 20 // 119路的循環天氣
WEATHER_ROUTE123_CYCLE     = 21 // 123路的循環天氣
```

### 2.2 天氣函數表架構

```c
// src/field_weather.c:85
static const struct WeatherCallbacks sWeatherFuncs[] = {
    [WEATHER_XXX] = {
        .initVars = Xxx_InitVars,  // 快速初始化（用於切換開始時）
        .main     = Xxx_Main,      // 每幀驅動（粒子/Sprite 更新）
        .initAll  = Xxx_InitAll,   // 完整初始化（地圖初次載入時）
        .finish   = Xxx_Finish,    // 淡出/清理（返回 bool8，TRUE 表示完成）
    },
};
```

### 2.3 天氣狀態機（`Task_WeatherMain`）

```
Task_WeatherInit（Priority 80）
  → 等待 readyForInit = TRUE（地圖初始化完成後）
  → 呼叫 initAll()

Task_WeatherMain（每幀）：
  palProcessingState 狀態機：
    CHANGING_WEATHER:
      finish() 返回 TRUE → 當前天氣清理完成
        → initVars(nextWeather)   ← 開始新天氣的變數初始化
      main(currWeather) 每幀驅動

    SCREEN_FADING_IN:
      FadeInScreenWithWeather()   ← 進入地圖時的淡入效果
        針對不同天氣有特化淡入（Rain/Drought/FogH 各一）

    SCREEN_FADING_OUT / IDLE:
      DoNothing()
```

### 2.4 調色板色彩映射

```c
// 全32個調色板（16 BG + 16 Sprite）的對應類型
sBasePaletteColorMapTypes[32]:
  BG 0-13   → COLOR_MAP_DARK_CONTRAST（天氣影響背景）
  BG 14-15  → COLOR_MAP_NONE（UI不受天氣影響）
  Sprite 0  → COLOR_MAP_CONTRAST
  Sprite 1  → COLOR_MAP_DARK_CONTRAST
  ...（依具體調色板用途決定）

// 應用函數：
ApplyColorMap(startPalIndex, numPals, colorMapIndex)
ApplyColorMapWithBlend(startPalIndex, numPals, colorMapIndex, blendCoeff, blendColor)
ApplyFogBlend(blendCoeff, blendColor)          // 霧的 alpha 混色
```

### 2.5 乾旱天氣（DROUGHT）特殊處理

```c
// 預計算查詢表（rom data，共 6組 × 4096 colors）：
static const u16 sDroughtWeatherColors[][0x1000] = {
    INCBIN_U16("graphics/weather/drought/colors_0.bin"),
    ...  // colors_0 ~ colors_5
};
// 每組代表乾旱強度不同階段的完整調色板轉換表
// ApplyDroughtColorMapWithBlend 直接查表，效能遠優於即時計算 RGB 偏移

#define DROUGHT_COLOR_INDEX(color) (((color >> 1) & 0xF) | ((color >> 2) & 0xF0) | ((color >> 3) & 0xF00))
```

---

## 三、自行車物理系統 — `src/bike.c`

### 3.1 兩種自行車統一入口

```c
// src/bike.c:127
void MovePlayerOnBike(u8 direction, u16 newKeys, u16 heldKeys)
{
    if (PLAYER_AVATAR_FLAG_MACH_BIKE)  → MovePlayerOnMachBike()
    else                               → MovePlayerOnAcroBike()
}
```

---

### 3.2 跑車腳踏車（Mach Bike）— 速度累積機制

**速度狀態**：

| `bikeFrameCounter` | 速度（`bikeSpeed`）| 移動函數 |
|:---:|:---:|:---|
| 0 | 0（`PLAYER_SPEED_STANDING`）| 靜止 |
| 0 | 1（`PLAYER_SPEED_NORMAL`）| `PlayerWalkNormal`（1格/幀）|
| 1 | 1（`PLAYER_SPEED_FAST`）| `PlayerWalkFast`（每2幀移2格）|
| 2 | 3（`PLAYER_SPEED_FASTEST`）| `PlayerWalkFaster`（每幀2格）|

```c
// 加速公式（src/bike.c:238）
bikeSpeed = bikeFrameCounter + (bikeFrameCounter >> 1);  // ×1.5
// counter 0 → speed 0, counter 1 → speed 1, counter 2 → speed 3

// 加速：每幀 bikeFrameCounter++ (上限 2)
// 減速：bikeFrameCounter = --bikeSpeed（遇牆或放開方向鍵）
```

**狀態轉換表（`sMachBikeTransitions[]`）**：

```
MACH_TRANS_FACE_DIRECTION  → MachBikeTransition_FaceDirection
  僅改變朝向，不播轉向音效

MACH_TRANS_TURN_DIRECTION  → MachBikeTransition_TurnDirection
  改向 + 播音效；若前方不能騎（窄路）則 FaceDirection

MACH_TRANS_START_MOVING（→ keep moving）
MACH_TRANS_KEEP_MOVING     → MachBikeTransition_TrySpeedUp
  無碰撞 → 呼叫 sMachBikeSpeedCallbacks[bikeFrameCounter] + bikeFrameCounter++
  碰撞（非崖壁）→ TrySlowDown；崖壁跳躍 → PlayerJumpLedge

MACH_TRANS_SLOW_DOWN       → MachBikeTransition_TrySlowDown
  bikeSpeed-- → 繼續移動但速度降低；若歸零則靜止
```

---

### 3.3 特技腳踏車（Acro Bike）— 輸入歷史機制

**13種動作轉換（`sAcroBikeTransitions[]`）**：

```
FaceDirection      轉向但不移動
TurnDirection      轉向（有碰撞判定）
Moving             一般行走
NormalToWheelie    前輪抬起開始（靜止+按B）
WheelieToNormal    前輪放下
WheelieIdle        靜止翹輪狀態
WheelieHoppingStanding  靜止跳（翹輪+按B）
WheelieHoppingMoving    移動跳（翹輪+按B）
SideJump           側跳（跨越2格窄台）
TurnJump           轉向跳
WheelieMoving          翹輪移動
WheelieRisingMoving    翹輪上升中移動
WheelieLoweringMoving  翹輪下降中移動
```

**7種輸入處理器（`sAcroBikeInputHandlers[]`）**：
```
AcroBikeHandleInputNormal          一般狀態
AcroBikeHandleInputTurning         轉向中
AcroBikeHandleInputWheelieStanding 靜止翹輪
AcroBikeHandleInputBunnyHop        兔跳（連按跳組合）
AcroBikeHandleInputWheelieMoving   移動翹輪
AcroBikeHandleInputSidewaysJump    側向跳躍
AcroBikeHandleInputTurnJump        轉向跳躍
```

**按鍵歷史（`Bike_TryAcroBikeHistoryUpdate`）**：
```c
// 追蹤最近N幀的按鍵輸入
// 用於判斷 Bunny Hop 時機（靜止翹輪時連按B）
// 4幀計時器：sAcroBikeJumpTimerList = {4, 0}
```

---

## 四、玩家移動強制行為（Forced Movement）— `src/field_player_avatar.c`

```c
// 18 種地形強制移動（NUM_FORCED_MOVEMENTS = 18）
static bool8 (*const sForcedMovementFunctions[])() = {
    ForcedMovement_None,
    ForcedMovement_Slip,              // 滑倒（沙地）
    ForcedMovement_WalkSouth/North/West/East,  // 單向走道
    ForcedMovement_PushedXxxByCurrent, // 4方向水流
    ForcedMovement_SlideXxx,           // 4方向滑動（冰地板）
    ForcedMovement_MatJump,            // 跳台
    ForcedMovement_MatSpin,            // 旋轉地板（Trick House）
    ForcedMovement_MuddySlope,         // 泥濘斜坡（上坡慢/下坡滑）
};

// 由 GetForcedMovementByMetatileBehavior() 根據腳下 Metatile 的 behavior 決定
// TryDoMetatileBehaviorForcedMovement() 每步後呼叫
```

**玩家移動碰撞判定**（`CheckForPlayerAvatarCollision`）：
- 靜態碰撞（牆/物件/水）
- 崖壁跳躍（`ShouldJumpLedge`）
- 推石頭（`TryPushBoulder`）
- 停止衝浪（`CanStopSurfing`）

---

## 附錄：事件系統資料流

```
地圖事件觸發 → 腳本 Script (.s) → gScriptCmdTable[opcode]() 
→ ScrCmd_* 函數
  ├─ 讀 Flag（gSaveBlock1Ptr->flags[]）
  ├─ 讀/寫 Var（gSaveBlock1Ptr->vars[]）
  ├─ 呼叫 gSpecials[index]() → C 函數
  ├─ warp → 切換地圖（CB2_ReturnToField）
  └─ trainerbattle → 設定對手 → CB2_InitBattleInternal
```
