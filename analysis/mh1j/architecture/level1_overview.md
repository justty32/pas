# mh1j — Level 1 初始探索：專案概覽與技術棧

## 專案身份

- **全名**：Monster Hunter 1 Japan (SLPM_654.95)
- **平台**：PlayStation 2 (MIPS R5900 EE 處理器，小端序)
- **目標**：對 PS2 遊戲碟進行逐位元組匹配的反組譯重建 (matching decompilation)
- **現況**：早期階段，主 ELF 中僅少數函數已完成 C 語言反組譯，大部分仍為組語 (INCLUDE_ASM 宏)

---

## 技術棧 (Tech Stack)

### 編譯器鏈
| 工具 | 說明 |
|---|---|
| `MWCCPS2` (mwccps2.exe) | MetroWerks CodeWarrior PS2 編譯器，原始遊戲所用編譯器 |
| `MWLDPS2` (mwldps2.exe) | MetroWerks PS2 連結器 |
| `mips-ps2-decompals-as` | PS2 專用 MIPS 組譯器 (binutils fork) |
| `EEGCC` (ee-gcc 2.96) | Sony EE-GCC，用於 CRI 函式庫（原始碼使用不同編譯器） |
| `wibo` | 在 Linux 下執行 Windows .exe 的相容層 |

### 分析/拆分工具
| 工具 | 說明 |
|---|---|
| `splat64[mips]` | 核心二進位拆分器，依 YAML 設定將 ELF 拆成 .s/.c 及資料檔 |
| `mwccgap.py` | MWCC 包裝器，處理 C 原始碼到物件檔的編譯 |
| `funcrypt.py` | DNAS overlay 加/解密工具（反混淆索尼反盜版機制） |
| `packer.py` | 解包遊戲碟 AFS 資產封存 |
| `verify.py` | 逐位元組對比建置輸出與原始二進位 |
| `report.py` | 輸出反組譯進度統計 |
| `m2ctx.py` | 為 decomp.me 線上工具產生 C 上下文 |
| `generate_lcf.py` | 從設定產生 MetroWerks 連結腳本 (LCF) |

### 外部依賴
- `decomp.me`：線上 PS2 反組譯協作平台（選擇 Monster Hunter JP preset）
- Ghidra + `emotionengine-reloaded` 插件：輔助生成初始 C 推導
- Python 3.9+、splat v0.36.3

---

## 二進位架構：主 ELF + 6 個 Overlay

遊戲使用 **overlay 系統**在執行時動態載入不同模組到固定記憶體區段。

### 主 ELF：`SLPM_654.95`
- VRAM 基底：`0x100000`
- 大小：約 `0x28A080` 位元組 (≈2.6 MB)
- BSS 區段：`0x1A9900` 位元組

### 6 個遊戲 Overlay
| Overlay 名稱 | 載入地址 | 大小 | 說明 |
|---|---|---|---|
| `game.bin` | `0x533980` (overlaygroup) | 0x15B780 | 遊戲核心邏輯（狩獵場景） |
| `lobby.bin` | (overlaygroup: game) | 0x134E00 | 大廳/村莊場景 |
| `select.bin` | (overlaygroup: game) | 0x8000 | 角色/任務選擇畫面 |
| `yn.bin` | (overlaygroup: game) | 0xDD00 | Yes/No 確認對話框 |
| `dnas_net.bin` | `0xA06200` (overlaygroup: net) | 0xA1000 | DNAS 網路認證（加密） |
| `dnas_ins.bin` | (overlaygroup: net) | 0x31B00 | DNAS 安裝程序（加密） |

> DNAS (Digital Network Authentication System) = 索尼 PS2 線上防盜版驗證系統，兩個 DNAS overlay 在原始遊戲中使用函數級加密。

---

## 目錄結構

```
mh1j/
├── config/                  # splat YAML 設定 + 符號地址列表
│   ├── main.yaml            # 主 ELF 拆分設定 (sha1: 0e6b14fe...)
│   ├── game.yaml            # game overlay 設定
│   ├── lobby.yaml           # lobby overlay 設定
│   ├── select.yaml          # select overlay 設定
│   ├── yn.yaml              # yn overlay 設定
│   ├── dnas_ins.yaml        # DNAS 安裝 overlay 設定
│   ├── dnas_net.yaml        # DNAS 網路 overlay 設定
│   ├── *_symbol_addrs.txt   # 已識別符號地址
│   ├── *_funcs_auto.txt     # 自動偵測函數
│   └── cryptlist*.txt       # DNAS 加密函數列表
├── include/
│   ├── types.h              # 基本型別 (u8/s16/f32 等)
│   ├── structs.h            # 主要資料結構定義
│   ├── common.h             # 通用標頭
│   ├── include_asm.h        # INCLUDE_ASM 宏定義
│   ├── macro.inc            # 組語宏
│   └── labels.inc           # 組語標籤
├── src/
│   └── main/                # 已反組譯的 C 原始碼
│       ├── camera.c         # 攝影機系統（大部分仍為 INCLUDE_ASM）
│       ├── cardinit.c       # 記憶卡初始化
│       ├── load.c           # 載入系統
│       ├── math.c           # 數學函數
│       ├── prim.c           # 圖元渲染
│       ├── stage.c          # 場景/關卡
│       ├── vib.c            # 震動回饋
│       └── view.c           # 視角/視口
├── tools/
│   ├── funcrypt.py          # DNAS 加解密
│   ├── packer.py            # AFS 封存解包
│   ├── verify.py            # 位元組對比驗證
│   ├── report.py            # 進度報告
│   ├── asmelf.py            # ELF 組語工具
│   ├── afsenum.py           # AFS 列舉工具
│   ├── m2ctx.py             # decomp.me 上下文產生器
│   ├── lcf/generate_lcf.py  # 連結腳本產生器
│   └── mwccgap/mwccgap.py   # MetroWerks 編譯器包裝器
├── asm/                     # (由 make split 產生) 組語檔
├── build/                   # (由 make build 產生) 編譯輸出
├── overlays/                # 6 個 overlay 二進位原件
├── assets/AFS/              # 解包後的 AFS 資產
├── Makefile                 # 建置系統
└── readme                   # 專案說明文件
```

