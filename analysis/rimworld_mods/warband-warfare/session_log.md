# session_log（warband-warfare 分析，核心+擴充共用）

- [擴充agent] 分析 WAWLeadership.dll：指揮官RPG系統，CompLeadership掛pawn、六屬性硬編無Def、屬性→warband數值同步、世界地圖指揮官互動。
- [擴充agent] 分析 WarbandWarfareQuestline.dll：救援村莊任務為硬編C# Quest（QuestScriptDef空殼）、聯盟League元層、PolicyDef政策樹資料驅動、FactionTraitDef特質資料驅動。
- [擴充agent] 產出 architecture/02_questline_and_leadership.md + details/questline_leadership_extension.md（純XML vs C#接點）。未動 00/01/SOURCE_POINTER。
- [核心agent] 讀 About+1.6檔樹+核心DLL(12286行)：Warband:Site為核心世界物件，bandMembers=Dictionary<pawnKindDefName,int>非Pawn列表。
- [核心agent] 雇用=PlayerWarbandArrangement編組預設→成本Σ人數×combatPower×establishFeeMultiplier→普通(招募倒數)/立即(2x)落地，扣銀行或殖民地倉庫銀子。
- [核心agent] 攻擊=AttackLand生成真Pawn(MercenaryUtil)→CaravanEnter真實地圖實戰；NPC突襲=RaidEnemy incident，points只決定敵軍規模——非抽象結算。
- [核心agent] 5種升級(Elite/Engineer/Outpost/Psycaster/Vehicle)硬編C#子類非data-driven；Harmony群皆加掛非改數值。
- [核心agent] 純XML擴充：兵種池(任意符合PawnKindDef自動入選)/FactionTraitDef/PolicyCategoryDef/PolicyDef數值欄位(效果需workerClass)。
- [核心agent] 產出 architecture/00_overview.md、01_warband_mechanics.md、details/extension_points.md + projects端 SOURCE_POINTER.md。
