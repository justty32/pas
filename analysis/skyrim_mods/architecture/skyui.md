# SkyUI SE

## 定位

SkyUI 有兩個截然不同的身分，分析時必須分開看：

- **(a) 玩家面 —— UI 替換**：替換 vanilla 的物品欄、魔法、地圖、收藏等 Flash（Scaleform）介面，提供搜尋、排序、分欄等現代化操作。這部分的本體是 BSA 內的 `.swf`，**不是傳統 record**，從 ESP 層看不到，只能靠公開知識描述。
- **(b) mod 開發者面 —— MCM（Mod Configuration Menu）框架**：SkyUI 在系統選單裡掛出一個「Mod Configuration」分頁，任何 mod 只要寫一個 `extends SKI_ConfigBase` 的 quest script，就能在裡面註冊一個專屬設定頁（toggle / slider / 下拉等控制項）。整個 Skyrim modding 生態的「遊戲內設定 UI」幾乎都建立在這套機制上。

對 ModForge 而言，**(b) 才是重點**：它是「程式化生成的 mod 要不要有設定選單」這個問題的標準答案。(a) 是純美術與 Flash 工程，與 record 生成器無關。

與既有分析的對照：SkyUI 像 JContainers 一樣是「被別的 mod 依賴的基礎設施」（見 `jcontainers.md`），但 JContainers 是 native 資料結構 library，SkyUI 提供的是 **UI 服務面**。而 Sofia（見 `sofia-follower.md`）正是消費 SkyUI 的下游實例——它的 `JJSofiaMCM` quest 就是一個 MCM 設定頁。

## 檔案結構

來源：`~/skyrim_mods/SkyUI/`

| 檔案 | 大小 | 內容 |
|---|---|---|
| `SkyUI_SE.esp` | 2.4 KB | 只有 **7 個 record，全是 Quest**；master = `[Skyrim.esm]` |
| `SkyUI_SE.bsa` | 2.9 MB | Flash UI（`.swf`）+ 編譯後的 `SKI_*.pex` Papyrus 腳本 |

關鍵的結構觀察：**邏輯在 ESP 的 7 個 quest-script，視覺與程式碼本體在 BSA**。

- ESP 之所以只有 quest，是因為 SkyUI 的本體是 **Papyrus（行為）+ Flash（畫面）**，兩者都不是遊戲世界資料 record。ESP 在這裡退化成一張極薄的「腳本掛載清單」：每個 quest 唯一的作用就是當一個**常駐單例**，把對應的 `SKI_*` script 實例化並掛上去。
- BSA 內含 SWF 與 `SKI_*.psc/.pex`，本機**無工具解包**，故以下 record 解剖聚焦 ESP 暴露的 quest + script 名稱，腳本內部行為以公開知識補述（已標註）。
- 安裝結構為 MO2 標準平鋪（`.esp` + `.bsa` 同名成對放在 `Data/` 根；BSA 靠同名 ESP 自動載入）。

## record 解剖

來源：`dotnet run --project src/ModForge.Cli -- dump ~/skyrim_mods/SkyUI/SkyUI_SE.esp`（已重跑驗證）

七個 quest 一律是「**用 quest 當常駐單例 script 容器**」的慣用法——quest 本身沒有 stage 邏輯、沒有 alias、priority=0，存在的唯一目的是承載一個 SkyUI 子系統的 Papyrus 物件，並靠 quest flags 讓它在開新遊戲時自動常駐。

