# T-Engine 4 架構總覽 (v1.7.6)

T-Engine 4 (TE4) 是一個以 **C + Lua** 雙層架構設計的 roguelike 遊戲引擎，底層用 C/SDL2/OpenGL 處理效能敏感的操作，上層用 Lua 實作遊戲邏輯，兩層透過 Lua C API 橋接。遊戲模組以 `.teae` / `.team` 壓縮包（zip 格式）發佈。

---

## 整體分層架構

```
┌─────────────────────────────────────────────────────┐
│               遊戲模組 (Lua)                         │
│  modules/tome, modules/example, ...                  │
├─────────────────────────────────────────────────────┤
│               引擎核心 (Lua)                          │
│  engine/*.lua  (實體系統、地圖、UI、AI、存檔…)        │
├─────────────────────────────────────────────────────┤
│          C ↔ Lua 橋接層 (core.* API)                 │
│  core_lua.c, display_sdl.c, map.c, shaders.c …      │
├─────────────────────────────────────────────────────┤
│               底層 C 函式庫                           │
│  SDL2, OpenGL/GLEW, PhysFS, LuaJIT/Lua5.1,          │
│  libvorbis, expat, zlib, bzip2, LuaSocket …          │
└─────────────────────────────────────────────────────┘
```

---

## 一、C 層模組 (`src/`)

### 1.1 入口 & 視窗管理
- **`main.c`** — 程式入口；SDL2 視窗、OpenGL context、主迴圈（遊戲 tick、事件分派、FPS 控制）、搖桿/手把支援。

### 1.2 顯示 & 渲染
| 檔案 | 功能 |
|------|------|
| `display_sdl.c / .h` | SDL2 渲染後端，FBO、材質管理 |
| `shaders.c / .h` | GLSL shader 載入、編譯、管理 |
| `map.c / .h` | 地圖圖磚快速繪製（C 層加速） |
| `particles.c / .h` | 粒子系統渲染 |
| `glew.c / .h` | OpenGL 擴充載入 |

### 1.3 音訊
- **`music.c / .h`** — 音樂播放（OGG/vorbis）、音效。

### 1.4 Lua 虛擬機
- **`src/lua/`** — 標準 Lua 5.1
- **`src/luajit2/`** — LuaJIT 2.x（可替換，由編譯選項決定）
- **`core_lua.c / .h`** — 將所有 C 功能注入 Lua `core.*` 命名空間

### 1.5 虛擬檔案系統
- **`src/physfs/`** + **`physfs.c`** — PhysFS 函式庫，支援直接讀取 zip 壓縮包（`.teae`/`.team`），讓模組以單一壓縮包發佈。

### 1.6 亂數
- **`SFMT.c / .h`** — SIMD 版 Mersenne Twister（週期 2^19937-1），高品質偽亂數。
- **`noise.c`** + **`src/libtcod_import/`** — Perlin/Simplex noise（來自 libtcod）。

### 1.7 視野演算法 (FOV)
- **`fov.c / .h`** + **`src/fov/`** — 多種 FOV 演算法（recursive shadowcasting 等）。

### 1.8 Wave Function Collapse
- **`src/wfc/`** (C++) — WFC 演算法實作，供程序化地圖生成使用。

### 1.9 網路 & 在線功能
- **`src/luasocket/`** — TCP/UDP socket（LuaSocket 移植）
- **`profile.c / .h`** — 玩家在線 profile、排行榜、成就上傳
- **`serial.c / .h`** — 序列化協議
- **`src/web-cef3/`** / **`src/web-awesomium/`** — 嵌入式瀏覽器（可選編譯）
- **`discord-te4.c`** + **`src/discord-rpc/`** — Discord Rich Presence 整合

