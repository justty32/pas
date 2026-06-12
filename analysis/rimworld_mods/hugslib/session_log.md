# HugsLib 分析 session log

## 2026-06-12 建檔（淺層、坑點導向）

- 動機：使用者自家 mod 零依賴 HugsLib，310 mod 清單裡有老 mod 依賴它（Rim War 1.6 已脫離）；只要知道「裝著時的全域影響面」。
- 辨識：`UnlimitedHugs.HugsLib` / workshop 818773962，版本 12.0.0，supportedVersions 1.0–1.6（**1.6 現行支援**），唯一相依 brrainz.harmony。
- 來源：本機 Steam 安裝 `…/294100/818773962/`；以 ilspycmd 反編譯 `v1.6/Assemblies/HugsLib.dll` → `projects/rimworld_mods/hugslib/decompiled/hugslib_v1.6.cs`（10,408 行）。
- 結構盤點：HugsLibController(:105) 樞紐＋17 個全域 Harmony patch（`HugsLib.Patches` :7597-7924，單一實例 "UnlimitedHugs.HugsLib" PatchAll :816）；ModBase 自動實例化(:743)＋依賴 mod 組件 auto-PatchAll(:998)；設定集中存 SaveData/HugsLib/ModSettings.xml(:10113)；UpdateFeatureManager 掃所有 mod News/(:8229) 進圖彈窗(:664)；LogPublisher Ctrl+F12 上傳 GitHub Gist(:3814)；Quickstart dev 工具(:7251)；UtilityWorldObject 過時存檔機制(:3135, [Obsolete])。
- 關鍵發現：17 patch 中僅 3 個硬改原版行為——LanguageDatabase.SelectLanguage prefix-false 強制重啟(:7748)、ModsConfig.RestartFromChangedMods dev 自動重啟(:7870)、MainMenuDrawer quicktest 改接 quickstarter(:7651)；其餘為回呼掛點與 UI 注入（Dialog_Options 反射+transpiler :7599/:7609、EditWindow_Log 壓縮列表加按鈕 :7792、DebugWindowsOpener 工具列按鈕 :7692）。不碰 Scribe、不注入 MapComponent。
- 殘留物：HugsLibProxy GameObject(:209)、HugsTickProxy 假 Thing 進 TickManager(:544/:9988, isSaveable=false)。
- 舊 DLL：根目錄 Assemblies/ 有 RW1.0 用 HugsLib.dll 6.1.3＋0Harmony 1.2.0.1；LoadFolders 對各版本含 "/"。推斷 versioned DLL 以同相對路徑蓋掉根目錄版、0Harmony 1.2.0.1 仍會載入（惰性）——**未實測**，已在主文標註。
- 結論：裝著＝有全域影響但可枚舉；對零依賴的自家 mod 幾乎無干擾，注意點＝dev 模式自動重啟、進圖新聞彈窗/log 視窗改造、存檔 UWO 黏性、4 個 UI patch 疊加點。
- 產出：architecture/00_overview.md、details/pitfalls_and_global_patches.md、projects/…/hugslib/SOURCE_POINTER.md。未 commit（主線統一提交）。
