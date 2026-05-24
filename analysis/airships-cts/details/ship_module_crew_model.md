# Airships: CTS — 船艦／模組／船員 執行期實體模型 + 可加成數值系統

> 面向「用 C++ 從零重寫」的剖析。事實來源＝CFR 反編譯 Java（`projects/airships-cts/src/com/zarkonnen/airships/`），所有行號均為真實行號。
> 涉及檔案：`ModuleType.java`、`Module.java`、`Airship.java`、`Crewman.java`、`BonusableValue.java`、`BonusSet.java`、`Bonus.java`、`Wheel/Leg/Tentacle/Tether.java`、`Tile.java`、`GameSetting.java`。
> 資料來源（JSON）：`data/ModuleType/*.json` 等（已用 `CANNON.json` 交叉驗證）。

---

## 0. 全域心智模型（先讀這段）

一艘船 = **格子集合 (Tile grid)**。每個 16px 方格 (`Tile`) 同時持有：
- 一個 `Module`（執行期實例，可橫跨多格 w×h；同一個 Module 物件被它覆蓋的每個 Tile 共用引用）。
- 一個 `ArmourPlate armour`（逐格的裝甲，獨立 HP）。
詳見 `Tile.java:43-46`（`int x,y; ArmourPlate armour; Module module`）。

三層分離：
1. **定義層 `ModuleType`**（Loadable，由 JSON 載入，全程唯讀、單例共享）—— 幾乎所有數值欄位都是 `BonusableValue<T>`。
2. **實例層 `Module`**（放在某船 (x,y)；持火焰/HP/彈藥/冷卻等可變狀態）。
3. **容器層 `Airship`**（持 `modules`、`tiles`、`crew`，負責物理、連通性、HP 重算、指令點）。

數值取值的核心介面是 `someType.getXxx(ship.currentBonuses)`：`ModuleType` 存的是「公式」，傳入該船目前生效的加成集合 `BonusSet` 才解出實際數字。

---

## 1. Type vs Instance 分離

### 1.1 ModuleType（定義；唯讀單例）
- 繼承 `Loadable`，建構子 `ModuleType(JSONObject o)` 於 `ModuleType.java:440` 解析 JSON。
- 結構不變欄位（非 Bonusable）：`int w, h`（`ModuleType.java:88-89`，**固定**整數，由 JSON `"w"/"h"`）、各種 `boolean[]`（門/單面性，見下）、`categories`、`availableFor`。
- 大量 **`BonusableValue<T>` 公式欄位**（`ModuleType.java:90-267`），例如：
  - `hp`(90)、`destroyedHP`(91)、`destructionLength`(92)、`fireHP`(105)、`explodeHP`(106)、`explodeDmg`(107)、`explodeRadius`(108)、`explodeFuzeLength`(109)、`weight`(111)、`firedWeightDecrease`(112)、`coal/ammo/repair/water`(113-123)、`crew/optionalCrew/recommendedGuards/fixedGuards`(169-173)、`command`(128)、`lift`(130)、`propulsion`(131)、`reload`(134)、`clip/ammoPerClip`(137-138)、`blastDmg/penDmg/directDmg`(143-149)、`fireArc`(181)、`adjacencyBonusStrength`(226)、`structuralStressAmount`(228)、`shipHPBonus`(176)…
  - 取值一律透過 getter，例如 `getHp(BonusSet)` `ModuleType.java:1442`、`getFireHP` 1538、`getExplodeDmg` 1546、`getAdjacencyBonusStrength` 1857、`getCommand` 1649、`getLift` 1657、`getPropulsion` 1665。
- 門 / 連通性（**非 Bonusable，是 `boolean[]`，建構時定死**）：
  - `leftDoors[h]`、`rightDoors[h]`、`upDoors[w]`（`ModuleType.java:212-214`；預設只有底排 `leftDoors[h-1]=rightDoors[h-1]=true`，見 541-545；JSON `leftDoors/rightDoors/upDoors` 覆寫，705-742）。getter：`getLeftDoors/getRightDoors/getUpDoors` 1885-1895。
  - `frontOnly/backOnly/topOnly/bottomOnly`（162-165）控制裝甲面向。
- 結構性 `boolean`：`instantlyDestroyed`(93)、`destroyEntireShipOnDestruction`(94)、`isWeapon`(190)、`isRam/isSail`(179-180)、`ignoreHPAdjacency`(227)、`reloadCoalFromSelf`(133)、`runsWhenDestroyed`(249)、`usesSuspendium`(252)。
- 部件規格（**唯讀**，供實例 new 出對應物件）：`springs`(232)、`wheelSpecs`(233)、`legSpecs`(234)、`tentacleSpecs`(236)。