### 1.10 其他工具
- **`src/expat/`** + **`src/lxp/`** — XML 解析（Expat + Lua 綁定）
- **`src/zlib/`** + **`src/bzip2/`** — 壓縮/解壓縮
- **`src/lzlib/`** — zlib 的 Lua 綁定
- **`src/utf8proc/`** — UTF-8 字串處理
- **`src/luamd5/`** — MD5 雜湊
- **`src/luaprofiler/`** — Lua 效能分析器
- **`src/luabitop/`** — Lua 位元運算
- **`src/lpeg/`** — LPeg 解析表達式語法庫
- **`getself.c`** — 取得執行檔自身路徑（自解壓縮支援）
- **`bspatch.c`** — 二進位差分補丁（熱更新）

---

## 二、Lua 引擎層 (`engine/*.lua`)

打包於 `game/engines/te4-1.7.6.teae`。

### 2.1 核心實體系統
| 類別 | 說明 |
|------|------|
| `Entity.lua` | 所有遊戲物件的基底類別，屬性、define/resolve 系統 |
| `Actor.lua` | 角色/怪物，繼承 Entity |
| `Grid.lua` | 地圖格（terrain tile） |
| `Object.lua` | 物品/裝備 |
| `Trap.lua` | 陷阱 |
| `Projectile.lua` | 投射物 |

### 2.2 世界結構
| 類別 | 說明 |
|------|------|
| `Zone.lua` | 區域（含多層 Level） |
| `Level.lua` | 單一樓層，持有 Map 與 Actor 列表 |
| `Map.lua` | 地圖資料與渲染 |
| `MapEffect.lua` | 地圖上的持續效果（毒霧、火焰…） |
| `World.lua` | 全局世界狀態（跨 Zone 持久資料） |

### 2.3 遊戲迴圈
| 類別 | 說明 |
|------|------|
| `Game.lua` | 基底遊戲類別，主迴圈介面 |
| `GameTurnBased.lua` | 回合制迴圈（energy 耗盡才輪到下一個） |
| `GameEnergyBased.lua` | Energy-based tick 系統（各 Actor 依速度累積 energy） |

### 2.4 介面混入 (Interface Mixins, `engine/interface/`)
Actor 相關：
- `ActorAI.lua` — AI 行為掛勾
- `ActorFOV.lua` — 視野計算
- `ActorInventory.lua` — 揹包管理
- `ActorLevel.lua` — 經驗值/等級
- `ActorLife.lua` — HP、死亡
- `ActorProject.lua` — 投射/施法
- `ActorQuest.lua` — 任務狀態
- `ActorResource.lua` — 資源（魔力、理智…）
- `ActorStats.lua` — 基礎屬性（力量、敏捷…）
- `ActorTalents.lua` — 技能系統（cooldown、使用、學習）
- `ActorTemporaryEffects.lua` — Buff/Debuff 系統

Player 專用：
- `PlayerExplore.lua` — 自動探索
- `PlayerRun.lua` — 自動移動
- `PlayerRest.lua` — 休息/等待
- `PlayerMouse.lua` — 滑鼠點擊移動
- `PlayerHotkeys.lua` — 快捷鍵
- `PlayerDumpJSON.lua` — 匯出角色資料（JSON）
- `PlayerSlide.lua` — 滑行移動

其他：
- `GameMusic.lua` — 音樂控制
- `GameSound.lua` — 音效控制
- `GameTargeting.lua` — 目標選擇系統
- `WorldAchievements.lua` — 成就系統
- `BloodyDeath.lua` — 死亡表現效果

### 2.5 AI 系統 (`engine/ai/`)
- `simple.lua` — 基礎 AI（追擊、攻擊）
- `talented.lua` — 技能使用 AI
- `special_movements.lua` — 特殊移動 AI（繞路、飛行）

### 2.6 程序地圖生成 (`engine/generator/map/`)
| 生成器 | 說明 |
|--------|------|
| `Roomer.lua` / `Rooms.lua` / `RoomsLoader.lua` | 房間式地牢 |
| `Cavern.lua` / `CavernousTunnel.lua` | 洞窟 |
| `Maze.lua` | 迷宮 |
| `Forest.lua` | 森林 |
| `Heightmap.lua` | 高度圖地形 |
| `Building.lua` | 建築 |
| `Town.lua` | 城鎮 |
| `Static.lua` | 手工靜態地圖 |
| `MapScript.lua` | Script 驅動的程序地圖 |
| `GOL.lua` | Game of Life 細胞自動機 |
| `Hexacle.lua` | 六角形佈局 |
| `Octopus.lua` | 章魚形連通圖 |
| `TileSet.lua` | 圖磚集對應 |
| `WaveFunctionCollapse`（via C++ WFC） | 波函數塌縮生成 |

