# pokeemerald — Level 6：VBlank 渲染管線 / OAM Sprite 系統 / M4A 音效引擎

---

## 一、每幀渲染時序（主迴圈 × VBlank 協作）

GBA 的渲染採用雙階段設計：主迴圈準備資料，VBlank 中斷安全寫入硬體。

```
┌─────────────────────────────────────────────────────────┐
│  主迴圈（CPU 執行期，掃描線繪製中，此時不可寫 OAM/VRAM）  │
│                                                          │
│  CallCallbacks()                                         │
│    └─ gMain.callback1() + gMain.callback2()              │
│         └─ AnimateSprites()   ← Sprite callback + 動畫   │
│         └─ BuildOamBuffer()   ← 座標計算→排序→填充緩衝   │
│  WaitForVBlank()              ← 等待 VBlank 訊號          │
└─────────────────────────────────────────────────────────┘
                        ↓ VBLANK 中斷觸發（每 1/60 秒）
┌─────────────────────────────────────────────────────────┐
│  VBlankIntr()（src/main.c:340）                          │
│                                                          │
│  1. RfuVSync() / LinkVSync()       無線/有線通訊同步      │
│  2. gMain.vblankCounter1++         幀計數器               │
│  3. gMain.vblankCallback()         場景 VBlank 回調       │
│       └─ LoadOam()                 ← OAM 緩衝→硬體 OAM   │
│  4. gMain.vblankCounter2++                               │
│  5. CopyBufferedValuesToGpuRegs()  GPU 暫存器安全更新     │
│  6. ProcessDma3Requests()          DMA 請求批次處理       │
│  7. gPcmDmaCounter 同步           音效 DMA 計數           │
│  8. m4aSoundMain()                 M4A 音效主更新         │
│  9. TryReceiveLinkBattleData()     連線戰鬥資料接收       │
│  10. Random()                      自動推進 RNG（非連線） │
│  11. UpdateWirelessStatusIndicatorSprite()               │
└─────────────────────────────────────────────────────────┘
                        ↓ VCount 中斷（第 150 條掃描線）
┌─────────────────────────────────────────────────────────┐
│  VCountIntr()（src/main.c:388）                          │
│  1. gMain.vcountCallback()    視差捲動、掃描線效果        │
│  2. m4aSoundVSync()           M4A 精確時序同步            │
└─────────────────────────────────────────────────────────┘
```

**為何要等 VBlank？**  
GBA 顯示電路在掃描線繪製期間（VDraw，160條線）讀取 OAM/VRAM，此時 CPU 寫入會造成閃爍。VBlank（68條空白線，約 1.23ms）是唯一安全的寫入窗口。

---

## 二、Sprite / OAM 系統 — `src/sprite.c`

### 2.1 核心資料結構

```c
// include/sprite.h

struct SpriteTemplate {    // 唯讀「藍圖」，通常為 const ROM 資料
    u16 tileTag;           // VRAM tile 資源 tag
    u16 paletteTag;        // 調色板資源 tag
    const struct OamData *oam;   // 形狀/大小/模式
    const union AnimCmd *const *anims;       // 動畫序列表
    const struct SpriteFrameImage *images;  // 幀圖形資料
    const union AffineAnimCmd *const *affineAnims; // 旋轉/縮放動畫
    SpriteCallback callback;    // 每幀呼叫的邏輯函數
};

struct Sprite {            // 可變「實例」，EWRAM 中的 gSprites[]
    struct OamData oam;    // 直接對應 GBA 硬體 OAM 格式（8 bytes）
    // ...動畫指標同上...
    SpriteCallback callback;
    s16 x, y;             // 世界座標
    s16 x2, y2;           // 動畫偏移（震動、彈跳等）
    s8  centerToCornerVecX/Y;  // 旋轉中心偏移
    u8  animNum, animCmdIndex; // 當前動畫序號與指令索引
    s16 data[8];          // 通用資料（等同 Task.data，供 callback 使用）
    bool16 inUse:1;
    bool16 invisible:1;
    bool16 coordOffsetEnabled:1; // 是否套用 gSpriteCoordOffsetX/Y（鏡頭偏移）
    bool16 hFlip:1, vFlip:1;
    u16 sheetTileStart;   // 在 VRAM 中的起始 tile 編號
    u8  subpriority;      // OAM 排序用（0=最高）
};

// 全域陣列
extern struct Sprite gSprites[MAX_SPRITES + 1]; // MAX_SPRITES = 64（EWRAM）
// 硬體 OAM 緩衝
gMain.oamBuffer[128];   // 每幀複製至 0x07000000（IWRAM）
```

