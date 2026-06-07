# Warband 核心機制深入剖析

> 來源全部出自 `projects/rimworld_mods/warband-warfare/decompiled/WarfareAndWarbands/WarfareAndWarbands.decompiled.cs`（下稱 `core.cs`）。

## 1. warband 是什麼物件？
**是世界地圖 `WorldObject`，而且是 `Site` 的子類**：`Warband : Site`（`core.cs:3192`）。
- XML 端：`WorldObjectDef` defName `WAW_Warband`，`worldObjectClass=WarfareAndWarbands.Warband.Warband`，掛兩個 comp：`WorldObjectCompProperties_PlayerWarband`（核心，DLL:4176）與 `WAWLeadership.…PlayerWarbandLeader`（LD DLL）。
- 用 `Site` 而非 `Caravan` 的好處：可被攻擊時自行生成地圖（`PostMapGenerate`→`SpawnDefenders` `core.cs:3360/3398`），且能用 site 的「進入/拜訪」浮動選單。
- 玩家 warband 落地時帶 `WAWEmptySite` site part；NPC warband 帶原版 `Outpost`（`WarbandUtil.SpawnWarband` `core.cs:3910/3917`）。

關聯的世界物件（同 XML）：
- `WAW_WarbandRecruiting`（`WorldObject_WarbandRecruiting` `core.cs:1734`）：**招募倒數**狀態，倒數結束才轉成真正的 `Warband`。
- `WAW_WarbandVassal`（`WorldObject_VassalWarband` `core.cs:7426`）：附庸傭兵團（玩家出錢委託，由 vassal 派系操作）。

## 2. 兵員怎麼存？→ `Dictionary<string,int>`（兵種 defName → 人數），不是 Pawn 列表
- `Warband.bandMembers : Dictionary<string,int>`（`core.cs:3194`）。key 是 `PawnKindDef.defName`，value 是該兵種人數。
- 平時 warband **不持有任何實體 Pawn**，只有這張計數表（外加領袖那一個真 Pawn）。Pawn 只在「進地圖打」的當下被臨時 `PawnGenerator.GeneratePawn` 生出來；退場 (`ExitMapPatch` `core.cs:9388`) 即被 `DeSpawn` 銷毀。
- 可選兵種清單由 `WarbandUtil.GetSoldierPawnKinds()`（`core.cs:3838`）動態算出：所有 `isFighter && race.Humanlike && 非貴族` 的 `PawnKindDef`，依 `combatPower` 排序，**再加上玩家在遊戲內客製出來的兵種**（`GameComponent_Customization.GeneratedKindDefs`）。
- 存檔：`Scribe_Collections.Look(bandMembers …)`（`core.cs:3646`），純字串/整數，存檔安全。

### 雇用流程
1. 玩家在主分頁/通訊台用三步精靈（`Window_ArrangeWarband` `core.cs:3659`，`StepOne/Two/Three`）填 `playerWarbandPreset.bandMembers`（全域編組預設，`PlayerWarbandArrangement` `core.cs:2777`）。最低門檻 5 人（`ValidateCreation` `core.cs:2880`）。
2. 成本 = `GetCostOriginal()`（Σ 人數 × 該兵種 `combatPower`，`core.cs:2815`）× `WAWSettings.establishFeeMultiplier`。立即版再 ×2（`GetCostEstablishmentImmediate` `core.cs:2848`）。
3. 在世界地圖選格落地：`CreateWarbandWorldObject`（`core.cs:2931`）→ 浮動選單兩選項（普通=招募倒數，立即=2×費用直接成軍，`SelectWarbandWorldObjectOptions` `core.cs:2953`）。
4. 付款 `TryToSpendSilverFromColonyOrBank`（`core.cs:4041`）：優先扣銀行帳戶，不足再從**任一玩家殖民地倉庫**的銀子實扣。
5. `PostAdd`（`core.cs:3242`）：若 `bandMembers` 空，依派系自動生成戰鬥群（玩家＝複製 preset；NPC＝`GenerateNPCCombatGroup`）。

