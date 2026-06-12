# HugsLib 淺層總覽（坑點導向）

> 分析目的：使用者自家 mod **不依賴** HugsLib，但 310 mod 清單裡有老 mod 依賴它。本文回答「HugsLib 裝著時，它的全域行為會不會影響別人／坑到我」。深度刻意停在「影響面」層級。

- **packageId / workshop**：`UnlimitedHugs.HugsLib` / 818773962，作者 UnlimitedHugs
- **版本**：12.0.0（`About/Version.xml` overrideVersion；`About/About.xml` supportedVersions 1.0–1.6，**1.6 已正式支援**，本機 v1.6 資料夾有獨立 DLL）
- **相依**：只硬依賴 `brrainz.harmony`
- **本質**：給其他 mod 用的**生命週期＋設定＋雜項工具框架**，自己不加任何遊戲內容。但「框架」不等於「被動」——它靠 **17 個全域 Harmony patch** 把自己掛進遊戲主迴圈、UI 與地圖生命週期，**這些 patch 不管有沒有 mod 依賴它都會生效**。
- **反編譯源**：`projects/rimworld_mods/hugslib/decompiled/hugslib_v1.6.cs`（下文行號皆指此檔）

## 核心子系統（各一兩句）

| 子系統 | 是什麼 | 行號 |
|---|---|---|
| **HugsLibController** | 樞紐單例。`HugsLibMod`（`Verse.Mod` 子類）建構時早期初始化，建立 `HugsLibProxy` GameObject（DontDestroyOnLoad）接 Unity 事件，並 `PatchAll` 自己的 17 個 patch | `:105`、`:189`、`:209`、`:816` |
| **ModBase 生命週期框架** | 掃描**所有** running mod 組件中 `ModBase` 子類，自動實例化並依序回呼 `DefsLoaded/WorldLoaded/MapLoaded/Tick/Update/OnGUI…`；每個回呼都包 try/catch，炸了只記 log 不炸遊戲 | `:743`、`:864` |
| **設定框架** | `ModSettingsManager`：HugsLib 系 mod 的設定**不存原版 Mod 設定檔**，集中存 `SaveData/HugsLib/ModSettings.xml`；設定視窗用反射＋transpiler 注入原版選項對話框 | `:6255`、`:10113`、`:5115` |
| **版本檢查** | `LibraryVersionChecker`：mod 的 Version.xml 要求更新版 HugsLib 時跳更新對話框；`LoadOrderChecker`：HugsLib 排在 Core 前面時跳警告框 | `:9711`、`:9823` |
| **UpdateFeatureManager（更新新聞）** | 掃**所有** running mod 的 `News/` 資料夾（不限 HugsLib 系），版本比上次高就在**進地圖時**彈出「mod 更新新聞」視窗；已讀進度存 `SaveData/HugsLib/LastSeenNews.xml` | `:9216`、`:8229`、`:664` |
| **Log 上傳（Ctrl+F12）** | `LogPublisher`：把 log（含 mod 清單、Harmony patch 清單、系統資訊）上傳到 **GitHub Gist**（內嵌反轉字串藏的 auth token）；log 視窗底部也被加一排按鈕（綠色 Share logs 等） | `:3814`、`:4376` |
| **DevTools / Quickstart** | dev 模式下：主選單「Dev quicktest」按鈕被改接 HugsLib quickstarter；dev 工具列多一顆 quickstart 按鈕；可設定開遊戲自動生圖/載檔 | `:7251`、`:7651`、`:7692` |
| **UtilityWorldObject（過時存檔機制）** | 注入一個 `UtilityWorldObject` WorldObjectDef 讓老 mod 把資料存進世界物件；已標 `[Obsolete]`，建議改用 GameComponent/WorldComponent | `:3135`、`:3145`、`:3203` |

## 一句話結論

**HugsLib 裝著就有全域影響，但影響面可枚舉且大多是「UI／dev 工具／回呼掛點」**：17 個 patch 裡只有 3 個真正改寫原版行為（語言切換強制重啟、dev 模式改 modlist 自動重啟、Dev quicktest 按鈕改接 quickstart），其餘是純 postfix 回呼或 UI 注入。對零依賴 HugsLib 的自家 mod，正常情況**幾乎無干擾**；會踩到的情境集中在：你也 patch 同一批 UI 方法、你在 dev 模式下的工作流、以及玩家存檔裡老 mod 的 UtilityWorldObject 殘留。完整坑點見 `../details/pitfalls_and_global_patches.md`。
