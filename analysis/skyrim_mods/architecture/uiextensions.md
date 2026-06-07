# UIExtensions (v1.2.0, Nexus #17561)

## 定位

runtime **自訂 UI 元件 library**——它本身**不替換、不修改任何遊戲既有畫面**，而是提供一組「從 Papyrus 主動叫出來」的可重用互動選單元件：捲動清單選單、輪盤（radial）快捷選單、文字輸入框、自訂選擇選單、法術/數值面板、外觀/染色面板等。別的 mod 在需要「讓玩家選一個選項 / 輸入一段文字 / 用轉輪選快捷」時呼叫它，得到玩家的選擇後繼續自己的邏輯。

與 **SkyUI** 的關係是**互補而非競爭**：

| | SkyUI | UIExtensions |
|---|---|---|
| 改動對象 | **替換**固定的遊戲畫面（物品欄、地圖、魔法欄）+ 提供 MCM 設定頁框架 | **不碰**既有畫面，**新增**臨時跳出的互動元件 |
| 觸發時機 | 玩家按 Tab/M 等固定鍵進入的常駐畫面 | mod 腳本在任意時點主動 `OpenMenu(...)` 叫出 |
| 給誰用 | 終端使用者（直接看到的 UI 翻新）+ MCM 作者 | mod 作者（當作通用互動原語） |
| 角色 | 固定畫面的翻新與設定框架 | Papyrus 缺乏的「即時互動 UI」補完 |

兩者都是「mod 平台型」依賴：自身幾乎無遊戲內容，價值在於被別的 mod 呼叫。

## 檔案結構

來源：`~/skyrim_mods/UIExtensions/`

```
UIExtensions/
├── UIExtensions.esp   (1.1 KB) ← 純邏輯註冊：9 record
└── UIExtensions.bsa   (467 KB) ← 視覺 (SWF) + 腳本 (PEX/PSC)
```

**強調 `master(s)=[]`：完全自包含的獨立 plugin**（驗證：`dump UIExtensions.esp` 輸出 `master(s)=[]`）。它不 override、不引用 Skyrim.esm 的任何 record，9 個 record 全是新增的 menu 註冊容器與一個結果傳遞用 FormList。因此它可以放在 load order 任意位置、不挑前置，這正是 library 型 plugin 該有的形態。

邏輯與資產的分工：

- **邏輯在 ESP 的 9 record**：8 個常駐 quest 當 menu 的單例腳本容器 + 1 個 FormList 當選取結果的傳遞通道。
- **視覺/實作在 BSA**：每個 menu 一個 Flash `.swf`（畫面與動畫）+ 對應 `.pex`（編譯後 Papyrus）。

BSA 內可辨識的資產（來源：`strings UIExtensions.bsa`）：

| 類別 | 內容 |
|---|---|
| menu SWF | `listmenu.swf` / `selectionmenu.swf` / `wheelmenu.swf` / `textentrymenu.swf` / `magicmenuext.swf` / `statssheetmenu.swf` / `cosmeticmenu.swf` / `dyemenu.swf` / `followermenu.swf` |
| 輔助 SWF | `messagebox.swf` / `meter.swf` / `bottombar.swf` / `buttonart.swf` |
| 圖示 SWF | `icons_category_psychosteve.swf` / `skyui_icons_psychosteve.swf` |
| menu 腳本 (.pex/.psc) | 對應 8 個 ESP menu，外加輔助 `UIExtensions` / `UIMenuBase` / `UIMenuLoad`（基底/載入器，不掛 quest，被各 menu 共用） |

> 註：`followermenu.swf` 存在於 BSA，但 ESP 沒有對應的常駐 quest record，研判為內部/未公開或由其他 menu 共用的資產。BSA **無工具解包**，SWF 與 .pex 的內部細節不在本分析範圍，以下聚焦 ESP record + 公開知識。

## record 解剖

### 8 個 menu quest（單例容器慣用法）

8 個 record 全是 **Quest**，各掛一個（CosmeticMenu 掛兩個）UI menu 腳本，`flags=273`、`priority=0`：

| FormID | Quest / 掛載腳本 | 用途 |
|---|---|---|
| `[000E05:UIExtensions.esp] Quest UIListMenu` (腳本 `UIListMenu`) | **捲動清單選一項**——把一串字串條目列成可上下捲的清單，回傳玩家選中的索引。最基礎、被別的 mod 用得最多的元件 |
| `[000E00:UIExtensions.esp] Quest UISelectionMenu` (腳本 `UISelectionMenu`，**1 prop**) | **自訂選擇選單**——清單選單的進階版，條目可帶圖示/分組，配合 `SelectedForms` FormList 傳遞「選了哪些 form」。是 9 record 中唯一帶 property 的，研判用來持有預設條目或回傳結果參考 |
| `[000E04:UIExtensions.esp] Quest UITextEntryMenu` (腳本 `UITextEntryMenu`) | **彈出鍵盤輸入字串**——命名自訂物品、角色、存檔標籤等場景，回傳玩家輸入的文字。原生 Papyrus 完全缺這個能力 |
| `[000E01:UIExtensions.esp] Quest UIWheelMenu` (腳本 `UIWheelMenu`) | **輪盤式（radial）快捷選單**——環狀分格的快捷選擇，常用於戰鬥/動作快捷指令（如表情、戰術指令、隨從命令） |
| `[000E02:UIExtensions.esp] Quest UIMagicMenu` (腳本 `UIMagicMenu`) | **法術/能力面板**——以魔法欄風格列出法術或能力供選擇 |
| `[000E03:UIExtensions.esp] Quest UIStatsMenu` (腳本 `UIStatsMenu`) | **數值面板**——以角色數值表（stats sheet）風格呈現/選擇屬性 |
| `[000E06:UIExtensions.esp] Quest UICosmeticMenu` (腳本 `CosmeticMenu` + `UICosmeticMenu`) | **外觀面板**——調整角色外觀。唯一掛兩個腳本（一個 UI 層 `UICosmeticMenu`、一個邏輯/資料層 `CosmeticMenu`） |
| `[000E07:UIExtensions.esp] Quest UIDyeMenu` (腳本 `UIDyeMenu`) | **染色面板**——裝備染色選色 |