### 補充 / 重編 / 升遷
- 重新編組：`Window_ReArrangeWarband`（`core.cs:3075`）→ `SetNewWarBandMembers`（`core.cs:2983`）只補差額成本（`GetCostExtra`）。受冷卻限制（`CanFireRaid`）。
- 戰場上把單一傭兵「升遷」為正式殖民地成員：`CompMercenary.TryToPromote`（`core.cs:2664`）——付該 pawn `MarketValue`，`SetFaction(Faction.OfPlayer)`，從此脫離 warband 計數。
- 受傷成員：`PlayerWarbandInjuries`（`core.cs:6937`）記錄哪些兵種因戰損暫時不可用，需恢復天數。

## 3. 世界地圖移動
- `WarbandPather`（`core.cs:4657`，`IExposable`）自製世界尋路器，`Warband.DrawPos => worldPather.TweenedPos`（`core.cs:3218`），每 tick `worldPather?.Tick()`（`core.cs:3377`）。
- 玩家下令移動：`MoveWarbandCommand`（`core.cs:8118`）→ `OrderPlayerWarbandToResettle`（`core.cs:3528`）世界選格 → `PlayerWarbandResettleManager`（`core.cs:5422`）。移動速度可被升級覆寫（`upgradeHolder.MoveSpeed`）。
- 是否顯示移動 gizmo 受升級 `CanMove` 控制（`WorldObjectComp_PlayerWarband.GetGizmos` `core.cs:4193`）。

## 4. 攻擊聚落 / 與其他派系交戰
gizmo 集中在 `WorldObjectComp_PlayerWarband.GetGizmos`（`core.cs:4187`）：移動、攻擊、解散、提領戰利品、重編、改名。

攻擊流程（**核心結論：進真實地圖實戰，非抽象結算**）：
1. `OrderWarbandToAttackCommand`（`core.cs:8136`）→ `PlayerWarbandManager.OrderPlayerWarbandToAttack`（`core.cs:5606`）世界選目標。
2. 校驗：有活躍成員、冷卻已過、目標是敵對 `MapParent` 或任務目標、距離 ≤ `playerAttackRange=10` 格（`core.cs:5618`）。
3. 選打法 `PlayerWarbandAttackOptions`（`core.cs:8198`）：陸攻 `AttackLand`、空投 `AttackDropPod`（需升級且目標已有地圖）、升級提供的額外打法。
4. `AttackLand`（`core.cs:5669`）→ 付費（若升級 `CostsSilver`）→ `WarbandUtil.OrderPlayerWarbandToAttack`（`core.cs:3971`）：
   - `MercenaryUtil.GenerateWarbandPawns(warband)`（`core.cs:8967`）把 `bandMembers` 表逐一 `PawnGenerator.GeneratePawn` 實體化（玩家版會套用顏色、裝備品質=升級 `GearQuality`、技能加成、領袖本人）。
   - `CaravanMaker.MakeCaravan(...)`（或 Vehicle Framework 版）組成商隊。
   - `GetOrGenerateMapUtility.GetOrGenerateMap` 生成/取得目標地圖，`CaravanEnterMapUtility.Enter(...)` **真的進場由玩家操控戰鬥**。
5. NPC warband 攻擊：`SpawnOffenders`（`core.cs:3423`）在目標地圖邊緣生成 pawn 並掛 `LordJob_AssaultColony`；防守時 `SpawnDefenders`（`core.cs:3398`）掛 `LordJob_DefendPoint`。

### NPC 反過來突襲玩家 warband
- `GameComponent_PlayerWarbandRaidManager`（`core.cs:4371`）：每 `RaidPlayerDuration=300000` tick 擲骰（`raidPlayerWarbandChance` 設定）挑一個玩家 warband。
- `PlayerWarbandRaidUtil.RaidPlayer`（`core.cs:4534`）：`GetOrGenerateMap` 生成 warband 所在地圖、清霧、`IncidentParms{ points = max(DefaultThreatPointsNow, 250) }` 排入 `IncidentDefOf.RaidEnemy`。**points 只決定來犯敵軍規模**，玩家要親自進地圖守。
- `MapComponent_WarbandRaidTracker`（`core.cs:4459`）：守住沒敵人就發捷報信、`forceQuitTicks=60000` 後強制收地圖。

