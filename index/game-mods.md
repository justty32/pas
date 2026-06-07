# Mod 與 Mod 框架分析

> [← 回總索引 index.md](../index.md)。本檔收錄遊戲 mod／mod 框架的逆向與開發導向分析。

| 專案名稱 | 類型 | 分析深度 | 狀態 | 核心內容摘要 |
| :--- | :--- | :--- | :--- | :--- |
| **RimWorld** | 遊戲模組/引擎 | 高 (Architecture+Tutorial) | 已遷移 | 包含 AI、派系、地圖系統與豐富的 C# 開發教學。 |
| **RimWorld Mods（群組）** | RimWorld 1.6 Workshop mod 分析群組 | 中 (Architecture+Tutorial, create 導向) | 28 mod 全數已分析 (2026-06-07) | `analysis/rimworld_mods/`，反編譯/源碼在 `projects/rimworld_mods/`。11 批分析，涵蓋：**核心框架**（Vehicle Framework／Fortified Features／Exosuit／Ariandel Library SCMF／RimSim 經營框架／CQF）、**世界玩法**（Rim War／Empire Refactored／Faction Territories／Warband Warfare／VOE）、**內容包**（DMS 機兵／VBGE／MobileDragoon／Ancient Urban Ruins）、**地圖機制**（MultiFloors／Deep And Deeper／RV+PD／SimplePortal）、**工具/對話**（World Tech Level／Loading Progress／Simple Warrants／SpeakUp／Interaction Bubbles）等。每 mod 皆以「純 XML 可做 vs 必須 C#」二分＋擴充接點為核心交付。**完整逐 mod 表見 `analysis/rimworld_mods/README.md`。** |
| **Skyrim Mod** | 遊戲模組 | 極高 (Classified) | 已遷移 | 深度分類分析 (NPC, Magic, 3D)，含 CommonLibSSE-NG。 |
| **Skyrim Mods（群組）** | Skyrim SE mod 參考分析群組（ModForge 導向） | 中 (Architecture×7 + detail + 綜合) | 分析完成 (2026-06-06) | `analysis/skyrim_mods/`，對象在 `~/skyrim_mods/`（外部解壓目錄，非 git）。為 ModForge（`~/repo/ModForge`）拆解七 mod「怎麼做到」。**5 library**：JContainers(容器/JFormDB)、PapyrusUtil(輕量 per-form KV + JsonUtil)、powerofthree's Tweaks(45 項引擎修正)、SkyUI(MCM 框架 SKI_ConfigBase)、UIExtensions(runtime 清單/輸入/輪盤選單)；**2 內容範本**：Sofia(隨從=主控 quest+數十 comment quest+scene phase→topic+54 package)、RDO(對話 overhaul=override 1612 vanilla record + GetIsVoiceType×GetInFaction×GetRelationshipRank 按類投放)。ESP 用 ModForge CLI `dump` 解析(BSA 無工具解包)。釐清 Nexus#32444 實為 Address Library 非 UIExtensions。綜合結論：ModForge scene/SM 已對齊；最大 ROI=擴 condition 函式解鎖按類投放；範式缺口=dialogue override+批次 per-NPC 展開。詳見 `analysis/skyrim_mods/README.md` 與 `others/modforge-relevance.md`。 |
| **MC Mod** | 遊戲模組 | 高 (Architecture) | 已遷移 | Millenaire-Reborn 的村莊邏輯、AI 目標系統與文化體系分析。 |
| **下一站江湖Ⅱ (jianghu-2)** | 武俠 RPG / Unity Mono Mod (BepInEx) | 中 (實戰 Mod 完成) | 分析中 | ilspycmd 反編譯 Assembly-CSharp（3004 cs，置於 `projects/jianghu-2/`）。BepInEx 注入環境踩坑全解：MonoBehaviour.Update 不 tick→Harmony patch `AppGame.Update`、plugin fake-null→`ReferenceEquals`、`PlayAnim` 回傳值說謊→`HaveAnim`。首個 mod「閒置 NPC 原地坐下(chusheng_sit)」已上線運作。含通用開發指南＋API 速查＋mod 原始碼（`analysis/jianghu-2/mod_src/`）。 |
