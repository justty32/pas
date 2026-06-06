# SpeakUp 分析 session log

- 確認 SpeakUp 自帶完整 C# 原始碼（SpeakUp/*.cs + 8 個 HarmonyPatches），不需反編譯本體。
- 讀 About.xml：packageId cn.speakup.ttyet，硬相依 brrainz.harmony 與 Jaxe.Bubbles。
- 讀核心源：DialogManager/Talk/Statement/ExtraGrammarUtility/Settings，確認對話＝本地 GrammarResolver 規則，無 LLM/API/網路。
- 釐清管線：TryInteractWith→ToGameStringFromPOV_Worker(暫存雙方)→GrammarResolver.Resolve(注入ExtraRules)→r_logentry tag→Ensue排程續話→InteractionsTrackerTick發射。
- 反編譯 Bubbles.dll 到 projects/rimworld_mods/interaction-bubbles/decompiled/；確認 Bubbles 靠 Verse.PlayLog.Add Postfix 抓 LogEntry，與 SpeakUp 程式碼零耦合（共用 PlayLog 解耦）。
- 在 projects/rimworld_mods/speakup/ 留 SOURCE_POINTER.md（指標，不整包複製）。
- 產出 architecture/00_overview.md、architecture/01_dialogue_pipeline.md、details/extension_points.md。
- 結論：擴充對話＝純資料(1.6/Patches XML)；新情境變數＝改 ExtraGrammarUtility.cs::ExtraRules；新觸發＝改 DialogManager 排程(高風險)或另開外掛 mod。
