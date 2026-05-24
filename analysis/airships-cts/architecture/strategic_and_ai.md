# Airships: Conquer the Skies — 戰略／戰役層 + AI 子系統分析

> 事實來源：`projects/airships-cts/src/com/zarkonnen/airships/*.java`（CFR 反編譯）。
> 輔助佐證：`data/help_en/*.txt`（玩法說明）。
> 目的：為「以 C++ 從頭重寫」提供戰略層與 AI 的可移植規格。
> 所有行號為反編譯後真實行號。

---

## 0. 全景：兩層架構 + 確定性鎖步

戰役有兩個明確分層：

- **戰略層（strategic / campaign）**：`CampaignWorld` + `WorldMap` 持有整個世界狀態，以固定 16ms 步長即時推進（非傳統回合制，見 §2）。AI（外交/城市/艦隊/英雄）都在這一層跑。
- **戰術層（tactical / combat）**：`Combat`（145KB，本報告不深入）負責逐艦逐模組的物理戰鬥。

兩層由 `CombatInfo` / `CampaignCombatIntent` 橋接（§4）。

**確定性核心**：整個 `WorldMap` 共用一個 seeded `GuardedRandom`（`WorldMap.r`，`WorldMap.java:124`）。`GuardedRandom` 內部就是一個 `new Random(seed)`（`GuardedRandom.java:13-15`）。所有 AI、地圖、戰鬥隨機都從它抽。多人連線採 **lockstep（鎖步同步）**：相同 seed + 相同指令序列 → 相同結果，並用 checksum 偵測 desync（`CampaignWorld.doTick_` 中 `StoredState`/`strategicChecksum`，`CampaignWorld.java:697-715, 833-852`）。`GuardedRandom.guard` 旗標在 `doTick()` 前後切換（`CampaignWorld.java:663-667`），用來標記「現在處於必須確定性的階段」。**這對 C++ 重寫是頭號移植風險**（§6）。

---

## 1. 戰略世界模型（誰擁有誰、資源、補給、民怨、科技、時代）

### 1.1 `CampaignWorld`（`CampaignWorld.java`）— 會話／流程容器
持有一場戰役的「執行環境」，而非世界本體：
- `WorldMap map`（`:107`）— 真正的世界狀態。
- `Empire player`（`:108`）— 本機玩家帝國（單機時即唯一人類；多人時為本端視角）。
- `CombatInfo combatInfo`（`:110`）— 當前正在進行的戰術戰鬥（null = 純戰略推進）。
- `Speed speed`（`:111`）+ `SPEED_DIV=8`（`:105`）— 推進速度倍率。
- 多人欄位：`mpClient`/`mpServer`（`:154-155`）、`frameQueue`（`:124`）、`storedStates`（checksum 用，`:141`）、`SAVE_VERSION=10620`（`:158`）。
- `playerOffers`（外交提案佇列，於 tick 清理，`:528`）。

### 1.2 `WorldMap`（`WorldMap.java`，~222KB）— 世界本體
核心欄位（`:121-218`）：
- **帝國與勢力**：`ArrayList<Empire> empires`（`:125`）、`ArrayList<MonsterNest> nests`（`:128`，怪物巢，會主動 raid）、`TreeMap<Relationship.Key,Relationship> relationships`（`:126`，外交關係矩陣）。
- **地形（grid）**：`boolean[][] water`（`:130`）、`int[][] cityOwnership`（`:131`，格→城市領地）、`boolean[][] roads`（`:132`）、`rivers`/`features`（`:136-137`）、`transient double[][] height/resistance`（`:185-186`，運算用不存檔）。
- **連通性快取**：`connectionCache`（`:217`）配合常數 `BY_SEA/BY_LAND/DIRECT_BY_LAND...`（`:210-216`）— 城市間「陸路直連 / 海路 / 不連」決定 AI 攻擊目標分類與補給。
- **時間與時代**：`int age`（`:139`，毫秒制世界時鐘）、`MS_PER_DAY=400`、`DAYS_PER_WEEK=7`（`:117-118`）、`StrategicEra era`（`:157`）、`int eraAge`（`:158`）、`EraModifier eraModifier`（`:159`，特殊時代修正，預設 NO_BONUS）、`endEraMeter`（`:167`）。
- **難度與規則開關**：`DifficultyLevel difficulty`（`:141`）、`EnumSet<ConquestToggle> toggles`（`:152`，可關掉 SUPPLY/DIPLOMACY/REPUTATION/ESPIONAGE/AUTORESOLVE 等）、`TechSpeedSetting techSpeed`（`:145`）、`MonsterSetting`/`heroFrequency`/`incidentFrequency`（`:146-148`）。
- **事件**：`ArrayList<Incident> incidents`（`:175`）+ counters（`:176-178`）。
- **AI 排程游標**：`smartEmpireIndex`（`:127`）、`smartNestIndex`（`:129`）— round-robin 讓每步只有一個帝國做「smart」決策（§2）。
- `GuardedRandom r`（`:124`）、`seed`（`:122`）。

距離常數：`MIN_CITY_DIST=25`、`MIN_NEST_DIST=7`、`SCALE_FACTOR=8`（`:110,114-116`）。