| FormID | EditorID | 掛載 script | 職責（script 名稱 + 公開知識） |
|---|---|---|---|
| `[000802:SkyUI_SE.esp]` | `SKI_ConfigManagerInstance` | `SKI_QF_ConfigManagerInstance` (1 prop) + `SKI_ConfigManager` | **MCM 註冊中樞**：偵測場上所有 `extends SKI_ConfigBase` 的 config script、彙整成 MCM 左欄清單、把玩家點選分發給對應頁面 |
| `[00080A:SkyUI_SE.esp]` | `SKI_SettingsManagerInstance` | `SKI_SettingsManager` | 讀寫 SkyUI 自身偏好設定（持久化於存檔/設定檔） |
| `[000814:SkyUI_SE.esp]` | `SKI_MainInstance` | `SKI_Main` | 啟動協調者：版本檢查、初始化各子系統、UI 注入的進入點 |
| `[000820:SkyUI_SE.esp]` | `SKI_ConfigMenuInstance` | `SKI_ConfigMenu` (6 prop) | **設定頁渲染器**：把 ConfigManager 分發來的頁面實際畫到 MCM Flash 介面（SkyUI 自己的設定頁本身就是一個 SKI_ConfigBase 實例） |
| `[000822:SkyUI_SE.esp]` | `SKI_ActiveEffectsWidgetInstance` | `SKI_ActiveEffectsWidget` (1 prop) | HUD widget：在畫面顯示玩家身上的 active magic effect |
| `[000824:SkyUI_SE.esp]` | `SKI_WidgetManagerInstance` | `SKI_WidgetManager` | HUD widget 管理器：註冊/排版各 widget（給 widget 類 mod 用的框架） |
| `[00082A:SkyUI_SE.esp]` | `SKI_FavoritesManagerInstance` | `SKI_FavoritesManager` (1 prop) | 收藏群組（Favorites Groups）：把武器/法術綁定到 hotkey 群組 |

子系統可分成三組：

- **MCM 框架**：`SKI_ConfigManager`（註冊與分發）+ `SKI_ConfigMenu`（渲染）—— 對 ModForge 唯一有意義的部分。
- **HUD widget 框架**：`SKI_WidgetManager` + `SKI_ActiveEffectsWidget`。
- **啟動 / 設定 / 收藏**：`SKI_Main`、`SKI_SettingsManager`、`SKI_FavoritesManager`。

### quest flags = 常駐單例

dump 顯示 flags 並非隨意：

- `SKI_ConfigManagerInstance` flags = **281**，其餘六個 flags = **273**。
- 兩者都含 **Start Game Enabled** 位（quest 在新遊戲一開始就執行、整局常駐），這正是「把 quest 當常駐單例腳本容器」的前提。
- 差別在 ConfigManager 多了一個位：它是唯一帶有 `stage[1]`（空 log）的 quest，需要 stage table 存在（281 = 273 + 額外旗標），用以驅動它的初始化/掃描流程；其餘子系統不需要 stage。

> 慣例提煉：**Start Game Enabled quest + 掛一個 script（0 個 alias、priority 0）= 一個全域常駐的 Papyrus 單例**。這是 Skyrim 框架類 mod 共通的招式（Sofia 的 `JJSofiaMCM`、`SofiaFollowerScript` 等也是把狀態塞在常駐 quest 的 script property 上，見 `sofia-follower.md`）。

## MCM 機制概述

> 以下為一般性說明（公開知識 / SkyUI SDK 慣例），非從本機源碼解碼——BSA 未解包。

mod 作者要做的事：

1. 寫一個 quest script，宣告 `Scriptname MyMod_MCM extends SKI_ConfigBase`。
2. 覆寫生命週期回呼建構頁面：
   - `OnConfigInit()` —— 設定頁名、分頁數等一次性初始化；
   - `OnPageReset(string page)` —— 每次開啟該頁時呼叫，用 `AddToggleOption` / `AddSliderOption` / `AddMenuOption` / `AddTextOption` 等逐一加控制項；
   - `OnOptionSelect` / `OnOptionSliderAccept` 等 —— 玩家操作時的回呼，把值寫回 mod 的狀態（通常是 GlobalVariable 或 script property）。
3. 把這個 script 掛到一個 **Start Game Enabled quest** 上。

剩下的由 SkyUI 自動完成：`SKI_ConfigManager`（`[000802]`）在啟動時掃描所有 `SKI_ConfigBase` 子類、把它們列進 MCM 左欄，玩家點選時分發到對應實例，再由 `SKI_ConfigMenu`（`[000820]`）渲染。作者**完全不需碰 Flash**，只寫 Papyrus。

