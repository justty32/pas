# Simple Warrants 分析 session log

- 辨識：pb3n.SimpleWarrants（2676828755，作者 pb3n+Taranchuk），懸賞/通緝佈告欄；僅相依 Harmony。
- 自帶完整原始碼 1.6/Source/*.cs + SimpleWarrants.sln（~4682 行），直接讀源不反編譯。
- 讀 Warrant.cs：abstract Warrant:IExposable 基類（非 Def），抽象 AcceptChance/SuccessChance/MaxRewardValue；WarrantStatus enum。
- 型別系統：Warrant_Pawn(生擒/擊殺雙賞)/Warrant_TameAnimal/Warrant_Artifact 三封閉子類，靠 TargetType enum(Human/Animal/Artifact)。
- WarrantsManager:GameComponent 持 available/accepted/created/taken/postponed 五列表；MainTabWindow_Warrants(695行)UI；WarrantRequestComp 通訊台請求；TransportersArrivalAction_ReturnWarrant 送回領賞。
- 接單後地圖/任務生成走純 XML QuestScriptDef(vanilla DSL+QuestNode_GetSitePartDefsByTagsAndFaction 吃 SW_Camp tag)，僅 1 自訂節點 QuestNode_WarrantFailed。
- 小巧 Harmony patch：Pawn_Kill/Raid/JobGiver_AIFightEnemy 等接管擊殺/襲擊判定。
- 結論：目標種類封閉 C#(加新種需 C#)；通緝理由(RulePackDef)/營地(SitePartDef tag)/任務流程(QuestScriptDef)/平衡純 XML。SimpleSettings.cs=Taranchuk 通用反射設定框架。
- 產出 architecture/00_overview.md、details/extension_points.md、projects/.../SOURCE_POINTER.md。