### 1.3 `Empire`（`Empire.java`，~102KB）— 帝國
核心欄位（`:85-194`）：
- 身分：`int id`（`:86`，外交 hash/排序用）、`name`、`CoatOfArms arms`、`playerControlled`（`:117`）、`ArrayList<String> playerNames`（多人共控）。
- **資源**：`private int money`（`:95`）、`moneyMs`（`:105`，每 `MS_PER_INCOME=5600`ms 結算一次收入，`:85`）、`reputation=50`（`:98`，0-100）。
- **領地**：`ArrayList<City> cities`（`:101`，`cities.get(0)` 視為首都基準點，見 `AIUtils.DistCmp`）、`ArrayList<Fleet> fleets`（`:102`）。
- **加成系統**：`BonusSet bonuses`（`:93`）+ `rewardedBonuses`（`:94`）— 幾乎所有數值（收入/民怨/補給/科技/上限）都透過 `EmpireStat.XXX.get(bonuses)` 取得，加成由科技/升級/英雄/時代動態疊加（見 `Empire.tick`，`:1747-1835`）。
- **科技**：`ArrayList<Tech.Choice> techs`（`:121`）、`Tech.Choice research`（`:122`，當前研究中）、`researchPoints`（`:124`）、`ConstructionStrategy constructionStrategy`（`:126`，AI 的造艦/科技藍圖）。
- **外交/間諜**：`DiplomacyAI diplomacyAI`（`:137`）、`ArrayList<Spy> spies`（`:103`）、`locAggressiveness`（`:107`，對各地點的攻擊性權重）、`aggressiveness`（`:108`）。
- **AI 狀態快取**：`aiTargets`（`:118`，攻擊目標清單）、`aiAvailableShips/Landships/Buildings`（`:183-188`，當前可造設計）、`aiConstructionSpent`/`aiUpgradesSpent`（`:160-161`，造艦 vs 升級花費比，影響城市 AI 取捨）、`smartAccum`/`fleetSmartIndex`（`:88-89`，自身 AI 排程）。
- 收入公式：`totalIncome = EMPIRE_BASE_INCOME + cityIncome + tradeIncome + tributeIncome`（`:1487-1489`）；`incomeBalance = totalIncome - 艦隊維護 - 防禦維護 - 升級維護 - 加冕 - 終局儀式 - 進貢 - 英雄`（`:1491-1493`）。

### 1.4 `City`（`City.java`，~47KB）— 城鎮／城市
- `boolean isTown`（`:56`）— **town（鎮）vs city（市）**是核心區分：只有 city 能造船（`canBuildShips`, `:275`）、能加冕、計入加冕所需城市數。
- 經濟：`int income`（`:49`）、`economicDamage`（`:52`，0-5，劫掠/征服造成，`MAX_ECON_DAMAGES=5`，每 `ECON_DAMAGE_RECOVERY_TIME` 回復 1，`City.tick:747-754`）。
- **民怨來源**：`ArrayList<UnrestSource> unrests`（`:96`）+ `unrest(wm, explain, max0)`（`:422`）。基底 `TOWN_BASE_UNREST`/`CITY_BASE_UNREST`（`:427`），疊加：英雄、敕令 edict、瘟疫 plagueLevel、未選征服方式 takeoverNeeded、剛被劫掠 postRaidCooldown、罷工 strike、玩家難度修正 `playerUnrestModifier`（`:428-429`）等。佐證 `__Unrest.txt`：收入按民怨百分比扣減、隨時代降低。
- 升級：`ArrayList<CityUpgradeType> upgrades`（`:70`）、`upgradesEverBuilt`（`:71`）。
- 征服流程：`takeoverNeeded`（`:59`）、`TakeoverMethod takeoverMethod`（`:57`，gentle/brutal/pillage，佐證 `__Takeovers.txt`）、`previousOwner`/`originalEmpire`（`:58,61`，影響領土主張 claim）、`postTakeoverCooldown`/`postTakeoverMethod`（`:67-68`）。
- 勝利條件相關：`coronation`/`coronationProgress`（`:76,78`，加冕）、`isRitualSite`/`finalRitual`/`finalRitualProgress`（`:84-87`，邪教終局儀式）。
- 建造佇列：`constructing`（繼承自 `MapLocation`，`ConstructionEntry` 含 ship/upgrade/refit/repair）、`getConstructionTarget()`（AI 規劃中的下一個目標）。

### 1.5 周邊型別
- `CityUpgradeType`（`CityUpgradeType.java`）— 升級定義：income/research/production/globalSupply/localSupply/unrest/reputation/maintenance（皆為 `BonusableValue`）、`enableShipBuilding`、`preventsPlague`、`gives`（給 Bonus）、`consumesBonus`、`forTown`、`aiBuildIfPossible`。每多一個同類升級成本約 +50%（佐證 `__City_Upgrades.txt`）。
- `CityClaim`（`CityClaim.java`）— 多帝國共同征服一城時的「主張強度」計算：`strength() = 原主加成 + 距離加成 + 艦隊強度加成 + 先前獲賞加成`（`:69-71`），由 `WorldMap.conqueror` 取最高者得城（`WorldMap.java:2517-2532`）。
- `StrategicEra`（`StrategicEra.java`）— 時代：`startTime`、`startTimePerEmpire`（隨帝國數延後）、`bonus`、`modifierChance`（觸發特殊 EraModifier 機率）。`get(wm)` 依 `wm.age` 決定當前時代（`:38-45`）。佐證 `__Eras.txt`：時代推進 → 間諜數↑、研究速度↑、城鎮民怨↓（允許更大帝國）。
- `EraModifier`（`EraModifier.java`，~18KB）— 特殊時代（豐年/黑暗時代/可派遠征 expeditions），含勝利條件 `eraEndsWhenResearched`/`eraEndsWhenUpgradesBuilt`/`eraEndsWhenControllingUpgrades`/`eraEndsWhenClearingNest`，影響 AI 目標優先序（見 `FleetAI` 與 `CityAI`）。

---

## 2. 更新節奏：固定步長即時推進（非回合制）

**結論：不是回合制，是固定 16ms tick 的即時模擬，速度可調。**

### 2.1 外層節流：`CampaignWorld.tick(ms, ss)`（`CampaignWorld.java:525`）
- 累加 `accumulatedMs += ms`（`:591`），以 `while (accumulatedMs >= 16)` 迴圈每次扣 16ms 呼叫一次 `doTick()`（`:594-609`）。即固定 16ms quantum。
- 多人模式：先從網路 `frameQueue` 取 frame（`:562-565`），依佇列長度動態縮放 `ms`（追幀/緩衝，`:570-582`）；frame 每 64ms 消費一個（`:716-719`）。沒 frame 就不推進（lockstep）。
- 單迴圈最多跑 6 次或 200ms 就讓出（`:607`），避免卡 UI。