### 2.2 每幀 Sprite 更新流程

```
AnimateSprites()（src/sprite.c:308）
  for each gSprites[i]:
    sprite->callback(sprite)   ← 業務邏輯（移動、狀態機）
    AnimateSprite(sprite)      ← 推進動畫指令（AnimCmd_frame/end/jump/loop）

BuildOamBuffer()（src/sprite.c:325）
  1. UpdateOamCoords()
     sprite.oam.x = x + x2 + centerToCornerVecX [+ gSpriteCoordOffsetX]
     sprite.oam.y = y + y2 + centerToCornerVecY [+ gSpriteCoordOffsetY]

  2. BuildSpritePriorities()
     priority[i] = (oam.priority << 8) | subpriority

  3. SortSprites()  ← 插入排序（數字小 = 優先繪製在前）
     secondary key: Y 座標（用於偽3D層次感）

  4. AddSpritesToOamBuffer()
     依排序結果填入 gMain.oamBuffer[0..127]

  5. CopyMatricesToOamBuffer()
     將 Affine Matrix（旋轉/縮放 2×2 矩陣）嵌入 OAM 格式

  ← 設 sShouldProcessSpriteCopyRequests = TRUE

LoadOam()（VBlank 中）
  CpuCopy32(gMain.oamBuffer, (void*)OAM, sizeof(oamBuffer))
  // 128 個 OamData × 8 bytes = 1KB，一次 DMA-like 複製

ProcessSpriteCopyRequests()（VBlank 中）
  將新的 Sprite tile 資料從 ROM 複製到 VRAM Obj 區
```

### 2.3 Sprite Tile 分配

```c
// 點陣圖分配器（src/sprite.c）
sSpriteTileAllocBitmap[]   // 位元追蹤 VRAM OBJ 區的 tile 佔用狀況

AllocSpriteTiles(count):
  從 gReservedSpriteTileCount 開始，找 count 個連續空閒 tile
  標記並返回起始 index

FREE_SPRITE_TILE(n) / ALLOC_SPRITE_TILE(n):
  位元操作 sSpriteTileAllocBitmap[n/8] |= (1 << (n%8))

gReservedSpriteTileCount:
  保留給靜態 SpriteSheet 使用（不參與動態分配）
```

### 2.4 Affine 旋轉縮放矩陣

```c
gOamMatrices[OAM_MATRIX_COUNT]（struct OamMatrix）：
  s16 a, b, c, d   // 2×2 固定小數點矩陣（0x100 = 1.0）

ResetOamMatrices()：
  a=0x0100, b=0, c=0, d=0x0100   // 單位矩陣（無縮放無旋轉）

SetOamMatrix(matrixNum, a, b, c, d)：
  // 演化動畫、技能動畫中的放大/縮小效果
  // Double-size Affine Sprite 模式用於超出正常邊界的縮放
```

---

## 三、M4A 音效引擎（MKS4AGB）

### 3.1 引擎識別

- **開發者**：Smilesoft（SMASH）的 MKS4AGB 系統
- **識別碼**：`gSoundInfo.ident = 0x68736D53`（ASCII 'Smsh' 反序）
- **架構**：軟體混音 PCM DirectSound（透過 GBA DMA1/2 輸出）+ CGB 硬體音效

### 3.2 核心資料結構（`include/gba/m4a_internal.h`）