> 關鍵衍生用法：`explodeRadius` 不是獨立 JSON，而是用 `BonusableValue.derive(explodeDmg, …)` 從 explodeDmg 推導：`r = floor(30 + sqrt(dmg*2.5))`（`ModuleType.java:562-568`）。重寫時注意 derive 鏈。

### 1.2 Module（執行期實例）
建構子有兩個：`Module(Airship, ModuleType, x, y)`（`Module.java:2042`，新建）與 `Module(JSONObject, Airship)`（2124，載檔）。欄位（`Module.java:76-156`）分兩類：

**序列化（存檔，是模擬狀態）：**
- `ModuleType type; Airship ship; int x, y`（76-79）。
- `int hp`(110)、`lowestHP`(111)、`holdOnHp`(112)、`fire`(106)、`explodeFuze`(107)、`burntOut`(108)、`destructionTime`(113)。
- 武器狀態：`ammoLeft`(100)、`clipReloadCooldown`(101)、`shootAccumulator`(102)、`reTargetAccumulator`(103)、`retryFindingTargetCooldown`(104)、`msUntilCoal`(105)、`msSinceFired`(130)、`fired`(115)、`weaponAngle`(136)。
- 光束：`firingBeam`(122)、`beamAge`(123)、`beamStart/EndPositionX/Y`(125-128)、`beamShotsFired`(129)。
- 資源回充計數 `ammoRegen/coalRegen/repairRegen/waterRegen`(95-98)；`boolean[] ammoForClip`(99)。
- `EnumMap<Resource,Integer> resources`(142) —— 實際彈/煤/水/修存量（**注意：序列化時逐項展開成 `o.put(Resource.name(), v)`，見 toJSON 2068-2070；讀回 2161-2164**）。
- `int[] damageDealt/damageNotDealt`(151-152)；`externalPaint`(80)。
- `ArrayList<Job> jobs`(143) —— 由 `setupJobs()` 重建（不直接序列化，但 Crewman 用 `jobModule/jobIndex` 索引指回，見 §5）。
- 序列化清單見 `toJSON` `Module.java:2065-2122`。

**transient（執行期重算，不序列化）：** 全部標 `transient`：
- `maxHP`(109) —— **每次 `recalcHPs()` 重算**（見 §2.4）。
- `animOffset/variant`(81-82)（亂數視覺）、`glowAmt`(89)、`numCrewTmp/numGuardsTmp`(91-92)。
- 物理部件實例：`wheels/legs/tentacles`(83-87)、`tether`(88)、`touchingGround`(93)、`prevShipXForWheels`(94)。建構時依 type 的 spec new 出（2053-2061 / 2166-2174）。
- 渲染/暫態：`recoil`(137)、`barrelAnimation*`(138-141)、`subBeamFlickers`(124)、`shellOpen`(153)、`fireMode`(154)、`hidden/noValidTarget/noArcFound`(118-120)、`damageReported`(116)、各 `time`(114)。
- `fireMode`(154 `DirectControlFireMode`，玩家直控用)。

> **C++ 陷阱**：`maxHP` 是 transient → 載檔後必須立即跑一次 `recalcHPs()` 才正確；`wheels/legs/tentacles/tether` 也必須在 deserialize 後依 spec 重建。`resources` 用 EnumMap，重寫時用固定大小 `int[Resource::COUNT]`。

---

## 2. 逐格模擬（火焰、傷害、爆炸、解體、相鄰加成）

### 2.1 常數（`Module.java:64-75`）
```
ADJACENCY_BONUS                 = 0.4
ADJ_BASE                        = 0.7
INITIAL_FIRE                    = 6      // 點燃初始 fire 值
INITIAL_SPREAD_FIRE             = 3      // 蔓延而來的初始 fire 值
FIRE_INCREASE_RATIO             = 4.0e-5 // 火勢自增 roll
FIRE_DAMAGE_RATIO               = 1.3e-4 // 火每 ms 對自身造成 1 點傷害的 roll
FIRE_WALL_DMG_RATIO             = 1.0e-4 // 火對裝甲(牆)傷害 roll
FIRE_WALL_DMG_RATIO_REDUCE_PER_BLAST_ARMOUR = 1.0e-5 // 每點 blast 吸收減免
FIRE_SPREAD_RATIO               = 6.0e-6 // 無門蔓延
FIRE_SPREAD_RATIO_DOORS         = 6.0e-5 // 有門蔓延(×10)
EXPLODE_P                       = 0.2    // 爆炸觸發係數
BREAK_APART_HP                  = -16    // 解體門檻係數(見 2.5)
GLOW_PER_MS                     = 0.0025
```