### 2.2 內層一步：`doTick_()`（`CampaignWorld.java:669`）
若 `combatInfo != null`（戰術戰鬥進行中）→ 只 tick 戰鬥（`:774-803`），戰略凍結。
否則做一個戰略步（`:804-884`），`quantum = 2 * speed.getMsMult()`（`:805`）：
1. `smartEmpireIndex` round-robin +1（`:809`）— 決定**這一步哪個帝國做「smart」決策**。
2. 對每個帝國（`:811-824`）：
   - 空城帝國 → `map.removeEmpire`（`:813-815`，淘汰）。
   - 跳過玩家控制者（`:817`，玩家自己操作）。
   - `e.diplomacyAI.tick(...)` — 外交，傳入 `smart = (indexOf(e)==smartEmpireIndex)`（`:821`）。
   - `StrategicAI.tick(this, map, e, smart ? quantum : 0)`（`:823`）— 戰略/城市/艦隊/英雄/間諜/科技。
3. `map.tick(quantum, isMultiplayer)`（`:826`）— **世界推進**（見 §2.3）。
4. `resolveUncontestedSeaIntercepts` + 清理（`:828-831`）。
5. 多人 checksum（`:833-852`）。
6. 成就檢查（`:853-878`）。
7. `combatInfo = map.getNextCombat(...)`（`:879`）— **檢查是否有需要彈出的戰鬥**；有則 `waitingForCombatSetup=true` 並 return（§4）。

### 2.3 世界推進：`WorldMap.tick(ms, isMultiplayer)`（`WorldMap.java:2002`）
有勝利者就停（`:2003`）。`ms>0` 時依序：
1. `eraAge += ms`，重算時代 `StrategicEra.get(this)`，跨時代則擲骰決定是否啟用 EraModifier（`:2021-2072`）。
2. `eraModifier.hasBeenEnded` 檢查時代勝利條件（`:2073-2077`）。
3. `updateShipBonuses()` + `stats.tick`（`:2078-2079`）。
4. **每對帝國** `getRelationship(a,b).tick(ms)` — 外交關係衰減/到期（`:2086-2093`）。
5. `IncidentType.tickIncidents(ms, this)`（`:2094`）— 事件系統：round-robin（`incidentEmpireCounter`/`incidentTypeCounter`）對一個帝國嘗試觸發一種 IncidentType（`IncidentType.java:100-126`），頻率受 `incidentFrequency` 控；需開 DIPLOMACY toggle。
6. **每個帝國** `e.tick(ms, this)`（`:2096-2099`，見 §2.4）。
7. 清空城帝國（`:2100-2103`）。
8. **每個怪物巢** `n.tick(...)`，同樣 round-robin smart（`smartNestIndex`，`:2104-2112`）。
9. `Hero.tick`（`:2113`）。
10. `age += ms`、`timeSinceAIAttackVsHuman += ms`、`designateVillain()`（`:2114-2116`）。
11. 關係 `clean`、勝利者最終紀錄（`:2118-2125`）。

### 2.4 帝國一步：`Empire.tick(ms, map)`（`Empire.java:1743`）
- 重建 bonuses：清掉升級/英雄/時代給的，再依當前 techs/升級/英雄/時代重新疊加（`:1747-1835`）；設 `BROKE` bonus（`:1836`）。
- 圍城請求 BesiegeRequest 處理（`:1837-1850`）。
- 聲望衰減（往 19/50 兩個吸引子靠，每 `TIME_PER_REP_DECAY` 變 1，`:1864-1881`）。
- 遠征計時與回收（`:1891-1906`）。
- **每座城** `c.tick(ms, this, map)`（`:1910-1913`）— 建造進度、民怨來源衰減、瘟疫、征服計時、加冕/儀式進度（`City.tick:668-787`）。
- **收入結算**：`moneyMs += ms`，滿 5600 → `money += incomeBalance(map)`（`:1914-1918`）。
- **研究結算**：`researchPoints += researchOutput * ms`，滿則完成科技、套用 bonuses（`:1919-1933`）。
- **每支艦隊** `f.tick(ms, this, map)`（移動/補給，`:1943-1951`）。
- 間諜上限與 tick（`:1952-1971`）。

> **重寫提示**：「一回合」其實是「一個 16ms tick」。城市生產、收入、研究都是 **時間累積式**（`moneyMs`/`researchPoints`/`constructing.progress`），不是離散回合。AI 決策則用 round-robin 攤平到多個 tick（每步只一個帝國做重決策），這是效能考量也是確定性考量。

---

## 3. AI 決策

AI 分工：`StrategicAI`（總調度）→ 呼叫 `CityAI`/`FleetAI`/`HeroManagementAI`；`DiplomacyAI` 獨立由 `CampaignWorld.doTick_` 直接呼叫。難度 `AIQuality { INACTIVE, STUPID, NORMAL, SMART }`（`AIQuality.java:8-12`）。

### 3.1 `StrategicAI.tick(w, m, e, smartMs)`（`StrategicAI.java:46`）— 帝國總調度
- **smart 節流**：`smartAccum += smartMs`，每滿 16 才設 `smart=true`（`:56-61`）。非 smart（或 `deactivateAICheat`）只跑輕量：每城 `CityAI.simpleTick`、每艦隊 `FleetAI.simpleTick`（`:62-77`）。
- smart 步驟（`:78-280`）：
  1. 算 `incomeBalance` / `nonConstructionIncomeBalance`（`:78-80`）。
  2. `HeroManagementAI.manage(e, m, totalIncome)`（`:81`，§3.5）。
  3. 加冕就緒 → 在非 town 城啟動 `startCoronation`（`:82-92`）；終局儀式同理（`:93-103`）。
  4. 事件回應：`IncidentType.get(e,m).aiPickOption(m)`（`:104-106`）— AI 自動選事件選項。
  5. `AIConstructionUtils.updateDesigns`（`:107`，刷新可造設計 tier）。
  6. `doScience(m, e)`（`:108`，§3.6）。
  7. `targets(w, m, e)`（`:109`，§3.2，攻擊目標清單）。
  8. **間諜部署**：對所有城算 `spyQuality`，把間諜從最低分城移到最高分無間諜城（`:110-136`，受 `MAX_SPIES` 限）。
  9. **間諜行動**：`espionage`（`:134-136`，§3.4）。
  10. **城市防禦預算分配**：依城市數均分 `perCityDefenceMaintenanceBudget`，上限 `CITY_DEFENCE_BUDGET`（`:137-152`）。
  11. 算 `costBase`（自身總戰力，用於攻防權衡）（`:153-166`）。
  12. 瘟疫應對：找最嚴重瘟疫城、預備建防疫升級 `buildNow`（`:167-180`）。
  13. 統計各城研究/補給/生產，挑 `bestProductionCity`、`minNumberOfUpgradesInCities`（`:181-214`）。
  14. **每城** `CityAI.tick(...)`（`:216-221`，§3.3，傳入大量預算/上限參數）。
  15. 破產且赤字 → `AIConstructionUtils.scrapShips`（拆最便宜艦回血，`:222-224`）。
  16. 勳章設計（英雄擴充，`:225-230`）。
  17. **艦隊**：`fleetSmartIndex` round-robin（`:231-233`），只有被選中的艦隊跑完整 `FleetAI.tick`（含目標、攻擊權衡），其餘只 `simpleTick`（`:234-249`）。
  18. 遠征：若時代允許且自己不弱於鄰國 1.2 倍，派一半艦隊出遠征（`:250-280`）。