**連結回 Sofia 分析**：Sofia 的 `JJSofiaMCM "Sofia Config Menu"` quest（`[00C55D]`，掛 `SofiaMCMscript` 26 prop，見 `sofia-follower.md:53`）就是這套機制的一個實例——它在 MCM 裡提供 catch-up 距離、評論頻率、戰鬥風格切換等開關，玩家在選單調整後寫回 `SofiaCatchUpEnabled` / `SofiaCommentFrequency` 等 GlobalVariable（`sofia-follower.md:127`）。Sofia 同時用 `JJSofiaGetHasSKSE` 在 runtime 探測 SKSE 是否存在、缺了就降級停用 MCM——印證了「**MCM 是選配，核心功能不該硬依賴它**」。

## 對 ModForge 的意義

ModForge（`~/repo/ModForge`，程式化生成 plugin）目前的設定儲存是 **GLOB（GlobalVariable）**（見 `src/ModForge.Core/Spec.Globals.cs`、`Generator.Build.Globals.cs`，以及 ModForge CLAUDE.md「已落地功能 → GlobalVariable」），**但沒有任何遊戲內設定 UI**——使用者只能靠 console 或外部工具改 GLOB 值。

### 要生成 MCM 設定頁需要什麼

若想讓 ModForge 生成的 mod 有設定選單，本質上要產出一個「`extends SKI_ConfigBase` 的 quest + script」，拆成三個能力需求：

| 需求 | ModForge 現況 | 缺口 |
|---|---|---|
| (a) 生成繼承特定 base 的 Papyrus script | **已具備雛形**：ModForge 已會生成 `extends Quest` / `extends TopicInfo` 的腳本並編譯（`Generator.QuestFragments.cs:43,86`、`Generator.WordWall.cs:41`、`Generator.Build.Scene.cs`）；改成 `extends SKI_ConfigBase` 並產生 `OnPageReset` body 是同類工作 | 需 `SKI_ConfigBase` 的 header（編譯期 import），即 build 機器要有 SkyUI 的 source/header；ModForge 的 Papyrus header 機制（`MODFORGE_PAPYRUS_HEADERS`，見 ModForge CLAUDE.md 踩坑）可指過去 |
| (b) Start Game Enabled quest 掛 script property | **已具備**：ModForge 已能生 quest 並掛 script + property（quest stage / scene controller 都這樣做） | 需把 quest flag 設成含 Start Game Enabled（對照本檔 273/281），並把 GLOB 當 property 餵給 config script，讓控制項讀寫對得上 |
| (c) 依賴 SkyUI | 無 | 產出的 plugin 變成**硬依賴 SkyUI（且 MCM 需 SKSE）**；終端使用者必須安裝這兩者 |

### 可行性結論（務實）

- **技術上可行，且門檻不高**：ModForge 既有的「生成 `extends X` 的 Papyrus + 掛到 quest + 編譯」管線，與生成一個 MCM config script 是**同型工作**，差別主要在 base class 名稱、回呼樣板（`OnPageReset` 的 `AddToggleOption`/`AddSliderOption`）與一張「GLOB ↔ 控制項」的映射表（可從現有的 `GlobalSpec` 自動推導：short/bool → toggle，float → slider）。
- **但不該預設依賴 SkyUI**：這會把一個 native/UI 框架塞進每個產物的依賴鏈，違反 ModForge「預設零外部依賴」的取向（與 `jcontainers.md` 的結論一致——JFormDB 也被定位為「進階選項，不該預設」）。Sofia 的做法（核心零 SKSE、MCM 選配並 runtime 降級）是正確範式。
- **建議定位為 opt-in 進階功能**：在 spec 增設一個明確的 `mcm` 區塊（例如列出要暴露的 GLOB 與對應控制項型別），只有作者顯式啟用時才生成 config script、加上 SkyUI master/依賴標記，並在文件提醒終端使用者需裝 SkyUI + SKSE。預設仍維持「GLOB + 無 UI」。
- **優先級判斷**：對隨從/內容類 mod 而言，MCM 是「使用者可調設定」的標準缺口（見 `sofia-follower.md` 結論點出這是該品類最大缺口）。若 ModForge 要瞄準隨從這類品類，MCM 生成的投資報酬率高於 native 資料結構（JContainers）持久化。
