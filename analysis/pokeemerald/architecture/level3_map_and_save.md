# pokeemerald — Level 3：地圖系統與存檔系統

---

## 一、地圖（Fieldmap）系統

### 1.1 地圖資料結構

```
MapHeader（gMapHeader）
├── mapLayout*         → MapLayout（靜態地圖佈局）
│     ├── width, height  地圖格數
│     ├── border[4]      越界時顯示的邊框 Metatile
│     ├── primaryTileset*   主圖塊集
│     ├── secondaryTileset* 副圖塊集
│     └── map[]           u16 陣列，每格存 Metatile ID（11位）+ 碰撞屬性
├── events*            → 地圖事件（物件/翹板/背景/連線點）
├── mapScripts*        → OnLoad/OnTransition/OnResume 腳本
└── connections*       → 相鄰地圖連接資料
```

**工作地圖（gBackupMapLayout）**：
```c
// src/fieldmap.c:25
EWRAM_DATA struct BackupMapLayout gBackupMapLayout;
// 實際大小 = (width + MAP_OFFSET_W) × (height + MAP_OFFSET_H)
// MAP_OFFSET 是每邊多出的邊界格（用於填入相鄰地圖資料）
```

### 1.2 Metatile 格式（u16）

```
Bits [10:0]  = Metatile ID（0~2047，最多 0x800個）
Bits [15:11] = MAPGRID_COLLISION_MASK（碰撞 + 通道層級）
MAPGRID_IMPASSABLE = 0xC000 → 完全不可通行（邊界外）
```

### 1.3 地圖初始化流程

```c
// src/fieldmap.c
InitMap()
  ├── InitMapLayoutData(&gMapHeader)    ← 清空工作地圖、填入主地圖資料
  │     ├── CpuFastFill16(MAPGRID_UNDEFINED, sBackupMapData)
  │     ├── InitBackupMapLayoutData()  ← 複製主地圖 metatile 到工作緩衝
  │     └── InitBackupMapLayoutConnections()  ← 填充4方向相鄰地圖邊緣
  ├── SetOccupiedSecretBaseEntranceMetatiles()
  └── RunOnLoadMapScript()
```

**地圖連接填充**（4方向）：
```c
FillSouthConnection(mapHeader, connectedHeader, offset)
FillNorthConnection(...)
FillEastConnection(...)
FillWestConnection(...)
// 將相鄰地圖的邊緣 Metatile 複製到 gBackupMapLayout 的邊界區
// 使玩家走到邊緣時畫面能平滑捲動到下一張地圖
```

### 1.4 Metatile Behavior（地形行為）

每個 Metatile 有對應的 `behavior byte`（u8），查詢方式：
```c
// 從 metatile ID → tileset → behavior 表查詢
MetatileBehavior_IsEncounterTile(behavior)  → 會觸發野生寶可夢
MetatileBehavior_IsSurfableWaterOrUnderwater() → 可衝浪
MetatileBehavior_IsJumpSouth() → 跳崖（南向）
MetatileBehavior_IsIce()       → 冰地板（滑動）
MetatileBehavior_IsWarpDoor()  → 傳送門
MetatileBehavior_IsNorthwardCurrent() → 水流（洞窟激流）
MetatileBehavior_IsCounter()   → 商店櫃台（互動）
MetatileBehavior_IsPC()        → 電腦（儲存/箱子）
```

共約 60+ 種行為類型，定義於 `constants/metatile_behaviors.h`。

### 1.5 特殊地圖

| 地圖 | 函數 | 說明 |
|:---|:---|:---|
| 對戰金字塔 | `InitBattlePyramidMap()` | `GenerateBattlePyramidFloorLayout()` 程序生成 |
| 訓練師山丘 | `InitTrainerHillMap()` | `GenerateTrainerHillFloorLayout()` 程序生成 |
| 一般地圖 | `InitMap()` | 讀取固定佈局資料 |

---

## 二、存檔系統（Save System）

### 2.1 Flash 記憶體佈局（32 個 4KB Sector）

```
Sector  0       SaveBlock2              （訓練師資料：姓名/ID/時間等）
Sector  1-4     SaveBlock1              （地圖、事件、物品、隊伍等）
Sector  5-13    PokemonStorage          （寶可夢圖鑑倉庫 Box 1-18）
--- 存檔槽 2（與槽1輪替）---
Sector  14-27   同上結構（第二存檔槽）
--- 特殊扇區 ---
Sector  28-29   名人堂（Hall of Fame）
Sector  30      訓練師山丘紀錄
Sector  31      對戰錄影資料
```

### 2.2 雙槽輪替策略

```c
// src/save.c
// 每次存檔交替使用 Slot 1 / Slot 2
// 讀取時比較兩槽的 sector.counter，取較大值（較新）

// Sector 旋轉：同一槽內的 14 個 sector 每次存檔旋轉起始 ID
// 目的：平均磨損 Flash 寫入壽命
```

### 2.3 Sector 結構

```c
struct SaveSector {
    u8  data[3968];          // 實際資料（SECTOR_DATA_SIZE）
    u8  unused[116];         // Footer 未使用空間
    u16 id;                  // Sector ID
    u16 checksum;            // 資料 checksum
    u32 signature;           // 0x8012025（固定魔法值）
    u32 counter;             // 存檔計數（用於判斷新舊）
};  // 共 4096 bytes（0x1000）
```

### 2.4 存檔資料結構

```
SaveBlock2（1 sector，≤3968 bytes）：
  訓練師名字、ID、祕密ID、遊玩時間、Pokédex、選項設定、Battle Frontier Points...

SaveBlock1（4 sectors，最多 15872 bytes）：
  隊伍寶可夢、背包物品、地圖位置、事件旗標（Flags）、事件變數（Vars）、
  Pokéblock、大地道具、秘密基地、時鐘資料、TV節目...

PokemonStorage（9 sectors）：
  Box 1-18 的所有 BoxPokemon 資料（每箱 30 隻 × 80 bytes）
```

### 2.5 存檔觸發類型

```c
// src/save.c（SAVE_* 列舉）
SAVE_NORMAL           → 一般遊戲內存檔（選單 Save）
SAVE_LINK             → 聯機 / 對戰設施用（不存地圖）
SAVE_HALL_OF_FAME     → 破關後存入名人堂 Sector 28-29
SAVE_OVERWRITE_DIFFERENT_FILE → 新遊戲覆寫存檔
```

### 2.6 存檔完整性驗證

```c
static u16 CalculateChecksum(void *data, u16 size)
// 對 data 每 4 bytes 做加總，取低 16 位
// 存入 sector.checksum

GetSaveValidStatus()
// 遍歷 14 個 sector，驗證 signature + checksum
// 返回 SAVE_STATUS_OK / CORRUPT / EMPTY / NO_FLASH
```

存在損毀時自動 fallback 到另一存檔槽，保障資料安全。

---

## 附錄：地圖資料資料夾結構

```
data/maps/<GroupName>_<MapName>/
├── map.json          Tilemap 資料（由工具轉換為 .c）
├── events.inc        物件/翹板/背景/Warp 事件定義
└── scripts.inc       地圖腳本（引用 data/event_scripts.s）

data/layouts/
  每個佈局 ID 對應一個 MapLayout 結構（width/height/tileset 指標）

data/tilesets/
  primaryTileset / secondaryTileset 的圖塊 + 行為表
```