`attackFailed`（`:283-291`）：攻擊失敗後降低對該地點的 `locAggressiveness`（學習：下次不打），公式 `0.4 * min(舊值, 防/攻實際比)`。

### 3.2 目標選擇 `targets()`（`StrategicAI.java:472`）— 評分前的候選過濾
- 有快取（`aiTargets`）且戰爭 hash/城市集未變則重用（`:481-496`）。
- 對所有敵城（處於 WAR）分三類：陸路直連 `adj`、海路相連 `seaAdj`、其他 `nonAdj`（`:500-515`）。**新增此城會超過 `personality.maxConquestUnrest` 則跳過**（`:503-504`，民怨自我克制）。
- 怪物巢：除非個性 `attackOthersMonsterNests`，否則只打自己領地內的（`:516-527`）。
- 各類按 `DistCmp`（距首都距離）排序，合併取前 `NUM_TARGETS=4`（`:41,528-541`）。
- 後處理優先序：含「想要升級/特產」的城提前（`:546-553`）、加冕中/儀式中的城**最優先**（插到 list 頭，`:554-558`）。
- `withoutMostDamaged` 排除經濟損傷最大的城（剛打過的，`:562-572`）。

### 3.3 `CityAI.tick(...)`（`CityAI.java:114`）— 單城經營（評分式）
順序決策（先到先做，每步至多啟動一項建造）：
1. `simpleTick`：處理征服方式選擇 takeover（`:31-47`）。
2. 拆無用升級 `shouldScrapUpgrade`（純維護無產出、或重複供應、或研究停滯時拆掉，`:49-69`）。
3. 防疫升級 `buildNow` 優先（`:127-134`）。
4. 時代勝利升級（`eraEndsWhenUpgradesBuilt`）按 `cityUpgradesTargetSpendProportion` 比例建（`:135-143`）。
5. **一般升級評分** `upgradeQuality`（`:71-112`）：以個性年度目標（research/production/supply per year）與當前缺口加權；`aiBuildIfPossible` 直接給 1000；缺乏造船能力時 `enableShipBuilding` +200；高民怨時減民怨升級加權放大（`:89-95`）。挑最高分建造（`:144-162`，受 `aiUpgradesSpent` 比例與 `minNumberOfUpgradesInCities` 均衡限制）。
6. 防禦建築升級/修復（`:166-179`）。
7. **造艦/造防禦目標選擇**（`:180-301`）：
   - town 已有防禦就不再造（`:195-197`）。
   - 需要補給艦（`wantSupplyShip`：開 SUPPLY 且補給艦 < 總艦數/5，`SUPPLY_SHIP_RATIO=5`，`:343-345`）則造補給艦。
   - 否則在「建防禦建築」與「造機動艦」間擲骰權衡（`doBuilding`，依防禦維護預算與 `r.nextInt(3)`，`:209-212`）。
   - 造艦時依 `landshipFocus`、是否陸連敵人 `connectedByLandToEnemy` 選 airship/landship 設計，`Collections.shuffle` 隨機挑一個可造設計（`:250-287`）。
   - `numBonusConstructions` 受 `difficulty.maxAIBonusConstructions` 限（防 AI 濫造特殊艦，`:209,304-337`）。
   - 最終付款入列建造（成本/維護需可負擔、不能有未防禦城時還造艦，`:289-301`）。

### 3.4 間諜 `espionage()`（`StrategicAI.java:401`）+ `spyQuality()`（`:351`）
- `spyQuality`：基底 50，town -15；依關係調整（ALLIANCE -30 … WAR +15）；已有間諜 +20+網路等級；相鄰 +15；是攻擊目標 +15；加冕中 +50；終局儀式中 +100（`:355-398`）。
- `espionage`：對每個有間諜的目標城，列舉 `CitySpyAction`/`ShipSpyAction`，過濾成功率 ≥70%、冷卻、`minSpyInterval`，選 `aiPriority` 最高者執行（破壞加冕/儀式為特例不受間諜間隔限制，`:417-458`）。需開 ESPIONAGE toggle（佐證 `__Espionage.txt`）。

### 3.5 `HeroManagementAI.manage(e, m, totalIncome)`（`HeroManagementAI.java:21`）— 英雄管理
- 算英雄成本佔收入比 `heroCostPercentage`（`:24-26`）；< 20% 雇用、否則解雇尚未雇的（`:29-35`）。
- **CAPTAIN（艦長）**：指派到價值最高、無艦長、非特殊艦的船（`:36-64`）。
- **GOVERNOR（總督）**：用 `assignQuality` 評分指派到最佳城（優先 city 後 town，`:65-89`）。`assignQuality`（`:144-183`）= 收入變化 + 防禦預算補貼 + 民怨改善 + 研究×5 + 可清巢×50 + 敕令品質。
- 總督附加行為：清/移除領地內怪物巢（`:91-100`）、發敕令 `edictQuality` 最高者（`:101-110`）。`edictQuality`（`:185-227`）綜合金錢/研究/聲望（受 `reputationLossSensitivity` 調）/加速建造。
- 成本 > 30% 收入則裁員（先裁低價值艦長、town 總督，`:112-138`）。