Tilemap（`engine/tilemaps/`）：
- `BSP.lua`, `Maze.lua`, `Heightmap.lua`, `Noise.lua`, `Rooms.lua`, `Static.lua`, `Tilemap.lua`, `WaveFunctionCollapse.lua`, `Proxy.lua`

Actor 生成器（`engine/generator/actor/`）：`Random.lua`, `OnSpots.lua`

演算法（`engine/algorithms/`）：`BSP.lua`（二元空間分割）、`MST.lua`（最小生成樹，用於房間連通）

### 2.7 UI 框架 (`engine/ui/`)
完整的 UI 元件庫（純 Lua 繪製於 OpenGL）：

`Base.lua`（基底）→ `Button`, `ButtonImage`, `Checkbox`, `Dropdown`, `Focusable`, `GenericContainer`, `Image`, `ImageList`, `List`, `ListColumns`, `NumberSlider`, `Numberbox`, `Separator`, `Slider`, `Tab`, `Tabs`, `Textbox`, `Textzone`, `TextzoneList`, `TreeList`, `UIContainer`, `UIGroup`, `VariableList`, `Waitbar`, `Waiter`, `WebView` ...

還有 `Dialog.lua`（視窗基底）、`SubDialog.lua`、`WithTitle.lua`、`Gestures.lua`（觸控）、`EquipDoll.lua`（裝備展示）、`EntityDisplay.lua`、`SurfaceZone.lua`。

### 2.8 預建對話框 (`engine/dialogs/`)
| 對話框 | 功能 |
|--------|------|
| `GameMenu.lua` | 主選單/暫停選單 |
| `ShowInventory.lua` / `ShowEquipment.lua` / `ShowEquipInven.lua` | 物品/裝備管理 |
| `ShowPickupFloor.lua` | 地板撿取 |
| `ShowStore.lua` | 商店界面 |
| `ShowQuests.lua` | 任務列表 |
| `ShowLog.lua` | 訊息記錄 |
| `ShowAchievements.lua` | 成就 |
| `ViewHighScores.lua` | 排行榜 |
| `UseTalents.lua` | 技能使用 |
| `KeyBinder.lua` | 按鍵設定 |
| `VideoOptions.lua` / `AudioOptions.lua` | 影音設定 |
| `DisplayResolution.lua` | 解析度設定 |
| `LanguageSelect.lua` | 語言選擇 |
| `Downloader.lua` | 更新/下載器 |
| `Chat.lua` / `ChatChannels.lua` / `ChatFilter.lua` / `ChatIgnores.lua` | 在線聊天 |
| `GetText.lua` / `GetQuantity.lua` / `Talkbox.lua` | 輸入對話 |
| `UserInfo.lua` | 用戶資料 |