### 2.2 HP / fireHP / 火焰每 tick（`Module.tick`，`Module.java:599` 起）
火焰段在 `Module.java:867-936`（**全部用 `c.r.nextDouble()`，確定性 RNG，見 §6**）：
1. **熄滅（晝夜效果）**：`fire>0` 且 `r < timeOfDay.effect.fireExtinguishChance * ms` → `fire--`（867-872）。
2. **火對自身傷害**：`r < 1.3e-4 * fire * ms` → `doDamage(1)`（876-878）。
3. **火對裝甲傷害**：對每個屬於本模組的 Tile，`r < (1.0e-4 - 1.0e-5 * armour.getBlastDmgAbsorb()) * fire * ms` → `armour.hp = max(0, hp-1)`（880-884）。**blast armour 透過降低係數來抵抗火牆傷害**。
4. **火焰蔓延**（上/下/左/右四方向；`Module.java:885-932`）：對相鄰未著火、`hp>0`、`fireHP>0` 的模組計算蔓延機率：
   ```
   fireSpreadRollVs = (door ? 6.0e-5 : 6.0e-6)
                    * fire * ms
                    * neighbour.fireHP / neighbour.hp_base / neighbour.w / neighbour.h
   // 再乘上指揮官易燃修正、徽章易燃修正、艦隊易燃倍率
   fireSpreadRollVs *= (100 + captain.flammabilityPercent)/100
                     * (100 + ship.flammabilityPercentFromMedals)/100
                     * fleetFlammabilityMult
   if (r < fireSpreadRollVs) neighbour.fire = 3   // = INITIAL_SPREAD_FIRE
   ```
   - 門的判定：上方向用 `this.getUpDoors()[xx]`（889）；左/右需**雙向都有門**（`getLeftDoors()[yy] && leftT.getRightDoors()[...]`，913 / 924）—— 重寫時注意門是「兩格各自的門都要開」。
5. **火勢自增**：`r < 4.0e-5 * fire * ms` → `fire++`（933-935）。
6. **HP<=0 善後**：`fire=0; burntOut=true`（937-940）。

> 著火來源（`fire = INITIAL_FIRE = 6`）由命中/燃燒武器設定（不在本檔，見 `Shot/Tile.hit`）。

### 2.3 爆炸與解體（同 `Module.tick`）
- **爆炸判定**（`Module.java:941-946`）：
  ```
  adjExplodeHP = type.getExplodeHP() * maxHP / type.getHp()   // 依當前 maxHP 縮放
  explodeChanceAdjust = (100+captain.explosionRiskPercent)/100 * fleetExplosionRiskMult * (100+ship.explosionRiskPercentFromMedals)/100
  if (explodeFuze==0 && hp>0 && hp<adjExplodeHP && explodeDmg()>0
      && adjExplodeHP*ms*0.2*r*explodeChanceAdjust > hp)   // 0.2 = EXPLODE_P
      explodeFuze = type.explodeFuzeLength()
  ```
- **引信倒數→爆**（947-965）：每 tick `explodeFuze -= ms`；到 0 時 `doDamage(eDmg*2)`、`ship.explosionAmount += eDmg`、`explode(c,…)`（粒子/音效，`Module.java:1203`）、`c.doSplashDmg(... eDmg, explodeRadius ...)`（範圍傷害）。
- **`explodeDmg()`**（`Module.java:581-593`）：基礎 `getExplodeDmg()`，再按 `ammoLeft/clip` 與 `resources[AMMO]/ammo容量` 線性縮放（彈藥越多炸越狠）。
- **`dealDestructionDamage()`**（418-437）：模組消失時對四周相鄰模組施加 `ceil(neighbour.hp_base * 0.8 / (2w+2h))` 的傷害（解體擴散）。

### 2.4 相鄰加成 → 影響 maxHP（`Module.calcMaxHP`，`Module.java:187-222`）
```
maxHP = type.getHp(currentBonuses)
if (!type.ignoreHPAdjacency()):
    maxAdjacents = w + h
    adjacents = Σ 邊界相鄰模組的 type.getAdjacencyBonusStrength(...)   // 上下各掃 w 格、左右各掃 h 格(198-213)
    if (ship.type==BUILDING && 貼地)  adjacents += w               // 建築貼地視為有支撐(214-216)
    adjacents = min(adjacents, maxAdjacents)
    maxHP = ceil(maxHP * (0.3 + 0.8 * adjacents/maxAdjacents))      // 218: 孤立模組僅 0.3 倍 HP
maxHP += bonusHPPerTile * w * h                                     // 來自 shipHPBonus 模組(220)
maxHP = (int)(maxHP * structuralStressHPMultiplier)                // 結構應力懲罰(221)
```
- `0.3 + 0.8 * ratio`：完全被包圍(ratio=1) → 1.1×；完全孤立 → 0.3×。**鼓勵密實船體**。
- 由 `Airship.recalcHPs()`（`Airship.java:4167-4175`）對所有模組統一觸發，每當增刪模組或解體後呼叫。