---

## 建置工作流程

```
make setup     → 解包 AFS_DATA.AFS + 下載編譯工具
make split     → splat 拆分 ELF → asm/*.s 檔，funcrypt.py 解密 DNAS overlay
make build     → 用 MWCCPS2 重新編譯所有 .c + 組譯所有 .s → 連結 ELF + overlay
               → verify.py 逐位元組對比，report.py 輸出進度
```

**依賴的原始遊戲檔案**（需自備）：
- `SLPM_654.95` (主 ELF)
- `AFS_DATA.AFS` (資產封存)

---

## 主要模組清單（main.yaml 程式碼段）

依功能分類，格式 `(offset_hex, 名稱)`：

### 遊戲核心
| 模組 | VRAM 偏移 | 說明 |
|---|---|---|
| `crt0` | 0x180 | C 語言執行時啟動 |
| `main` | 0x1f570 | 主迴圈 |
| `game` | 0xf1d0 | 遊戲狀態機 |
| `scheduler` | 0x251e0 | 任務排程器 |
| `heap` | 0x55020 | 記憶體堆積管理 |

### 玩家與戰鬥
| 模組 | VRAM 偏移 | 說明 |
|---|---|---|
| `player` | 0x34bc0 | 玩家控制 |
| `weapon` | 0x64280 | 武器系統 |
| `hitcoll` | 0x18cdc0 | 碰撞偵測 |
| `em` | 0x9fb0 | 敵人（怪物）系統 |
| `em_work` | 0x69fd0 | 怪物工作狀態 |
| `fl` | 0x6ad20 | 場域(field) |
| `pl` | 0x8f240 | 玩家輔助 |
| `item` | 0x1cf70 | 道具系統 |
| `npc` | 0x13d9f0 | NPC 系統 |

### 渲染與視覺
| 模組 | VRAM 偏移 | 說明 |
|---|---|---|
| `camera` | 0x11f550 | 攝影機 |
| `model` | 0x21cf0 | 3D 模型 |
| `prim` | 0x69340 | 圖元(primitive)渲染 |
| `light` | 0x1dc90 | 光照 |
| `tex` | 0x1e9e0 | 貼圖管理 |
| `sprite` | 0x5a6a0 | 2D 精靈圖 |
| `eft/eft20/eft26/eft02` | 各處 | 特效系統 |
| `trans` | 0x63c30 | 場景轉換/淡入淡出 |
| `motion` | 0x254c0 | 骨骼動畫 |
| `parts` | 0x21110 | 模型部位 |
| `yure` | 0x214b0 | 物理搖晃 |

### 音效
| 模組 | VRAM 偏移 | 說明 |
|---|---|---|
| `sound` | 0x59550 | 音效系統 |
| `bgm` | 0x11d5f0 | 背景音樂 |
| `ADX` | 0xf3620 | CRI ADX 音頻解碼器 |
| `sfd` | 0xbd7e0 | SFD 串流影片音頻 |

### 系統/PS2 硬體
| 模組 | VRAM 偏移 | 說明 |
|---|---|---|
| `ps2` | 0x94b80 | PS2 硬體抽象層 |
| `sce_hw` | 0x964b0 | Sony CE 硬體介面 |
| `sceGs` | 0xa96b8 | GS (Graphics Synthesizer) |
| `sceIpu` | 0xaa078 | IPU (Image Processing Unit) |
| `sceMc` | 0xaf6e0 | 記憶卡 |
| `sceMpeg` | 0xb2c28 | MPEG 解碼 |
| `scePad2` | 0xb7e28 | 控制器輸入 |
| `sceVib` | 0xb8720 | 震動馬達 |
| `sceVu0` | 0xb8890 | VU0 向量運算單元 |
| `sceSif` | 0x132dd0 | SIF 匯流排 (EE↔IOP 通訊) |