→ 整套戰鬥是 **RimWorld 原生的「進地圖實際打」**，沒有任何「戰力相減判勝負」的抽象結算。`points` 一律只當敵方/援軍生成的威脅值。

## 5. 兵員實體化的細節（`MercenaryUtil`）
- `GenerateWarbandPawns`（`core.cs:8967`）：玩家版只取「活躍（未受傷）成員」`injuriesManager.GetActiveMembers`；NPC 版取全表。會加領袖、加升級提供的 `ExtraPawns`。
- 每個生出來的 pawn 都跑 `SetMercenaryComp`（`core.cs:8282`）掛上 `CompMercenary`（記 warband、服務派系、兵種名、是否玩家控制）。`CompProperties_Mercenary` 由 `HumanlikePatch.xml` 注入**所有** `thingClass="Pawn"` 的 ThingDef。
- 客製兵種：若該兵種名命中 `GameComponent_Customization.CustomizationRequests`，會 `CustomizePawn` 套用玩家自訂外觀/裝備/技能（`core.cs:9186`）。

## 6. 領袖、升級、銀行（與其他子系統的耦合點）
- 領袖：`PlayerWarbandLeader`（`core.cs:7099`，核心定義）持有一個真 Pawn；`WorldPawnPatch`（`core.cs:9341`）把領袖在世界 pawn 池的狀態設為「保留」。實際領袖能力/UI 在 WAWLeadership DLL。
- 升級：`PlayerWarbandUpgradeHolder`（`core.cs:6152`）一次只能掛一個 `PlayerWarbandUpgrade`（抽象基類 `core.cs:5986`）。五種硬編子類：Elite/Engineer/Outpost/Psycaster/Vehicle。升級覆寫攻擊/移動/空投/裝備品質/維護天數等行為。
- 銀行：`WAWBankAccount`（`core.cs:1589`）＋戰利品 `PlayerWarbandLootManager`（`core.cs:5203`，`IThingHolder`）；可把撿到的物資原樣提領、換成銀子、或存入銀行帳戶。

## 7. Harmony patch 群（核心 DLL 改了原版什麼）
`WAWHarmony` 靜態建構（`core.cs:954`）統一註冊：

| Patch（位置） | 目標方法 | 作用 |
|---|---|---|
| `CommsPatch`（`core.cs:984`） | `Building_CommsConsole.GetFloatMenuOptions` | 通訊台加「開派系資訊分頁」選項 |
| `GetHomeFactionPatch`（`core.cs:9403`） | `QuestUtility.GetExtraHomeFaction` | 讓無 home faction 的傭兵歸屬隱藏 `PlayerWarband` 派系 |
| `ExitMapPatch`（`core.cs:9377`） | `Pawn.ExitMap` | 傭兵離場時轉回 `PlayerWarband` 派系並 DeSpawn（不留實體 pawn） |
| `WorldPawnPatch`（`core.cs:9341`） | `WorldPawns.GetSituation` | 領袖在世界 pawn 池標為保留狀態(9) |
| `CaravanGizmosPatch`（`core.cs:9361`） | `Caravan.GetGizmos` | 商隊加「就地建立 warband」按鈕 |
| `WorldObjectGizmosPatch`（`core.cs:9423`） | `Pawn_RoyaltyTracker.GetGizmos` | 地圖上加「全員撤退」 |
| `MapParentGizmosPatch`（`core.cs:10558`） | MapParent gizmos | warband 地圖相關 gizmo |
| `AnyHostileToPlayerCheckPatch`（`core.cs:10526`） | 敵意判定 | 配合 warband 地圖收圖邏輯 |
| `SettlemntDestroyedPatch`（`core.cs:1569`） | 聚落被毀 | 戰況/同盟相關 |
| `BetterGCHarmony`（`core.cs:10151`，條件載入） | Better GC | 防止傭兵 pawn 被垃圾回收誤殺 |

均為「加掛選項 / 改派系歸屬 / 配合自製世界物件」性質，**沒有改動原版核心戰鬥數值或勝負判定**。