### 3.6 科技 `doScience()`（`StrategicAI.java:297`）+ `getScienceOption()`（`:318`）
- 目標科技來自 `e.constructionStrategy.techs`（藍圖）；若時代有 `eraEndsWhenResearched` 且能趕在下個時代前研完，改衝該科技（`:301-314`）。
- `getScienceOption`：在目標科技的依賴樹中，挑「已滿足前置、tier 最低」的可研項（BFS 展開依賴，`:318-349`）。

### 3.7 `DiplomacyAI`（`DiplomacyAI.java`，~146KB）+ `DiplomacyPersonality`（~28KB）— 外交（評分核心）
**這是整個戰略 AI 最複雜的部分，純評分制（quality score），個性=評分權重表。**

關係等級 `Relationship.Level`：WAR / TRUCE / PEACE / NON_AGGRESSION_PACT / DEFENSIVE_PACT / ALLIANCE（見 `StrategicAI.spyQuality` switch，`:360-379`）。

- **`tick(me, w, m, ms, smart)`**（`:160`）：
  1. 需開 DIPLOMACY toggle（`:166`）。
  2. 對每個關係：更新 `EmpireRecord`、**回應對方提案**：`evaluateOffer > 0` 就 `agree`，否則 `reject`（`:179-211`），決策記入 `aiDiplomacyDecisionRecords`（可在 UI debug 看，`:190,198`）。
  3. 回應 challenge（DELEGATION/INSULT，機率制 `acceptDelegationProbability`/`insultBackProbability`，`:213-230`）。
  4. `diplomacyCooldown` 節流（`:232-236`），冷卻中不主動。
  5. 回應最後通牒 ultimatum：`acceptLikelihoodPercent = relativeQuality * ultimatumQualityDifferenceToLikelihoodPercent + agreeToUltimatumBaseline`，擲骰決定 accede/defy（`:239-262`）；自己發的 ultimatum 被拒則 `enforceThreatProbability` 決定是否執行（`:263-275`）。
  6. smart 且無待答時（`:281`）：被併吞判斷（單一 town 帝國找最佳併吞者，`:283-317`）；`activeEmpire` round-robin 推進，對其呼叫 `getDecision`（`:318-325`）並執行產出的 offer/ultimatum/challenge。
- **`getDecision(me, m, r, onlyThem, sb)`**（`:465`）：對每個（或指定）對手，`generateValidOffers` 生成所有合法提案（normal + forced），用 `evaluateOffer` 算「對我的價值 meVal」與「對對方的價值 themVal（以假定個性 `assumeOtherPersonality` 估）」，再用 `compromiseQuality`/`betweenAIsCompromiseQuality` 算妥協品質，挑最佳可行方案（`:510-560+`）。對 AI 對手要雙方都正收益；對人類玩家加 `unfairOfferForHumansBonus`（`:549`）。
- **`evaluateOffer(...)`**（`:831/835`）：把一份 offer 拆成各條款，計算 `newLevel - oldLevel` 的品質差，由各 `xxxQuality` 函式組成（war/peace/各種 pact/treaty/tribute/money/submission，見 `:779-885`）。
- **品質函式範例 `warQuality`**（`:1306`）：`q = warBaseline + 相對戰力×warRelativeStrengthFactor + 想要對方特產 + (不相鄰懲罰) - 其他戰爭數 - 民怨懲罰 + 擋人勝利 + 阻止對方加冕/儀式 + 戰意 warAggression + 對方低聲望加成 + 個性對該勢力 opinion`，最後 clamp 到 `[minWarQuality, maxWarQuality]`，再諮詢盟友戰意（`canConsultAllies`，`:1387-1399`）。結果快取 `warQualities`。
- **`DiplomacyPersonality`**：~150 個可調參數（`:19-171`），全部從 JSON 載入。例：`maxConquestUnrest=20`（民怨上限，影響攻擊目標）、`warBaseline`/`peaceBaseline`/各 pact baseline、`reputationLossSensitivity=3.0`、`takeoverMethod`（AI 偏好的征服方式）、`cityUpgradesTargetSpendProportion=0.4`（升級 vs 造艦花費比）、`assumeOtherEmpiresHaveThisPersonality`（推估對手用的個性）。佐證 `__AI_Personalities.txt`：個性影響外交評估，tooltip 可見各項貢獻。
- `EmpireRecord`（內部類，`:2594` tick）：記錄與某帝國的歷史（戰意 `warAggression` 隨和平時間上升、已問過/已給過的 offer、是否已提併吞），用於冷卻與不重複騷擾。

### 3.8 難度如何調節 AI（`DifficultyLevel.java`）
- `enemyAI`（AIQuality）— 直接門檻：例 `FleetAI` 中「考慮敵方馳援」需 `enemyAI >= NORMAL`（`FleetAI.java:352`），「考慮敵方補給縮放」需 `>= SMART`（`:362`）。
- 數值乘數（隨 `age` 透過 `rampUpTime` 線性 ramp 到滿）：`aiIncomeMultiplier`/`aiProductionMultiplier`/`aiResearchMultiplier`/`aiResupplyMultiplier`（`:44-70`）。
- `attackInterval`/`playerAttackInterval`（攻擊冷卻，後者專門節制對人類玩家的攻擊頻率，`FleetAI.java:412`）、`maxAIBonusConstructions`、`extraAIStartingTechs`、`aiExtraMoney`、`aiAvoidWarWithHumanPlayersInOtherWars`（外交對人類友善度）、`minSpyInterval`、`playerUnrestModifier` 等。