### 2.5 模組移除與「解體成 chunk」
- **判定消失**（`Airship.tick` 內，`Airship.java:2715-2746`）：對「在邊緣 (`isAtEdge`) 且 `hp <= type.getDestroyedHP()`」的模組：
  - 有 `destructionLength` → 計時 `destructionTime`，到時 `destroyModule`（2721-2737）。
  - 否則 `hp -= ms` 慢慢爛，直到 `instantlyDestroyed || hp <= type.getHp() * -16`（**這就是 `BREAK_APART_HP=-16` 的語義：負的基礎 HP 的 16 倍**）才 `destroyModule`（2739-2745）。
  - `destroyEntireShipOnDestruction` → 把全船所有模組 `hp = min(0, hp)`（2747-2753）。
- **連通性切割 `splitIfNeeded`**（`Airship.java:2330-2443`）：
  1. `regenerateTileGrid()`（重建 `tileGrid[h][w]`）。
  2. `chunks(null)` 做 4 向 flood fill（**單純鄰接，不看門**，`Airship.java:2262-2291`）。
  3. 孤立單格 chunk 直接 destroy（2336-2343）。
  4. 多 chunk 時，保留「存活模組總重量最大」的 chunk 為本船，其餘各 new 一艘 `Airship`（"Fragment of …"），搬移其 `modules/tiles/crew/boarders`，再對雙方 `layout() / recalcHPs() / assignJobs()`（2347-2442）。
- **兩種 flood fill 要分清**：
  - `chunks(Module ignore)`（2262）—— 純物理鄰接，用於「物理上是否相連／解體」。
  - `pathChunks(Module ignore)`（2211）—— **看門**（`leftDoors/rightDoors/upDoors`），用於「船員能否走到」。`hasMultipleChunks` 兩者皆查（1327）。

---

## 3. 船艦物理（升力 vs 重量、推進、轉向、指令點）

`Airship` 繼承 `GridBody`/`Body`，採通用「力累加器」積分（`xForce/yForce`、`xSpeed/ySpeed`），重量即質量。

### 3.1 重量與質量
- `updateWeight()`（`Airship.java:1717-1731`）：`weight = Σ module.type.getWeight() + Σ tile.armour.type.getWeight()`；已打空的一次性武器扣 `firedWeightDecrease`（1723-1724）。
- `getMass() = max(weight, 10)`（`Airship.java:3017-3019`）；`getCollisionMass()` 同（3012）。

### 3.2 升力 vs 重量 → 升降（垂直）
- `getLift()`（`Airship.java:1786-1808`）：`Σ module.lift（僅可在戰中補給者）+ Σ armour.lift`，再乘指揮官 `liftPercent`、徽章 `liftPercentFromMedals`，超充懸浮(superchargeSuspendiumTime) ×2。
- **服務升限** `serviceCeiling()`（5517-5522）：
  ```
  ceiling = pow(max(1, (lift*400*2/mass - 400) * 30), 2/3)
  ```
  即升力相對質量越大，能飛越高。`availableSuspendiumForce`（5451-5454）依「離地板高度」衰減：離地越高，可用懸浮力越小 → 自然平衡到升限。
- **垂直力** `suspendiumForceForY(ty, …)`（5494-5497）：朝目標高度 `altitudeOrder` 施加上推力，上限為 `availableSuspendiumForce`。基準 `mass * 0.001`，上升乘 `/0.88`、下降乘 `0.88`（不對稱，下沉較易）。由 `tick` 在 2823 / 2941-2952 套用到 `yForce`。
- 沒有獨立「重力常數」：重力 = `mass*0.001` 的等效力，懸浮力與之抗衡。

### 3.3 推進（水平）與最高速
- `availablePropulsion(...)`（5595-5642）：`Σ module.propulsion`（只算 `canRun()` 的；陸行艦需腳/輪著地，downLegs/downWheels 不足時 ×0.5 或 0，5602-5628），乘指揮官/徽章/爆速/逆風修正。
- 水平力直接 = 推進力：`xForce += availablePropulsion(true) * speedOrder.powerMult`（2804）。
- **終端速度** `availableSpeed()`（5717-5719）：`min(maxXSpeed, sqrt(propulsion / mass / frontAirFriction()))`；`frontAirFriction = 0.001 + frontDrag*0.002/5`（3002-3004）。即速度由「推進力 = 空氣阻力 (∝v²)」平衡決定。

### 3.4 轉向（翻面）
- 轉向不是連續旋轉，而是「翻面」(`flipped`) 並耗時間：`turningCost() = 5 + w*15 + 500/speed + weight/10`（5538-5544）。
- `tick` 中 `flipMs += ms`，達 `availableTurningCost()` 才完成翻面（2807-2813）。轉向期間 `enginesRunning=true`。

