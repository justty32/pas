# HugsLib 坑點主文：全域 Harmony patch 清單與風險評估

> 源：`projects/rimworld_mods/hugslib/decompiled/hugslib_v1.6.cs`（v1.6 DLL，HugsLib 12.0.0）。行號皆指此檔。
> 視角：使用者自家 mod 零依賴 HugsLib；清單裡有老 mod 依賴它。

## 1. 全域 Harmony patch 完整清單（17 個，`HugsLib.Patches` 命名空間 `:7597-7924`）

全部由單一 Harmony 實例 `"UnlimitedHugs.HugsLib"` 在 Mod 建構期 `PatchAll` 套上（`:816-833`）。**不論有沒有 mod 依賴 HugsLib，這 17 個都生效。**

### 1a. 改寫原版行為（prefix-skip / transpiler 改邏輯）——真正的「行為變更」

| # | Patch 目標 | 類型 | 做什麼 | 行號 |
|---|---|---|---|---|
| 1 | `LanguageDatabase.SelectLanguage` | **prefix 回傳 false（整段取代）** | 原版「即時重載語言」被換成「存 prefs → 跳重啟對話框」；**dev 模式下直接自動重啟遊戲**（按住 Shift 可擋，`QuickRestarter :9961`） | `:7748` |
| 2 | `ModsConfig.RestartFromChangedMods` | prefix 條件 skip | dev 模式下改完 modlist **跳過確認對話框直接重啟**（Shift 擋） | `:7870` |
| 3 | `MainMenuDrawer.DoMainMenuControls` | transpiler | 主選單「Dev quicktest」按鈕的 action 被換成 `QuickstartController.InitiateMapGeneration` | `:7651` |
| 4 | `Dialog_Options.DoModOptions` | transpiler | 攔截 `new Dialog_ModSettings(mod)`，HugsLib 系 mod 開自家設定視窗；**非 HugsLib mod 走原路不變**（`GetModSettingsWindow :5149`）；patch 失敗會 Error log（`:7616`） | `:7609` |
| 5 | `DebugWindowsOpener.DrawButtons` | transpiler | dev 工具列多畫一顆 quickstart 按鈕（盯 `Bne_Un_S` opcode 找插入點，脆弱；失敗只記 Error） | `:7692` |

### 1b. UI 注入（postfix/prefix 加料，不改原邏輯）

| # | Patch 目標 | 做什麼 | 行號 |
|---|---|---|---|
| 6 | `Dialog_Options.PostOpen` | 反射改 `cachedModsWithSettings`/`hasModSettings` 私有欄位，把 HugsLib 系 mod 設定項塞進選項對話框清單（`OptionsDialogExtensions :5115`） | `:7599` |
| 7 | `EditWindow_Log.DoMessagesListing` | **壓縮 log 視窗列表區**，底部騰出一排 HugsLib 按鈕區（Share logs / Files…，`LogWindowExtensions :4376`），且開放其他 mod 註冊自己的按鈕 | `:7792` |

### 1c. 純掛點（postfix 回呼，轉發給 ModBase 子類；無依賴 mod 時近似空轉）

| # | Patch 目標 | 提供的回呼 | 行號 |
|---|---|---|---|
| 8 | `Root.Update` | 每幀 `OnUpdate` → ModBase.Update、DoLater 排程 | `:7897` |
| 9 | `Root.OnGUI` | 未過濾 OnGUI → quickstart 狀態框（載入畫面也畫） | `:7913` |
| 10 | `UIRoot.UIRootOnGUI` | OnGUI → **KeyBindingHandler 全域按鍵**＋ModBase.OnGUI | `:7677` |
| 11 | `PlayDataLoader.DoPlayLoad` | DefsLoaded 鏈（含 UWO def 注入） | `:7883` |
| 12 | `Game.FillComponents` | 遊戲早期 init：**把 `HugsTickProxy` 假 Thing 註冊進 TickManager**（`:544`、`:9988`；`isSaveable=false`、永不 spawn，不進存檔） | `:7734` |
| 13 | `Game.FinalizeInit` | WorldLoaded 回呼＋UWO null-def 巡檢 | `:7813` |
| 14 | `MapComponentUtility.MapGenerated` | MapGenerated 回呼 | `:7827` |
| 15 | `Map.ConstructComponents` | MapComponentsInitializing 回呼 | `:7841` |
| 16 | `Map.FinalizeInit` | MapLoaded 回呼＋**進地圖時嘗試彈更新新聞視窗**（`:664`） | `:7855` |
| 17 | `Game.DeinitAndRemoveMap` | MapDiscarded 回呼 | `:7774` |

註：HugsLib **沒有**碰 Scribe／存檔序列化本身——存檔影響全部來自 UtilityWorldObject（見 §3）。MapComponent 也沒被注入；地圖鉤子都是 postfix 回呼。