### 3.9 `FleetAI`（`FleetAI.java`）— 艦隊行動（攻防價值權衡）
`tick(w, m, e, f, targets)`（`:161`）核心是**攻擊期望值計算**：
- 撤退/解圍/被入侵處理（`:164-200`）；在我方可造船城則升級/修復/拆小艦（`:201-245`）。
- **馳援盟友/自城**：算敵艦能否比我先到目標，估算後決定是否分兵馳援（`:254-298`）。
- **發動攻擊**（`:307-471`）：對每個 target 算 `defenceValue`（`AIUtils.getValue`：基底防禦 700 + 各防禦建築 cost + 駐軍 cost，`AIUtils.java:39-57`）與 `attackValue`（艦隊 cost）。
  - `enemyAI >= NORMAL` 時把「能比我先趕到的敵方馳援艦隊」也算進 defenceValue；`>= SMART` 還用補給可達性 `supplyScalingFactor` 縮放敵援（`:352-373`）。
  - 加入盟友圍城艦隊價值（`:374-409`）。
  - **攻擊條件**：`defenceValue <= attackValue * getAggressivenessFor(e, loc)`（`:410`）才出擊；`getAggressivenessFor` 取 `locAggressiveness`（學習過的）或 `aggressiveness`。
  - 對人類城有額外冷卻 `playerAttackInterval`（`:412`）。
  - 選 `relativeForce`（攻/防比）最高或時代優先目標出擊（`:414-428`）。
  - 出擊後設 `warConsiderDelay`（隨機冷卻，`:436,442`），可向人類盟友發圍城請求 BesiegeRequest（`:447-455`）。
- 無攻擊則嘗試合併艦隊（`mergeTarget`，≤16 艦，`:458-470`）、離開怪物巢/回造船城（`:472-501`）。
- `simpleTick`（`:78`）：只處理撤退與解圍轉攻擊。
- 補給：開 SUPPLY toggle 時，每次移動都用 `FuelEfficiencyCmp`（cost/補給容量比）排序後砍到補給夠用為止（`:276-280, 344-349`）。佐證 `__Supply.txt`。

---

## 4. 戰鬥橋接（戰略 ↔ 戰術）

### 4.1 戰略層如何「發起」一場戰鬥：`WorldMap.getNextCombat(g, cw)`（`WorldMap.java:2534`）
每個戰略步末由 `doTick_` 呼叫（`CampaignWorld.java:879`）。優先序掃描所有帝國找出一場待處理戰鬥：
1. `getInterceptCombat`（攔截，`:2540`）
2. `getNearCityCombat`（城邊野戰，`:2547`）
3. `getCityCombat`（攻城，`:2554`）
4. `getRaidCombat`（怪物巢劫掠，`:2563`）
找到就指定 `conquestID`（`++combatIDCounter`）並回傳 `CombatInfo`。

**關鍵分流（`getCityCombat`，`:2610-2627`）**：
```
若 攻方盟友 或 守方 任一方含人類玩家(containsPlayerControlled)
    → makeCombat(...) 建立真實 Combat（彈出戰術戰鬥畫面）
否則
    → quickResolveCombat(...) 直接靜默自動解算（純 AI vs AI 不進戰術層）
```
即 **AI 對 AI 的戰鬥永遠走 autoresolve（quickResolve），完全不建 Combat 物件**——這是巨大的效能來源，也是重寫時的關鍵設計。

### 4.2 丟進 Combat 的資料 / `CombatInfo`（`CombatInfo.java`）
`CombatInfo` 是橋接資料包（`:43`）：`Combat combat`、`attackingFleets`/`defendingFleets`、`defendingLoc`、`nearLoc`、`aiQuality`、`attackerAIValue`/`defenderAIValue`（雙方總 cost+100，給 autoresolve 預估與 UI，`:51-67`）。
建立真 Combat 用：`new Combat(g, TimeOfDay.getRandom(r, 地形, 季節, ...), r, cw)`（`WorldMap.java:2956` 等）——時段/季節影響戰鬥（晝夜閃電機率等）。
`CampaignCombatIntent`（`CampaignCombatIntent.java`）是 UI intent，戰鬥結束時呼叫 `ss.w.immediatePostCombat()`（`:27-31`），離開時 `postCombat()`（`:45-48`）。

### 4.3 結果回寫
**`immediatePostCombat()`**（`CampaignWorld.java:887`）— 戰鬥剛結束、玩家離開前：鎖定各方損失 `lostLocked`、處理投降艦的接收（boarding）、歸還登艦兵、依攻守勝負設修復狀態 RepairStatus、修剪無用艦（`:905-940`）。
**`postCombat(uncontested)`**（`CampaignWorld.java:943`）— 完整回寫：
- 判定 `attackerWon`/`defenderWon`（`:953-954`）。
- 英雄事件、艦長受傷（隨機週數）、船員經驗（勝方/監戰巢額外加成）（`:958-1062`）。
- 攻擊失敗 → `StrategicAI.attackFailed`（降低攻擊性，`:1065-1069`）。
- **重組艦隊**：戰後存活艦放回原 fleet/守地，全滅艦隊移除（`:1071-1130`）。
- 玩家損失訊息、移除被毀防禦建築（`:1131-1154`）。
- 攻方艦隊移動/回家（`:1155+`）。
- 佔領由 `quickResolveCombat`/conquest 路徑處理城易主（見下）。

**佔領與易主**（在 `quickResolveCombat` 攻方勝時，`WorldMap.java:2436-2468`，真戰鬥走對應 `postCombat` 邏輯）：
- `conqueror(city, fleets)` 比各 `CityClaim.strength()` 取最高者得城（`:2440, 2517-2532`）。
- 舊主移除城（空了則 `removeEmpire`）、新主加城、設 `takeoverNeeded`（非原主時需選征服方式）、清路徑快取、發征服訊息（`:2441-2467`）。