### 3.5 指令點 commandPoints（指令冷卻）
- `commandPointsRequired()`（5175-5193）：基礎 700 + 每活躍工作船員 `commandPointsRequired` + 每模組 `w*h*5 + extraCommandPointsRequired`，全乘 16；再乘指揮官/徽章冷卻修正；下限 100。
- `commandPointsGenerated()`（5205-5217）：`cp = Σ command模組.getCommand * staffProportion`；回傳 `max(minGen, ceil(log(cp*1.5)*4))`（**對數遞減**）。
- 累積（`Airship.tick`，2766）：`commandPoints = clamp(0, required, commandPoints + generated*ms*(1+fleetCommandBonus)/(fleetCommandCooldownMult+0.01))`。
- `readyForCommand()`（5151-5153）：`paralysis<=0 && momentOfDoubt<=0 && commandPoints>=required && generatesCommandPoints()`。下達指令後 `commandPoints=0`（5146-5147 `commandGiven`）。
- `isPermanentlyNotUnderCommand()`：`notUnderCommandMs > 500`（447-448）；無指令時一次性武器/升力/推進可被「釋放」(release) 自動運轉。

> 連通結構：模組透過 Tile grid 連續放置，連通性由 §2.5 兩種 flood fill 維護；被打斷即解體。

---

## 4. 加成系統（`BonusableValue<T>` / `BonusSet` / `Bonus`）—— C++ 重寫的關鍵抽象

### 4.1 概念
- `Bonus`（`Bonus.java`）是 Loadable enum-like：每個 bonus 有 `ordinal()`（首次查表決定，128-132）。來源 = Tech 選擇（`getTech()` 165-173）、EraModifier、特定模組 `providesBonus`、相鄰等。
- `BonusSet`（`BonusSet.java`）：一艘船「目前生效的所有 bonus」。內部 = `boolean[] contains`(12) + `long[] data`(13) 位元集合。核心操作：`containsAll`(57)、`intersects`(65)、`add/remove`(83-93)、`clone`(165)。
- `BonusableValue<T>`（抽象，`BonusableValue.java:20`）：一個「可被加成修改的數值公式」。核心 API：
  - `T get(BonusSet)`（36）—— 解出實際值。
  - `String explain(BonusSet, formatter, transform)`（38）—— 產生 tooltip 拆解。
  - `List<String> descriptions(BonusSet)`（40）。

### 4.2 五種實作（對應 JSON 形態）
| 子類 | JSON 形態 | get() 行為 | 行號 |
|---|---|---|---|
| `NoBonus<T>` | `42` 或 `"key": 42` | 永遠回 base | 1044-1066 |
| `SingleBonus<T>` | `{ "base":X, "BONUS":Y }` | 含該 bonus 回 Y，否則 X | 977-1042 |
| `SetBonus<T>` | `{ "base":X, "cases":[{"bonuses":[…],"value":…}] }` | 第一個 `containsAll` 的 case | 555-620 |
| `ObjectVariantBonus<T>` | `{ "base":…, "BONUS_A":…, "BONUS_B":… }`（物件型） | 第一個命中的單 bonus | 622-674 |
| `IntArithmeticBonus` / `DoubleArithmeticBonus` | `{ "base":X, "deltas":{…}, "multipliers":{…}, "dividers":{…} }` | **先加全部 delta，再乘全部 mult/div**，最後 clamp[min,max] | 729-975 |

> 算術型求值順序（**重要，重寫要照搬**，`DoubleArithmeticBonus.get` 740-752 / `IntArithmeticBonus.get` 860-872）：
> ```
> value = base
> for each active bonus: value += delta_i        // 全部加完
> for each active bonus: value *= mult_i / div_i // 再全部乘
> // Int 版最後 clamp(min, max) 並截斷成 int
> ```
- `CANNON.json` 驗證：`penDmg = { base:40, multipliers:{ INCREASED_CANNON_DAMAGE:1.2, MASTER_METALLURGIST:1.2, HEAVY_GUNNERY:1.5 } }`、`reload = { base:3100, multipliers:{ FASTER_CANNON_RELOAD:0.8, HEAVY_GUNNERY:1.3 } }`、`explodeHP/explodeDmg = { base:30, SAFER_CANNONS:0 }`（SingleBonus）。

### 4.3 derive（衍生公式鏈）
`BonusableValue.derive(from, d)`（101-132）：把一個 BonusableValue 包成另一個（保留 bonus 結構，逐 case/變體套用 `d.derive`）。例：`explodeRadius` 從 `explodeDmg` 衍生（`ModuleType.java:562`）；`appFragments/appWreckage/externalFragments` 從外觀衍生（472-485, 682）。