## 2. 「裝著就影響所有人」的全域行為（與依賴它的 mod 無關）

1. **語言切換體驗整個被換掉**（§1a#1）：任何玩家換語言都會被要求/被迫重啟。這是唯一一個對一般玩家「永遠開著」的硬行為變更。
2. **全域按鍵**（`KeyBindingHandler :9657`、`Defs/KeyBindingDefs/KeyBindings.xml`）：新增 5 個 KeyBindingDef（設定→按鍵多一個 HugsLib 分類）。預設只綁 `F12`：**Ctrl+F12 = 上傳 log 到公開 GitHub Gist**、Ctrl+Alt+F12 = 複製到剪貼簿；其餘（開 log 檔、重啟遊戲、開 mod 設定、開更新新聞）預設未綁。命中後 `Event.current.Use()` 吃掉事件。注意 log 內含完整 mod 清單＋Harmony patch 清單＋系統資訊（`:4092`），屬輕微隱私面；縮網址用已停服的 git.io（`:4041`），實務上會退回長網址。
3. **Log 視窗被改造**（§1b#7）：偵錯時看到 log 視窗底部多一排按鈕、列表區變矮，是 HugsLib。
4. **更新新聞彈窗**：只要清單裡任何 mod（**不需依賴 HugsLib**，它掃所有 mod 的 `News/` 資料夾 `:8229`）帶 UpdateFeatureDef 且版本比記錄新，進地圖就彈 `Dialog_UpdateFeatures`。可在 HugsLib 設定關（`modUpdateNews`）。
5. **Dev 模式工作流改變**（§1a#1/2/3＋quickstart）：改 modlist 自動重啟、換語言自動重啟、quicktest 按鈕行為不同、dev 工具列多按鈕。**對 mod 作者（常開 dev 模式）這是最有感的一組**——自動重啟看起來像閃退。
6. **常駐物件**：`HugsLibProxy` GameObject（DontDestroyOnLoad，`:209`）＋每個 Game 一個 `HugsTickProxy` 假 Thing 在 tick 清單裡。排查 tick/場景物件時看到它們不要誤判成洩漏。
7. **設定集中存放**：HugsLib 系 mod 設定在 `SaveData/HugsLib/ModSettings.xml`（`:10113`），不在原版 `Config/Mod_*.xml`——同步/備份設定時容易漏。
8. **ModBase 自動實例化**：掃所有 mod 組件找 `ModBase` 子類自動 new（`:743`）＋自動 `PatchAll` 該組件（harmony id = packageId，`:998`）。例外都被吞進 log（`Logger.ReportException`），不會連鎖炸遊戲。

## 3. 歷史問題／相容性雷區

- **UtilityWorldObjects 存檔殘留**（`:3135`）：UWO 是存進存檔 world objects 的真實 WorldObject。
  - 移除「用 UWO 的 mod」：載入時 HugsLib 偵測 def-null 的 UWO 並**自動移除＋紅字**（`CheckForWorldObjectsWithoutDef :3180`），存檔可救。
  - 移除「HugsLib 本身」：存檔裡的 UWO（def `UtilityWorldObject`＋mod 自訂 worldObjectClass）變成無法解析的類別/def → 原版載入紅字。老存檔黏性主要在這。
  - 機制已 `[Obsolete]`（`:3145`），新 mod 不該再用；Rim War 1.6 脫離 HugsLib 即屬此遷移潮。
- **過時 ModBase 子類在 1.6**：HugsLib 對子 mod 實例化/每個回呼都有 try/catch（`:765-775`、`:355-361` 等），老 mod 編譯目標不符時表現為「該 mod 紅字＋功能死掉」，不是整體崩潰。崩潰模式通常出在老 mod 自己的 Harmony patch 對不上 1.6 簽名，與 HugsLib 無關。
- **雙 Harmony 實例／重複 patch**：HugsLib 對依賴 mod 的組件自動 `PatchAll`；若該 mod 又自己 `PatchAll`（StaticConstructorOnStartup 老樣板）→ 同組件被 patch 兩次。HugsLib 有防重表（`ShouldHarmonyAutoPatch :637`）但只防「HugsLib 自己重複」，防不了 mod 自打。這是依賴 HugsLib 的 mod 的經典坑，零依賴者無關。
- **舊版 DLL 殘留**：mod 根目錄 `Assemblies/` 還躺著 RW 1.0 用的 HugsLib.dll（file version 6.1.3）＋ **0Harmony.dll 1.2.0.1（Harmony 1.x）**，而 `LoadFolders.xml` 對 1.1–1.6 都含 `/`。依原版 load-folder 同相對路徑去重，versioned `HugsLib.dll` 蓋掉根目錄版；但 `0Harmony.dll` 無對應檔，推斷會被載入 AppDomain（**未實測**）。Harmony 1.x 無人實例化即惰性，實務風險低，但在 log 的組件清單裡看到 Harmony 1.2.0.1 不用驚訝。
- **脆弱反射點**（壞了只噴 Error log、功能失效，不炸遊戲）：`Dialog_Options.cachedModsWithSettings/hasModSettings`（`:5157`）、`ShortHashGiver.takenHashesPerDeftype/GiveShortHash`（`InjectedDefHasher :2782`）、`DebugWindowsOpener.widgetRow`（`:7716`）。原版改名時 HugsLib 這些功能先斷。
- **InjectedDefHasher**：用反射呼叫原版 short-hash 內部，給「執行期注入的 def」發 short hash。其他 mod 也可呼叫它；hash 空間是全域的，理論上與大量動態 def 的 mod 共享碰撞空間，原版有去重處理，實務無事。
- **1.6 相容現況**：About.xml 明列 1.6、v1.6 專用 DLL 存在、版本 12.0.0；本機檔案時間 2026-06-06（Steam 下載時間，非發布時間）。**1.6 支援為現行狀態，無「未更新」問題。**