### 4.4 Autoresolve 估算演算法：`WorldMap.autoResolveCombat(...)`（`WorldMap.java:2266`）
**不進戰術層的戰鬥估算（也用於 UI 的建議結果）**：
- 人類參與會放大對側強度：守方有人類 → 攻方強度 ×3（`d=3.0`）；攻方有人類 → 守方強度 ×3（`defenderStrengthMult=3.0`）；`damageDiv` 也加大（`:2279-2281`）。**意即 autoresolve 對人類偏保守/懲罰**（佐證 `__Autoresolve.txt`：手動打通常更好）。
- 雙方強度 = Σ `getResourceAdjustedStrength() × mult`，艦長另計 `singleCombatCost`（`:2291-2304`）。
- **隨機消耗迴圈**（`:2311-2348`）：`while 攻 > 守/2 且 守 > 攻/4 (且劫掠未達上限)`：擲骰 `roll < 攻強+艦長` → 對守方造成 `(攻強+艦長)/damageDiv` 傷害，隨機抽守方艦扣除（足夠則擊沉、累計死亡 crew 數）；否則對攻方造成對應傷害。
- 結束時 `attackerStrength > defenderStrength` 即攻方勝（`:2364`），勝方加回非戰鬥艦（補給艦等，`:2355-2363`）。
- 劫掠 loot 上限 `min(3, 5 - economicDamage)`（`:2307`）。
- `CombatInfo` 建構時（若開 AUTORESOLVE toggle 且非怪物巢）就預跑一次 autoresolve，存 `autoAttackerRemainingShips`/`autoDefenderRemainingShips`/`autoAttackerWon`/`autoLoot`，供 UI 顯示「建議結果」（`CombatInfo.java:68-86`，`canAutoresolve()`）。

> **此 autoresolve 用 `WorldMap.r` 抽隨機，故結果是確定性的**（同 seed/同狀態 → 同結果），這是多人鎖步所必需。

---

## 5. 任務／戰役系統（Missions）

與 Conquest（程序生成戰役）平行的是**手作任務**系統（`data/missions/` 下如「The Kraken」「Boarding Action」等資料夾）。

- **`MissionSequence`**（`MissionSequence.java`）— 一個任務序列（劇情關卡集）：`missions_info.json`（HEADER_FILE）含多語 `name`/`description`、`tags`、`modIDs`、`expansions`、`numMissions`（`:31-45, 77-159`）。每個 mission 存成 `mission_N_meta.json` + `mission_N_combat.json`（`:104-108, 147-149`）。UGC 前綴 `MISSIONSEQ`，可上傳 Steam Workshop。
- **`MissionSequence.Mission`**（內部類，`:250`）：
  - `playerSideIndex`（玩家屬哪一方）、`playerBudget`（玩家可花預算建艦）、`enemyAIQuality`（敵方 AIQuality，預設 NORMAL，`:257`）。
  - `sideArms[]`（雙方紋章）。
  - `Combat combat`（`combatF` 載入的實際戰鬥場景，`:342-354`）。
  - `texts: EnumMap<TextSlot,...>`，TextSlot = `intro / victory / defeat`（`:356-361`）— 劇情文字（多語）。
- **`MissionBackend`**（`MissionBackend.java`）— 檔案系統後端（`FileScreen.Backend`）：從三處列舉任務——`Static:`（遊戲內建 `data/missions`）、本機 `missions/`、`Steam:`（Workshop UGC）+ 各 enabled mod 的 `missions/`（`:124-158`）。`isMission` 以是否含 `missions_info.json` 判定（`:47-52`）。`localOnly` 模式只列本機與內建。

> **與 Conquest 的關係**：Mission 是「預設好雙方艦隊/地形/AI 難度的單場或連續戰術戰鬥 + 劇情文字」，不跑 §1-3 的戰略模擬，直接走戰術 `Combat`。Conquest（戰役）才是完整的 `CampaignWorld`/`WorldMap` 模擬。兩者共用底層 `Combat`。

---

## 6. C++ 重寫建議

### 6.1 戰略狀態 struct 分解（對應 §1）
```cpp
struct WorldMap {            // 世界本體（可序列化、可 checksum）
    uint64_t seed; Rng rng;  // 單一確定性 RNG（見 6.4）
    int age_ms;              // 毫秒制世界時鐘（非回合）
    std::vector<Empire> empires;
    std::vector<MonsterNest> nests;
    RelationshipMatrix relationships;     // (id,id)->Relationship
    Grid<bool> water; Grid<int> cityOwnership; Grid<bool> roads; // 地形 grid
    ConnectionCache connections;          // 城市連通性快取（陸/海/不連）
    StrategicEra era; int eraAge_ms; EraModifier eraModifier;
    DifficultyLevel difficulty; EnumSet<ConquestToggle> toggles;
    std::vector<Incident> incidents;
    int smartEmpireIndex, smartNestIndex; // round-robin 游標
};
struct Empire {
    int id; std::string name; CoatOfArms arms; bool playerControlled;
    int money, money_ms, reputation;      // 時間累積式收入
    BonusSet bonuses, rewardedBonuses;    // 所有數值的來源
    std::vector<City> cities; std::vector<Fleet> fleets; std::vector<Spy> spies;
    TechState tech; ConstructionStrategy strategy;
    DiplomacyAIState diplo;               // EmpireRecord map + 個性指標
    AiState ai;                           // aiTargets, locAggressiveness, 預算快取...
};
struct City { bool isTown; int income; int economicDamage; /*0-5*/
    std::vector<CityUpgrade> upgrades; ConstructionQueue constructing;
    TakeoverState takeover; CoronationState coronation; /* unrest sources */ };
```
- **`CampaignWorld` 拆成「會話/網路層」**（speed、frameQueue、checksum、player 視角），與 `WorldMap`（純模擬狀態）分離——這是反編譯碼已有的良好邊界，務必保留。
- **`BonusSet` 是中樞**：幾乎所有數值經 `EmpireStat::get(bonuses)`。建議實作為固定大小 bitset/向量 + 一張靜態 `EmpireStat` 表（從 JSON 載入 base+per-bonus 修正）。這讓科技/升級/英雄/時代的數值疊加統一化。

### 6.2 更新節奏（對應 §2）
- 固定 16ms tick 的 `world.tick(quantum)`；速度只改 `quantum` 倍率，**不改步長**（保證確定性）。
- 保留 **round-robin smart**：每 tick 只一個帝國/巢做完整重決策（`smartEmpireIndex`），其餘走 `simpleTick`。這同時是效能與確定性設計，別改成「每帝國每幀全跑」。
- 城市生產/收入/研究/建造一律 **時間累積**（`accumulator >= threshold` 觸發），不要改成離散回合。