### 4.4 explain() 如何拆 tooltip
以算術型為例（`DoubleArithmeticBonus.explain` 767-828）：先印最終值，再括號內逐 active bonus 印 `+Δ from BONUS` / `xN from BONUS` / `÷N from BONUS`（用 `Lang._t("from_bonus_x", …)`）。`SingleBonus.explain`（1004-1036）印 `值 (+差 from BONUS)`。

### 4.5 C++ 對應建議
- `Bonus` → `enum class Bonus : uint16_t`，全域固定編號（取代 Loadable 動態 ordinal）。
- `BonusSet` → `std::bitset<N_BONUS>`（直接拿到 `containsAll = (a & b)==b`、`intersects = (a&b).any()`）。**比 Java 的 long[] 更乾淨**。
- `BonusableValue<T>` → 兩條路線：
  1. **`std::variant`**：`using BV = std::variant<NoBonus<T>, SingleBonus<T>, SetBonus<T>, VariantBonus<T>, ArithmeticBonus>;`，`get()` 用 `std::visit`。型別安全、零虛函式。
  2. **模板 + 多型**：`template<class T> struct BonusableValue { virtual T get(const BonusSet&) const = 0; };`（接近原版，但有 vtable 與堆配置）。
  - 建議路線 1（variant），因為形態只有 5 種且固定，且 `get()` 是熱路徑（每幀對每模組呼叫多次）。
  - `T` 主要是 `int`/`double`/`bool`，以及指標型（指向 `Appearance/Arc/CrewType` 等定義）。指標型用 raw pointer 指向唯讀單例池即可。
- **快取**：原版每次 `getXxx(currentBonuses)` 都即時求值。`currentBonuses` 只在增刪模組/換船長時變（`recalculateBonuses` 6020-6035）→ C++ 可在 `currentBonuses` 變動時，把每個模組常用數值（hp, weight, lift, propulsion, reload…）一次性解算進 `Module` 的 POD 快取欄位，戰鬥迴圈讀快取，省掉 visit。這是最大效能槓桿。

---

## 5. 船員 AI（`Crewman.java` + `Airship.assignJobs`）

### 5.1 Job 抽象（定義在 `Module.java` 內部類）
每個 `Module` 在 `setupJobs()`（`Module.java:2213-2243`）按 type 數值產生 Job 清單：`RepairJob/WaterJob`（各 min(3, 可佔格數) 個，含 div 優先級遞減）、`StaffJob`（getCrew 個）、`ReadyJob`（optionalCrew）、`AmmoJob`（ammoPerClip，需可補給）、`CoalJob`、`InjuryJob`（sickbay）、`GuardJob/FixedGuardJob`。Job 介面有 `module()/resource()/priority()/active()/requiredType()/requiredUnoccupied()/isCaptain()`。
- 優先級範例：船長 staff=40（2282-2284）、升力(非貼地)=20/21（2259-2263）、focusOnMoving 推進=8.9（2276）、focusOnShooting 武器=2.8（2279）、一般=0.7（2285）。`staffJobPriority` 在 `Module.java:2255-2286`。
- `active()` 常見守門：HP>0、`hp > fire*3`（著火太旺不派人，2555）。

### 5.2 職務分派 `Airship.assignJobs`（`Airship.java:4896-4979`）
每 300ms 跑一次（`tick` 2776-2778；`assignJobsMs` 累積）：
1. 收集所有 `active() && 尚無人擔任` 的 Job → 依 `priority()` **降序**排序（`compare` 5108-5110）。
2. 逐 Job 找最佳船員：兩輪（attempt 0 = 只挑沒工作的；attempt 1 = 可搶優先級低於本 job×0.7 的人，4946）。
3. 距離成本 = `getPath(...).size()`（含「先去拿資源再去模組」兩段路徑，4949-4965）；最終成本 `d = (d+0.5)*10*dMult * maxHP/hp / crewEffectiveness`（4968，**血少/效率低的人成本高**）。選成本最低者，`best.job = job`。

### 5.3 船內尋路（tile 圖）
- `paths` / `tilePaths`（`Airship.java:304-305`）是 BFS 預算的 tile→tile / tile→module 最短路快取，增刪模組時 `.clear()`。
- 圖的「邊」= `pathChunks` 的 4 向鄰接 **且通過門檢查**（`Airship.java:2228-2238`：跨模組時需該方向兩側門都開）。
- Crewman 每 tick 在 `tick`（`Crewman.java:772`）→ 主邏輯約 1270-1460：
  - 校驗 job 仍有效（1276-1279）；若 job 要資源，先找最近持有該資源的模組當 `target`（1283-1296）。
  - 取 `getPath(currentTile, target)` 的第一格當 `movingTowards`（1351-1370）。
  - 移動是格到格的時間累積：`msSinceMoved >= currentTile.getMoveDelay() / speed(...)` 才換格（1397-1399）。`speed` 受 `fleetCrewSpeedMult`、徽章、`reloadSlowdown`（1383-1385）影響。