```c
struct SoundInfo（gSoundInfo）：
  maxChans        ← 同時最多幾個 DirectSound 通道
  masterVolume    ← 全局音量（0~15）
  freq            ← PCM 取樣率（SOUND_MODE_FREQ_* 常數，5734~42048 Hz）
  reverb          ← 殘響強度
  chans[MAX_DIRECTSOUND_CHANNELS]  ← DirectSound 通道狀態陣列
  pcmBuffer[PCM_DMA_BUF_SIZE * 2] ← 雙緩衝（Ping-Pong PCM）
  musicPlayerHead ← MusicPlayerInfo 連結串列

struct ToneData（音色定義）：
  type: CGB硬體音/Fix固定頻/SPL分割音色/RHY打擊音
  key, pan_sweep
  wav*: WaveData（PCM 樣本：loopStart, size, data[]）
  attack/decay/sustain/release  ← ADSR 包絡參數（0~255）

struct SongHeader（曲目標頭）：
  trackCount   ← MIDI 音軌數
  priority     ← 搶佔優先序（高優先曲目可打斷低優先）
  reverb       ← 曲目殘響
  tone*        ← 音色表指標
  part[]       ← 各音軌位元組碼指標
```

### 3.3 更新時機

| 函數 | 觸發點 | 職責 |
|:---|:---|:---|
| `m4aSoundVSync()` | VCount 中斷（掃描線 150）| 精確時序：準備下一幀 PCM 緩衝 |
| `m4aSoundMain()` | VBlank 中斷 | 解讀 MIDI 事件、觸發音符、混音 |
| `m4aSoundInit()` | `AgbMain()` 啟動時 | 初始化整個 M4A 引擎 |

### 3.4 地圖音樂管理（`src/sound.c`）

```c
// 地圖音樂狀態機（sMapMusicState）
MapMusicMain()：
  state 0: 靜止
  state 1: PlayBGM(currentMapMusic)   → state 2（播放新地圖音樂）
  state 5: FadeOutBGM()               → state 6（等待淡出完成）
  state 6: 確認 IsBGMStopped()       → state 1（啟動新曲）

// 過場淡入速度由 sMapMusicFadeInSpeed 控制
```

### 3.5 寶可夢叫聲 BGM 閃避

```c
// 播放叫聲時自動降低背景音樂音量
Task_DuckBGMForPokemonCry(taskId)：
  gMPlay_PokemonCry = 獨立的 MusicPlayerInfo
  gPokemonCryBGMDuckingCounter 計數叫聲結束後的等待幀數
  RestoreBGMVolumeAfterPokemonCry()：計數到0後恢復原始音量
```

### 3.6 小曲（Fanfare）系統

```c
// src/sound.c
static const struct Fanfare sFanfares[] = {
    [FANFARE_LEVEL_UP]       = { MUS_LEVEL_UP,       80  },  // 80幀
    [FANFARE_OBTAIN_ITEM]    = { MUS_OBTAIN_ITEM,    160  },
    [FANFARE_EVOLVED]        = { MUS_EVOLVED,        220  },
    [FANFARE_OBTAIN_BADGE]   = { MUS_OBTAIN_BADGE,   340  },
    [FANFARE_AWAKEN_LEGEND]  = { MUS_AWAKEN_LEGEND,  710  },
    // 共 18 種小曲
};
// 持續時間計算：MIDI 時長（秒） × 59.7275（GBA 實際幀率） → 無條件進位
// Task_Fanfare 計數幀數到 duration 後回復 BGM
```

---

## 附錄：GBA 背景系統（BG）概覽

```
GBA 有 4 個背景層（BG0~BG3），各可設定：
  - 捲動偏移（scroll X/Y）
  - 優先序（0最高）
  - Tilemap 位址（VRAM）
  - Tileset 位址（VRAM）
  - 顯示模式（Text/Affine/Bitmap）

src/bg.c 管理：
  ResetBgs()          → 清零所有背景設定
  SetBgMode(mode)     → 切換 BG 模式（Mode 0 = 4個 Text BG）
  ShowBg(bgNum)       → 啟用背景層顯示
  CopyToBgTilemapBuffer → 複製地圖資料到緩衝區
  ScheduleBgCopyTilemapToVram → VBlank 時透過 DMA 安全複製
  
src/gpu_regs.c：
  CopyBufferedValuesToGpuRegs()
  // 在 VBlank 中才安全寫入 REG_BG*CNT, REG_BG*HOFS, REG_BG*VOFS 等硬體暫存器
```