### 6.3 AI 模組化（行為/評分函式）
- 分四個無狀態（或弱狀態）模組：`StrategicAI`（調度）、`CityAI`、`FleetAI`、`DiplomacyAI`，各自接 `(world, empire, ...)`。HeroManagementAI 可併入 StrategicAI。
- **評分函式統一介面**：所有決策都是 `int quality(...)` 形式（war/peace/pact/upgrade/edict/spy/fleet-attack）。建議定義
  ```cpp
  struct QualityBreakdown { int total; std::vector<std::pair<std::string,int>> terms; };
  ```
  保留「可解釋」（反編譯碼用 `StringBuilder e` 累積每項貢獻，對應遊戲 tooltip）。重寫時這對除錯 AI 極有價值。
- **個性=參數表**：把 `DiplomacyPersonality` 的 ~150 個欄位做成從 JSON 載入的 `struct`，AI 演算法本身不寫死數值。`assumeOtherPersonality` 機制（用假定個性估對手價值）要保留，否則 AI 對 AI 談判會崩。
- 攻擊權衡核心公式（`FleetAI`）：`attack if defenceValue <= attackValue * aggressiveness(loc)`，其中 `aggressiveness(loc)` 是**會學習的**（攻擊失敗後 `attackFailed` 降權，見 `StrategicAI.java:283-291`）。務必保留 per-location aggressiveness map。

### 6.4 戰略↔戰術介面契約
- 單一入口 `std::optional<CombatInfo> WorldMap::getNextCombat()`，回傳 null 表純戰略推進。
- **分流規則必須照搬**：任一方含人類 → 建真實 `Combat` 並暫停戰略；純 AI vs AI → `quickResolveCombat` 靜默解算。否則大地圖會因每場 AI 戰鬥都進戰術層而爆炸。
- 回寫契約：`immediatePostCombat()`（鎖定損失、處理投降/登艦、設修復狀態）→ `postCombat()`（重組艦隊、城易主、英雄/經驗、攻擊性學習）。建議把這拆成 `CombatResult { winner, attackerLosses, defenderLosses, captured, loot, deaths }` 的純資料結構，回寫邏輯吃這個結構（反編譯碼是直接操作 Combat.Side，耦合較重，重寫可解耦）。
- `CombatInfo.attackerAIValue/defenderAIValue`（總 cost）是輕量強度估計，給 UI 與 autoresolve 用，保留。

### 6.5 確定性考量（移植風險，**最高優先**）
- **單一 seeded RNG**：整個 `WorldMap` 共用一個 `Rng`（對應 `WorldMap.r`）。**禁止**在 AI/模擬中用任何非此來源的隨機（系統時間、全域 rand、`std::random_device`、執行緒本地 RNG、hash 順序）。
- **抽牌順序必須完全一致**：round-robin 游標、`Collections.shuffle(list, rng)`（`CityAI` 造艦選擇用到，`:231,277`）、容器走訪順序都會影響 RNG 序列。C++ 用 `std::unordered_map` 走訪序不穩 → **desync 來源**。對任何「走訪後抽 RNG 或做決策」的集合，改用有序容器（`std::map`/`std::vector` + 顯式排序，如 Empire 按 `id` 排）。反編譯碼已大量用 `id` 排序（`CombatInfo.java:158`、外交 `warHash` 用 `id`）正是為此。
- **浮點確定性**：Java 用 `strictfp`（幾乎每個類都標）+ `StrictMath`。autoresolve、外交相對戰力、aggressiveness 都用 `double`。C++ 要跨平台一致需：固定 `-ffp-contract=off`、避免 `-ffast-math`、考慮以整數/定點重寫關鍵路徑，或接受「單機可不嚴格、多人才需嚴格」的折衷。**這是 C++ 多人最大的坑**。
- **lockstep 同步模型**：若要做多人，照搬 frame-queue + 週期 checksum（`StoredState` 對 `age`/`combatTime`/`hash`）+ desync 偵測。`GuardedRandom.guard` 在 Java 已是空殼（`check()` 為空，`GuardedRandom.java:51-52`），原意是「在非確定階段抽 RNG 就報錯」的防呆，重寫時可實作成 debug-only assert：標記「現在不該抽 RNG」的區段。
- **存檔版本**：`SAVE_VERSION=10620`（`CampaignWorld.java:158`），全狀態 JSON 序列化（`toJSON`/from-JSON）。重寫建議沿用版本化序列化，並把 `transient` 欄位（快取/UI 狀態，`Empire`/`WorldMap` 中大量 `transient`）排除在存檔與 checksum 外。

### 6.6 其他移植風險
- **反編譯雜訊**：多處有 `void var19_33` 之類 CFR 反編譯產生的偽變數（如 `StrategicAI.java:48,172,215`、`HeroManagementAI.java:145,174,180`、`FleetAI.java:106,308`）。這些是反編譯瑕疵，原意需從上下文推斷（通常是某個迴圈累加值或 best-candidate 指標），**不要照抄字面**。
- **town vs city** 的區分滲透整個系統（造船/加冕/民怨/防禦預算），重寫時應為一級概念。
- **toggles 驅動的可選系統**：SUPPLY/DIPLOMACY/REPUTATION/ESPIONAGE/AUTORESOLVE 都可關。AI 各處都先查 toggle（如 `FleetAI` 補給、`DiplomacyAI.tick` 查 DIPLOMACY、`CityAI.upgradeQuality` 查 REPUTATION/SUPPLY）。重寫時把這些做成 feature flag，AI 行為分支對應之。
- **EraModifier 的勝利條件**會反向影響 AI 目標優先序（`eraEndsWhenResearched`→科技、`eraEndsWhenControllingUpgrades`→艦隊目標、`eraEndsWhenClearingNest`→打巢）。這是 AI 與規則的耦合點，需一併移植。
```
