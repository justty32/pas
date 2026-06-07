# session_log — skyrim_mods 分析

- 起始：2026-06-06，Linux/Manjaro，Claude Code (Opus 4.8)，分析對象 `~/skyrim_mods/`（非 git，外部 mod 解壓目錄）。
- 目的：為 ModForge（`~/repo/ModForge`）拆解參考 mod「怎麼做到」，回饋 spec/builder 設計。

## 操作紀錄
- 解壓並探查四個指定 mod：JContainers SE、powerofthree's Tweaks(FOMOD)、Sofia Follower、RDO Final。
- 用 ModForge CLI `dump` 取得 Sofia(1741 records)/RDO(9765 records) 的 ESP record dump → `/tmp/mfdump/{sofia,rdo}.txt`（BSA 無工具解包，分析聚焦 ESP + 可讀 .psc）。
- 撰寫 README.md + architecture/{jcontainers,powerofthree-tweaks,sofia-follower,relationship-dialogue-overhaul}.md + details/dialogue-targeting-technique.md（後四篇由並行 subagent 產出）。
- 使用者追加三個 mod：SkyUI、UIExtensions、PapyrusUtil。
- 釐清：Nexus #32444「All in one」實為 Address Library（22 個 version bin），非 UIExtensions；真 UIExtensions=#17561 `.7z`，已正確解壓。
- dump SkyUI(7 quest)/UIExtensions(9 record)；PapyrusUtil 的 .psc 源碼齊全可直接讀 API。
- 撰寫 architecture/{skyui,uiextensions,papyrusutil}.md（並行 subagent 產出）。
- 更新 README 為七 mod 版 + Address Library 釐清；撰寫綜合 others/modforge-relevance.md。

## 當前狀態
- 七個 mod 分析全數完成（5 library + 2 內容範本）+ 1 篇 dialogue 投放技術細節 + 1 篇 ModForge 綜合。
- 尚未 commit（依 pas/ModForge 慣例，未經確認不 push；此處為 pas repo，可視需要 commit）。

## 核心結論（接手用）
- ModForge 的 scene/SM 設計已對齊工業級 mod；最大短期 ROI 是擴 condition 函式（GetIsVoiceType 等）解鎖「按類投放」。
- 範式級缺口：dialogue override vanilla record（做「對話包」用）、批次 per-NPC 內容展開、進階狀態後端(PapyrusUtil 優先)。
- 五個 library 皆 native/SWF 依賴 → 全部 opt-in，預設維持零依賴。詳見 others/modforge-relevance.md。