## 4. 坑點風險表（高→低）

| 風險 | 機制 | 影響面 | 什麼情境會踩到 | 建議 |
|---|---|---|---|---|
| 高（對 dev 工作流） | dev 模式自動重啟（語言切換 `:7748`、modlist 變更 `:7870`） | 所有開 dev 模式的人 | 你測自家 mod 時改 modlist/換語言，遊戲「自己關掉重開」，誤判成 crash | 知道這是 HugsLib；按住 **Shift** 可以擋下自動重啟 |
| 高（對存檔） | UtilityWorldObject 存進存檔（`:3135`） | 用老 HugsLib mod 的存檔 | 中途移除 HugsLib 或其依賴 mod → 載入紅字/世界物件殘留 | 開檔後別拔 HugsLib；拔依賴 mod 時讓 HugsLib 留著載一次檔自清再說 |
| 中 | UI patch 疊加：`Dialog_Options`（postfix＋transpiler）、`EditWindow_Log`、`MainMenuDrawer`、`DebugWindowsOpener` | 同樣 patch 這些方法的 mod（設定管理器、log 工具類） | 你或別的 mod 也 transpile 同一方法、依賴特定 IL 形狀 → 互踩、按鈕消失 | 自家 mod 若要動這幾個 UI 方法，用 postfix 而非 transpiler；衝突時先懷疑這 4 個點 |
| 中 | 進地圖彈更新新聞（`:664`）＋掃所有 mod `News/`（`:8229`） | 所有玩家 | 大清單下多個 mod 更新 → 進圖被新聞視窗打斷；你的 mod 若有 `News/` 資料夾也會被它撿走 | 玩家端可關 `modUpdateNews`；自家 mod 別放 `News/` 資料夾除非真要發新聞 |
| 中低 | 全域按鍵吃事件（`:9657`，`Event.current.Use()`） | 用到 F12 組合鍵的 mod／玩家 | Ctrl+F12 被攔去開上傳對話框（還會撞 Steam 截圖鍵）；玩家誤觸把 log 傳上公開 gist | 自家 mod 按鍵避開 F12 組合；教玩家用它回報 log 反而方便 |
| 低 | ModBase 自動實例化＋auto-PatchAll（`:743`、`:998`） | 含 ModBase 子類的組件 | 只有依賴 HugsLib 的 mod；老 mod 壞掉時紅字署名清楚，被 try/catch 隔離 | 自家 mod 零依賴＝完全不受影響；別讓自家組件意外引用 HugsLib.dll |
| 低 | 每幀/每 tick 掛點（`Root.Update/OnGUI`、`HugsTickProxy`） | 全體（效能） | 無依賴 mod 時近似空轉（迴圈+try/catch），量測不出來 | 無需處理；profiling 時看到 HugsTickProxy/HugsLibProxy 屬正常 |
| 低 | 設定存 `SaveData/HugsLib/ModSettings.xml` | HugsLib 系 mod 的設定 | 備份/同步只抄 Config 資料夾會漏掉這些設定 | 備份時把 `SaveData/HugsLib/` 一起帶上 |
| 極低 | 舊 0Harmony 1.2.0.1 可能載入（推斷未實測） | AppDomain | 幾乎不會；惰性組件 | 看到 log 列出 Harmony 1.2.0.1 不用處理 |

## 5. 對使用者的具體判定

自家 mod 零依賴 HugsLib：**幾乎無事**。HugsLib 不碰 Scribe、不注入 MapComponent、不改遊戲規則數值；對你 mod 的程式路徑唯一可能交集是上表的 4 個 UI patch 點（你也 patch 才有事）。實際要記住的只有三件：dev 模式自動重啟不是 crash、進圖新聞彈窗與 log 視窗改造是它幹的、玩家存檔拔 HugsLib 前先想 UtilityWorldObject。