- 跳幫/船外移動：`jumpPoint`(`att.jumpPointCache`, 1746-1779)、`walkPoint`(`walkToGR/jumpSourceGR`)、`OutsideBodyPath`（`Crewman.java:134`）。常數 `MAX_JUMP_DOWN=120`、`JUMP_STRAIGHT_DOWN=128`、`ASSUMED_JUMP_DIST=50`（71-73）。

### 5.4 操作武器/修理/救火/搬彈（資源遞送）
- 到達模組後依 job 種類執行（`Crewman.tick` 後段 + `Module.giveResource`）：
  - `giveResource(Resource, …)`（`Module.java:1922-1998`）：
    - **AMMO**：填 `ammoForClip[slot]`，集滿一夾 → `ammoLeft += clip`（1926-1942）。
    - **COAL**：`msUntilCoal += coalReload`（1944-1946）。
    - **REPAIR**：`repairAmt = EmpireStat.REPAIR_AMOUNT * (船長/徽章/經驗/艦隊修正)`，補 hp 至 `getMaxRepairToHP()`，溢出補裝甲（1948-1980）。
    - **WATER（救火）**：`fire = max(0, fire - quenchAmt)`，quenchAmt 同樣受修正（1982-1996）。
- 開火由模組自身在 `Module.tick`（980-1019）驅動：`shootAccumulator` 依 `staffProportion` 累積，達 `reload*reloadFactor` 即 `fire(c, …)`（射擊解算在 `Module.java:1677-1896`，含彈道 `findBallisticAngle` 1904、跳彈/抖動 `jitter` 1536）。`reloadFactor` 受 fireMode、船長 fireRate、艦隊倍率、`crewExperience` 影響（989-996）。
- 船員自身武器（陸戰/跳幫）：`weaponReload`（`Crewman.java:95`）、`weaponReload(c)`（884），船上時 ×0.75，恐懼 ×4。

---

## 6. 確定性（重寫必讀）

- 戰鬥模擬 RNG 用 **`c.r`（Combat 的種子化 `Random`）**：火焰/爆炸/射擊抖動/目標選擇全用 `c.r.nextDouble()/nextInt()`（如 `Module.java:867,876,943,1445`）。**這是同步多人 / 重播的基礎，C++ 必須用同一套確定性 PRNG（Java `java.util.Random` 是 48-bit LCG，要逐位元復刻）並保持完全相同的呼叫順序。**
- **純視覺**的亂數用 `AGame.ANIM_R`（`Module.java:81-82,763,952,1073…`）—— 不影響模擬，可用任意 RNG。重寫時務必把這兩條 RNG 流分開。
- `strictfp`：所有相關類都標 `strictfp`（如 `Module`/`Airship`/`BonusableValue`），浮點需嚴格 IEEE-754；C++ 用 `-ffp-contract=off`、避免 FMA、固定 `double`。
- **HashMap 迭代序陷阱**：`Bonus.postLoad2`（`Bonus.java:51,111-115`）用 `HashMap` 收集 bonusConstructions 後**明確 `Collections.sort(keys)`** 才加入 → 有處理。但 `Module.resources` 是 `EnumMap`（迭代序＝enum 序，穩定，OK）。`Airship.shipwideTypes`/`paths` 是 HashMap 但只作快取查詢、不依賴迭代序。**C++ 重寫時，凡涉及模擬結果的容器一律用有序或固定序（vector / 按 ordinal 的陣列），勿用 unordered_map 迭代。**
- 模組/船員迭代序：`modules`/`tiles`/`crew` 都是 `ArrayList`（有序），求 lift/weight/command 等都是線性掃 → 直接用 `std::vector`，順序即存檔順序。

---

## 7. C++ 重寫建議（struct 佈局 / 介面 / 陷阱清單）