### 2.9 其他核心系統
| 模組 | 說明 |
|------|------|
| `class.lua` | 物件導向基礎（OOP，多重繼承 mixin） |
| `resolvers.lua` | 實體屬性解析器（隨機、範圍、表格查詢） |
| `utils.lua` | 全局工具函數 |
| `colors.lua` | 顏色常數與解析 |
| `KeyBind.lua` / `Key.lua` / `KeyCommand.lua` | 鍵盤輸入與綁定系統 |
| `Mouse.lua` | 滑鼠事件 |
| `Savefile.lua` / `SavefilePipe.lua` | 存檔（Lua serialization + zlib） |
| `Tiles.lua` | 圖磚載入、快取、動畫 |
| `Shader.lua` | Lua 端 shader 封裝 |
| `Particles.lua` / `ParticlesCallback.lua` | 粒子特效系統 |
| `FlyingText.lua` | 飄字效果（傷害數字等） |
| `DamageType.lua` | 傷害類型定義與處理 |
| `Target.lua` | 目標選擇（射程、形狀） |
| `Quest.lua` | 任務系統 |
| `Faction.lua` | 陣營/聲望系統 |
| `Store.lua` | 商店系統 |
| `Chat.lua` | NPC 對話腳本系統 |
| `HighScores.lua` | 本地高分榜 |
| `PlayerProfile.lua` | 在線玩家 profile（te4.org） |
| `NameGenerator.lua` / `NameGenerator2.lua` | 程序名稱生成（音節/文法） |
| `Birther.lua` | 角色創建嚮導 |
| `Autolevel.lua` | NPC 自動升級 |
| `Calendar.lua` | 遊戲內日曆/時間 |
| `Emote.lua` | 角色表情 |
| `Generator.lua` | 生成器基底類別 |
| `I18N.lua` | 國際化/在地化 |
| `Quadratic.lua` | 二次曲線工具 |
| `Heightmap.lua` | 高度圖工具 |
| `Astar.lua` | A* 路徑尋路 |
| `DirectPath.lua` | 直線路徑 |
| `MicroTxn.lua` | 微交易（Steam DLC） |
| `Module.lua` | 模組載入/管理 |
| `CharacterBallSave.lua` / `CharacterVaultSave.lua` | 角色存檔（雲端） |
| `LogDisplay.lua` / `LogFlasher.lua` | 訊息日誌顯示 |
| `HotkeysDisplay.lua` / `HotkeysIconsDisplay.lua` | 快捷鍵 HUD |
| `ActorsSeenDisplay.lua` | 視野內敵人顯示 |
| `Tooltip.lua` | 提示框 |
| `UserChat.lua` | 在線聊天後端 |
| `DebugConsole.lua` | 開發者除錯控制台 |
| `FontPackage.lua` | 字型打包管理 |
| `BootErrorHandler.lua` | 啟動錯誤處理 |
| `webcore.lua` | WebView 本地請求解析 |
| `version.lua` | 版本資訊 |

---

## 三、模組系統 (`game/modules/`)

每個模組是獨立的遊戲，以 `.team` 壓縮包發佈：
- `tome-1.7.6.team` — Tales of Maj'Eyal（主遊戲）
- `boot-te4-1.7.6-nomusic.team` — 啟動/選單模組
- `example/`, `example_realtime/` — 範例模組（範本）

模組透過繼承 `engine.*` 類別並覆寫方法來實作遊戲規則，引擎不強制任何具體遊戲規則。

---

## 四、資料層 (`data/`)
- `data/gfx/` — 圖像資源
- `data/font/` — 字型
- `data/sound/` — 音效
- `data/keybinds/` — 預設按鍵設定
- `data/locales/` — 在地化字串

---

## 五、建構系統

使用 **Premake4** (`premake4.lua`) 產生 Makefile/VS 專案：
- `build/te4core.lua` — 核心 C 程式建構規則
- `build/runner.lua` — Runner 工具
- `build/options.lua` — 編譯選項（lua 版本、web 後端、steam、32bit 等）

支援平台：Linux、Windows（含交叉編譯）、macOS（`mac/`）。

---

## 六、關鍵設計決策

1. **C/Lua 雙層**：效能瓶頸（FOV、地圖繪製、粒子）在 C，遊戲邏輯全在 Lua，方便模組開發者擴充。
2. **Mixin 架構**：`engine/interface/` 下的功能以 mixin 形式混入，Actor 只需繼承需要的介面，保持彈性。
3. **PhysFS 虛擬 FS**：所有資源透過虛擬路徑存取，引擎無需知道資源是在磁碟還是 zip 內。
4. **Resolvers 系統**：實體屬性在 define 時可用函數/表格描述，在 resolve 時才實際計算（支援隨機化、條件判斷）。
5. **模組獨立性**：遊戲模組與引擎完全分離，可發佈多個不同遊戲共用同一引擎。