### 線上/網路
| 模組 | VRAM 偏移 | 說明 |
|---|---|---|
| `netsync` | 0xba0f0 | 網路同步 |
| `CngInet` | 0x12c7e0 | 網路連線管理 |
| `InetDNS` | 0x137920 | DNS 客戶端 |
| `InetConnect` | 0x138070 | 網路連線建立 |
| `InetMcs` | 0x12ff80 | 網路 MCS 訊息 |
| `netOverlay` | 0x167320 | 網路 overlay 管理 |
| `netfile` | 0x186b20 | 網路檔案傳輸 |
| `cnLBS_download` | 0x17d090 | LBS(Location Based Service?) 下載 |

### UI/系統
| 模組 | VRAM 偏移 | 說明 |
|---|---|---|
| `cockpit` | 0x275c0 | HUD 儀表板 |
| `interface` | 0x174f90 | UI 介面 |
| `textinput` | 0x13e7b0 | 文字輸入 |
| `softkey` | 0x15fb00 | 軟鍵盤（日文輸入） |
| `flfnt` | 0x116610 | 字型渲染 |
| `stage` | 0x5bc30 | 場景/關卡載入 |
| `save` | 0x17f0e0 | 存檔系統 |
| `userdata` | 0x172020 | 使用者資料 |
| `result` | 0x190fd0 | 任務結果畫面 |
| `demo` | 0x186470 | 展示/片頭模式 |
| `quest` | 0x126970 | 任務系統 |
| `omake` | 0x13b630 | 額外內容 |
| `info` | 0x55660 | 資訊顯示 |
| `shell` | 0x590a0 | UI Shell |
| `option` | 0x26940 | 選項設定 |
| `modesel` | 0x13a270 | 模式選擇 |
| `poweroff` | 0x190de0 | 電源管理 |
| `staff` | 0x190940 | 製作名單 |
| `cardinit` | 0xfa0 | 記憶卡初始化 |

---

## 已識別的核心資料結構（include/structs.h）

| 結構 | 大小 | 說明 |
|---|---|---|
| `Vec3` | 0x0C | 三維浮點向量 (x, y, z) |
| `RGB` | 0x0C | 顏色 (diff_r/g/b) |
| `GAME_WORK` | 0x224 | 全局遊戲狀態（任務、玩家數、音樂、怪物、道具箱） |
| `SYSTEM_WORK` | 0x80 | 系統全局狀態（線上/離線、地區、音量、載入中） |
| `STAGE_WORK` | 0x64 | 場景/關卡狀態（當前區域、原點位置、模型指標） |
| `VIEW_WORK` | 0x50 | 攝影機/視角狀態（位置、目標、pitch/yaw/roll、FOV） |
| `OPTIONS_WORK` | 0x10 | 玩家選項（音效/BGM 音量、震動、瞄準類型、螢幕偏移） |
| `FADE_WORK` | 0x0C | 螢幕淡入/淡出狀態 |
| `CARD_WORK` | 0x84 | 記憶卡狀態 |
| `DEMO_WORK` | 0x44 | 展示/片頭畫面狀態（INIT→VIOLENCE→CRI→ACCESS→CAPCOM→OPENING→TITLE） |
| `ITEM_SLOT` | 0x08 | 道具槽（item id + quantity） |
| `ITEM_DATA` | 0x10 | 道具靜態資料（類型、稀有度、價格、音效） |
| `KEN_DATA` | 0x14+4 | 近戰武器資料（攻擊力、銳利度、屬性：火/水/雷/龍/毒/麻痺/睡眠） |
| `GUN_DATA` | 0x14 | 遠程武器資料（攻擊力、裝填延遲、彈藥類型） |
| `GUN_GROW_UP` | 0x18 | 弓槍強化資料（速度、散布、精靈大小） |
| `HITCAPSULE_DATA` | 0x28 | 碰撞膠囊（父骨骼、肉質分區、胴體群、半徑、兩端點） |
| `POISON_EFFICACY` | 0x0E | 毒/麻痺/睡眠耐性數值（耐性值、恢復時間、持續時間） |
| `prim` | (可變) | 渲染圖元（帶函數指標 trans） |
| `STAGE_FOG` | 0x0C | 場景霧化效果設定 |

---

## 字串編碼

所有組語檔、原始碼字串均以 **SHIFT-JIS** 編碼（日文），Makefile 中使用 `iconv` 在建置時轉換為 SJIS。

---

## 已知問題（摘自 readme）

1. 主 ELF 有 **14 個 mismatch**，來自 Sony PS2 函式庫（使用 EEGCC 風格分支），未來切換到預建函式庫可修復。
2. `__bss_start` 符號位置偏早（不影響 good build）。
3. NONMATCHING 標籤目前從 split 輸出中省略（MWLDPS2 符號數量限制）。

---

## 分析狀態

- [x] Level 1 初始探索（本文件）
- [ ] Level 2 核心模組職責（遊戲主迴圈、overlay 載入機制、DNAS 加密）
- [ ] Level 3 進階機制（怪物系統、戰鬥碰撞、任務系統、渲染管線）