### 7.1 資料結構
```cpp
// 定義層：唯讀單例池，載入後不變
struct ModuleType {
    int w, h;                       // 固定
    std::bitset<H_MAX> leftDoors, rightDoors;  // 長度 h
    std::bitset<W_MAX> upDoors;                // 長度 w
    BV<int> hp, fireHP, explodeHP, explodeDmg, weight, command, lift, reload, clip, ...;
    BV<double> propulsion, adjacencyBonusStrength, ...;
    bool isWeapon, ignoreHPAdjacency, instantlyDestroyed, destroyEntireShipOnDestruction, ...;
    std::vector<WheelSpec> wheelSpecs;  // + legSpecs, tentacleSpecs, springs
};

// 實例層：AoS（一個 Module 跨多格，故不適合純 SoA）
struct Module {
    const ModuleType* type;  Airship* ship;  int x, y;
    int hp, lowestHP, holdOnHp, fire, explodeFuze;  bool burntOut;
    int ammoLeft, clipReloadCooldown, shootAccumulator, msUntilCoal, msSinceFired;
    double weaponAngle;
    int resources[Resource::COUNT];     // 取代 EnumMap
    std::vector<bool> ammoForClip;
    // --- 以下對應 Java transient：載檔後重算 / 重建 ---
    int maxHP;                          // recalcHPs 重算
    std::vector<Wheel> wheels; std::vector<Leg> legs; std::vector<Tentacle> tentacles;
    std::optional<Tether> tether;
    // 視覺暫態(recoil, glowAmt, anim…) 可獨立放、不參與模擬
};

struct Tile { int x, y; Module* module; ArmourPlate armour; bool canOccupy; };

struct Airship {
    ShipType type;
    std::vector<Module> modules;   // 順序＝存檔序，勿排序
    std::vector<Tile>   tiles;
    std::vector<Crewman> crew;
    std::vector<std::vector<Tile*>> tileGrid;  // [h][w]，tileAt
    BonusSet currentBonuses;       // = std::bitset<N_BONUS>
    int weight, commandPoints;
    bool enginesRunning, suspendiumRunning;
    // 力積分：xForce/yForce/xSpeed/ySpeed/x/y
};
```
- **SoA vs AoS**：模組是「多格共用一個實例」且欄位異質、數量少（一艘船幾十個），用 **AoS**（`std::vector<Module>`）最直觀。若要 SIMD 跑火焰/HP，可另建平行的 SoA「熱欄位」陣列（hp[], fire[], maxHP[]）並每幀同步——但收益有限，初版不必。
- **網格表示**：保留 `tileGrid[h][w]`（`Airship.java:308,4355-4366`）做 O(1) `tileAt`；`tiles` 向量做迭代。模組座標 (x,y) + (w,h) 覆蓋多格。

### 7.2 加成系統介面
- `BV<T>` = `std::variant<...>`（見 §4.5）。`T get(const BonusSet&) const` 用 `std::visit`。
- 在 `recalculateBonuses()`（增刪模組/換船長時）後，把每模組常用數值快取進 POD，戰鬥迴圈讀快取。

### 7.3 與戰鬥模擬的介面
- `Combat` 持有：兩條 RNG（模擬用 `simRng` / 視覺用 `animRng`）、`sides`、`particles/fragments/blasts/shots`、`landFormations`、`timeOfDay`。
- 主迴圈每 tick(ms)：`Airship.tick` →（移除/解體 §2.5）→ `commandPoints` 更新 → 對每 `Module.tick`（火焰/爆炸/武器）→ 對每 `Crewman.tick`（尋路/工作）→ 物理積分。
- 每 300ms `assignJobs`；增刪模組後 `recalcHPs + recalculateBonuses + paths.clear`。

### 7.4 陷阱清單
1. **transient 欄位**：`maxHP`、`wheels/legs/tentacles/tether`、所有視覺暫態 → 載檔後必須重算/重建（`recalcHPs`、依 spec new 部件）。
2. **兩種 flood fill**：物理 `chunks`（不看門）vs 尋路 `pathChunks`（看門，且跨模組需雙側門開）。別混用。
3. **門是雙向 AND**：左右蔓延/連通需「兩格各自的對應門」都為 true（`Module.java:913,924`；`Airship.java:2234-2235`）。
4. **算術加成順序**：先全加 delta、再全乘 mult/div、Int 版最後 clamp（§4.2）。
5. **解體門檻**：常數 `BREAK_APART_HP=-16` 不是絕對 HP，而是 `hp <= type.getHp() * -16`（`Airship.java:2740`）。
6. **maxHP 縮放鏈**：相鄰加成 `0.3+0.8*ratio` → +shipHPBonus*面積 → ×結構應力倍率（`structuralStress` 常數：min=3500, perHP=12000, maxPenalty=0.75，`GameSetting.java:11-13`）。
7. **explodeRadius / appFragments 等是 derive**，非獨立 JSON。
8. **確定性**：Java `Random`（48-bit LCG）要逐位元復刻；模擬 RNG 與視覺 RNG 分流；`strictfp` 浮點。
9. **資源序列化**：Module 的 `resources` 在 JSON 攤平成 `"AMMO":n,"COAL":n…`（`Module.java:2068,2161`）。
10. **Crewman.job 的序列化**：用 `jobModule`(modules索引)+`jobIndex`(該模組 jobs 索引) 回指（`Crewman.java:337-338,463-464`）→ C++ 要保證 `setupJobs` 產生的 Job 順序與存檔時一致。