**單例容器慣用法**：8 個 quest 都用「常駐 quest 當 script 容器」這個 SkyUI/SKSE 生態的標準手法——`flags=273` 含 **Start Game Enabled** bit，遊戲一開始就把這些 quest 啟動並常駐，掛在上面的 menu 腳本因此始終存在、可被任何 mod 透過 `Quest.GetScript()` 或直接 cast 取得單例。quest 本身沒有 stage/objective/alias 等任務語意，純粹借用「常駐物件」的生命週期當腳本宿主。

### FormList SelectedForms `[002852]`

`[002852:UIExtensions.esp] FormList SelectedForms` 是**菜單與呼叫端之間的結果傳遞通道**。當 menu（特別是涉及 Form 選擇的 SelectionMenu）讓玩家勾選了一個或多個遊戲物件（Form）時，把結果寫進這個共用 FormList，呼叫端在 menu 關閉後讀取它即可取得「玩家選了哪些 form」。FormList 在此扮演 Papyrus 跨腳本傳遞「一組 Form」的便捷共享變數（避免逐一 SetPropertyValue 的麻煩）。

## 使用模式概述（一般性說明，公開知識）

> 以下為 UIExtensions 公開的通用呼叫慣例，非從 BSA 解出的逐行實作。

典型呼叫端流程：

1. **取得 menu 單例腳本**——對目標 menu quest 取得其掛載腳本（如把 `UIListMenu` quest cast 成 `UIListMenu` 腳本型別）。
2. **設定條目**——呼叫腳本上的方法填入清單條目、圖示、旗標等。
3. **`OpenMenu(...)` 顯示並阻塞等待**——叫出 SWF 畫面，呼叫**阻塞**直到玩家做出選擇或取消。
4. **回傳結果**——回傳被選中的**索引**（清單/輪盤）、**輸入字串**（文字框）或一組 **Form**（經 `SelectedForms` FormList）。

這補完了原生 Papyrus 沒有的「即時、互動、阻塞式」UI 原語——原生只有固定的 `MessageBox`（最多有限按鈕、無捲動、無輸入），UIExtensions 把「任意長清單選擇」「自由文字輸入」「輪盤快捷」這些常見互動變成幾行 Papyrus 就能叫出的元件。

## 對 ModForge 的意義

ModForge（`~/repo/ModForge`）目前的互動產出集中在**對話分支**（quest/dialogue/scene，見 ModForge CLAUDE.md「已落地功能」）。當生成的內容需要「對話以外的即時玩家選擇/輸入」時，UIExtensions 提供現成元件，省去自寫 SWF 的高成本工作。務實評估：

1. **適用場景**：動態指定目標（從一串候選 NPC/地點選一個）、命名（自訂物品/隨從/據點取名 → `UITextEntryMenu`）、分支選單（比對話框更緊湊的選項清單 → `UIListMenu`）、快捷指令（隨從命令輪盤 → `UIWheelMenu`）。這些用對話 INFO 樹做會很笨重，用 UIExtensions 元件更自然。

2. **使用代價**：ModForge 要用它，得**生成呼叫其 menu 腳本的 Papyrus**（取得單例 → 填條目 → `OpenMenu` → 讀回傳值），並把這段腳本編譯掛到生成的 quest/alias/magic-effect 上——這對既有的 Papyrus 生成管線（dispatcher/controller embed、Wine+CK 編譯）是可行的，但 menu 腳本的 header 需納入編譯時的 source/header 路徑。

3. **native + SWF 依賴**：UIExtensions = SKSE 環境下的 SWF + Papyrus 元件，**它是終端使用者必須額外安裝的前置**。ModForge 若產出依賴它的 plugin，等於要求玩家裝 UIExtensions（與 JContainers 同類的「進階選項，不該是預設」處境，見 `jcontainers.md` 的對照結論）。好處是它**無 master**、相容性極佳，當前置比多數 mod 安全。

4. **定位結論**：UIExtensions 對 ModForge 是「**對話分支以外互動**」的有用補充，而非核心依賴。建議列為**可選增強**——在生成需求明確包含「玩家臨時選擇/輸入」時才引入，並在產出 manifest 標明前置；預設管線仍以對話/scene 為主。
