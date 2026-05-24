# Airships: CTS — 戰鬥模擬核心 / 確定性鎖步 / 網路 — C++ 重寫剖析

> 目標讀者：要用 C++ 從零重新實作這款遊戲戰鬥的工程師。
> 事實來源：`projects/airships-cts/src/com/zarkonnen/airships/` 反編譯 Java（CFR 0.152）。所有行號為實際讀到的真實行號。
> 子系統範圍：`Combat`（模擬核心）、`Physics`、`GuardedRandom`、`Shot`/`Particle`/`Fragment`/`LandFormation`（戰鬥實體）、`Client`/`Server`（確定性鎖步多人 + 網路）。

---

## 0. 全域常數速查表

| 常數 | 值 | 出處 | 意義 |
|---|---|---|---|
| `TICK_LENGTH` | 16 | `Combat.java:113` | 一個 sim tick = 16 ms（固定步長） |
| `Server.SERVER_TICK` | 64 | `Server.java:33`, `AGame.java:117` | 伺服器每 64 ms 廣播一個 network frame（= 4 個 sim tick） |
| `HASH_EVERY` | 1024 | `Combat.java:110` | （宣告但實際用 hardcode 1024，見下）desync 檢查週期（ms） |
| `HISTORY_KEEP` | 8000 | `Combat.java:115` | hashHistory 保留窗口（ms） |
| `INITIAL_QUEUE_SIZE` | 5 | `Combat.java:116` | frameQueue 達 5 才開始跑模擬 |
| `MAX_FRAGMENTS` | 160 | `Combat.java:108` | 碎片數上限（純視覺） |
| `INITIAL_FRAG_LIFE_CUTOFF` | 200000 | `Combat.java:109` | 碎片裁切初始壽命門檻 |
| `OUTER_ZONE_W` | 400 | `Combat.java:99` | 場地外圈 |
| `COMBAT_AREA_W_OLD/NEW` | 6400 / 9600 | `Combat.java:100-101` | 戰場寬度（依地形決定，見 `combatAreaW()` :205） |
| `COMBAT_AREA_H` | 1600 | `Combat.java:102` | 戰場高度 |
| `LaunchSettings.maxParticles` | 4000 | `launch_settings.json:28` | 粒子上限（純視覺） |
| `Physics.gravity` | 0.001 | `Combat.java:1147` | 戰鬥重力（每 ms） |
| `AT_SPEED_BOUNDARY` | 0.005 | `Physics.java:13` | 高速碰撞判定邊界 |
| `Server.PORT / RECONNECT_PORT` | 29142 / 29143 | `Server.java:29-30` | 主連線埠 / 重連埠 |
| `VERSION` | 1212000 | `Server.java:32`, `Combat.java:1570` | 網路協定版本，握手必須相符 |

`combatAreaW()`：若有地形且第一塊地形 `getX() > -4700.0` 回 6400，否則 9600（`Combat.java:205-210`）。

---

## 1. Tick 管線（精確執行順序）

### 1.1 兩層 tick 包裝：`tick()` → `doTick()` → `doGenericTick()`

呼叫點（單人/離線範例）：`CombatIntent.java:82`
```
us.combat.tick(16 / us.combat.speed.div, us.mySide, us.getTimeOfDay().effect.lightningChance, us.combat.speed.getMult());
```
- 參數：`ms`、`viewingSide`（只影響音效/視覺，不影響模擬）、`lightningChance`、`serverTickMult`。
- `serverTickMult = CombatSpeed.getMult()`：NORMAL=1、FAST=2、VERY_FAST=4、QUARTER_SPEED 用 `div=4` 把 ms 除以 4（`CombatSpeed.java:9-35`）。
- 測試純跑：`CombatRunner.java:20` → `c.tick(16, sides.get(0), 0.0, 1)`。

**`tick(int ms, …)` — `Combat.java:975-1006`：**
1. 若 slowMotion/分數速度 → 標記 `hasHadFractionalSpeed=true`（會關閉錄影 hash，:977）。
2. 單人離線且 slowMotion → `ms /= 4`（:980-982）。
3. **多人時（`isSingleMultiplayer()` 即 `mpClient != null`，:785）做「橡皮筋」緩衝調速**（:983-1002）：依 `frameQueue.size()` 動態縮放 ms——佇列太空(<3)放慢一半、=3 放慢 3/4、>15 加倍、>7 加 1.5 倍。然後 `localMsAccum += ms`，**每累積滿 16 才呼叫一次 `doTick(16,…)`，且每幀最多消化兩次**（:994-1002）。**重點：多人下模擬步長永遠是固定 16 ms，調速只改「現實時間 → sim tick」的對應率，不改 sim 內容。**
4. 非多人 → 直接 `doTick(ms,…)`（:1004）。

**`doTick(int ms,…)` — `Combat.java:1008-1024`：**
1. `r.guard = false`（:1009，guard 機制已被閹割，見 §2.1）。
2. `checkSidesForDupes()`（:1010 → :847）：移除同一艦在 ships/reserve 重複。
3. 若 `combatFinished` 直接 return（:1011）。
4. 若 `connectionLost()` → `finish()` 並 return（:1014）。
5. **`frameMID = runTickCommands(serverTickMult)`（:1018）→ 套用本 tick 的玩家指令（見 §3）。**
6. 若 `!isTimeMoving() && !runSimAnyway` 或 `startCountdown > 0` → return（:1019，等網路幀就緒）。
7. **`doGenericTick(ms, viewingSide, lightningChance)`（:1022）→ 真正的模擬。**
8. `r.guard = true`（:1023）。

### 1.2 `doGenericTick()` 內部精確順序 — `Combat.java:1026-1486`

| # | 階段 | 行號 | 用 `this.r`? | 用 `ANIM_R`? | 備註 |
|---|---|---|---|---|---|
| 1 | 錄影初始化（首 tick 存 `initialCombat`） | 1029-1038 | | | 僅首 tick |
| 2 | **Blast tick**（爆風視覺，逐個 `tick(ms)`） | 1039-1043 | | | `blasts` 是 transient |
| 3 | 回放比對（debug，僅 `recordEntireCombatState`） | 1044-1053 | | | 通常關 |
| 4 | 首 tick：偷襲判定（surprise attack） | 1054-1075 | | | 把對方 commandPoints 歸零 |
| 5 | **CrashZone tick**（墜毀區魔法粒子） | 1076-1087 | | ✅ (:1079,1080,1088) | timeout 倒數；位置用 ANIM_R |
| 6 | **`s.aiTick()`（每個 Side 跑 AI）** | 1088-1090 | (AI 內) | | `Side.aiTick()`→`Combat.java:2729`，遍歷 `ships` 呼叫 `ship.getAI().tick()` |
| 7 | 錄影：記錄本幀指令/狀態 hash | 1091-1100 | | | |
| 8 | **`outcome()` 勝負判定 + finishedCountdown** | 1101-1115 | | | done 後倒數 5000 ms（`FINISHED_COUNTDOWN_MS`） |
| 9 | `runSimAnyway=false`；取 `wind` | 1116-1117 | | | |
| 10 | **`simTick++; time += ms`**（時間推進） | 1121-1123 | | | 注意：simTick/time 在這裡才推進 |
| 11 | 傷害統計老化（每 8000 ms 滾動） | 1124-1144 | | | |
| 12 | **首次：建立 Physics（gravity=0.001），把地形加入 bodies** | 1145-1151 | | | lazy init |
| 13 | **同步 physics.bodies**（加入新艦+腳/輪、移除 reserve 艦） | 1152-1186 | | | |
| 14 | Side 首次組成初始化 + **武器初始 reload 隨機相位** | 1187-1198 | ✅ (:1195) | | `shootAccumulator = reload/2 + r.nextInt(reload)/2` |
| 15 | 6000 ms 時的「強弱懸殊」事件 | 1199-1207 | | | |
| 16 | Raid 戰利品計算 | 1208-1218 | | | |
| 17 | **`physics.tick(ms, this)`（核心物理積分+碰撞，見 §1.3）** | 1219 | | | |
| 18 | **`TroopPhysics.tick(ms, this, viewingSide)`（外部船員/登艦兵物理）** | 1220 | (內部) | | |
| 19 | **`ship.precalcAIValues()`（每艦 AI 預算）** | 1221-1225 | | | |
| 20 | **每個 Side：`checkForCombatEvents()` + `side.tick()`** | 1226-1231 | (內部大量) | | **武器開火/裝填/傷害/火焰/船員/修理全在這**（見 §1.4） |
| 21 | 粒子裁切到 maxParticles（從頭刪） | 1232-1234 | | | |
| 22 | **Particle tick**（逐個 `tick(ms,wind,this)`，life≤0 移除） | 1235-1239 | | | 移動是確定的，但生成多半用 ANIM_R |
| 23 | **Fragment tick**（逐個 `tick(ms,this)`） | 1240-1244 | | ✅ | 純視覺；REDUCED_VISUAL_NOISE 時直接移除 |
| 24 | Fragment 數量裁切到 160（`MAX_FRAGMENTS`） | 1245-1254 | | | |
| 25 | **LandFormation tick + 分裂成 chunk** | 1255-1270 | | (內部 shake 用 ANIM_R) | 新生地形加進 physics.bodies |
| 26 | **Shot tick**（逐個 `tick(ms,this,…)`，命中/到達移除，見 §4.1） | 1271-1276 | | (粒子用 ANIM_R) | **傷害真正結算點** |
| 27 | Trail tick | 1277-1281 | | | 純視覺 |
| 28 | 地形邊緣粒子發射 | 1282-1298 | | ✅ (:1288) | |
| 29 | 各種環境/受損粒子+槍口火光（大段視覺） | 1299-1401 | | ✅ 全用 ANIM_R | 受 `REDUCED_VISUAL_NOISE`/`REDUCED_FLASHING` 控制 |
| 30 | **艦隻換邊（俘獲 switchSides）** | 1402-1418 | | | 改變 sides 歸屬 |
| 31 | **Time-of-Day 變化**（90000 ms 後機率切換） | 1419-1431 | ✅ (:1426,1427) | | `r.nextDouble() < 5.5e-6*ms` |
| 32 | **閃電**（timeOfDayAge>8000 後機率打擊艦隻） | 1432-1485 | ✅ (:1434,1444,1457) | (視覺用 ANIM_R) | 選 victim、扣甲/模組 HP、加 fire |

**關鍵：傷害不是在獨立的「碰撞傷害」階段結算，而是分散在三處：**
- `physics.tick`（#17）內的 `doCollision`（撞擊傷害）；
- `side.tick`（#20）內的武器開火（產生 `Shot` 入 `combat.shots`）+ 火焰蔓延 + 船員行為；
- `Shot.tick`（#26）內的命中結算（穿甲/爆破/直擊 + splash + 生成船員）。

時間推進（`time += ms`，#10）發生在物理/開火/命中**之前**，所以同一 tick 內所有子系統看到的 `time` 已是新值。

### 1.3 `Physics.tick` 四階段碰撞解算 — `Physics.java:64-213`

固定子步可由 `tickRepeatedly(iters, msPerIter, combat)` 包（:17-21），但戰鬥主迴圈是單次 `tick(ms)`。

**`tick(ms)` (:64-83)**：遍歷 bodies → `particlesTick`（黏著粒子，:35）→ `removeMe` 移除 → **邊界軟牆**：超出 `±combatAreaW/2` 加回推力 `mass * 越界量 * 1e-4`（:75-80）→ 進 `tick2`。

**`tick2` (:85-157)** — 積分 + 兩兩碰撞速度：
- 每個非 immobile body：`xSpeed += xForce*ms/mass`（:101）；`ySpeed += yForce*ms/mass`（:102）；`ySpeed += gravity*ms`（:103）。
- **空氣阻力（平方項）**：`airSlowdownX = xSpeed² * horizontalAirFriction * ms`，往零方向夾（:104-110）；Y 同理（:111-117）。
- 記 `oldX/oldY`、算 `newX = x + xSpeed*ms`（:118-121）、`postCollideXSpeed=groupXSpeed=xSpeed`。
- immobile body 速度全歸零、old=new=current（:89-99）。
- 清 `xForce/yForce`，保存 `lastExertedXForce/Y`（:127-132）。
- **兩兩 O(n²) 碰撞**（:134-155）：對每對 (b1,b2)，先把雙方移到 new 位置，AABB `Rect2D.intersects` + `collidesWith` 判定；命中則 `doCollision(b2, speedDeltaSquared*(mass1+mass2), combat, isHighSpeed)`，其中 `isHighSpeed = (b1.isAtSpeed()||b2.isAtSpeed()) && speedDeltaSquared > 2.5e-5`（:143）。
  - 對 immobile 對手：`postCollideSpeed = speed * -1 * elasticity1 * elasticity2`（彈回，:146-147）。
  - 雙方可動：標準動量守恆公式 `(e1*e2*m2*(v2-v1) + m1*v1 + m2*v2)/(m1+m2)`（:149-150）。

**`tick3` (:159-199)** — collider group 合併（迭代到穩定）：
- 反覆 `while(newGroups)`：先把各 body 移到 `oldX + groupXSpeed*ms`，再兩兩偵測重疊把它們併進同一 group（`addToColliderGroup` :23-62 使用 `colliderGroup`(ArrayList)+`colliderGroupSet`(HashSet) 雙結構）。
- 每個 group 算總動量 / 總質量 → 統一 `groupXSpeed/groupYSpeed`；group 內含 immobile 則 Y 速度歸零（:179-196）。

**`tick4` (:201-213)** — 套用最終 group 速度：`x = oldX + groupXSpeed*ms`，`xSpeed = groupXSpeed`。immobile 還原到 old。

> **C++ 注意**：`tick2`/`tick3` 的兩兩迴圈用 `for (Body b1 : bodies) for (Body b2 : bodies)`，**順序 = bodies ArrayList 的插入順序**（地形先、然後艦+腳+輪，見 #12/#13）。這個順序是確定的（ArrayList），但你必須在 C++ 用相同的插入順序，否則碰撞解算順序變、結果分歧。`addToColliderGroup` 內用了 `HashSet`（`colliderGroupSet`），但它只做 contains 查詢、不做迭代，所以**不影響確定性**（見 §2.2）。

### 1.4 `Side.tick` — 武器/火焰/船員（#20 展開）— `Combat.java:2736-2812`

1. 算艦隊級加成（fleet*Mult：射速、命中、船員速度、易燃、爆炸風險、指令冷卻、修理量），取各艦長 buff 的 max/min（:2738-2776）。`fleetCommandBonus` 由帶 `fleetCommandBonus` shipwide modifier 的模組累加，含「不可疊加」規則（:2760-2775）。
2. **逐艦 `s.tick(ms, c, won, lost, onViewingSide, fleetCommandBonus, …9 個 mult)`**（:2777-2781）→ 這是 `Airship.tick`，內含開火、裝填、火焰蔓延、修理、船員移動、命令點再生等（在 `Airship.java`，本子系統未逐行展開但須知它是模擬主體；回傳 true 表示該艦消滅 → 從 ships 與 physics.bodies 移除）。
3. `smartCMIndex++`（>10000 歸零，:2782-2785）→ 每 tick 只有一個 troop 被標記 `isSmart`（輪替，:2786-2789），用於分攤昂貴 AI。
4. 外部船員 `cm.outsideTick(...)`（:2790-2793）。
5. 首次宣告「艦隊最大艦」（用 `Collections.sort` 依 cost，:2794-2811，**確定性排序**）。

---

## 2. 確定性（C++ 逐位元重現的關鍵）

### 2.1 兩套 RNG —— 最大陷阱

| RNG | 宣告 | 種子 | 用途 | 影響模擬? |
|---|---|---|---|---|
| `Combat.r`（`GuardedRandom`） | `Combat.java:123` | `randomSeed`（由 Server channel.seed 派發，見 §3） | **模擬性 RNG** | **是，必須逐位元重現** |
| `AGame.ANIM_R`（`static GuardedRandom`） | `AGame.java:118`，`new GuardedRandom()` 無種子 | **系統時間隨機（不可重現）** | 粒子、碎片、槍口火光、地形震動、墜毀區、閃電視覺 | **否，純視覺** |

- `GuardedRandom`（`GuardedRandom.java:8-53`）只是 `java.util.Random` 的薄包裝。`guard` 旗標與 `check()` 方法**已被閹割成空函數**（:51-52），反編譯前可能有「在不該用 RNG 時用了就報錯」的守衛，現在無作用。`Combat.doTick` 仍在 :1009/:1023 切換 `r.guard`，但無效果。
- `Combat.r` 種子來源：建構子 `setRandomSeed(seed)`（:735-738）→ `new GuardedRandom(seed)` → `new java.util.Random(seed)`。多人時 seed 來自 `welcome` 訊息的 `channel.seed`（`Server.java:756`，由 `Server.r.nextLong()` 在建 Channel 時產生 :1042）。
- **`java.util.Random` 演算法是 48-bit LCG（乘子 0x5DEECE66D、加數 0xB、`nextDouble`= (next(26)<<27 + next(27)) / 2^53）。C++ 必須 1:1 重現這個 LCG**（包含 `nextInt(bound)` 的拒絕取樣迴圈），否則模擬性 RNG 分歧。`ANIM_R` 不用重現（它本來就跨機器不同，所以模擬不能依賴它）。

> **驗證原則**：凡 `doGenericTick` 表中標「✅ this.r」的呼叫（武器初始相位 #14、TOD 變化 #31、閃電 #32）以及 `Airship.tick`/AI/Shot travelTime 計算內所有 `this.r` / `combat.r`，都必須逐位元重現。標「ANIM_R」的一律是視覺，C++ 可用任意本地 RNG 或乾脆省略。

### 2.2 HashMap / 迭代順序陷阱

掃描結果——**模擬迴圈本身不依賴 HashMap 迭代順序**：
- `Combat.playerToSide` / `idToPlayer`（HashMap，:129-130）：用於投降判定（`execCommand` :466 遍歷 `playerToSide.entrySet()`）與成員處理（`processSingleMultiplayerMembership` :379-448）。**`processSingleMultiplayerMembership` 已先把 key 取出做 `Collections.sort`（:388）再用**，所以該處安全。但 `execCommand` :466 的 `entrySet()` 迭代只設 `surrendered` 布林（與 `&=` 結合，**順序無關**），安全。
- `Combat.hashHistory`（HashMap<Integer,Integer>，:134）：只做 put/get/remove，不迭代（§3.3）。安全。
- `Physics.colliderGroupSet`（HashSet）：僅 contains 查詢（`Physics.java:175`），不迭代。安全。
- `LandFormation.tick` 的 `destroySounds`（HashMap，:1008）+ `for(... destroySounds.keySet())`（:1029-1032）：**只播音效**，不改模擬狀態。安全（但 C++ 若要 bit-perfect 連音效都不在乎可忽略）。
- `Combat.surrenderedOwners`（HashSet<FleetOwnerRef>，:171）：`checkSurrenderedOwners` :474 用 `contains`，安全。
- `plinkedArmoursAndModules`（HashSet，:194 transient）：去重用途。

> **C++ 規則**：把上述容器照「用途」翻譯——需要穩定順序的地方（理論上目前沒有影響模擬的）用 `std::vector`/排序；純查詢用 `unordered_set`/`unordered_map` 即可。**真正驅動模擬順序的全是 `ArrayList`（`sides`、`ships`、`reserve`、`troops`、`modules`、`tiles`、`crew`、`boarders`、`shots`(LinkedList)、`particles`、`fragments`、`landFormations`、`physics.bodies`）——這些必須在 C++ 維持完全相同的插入/移除順序。** `shots/particles/fragments` 是 `LinkedList`，遍歷用 Iterator 並在中途 `it.remove()`（如 :1235-1276），C++ 用 `std::list` + erase-while-iterate 對應。

### 2.3 浮點：`strictfp` + StrictMath

- **`Combat`、`Physics`、`Shot`、`Particle`、`Fragment`、`LandFormation`、`Body`、`Side`、`CrashFormation` 等全部宣告 `strictfp`**（如 `Combat.java:96`、`Physics.java:12`、`Shot.java:31`、`Particle.java:23`、`Fragment.java:16`、`Body.java:13`、`Combat.java:2658` Side）。意味浮點運算嚴格遵循 IEEE-754 雙精度、無 80-bit 中間擴展、跨平台一致。
- 數學函數**幾乎全用 `StrictMath`**（`StrictMath.sqrt/cos/sin/atan2/min/max/round/floor/ceil`），如 `Physics.java:106`、`Shot.java:203,209,278`、`Particle.java:46,91`。`StrictMath` 在所有 JVM/平台給出完全相同的位元結果（基於 fdlibm）。少數地方用 `Math.*`（如 `Shot.getAngle()` :565,570 用 `Math.atan2`；`Combat.java:1392` 用 `Math.PI`）——`Math.PI` 是常數無差異；`Math.atan2` 在 `getAngle()` 只用於視覺繪製角度，不回饋模擬。
- **`cheapHash` 用 `new Double(x).hashCode()`**（`Combat.java:927-939`、`Airship.java:5856-5859`、`Crewman.java:241-248`）——這是把 double 的 64-bit 表示拆成 `(int)(bits ^ (bits>>>32))`。**desync 偵測直接比較 IEEE-754 位元**，所以任何最後一位的浮點差異都會被抓到。

> **C++ 確定性策略建議**：
> 1. **首選：嚴格 IEEE-754 雙精度**。用 `-ffp-contract=off`（禁 FMA 融合）、`-fno-fast-math`，並提供 fdlibm 等價的 `sqrt/sin/cos/atan2/...`（直接移植 fdlibm，或用 `crlibm`/`musl libm`），因為**標準庫的超越函數不保證跨平台逐位元相同**。`sqrt` 由 IEEE 保證正確捨入，安全；`sin/cos/atan2` 必須自帶確定性實作以匹配 `StrictMath`。
> 2. 若無法保證超越函數一致，**退而求其次用定點數重寫整個物理/模擬**——但這等於放棄與原版錄影/存檔相容，且工作量大。鑒於原版本身就靠 strictfp+StrictMath 達成跨機一致，**建議照抄 IEEE-754 + 移植 StrictMath 的 fdlibm**。
> 3. `Double.hashCode` 的 checksum 可照抄（`uint64 bits; int32 h = (int32)(bits ^ (bits>>32))`），方便與原版互檢。

---

## 3. 鎖步協定（lockstep）

### 3.1 架構：Server 是純訊息中繼，不跑模擬

`Server` 完全不含戰鬥邏輯。它每 64 ms（`SERVER_TICK`，`Server.java:411` `lastDigestSent + 64`）把該頻道在窗口內收到的所有訊息打包成一個 `frame` 廣播給頻道所有成員（`Channel.sendDigests` :1073-1165）。**每個 Client 各自跑完整的確定性模擬**，靠相同 seed + 相同指令序列 + 相同浮點達成一致。

`frame` 結構（`Server.java:1074-1084`）：
```json
{ "type":"frame", "channelID":N, "frameNumber":F,
  "messages":[ ...本窗口所有玩家指令... ],
  "members":[ clientID, ... ],
  "###": messageID }   // ### 由 Client.write 注入 (Server.java:766)
```
首次連線會多送歷史幀（`historyFrame:"both"/"global"/"channel"`，:1092-1153），把錯過的全域/頻道歷史訊息補上，之後才送一般 frame。

### 3.2 Client 端 frameQueue 填充與消化 — `getTickCommands` `Combat.java:257-294`

每個 `doTick` 開頭呼叫 `runTickCommands(serverTickMult)`（:300-307）→ `getTickCommands`：
1. **拉訊息**：`g.pollMessage()`（:259）取一則網路訊息，若 `type=="frame"` 就 `frameQueue.add(msg)` 且 `networkFrameHistory.add(msg)`（:260-263）。
2. **初始緩衝**：`frameQueue.size() >= 5` 時設 `initialQueueFilled=true`（:264-266）——即 §0 的 `INITIAL_QUEUE_SIZE`。建構子預先塞了 4 個空 frame（:780-782，`time=-1`）+ 第二建構子塞 4 個（:780），給緩衝起步。
3. **僅在 `initialQueueFilled && isTimeMoving()`**（:267）才推進：
   - `netTick==0` 時拍 `baseState = toJSON()`（:268-269，見 §3.4）。
   - **desync checksum**（:271-276，見 §3.3）。
   - `ticksSinceLastFrame++; netTick++`（:277-278）。
   - **當 `ticksSinceLastFrame == 64 * serverTickMult / 16`**（:279）→ 消化一個 frame：
     - `startCountdown` 倒數 64（:280）；`ticksSinceLastFrame=0`（:281）。
     - `JSONObject fr = frameQueue.pollFirst()`（:282）；`runSimAnyway=true`（:283）。
     - 單人多人成員變更處理（:284-286）。
     - 回傳 `(fr.###, fr.messages)`（:287）。
   - 其餘 tick 回傳 `(-1, [])`（:293）——即「空指令 tick」。
4. **`64*serverTickMult/16` 的意義**：NORMAL(mult=1) → 4，即每 4 個 16ms sim tick 消化一個 64ms 網路幀（完美對齊 SERVER_TICK）；FAST(mult=2) → 8（每幀對應更多 sim tick = 加速播放同一份指令流）。

`isTimeMoving()`（:296-298）：單機（mpClient==null）永遠 true；多人時要 `initialQueueFilled && !frameQueue.isEmpty()`。**佇列空 = 模擬暫停等網路**（`waitingForNetworkMessages()` :249-251）。

### 3.3 desync 偵測（`HASH_EVERY` / `cheapHash` / `hashHistory`）

- **送出**（`getTickCommands` :271-276）：`if (time != 0 && time % 1024 == 0 && !desyncConfirmed)`：
  - `hash = cheapHash()`（:272，見 §2.3，遍歷所有 ships/troops/shots/landFormations 的座標/速度/HP 的 Double 位元 hash，`Combat.java:914-942`）。
  - `hashHistory.remove(time - 8000)`（:273，滑窗 `HISTORY_KEEP=8000`）。
  - `hashHistory.put(time, hash)`（:274）。
  - `sendMessage(Client.msg("checksum").put("time",time).put("hash",hash))`（:275）——廣播自己的 checksum。
  > 注意：條件硬寫 `% 1024` 與 `time - 8000`，沒用 `HASH_EVERY`/`HISTORY_KEEP` 常數（雖然值相同）。
- **接收 / 比對**（checksum 指令執行器 `Combat.java:2096-2112`）：
  ```
  if (!desyncConfirmed && hashHistory.containsKey(time) && hashHistory.get(time) != hash) {
      desyncConfirmed = true;
      g.reportError("network_diverge_warning", ...);  // 把錄影附上回報
  }
  ```
  即：別人的 checksum 透過 frame 送達、當成一則「checksum 指令」執行；若同一 `time` 我方記錄的 hash 與對方不符 → 確認 desync。
- `mostRecentChecksumTime`（:147 transient）記最近檢查時間。

> **C++ 重點**：checksum 用「每 1024 ms（每 64 個 sim tick）一次」、比對所有實體的浮點位元 hash。要與原版互通須照抄 `cheapHash` 的乘法常數（ships×47/troops×43/shots×37/landFormations×31，及各實體內部的 31/37/41/29/43）與 `Double.hashCode` 演算法。若只是自家 C++ 客戶端互檢，可換成更穩健的 hash，但**比對週期、涵蓋欄位、迭代順序**必須一致才有意義。

### 3.4 baseState / networkFrameHistory 的作用

- `baseState`（:132，`netTick==0` 時 = `toJSON()` :269）：模擬正式起跑前的完整初始狀態快照（JSON）。
- `networkFrameHistory`（:133，每收到 frame 就 append :262）：完整的網路幀序列。
- 兩者合起來 = **「初始狀態 + 之後每幀的全部指令」**，即一份可完整重播的確定性記錄（這正是鎖步的精髓，也是 desync 回報時附帶錄影的素材，:2104-2106）。
- `Recording`（:189）獨立記錄 `tickCommands`（每 tick 的 `(frameMID, commandsExecutedInThisFrame)`，:1095）與選擇性的 `tickCombats`/`tickHashes`（:1098,1119）——這是本地回放系統，與網路 history 平行。

### 3.5 玩家指令封裝 / 執行

- 指令是 `JSONObject`，必有 `type`（對應 `EXECS` 中的 `CommandExecutor`，:197 靜態註冊 map）與 `t`（送出時間戳，`Client.msg()` 注入 `DateTime.now().getMillis()`，`Client.java:157`）。
- **送出**（`giveCommand` :309-323）：
  - 多人（`mpClient != null` 或 campaign 多人）→ `g.sendMessage(cmd)`（:319，丟給網路，不本地立即執行）。
  - 單機 → `execCommand(cmd, -1L)`（:321，立即執行）。
- **執行**（`execCommand(cmd, frameNumber)` :450-472）：
  - `frameNumber < 0` 時 `cmd.remove("t")`（:451-453）——**移除時間戳，使單機/網路指令在 hash 上等價**（避免 `t` 影響確定性）。
  - 查 `EXECS`（未知 type 報錯，:454-457）；錄影記錄（:458-460）；`EXECS.get(type).run(cmd, this)`（:461）。
  - append 到 `executedCommands`（含 frameNumber/time/simTick，:462）。
  - 重算所有玩家投降狀態（:463-471）。
- **消化順序**：`runTickCommands` 把 frame 的 `messages` 陣列**依序** `execCommand`（:303-305），順序 = 伺服器打包順序 = 各玩家訊息到達伺服器的順序。**這個順序對所有客戶端一致**（因為大家收到同一份 frame），這是鎖步一致性的基礎。

### 3.6 Client/Server 訊息類型與連線/重連

**Client → Server 訊息**（`Server.Client.processMessage` :770-883）：
| type | 作用 | 行號 |
|---|---|---|
| `retainMeIWillAckMessages` | 要求伺服器在斷線後保留此 client（含 playerName） | 860-862 |
| `hello` | 送玩家 info，廣播 addPlayer | 789-797 |
| `changeChannel` | 換頻道 | 782-788 |
| `createChannel` / `createOrJoinChannel` | 建/加頻道（含 seed/passhash/hidden/sealed） | 798-825 |
| `listChannels` | 要頻道清單 | 826-840 |
| `sealChannel`/`revealChannel`/`updateChannelInitiatorID` | 頻道管理 | 841-853 |
| `ack` | 確認收到 messageID ≤ mid | 854-859 |
| `bye` | 主動離線 | 863-866 |
| `fullReconnect` | （走 29143 重連埠，`Reconnector` :552-558） | |
| `global:true` 的任意訊息 | 廣播到所有頻道 + 進全域歷史(保留 8) | 867-876 |
| 其他（含戰鬥指令） | 進 `channel.messages`，下個 digest 廣播 | 877-882 |

**Server → Client 訊息**（`Client.tick` 解析 :620-658）：`assignID`（給 playerID+uniqueID，:632-634）、`welcome`（含 flipped/version/channelID/**seed**/info/playerID，:744-760 / 解析 :628-631）、`addPlayer`/`removePlayer`、`frame`（含 ping 回波計算延遲，:635-658）、`ack`、`channelList`、`reject`/`serverReject`、`ping`（包在 frame.messages 內）。

**連線流程（Client）**：
1. 建構子送 `retainMeIWillAckMessages`（`Client.java:233`）。
2. `tick()`（:289-693）是單執行緒 NIO 狀態機，每次最多 32 次 iteration（:304）。連 29142 埠（:405）。
3. 寫訊息加 4-byte 長度前綴 + UTF-8 payload（:502-509；Server 對應 :930-937）。每則含遞增 `###` messageID（:171,189）；對方回 `ack` 後從 `unAcknowledgedMessages` 移除（:620-627）。
4. **去重**：收到 `### <= mostRecentReceivedMessageID` 的訊息直接 skip（:606-618；Server 同 :776-780）。
5. **Ping/延遲**：定期送 `ping`（:439-450，間隔 `measureNetworkDelayEveryMilliseconds`=1000ms），用 frame 回波算 `recentPing`（:640），加權平滑（`smoothedRecentPing` :114-138，falloff 0.7）。

**重連流程**：
- 觸發條件：write/read 逾時（`tooMuchNetworkDelayMilliseconds`=3000，:486）、`readFuture.get` 回 -1（:571）、NYCE、ping 連續超標（`tooMuchNetworkDelayStrikes` 次後 :646-652）。
- `attemptFullReconnect=true` → 走 29143 重連埠（:356）送 `fullReconnect{uniqueID}`（:382）→ Server `Reconnector` 比對 uniqueID 找回保留的 Client、`fullReconnect(socketChannel)`（`Server.java:583`/:667-680）→ **把 `unAcknowledgedMessages` 重新塞回發送佇列頭部**（Client :338-339 / Server :677）達成無縫續傳。
- 退避：`crashReconnectBackoffMilliseconds`、`reconnectAttemptIntervalMilliseconds`=5000；`maxReconnectAttempts`=10（超過放棄 :250）。連線重試 `maxConnectAttempts`=3、`connectAttemptIntervalMilliseconds`=15000。
- Server 端保留時間 `clientRetainTime`=60000（`Server.java:887`），Reconnector 自身 120000 ms 逾時（:621）。

**launch_settings.json 網路參數**（`launch_settings.json`）：`maxNetworkSendBytes=50000`、`measureNetworkDelayEveryMilliseconds=1000`、`tooMuchNetworkDelayMilliseconds=3000`、`reconnectAttemptIntervalMilliseconds=5000`、`minimumLagReconnectInterval=10000`、`tooMuchNetworkDelayMillisecondsOnReconnect=6000`、`maxReconnectAttempts=10`、`maxConnectAttempts=3`、`connectAttemptIntervalMilliseconds=15000`、`maxResumeAttempts=3`、`maxParticles=4000`。

---

## 4. 戰鬥實體（欄位 / 生命週期 / 上限）

### 4.1 Shot — `Shot.java`

**欄位**（:32-58）：`target`(Airship)/`targetTroop`(Crewman)、`tX,tY`(目標相對/絕對)、`sX,sY`(起點)、`time`/`travelTime`/`delay`、`internal`/`vsBoarders`、`shooterType`(CrewType)/`weaponType`(ModuleType)/`weaponBonuses`(BonusSet)/`weapon`(Module)/`tentacle`、導引彈：`isArcing`+`arcing*`、`dX,dY,a`(導引速度與角度)、transient `done`。

**生命週期**：
- 建構：直射彈 `travelTime = dist / shotSpeed / shotSpeedMult`（:204,224,235,248）；導引彈把 `tX/tY` 轉成相對目標座標並設初速（:205-211,249-255）。`makeArcing` 設拋物線（:174-182）。
- `tick(ms, c, onViewingSide)`（:258-541）：
  1. `delay` 倒數（:260-267）。
  2. target 已不在場 → done（:268-271）。
  3. **導引彈**（:273-293）：轉向（`turnSpeed*ms` 限制，`Direction.normalizeRadians`）、判 `lockLost`（超過 `missileLockLossAngle`）、加速度積分、限 `topSpeed`、更新 sX/sY。
  4. 發射軌跡粒子（用 `ANIM_R`，:302）、exhaust（:321-323）。
  5. `time += ms`；拋物線更新（:325-329）。
  6. **命中判定**（`time >= travelTime || lockLost || fuseTriggered()`，:330）→ 結算：
     - `target.hit(...)` 回傳命中的 `Tile`（:340），累加 damageTaken/damageDealt/damageMissed/damageTakenFromAbove（:341-356）。
     - splash 傷害：blast/pen/direct 三型各自 `c.doSplashDmg(...)`（:362-370 → `Combat.doSplashDmg` :631-655，遍歷所有 side 的 ships+troops 做半徑線性衰減傷害）。
     - troop 命中（:371-374，計 aircraftDownedByAircraft）。
     - 命中生成船員（spawnCrewOnImpact，內側/外側/登艦邏輯，:383-486）。
     - 爆炸視覺（Blast+大量 ANIM_R 粒子+音效，:488-536）。
     - `done=true; return true`（移除）。
- **傷害取值**：`getPenDmg/getBlastDmg/getDirectDmg`（:573-603）依 weaponType→tentacle→shooterType 優先序；splash 半徑同理（:581-591）。`MIN_DMG=1`（:32）。
- 序列化（:80-127 toJSON / :129-172 ctor）：target/weapon 用 `(sideIndex, shipIndex, moduleIndex)` **索引**參照（**注意：依賴 sides/ships/modules 的 ArrayList 順序穩定**）。

### 4.2 Particle — `Particle.java`（純視覺）

- 欄位（:24-35）：`type`、`x,y,dx,dy,direction`、`life/lifespan`、`pic`、`startSize/endSize/scale`。
- **建構全程用 `ANIM_R`**（方向、速度、壽命、圖、起始大小，:44-63,71-85）→ **不可重現、不進模擬 hash**。
- `tick(ms, wind, c)`（:88-117）：重力 `dy += grav*ms/16`、風 `dx += wind*windMult*ms/16`、位移、可選黏著到 body（`stickSpeed`，:103-114，存入 `body.stuckParticles`）。`life<=0` 移除。
- 上限 `LaunchSettings.maxParticles`=4000（`Combat.java:1232`，超過從頭刪）。
- `Emitter` 內部類（:184-196）：`emitProbability`/`numParticles`/`soundEffect`，發射判定 `ANIM_R.nextDouble() < emitProbability*ms`。

### 4.3 Fragment — `Fragment.java`（純視覺）

- 欄位（:16-31）：`ssb/img`、`x,y,dx,dy,angle,dangle`、`age/life`、`fiery/smoky`(冒火/冒煙計數)、`wreckage`、`fuze`、`landed`。
- 建構：`fiery/smoky` 用 `ANIM_R`（:44-45,62-63）。
- `tick(ms, c)`（:67-107）：**`REDUCED_VISUAL_NOISE` 時直接 return true（移除）**（:68-70）→ 證明純視覺。重力 `dy += 0.001*ms/2`、位移、旋轉、`fuze` 倒數爆炸（`explode` :109-140 全 ANIM_R 粒子）、落地停住（用 `landFormations.get(0).yBoundaryAt`）。
- 上限 `MAX_FRAGMENTS`=160（`Combat.java:1246-1254`，超過用 `INITIAL_FRAG_LIFE_CUTOFF`=200000 逐步減半門檻裁切，每 4 個刪 1）。

### 4.4 LandFormation — `LandFormation.java`（模擬實體，extends GridBody extends Body）

- 欄位（:53-70）：`landscapeType`、`grid`(LandBlockType[][])、`hp`(int[][])、`immobile`、transient `destroy/phase/edge/reachable/chunkID/heightMap/opaqueHeightMap/dirty`、`shakeAmount/X/Y`。`GROUND_LF_Y_OFFSET=15`。
- 物理介面（覆寫 Body 抽象）：`getMass()=10+Σblock.weight`（min 10，:1257-1266）、`getCollisionMass()=min(500, mass/5)`（:1253-1255）、`isImmobile()=immobile`（:1268-1271）、`elasticity()=0`（:1284-1287，地形不彈）、`horizontalAirFriction=0.005 + height/width*0.01`（:1289-1292）、`removeMe`=無 `landFormationRemoveStopper` block 時 true（:1273-1282）。
- `tick(ms, c)`（:995-1042）：`shakeAmount` 衰減（×0.98，用 ANIM_R 算抖動位移，:996-1006）→ 處理 `destroy[][]` 標記（變 AIR + 收集 destroySound + `dirty`，:1009-1028）→ 播 destroy 音效（HashMap 迭代，純音效，:1029-1032）→ `crop()`（:1034）→ 非 immobile 設 `yForce = -availableSuspendiumForce()`（懸浮力，:1038-1040）。
- `splitIntoChunksIfNeeded()`（:1181-）：地形被打斷時分裂成多個 LandFormation（新塊在 doGenericTick #25 加入 physics.bodies）。
- 高度查詢：`yBoundaryAt`/`solidYBoundaryAt`（:1150-1165）用 `heightMap/opaqueHeightMap`，網格 16px。`canParticleStick`（:1073-）粒子黏著判定。
- 序列化：`base36CSV`/`hexString` 兩種格式，含 LandBlockType id 對映（:97-,204-）。

### 4.5 Body 物理基類 — `Body.java`

- 位置/速度/力欄位全在此（`xSpeed/ySpeed` private 帶 setter，**setter 會擲 NaN/Inf 例外**，:94-116）→ C++ 可保留這個防呆斷言抓確定性 bug。
- transient 物理中間量：`newX/oldX/postCollideXSpeed/groupXSpeed/exertedXForce/lastExertedXForce`、`colliderGroup/colliderGroupSet`、`stuckParticles`。
- `particlesTick`（:35-57）：黏著粒子滴落動畫（純視覺，但會 add 回 `c.particles`）。

---

## 5. C++ 重寫建議

### 5.1 建議的 class/struct 分解

```
struct Vec2 { double x, y; };

// 物理基類（對應 Body）
struct PhysicsBody {
  Vec2 pos, speed, force;
  Vec2 oldP, newP, postCollideSpeed, groupSpeed, exertedForce, lastExertedForce;
  // collider group：用 index 或指標，避免 Java 的 ArrayList+HashSet 雙結構
  std::vector<PhysicsBody*>* colliderGroup = nullptr;
  // 虛擬介面：mass(), collisionMass(), immobile(), elasticity(),
  //          hAirFriction(bool), vAirFriction(bool), collidesWith(), doCollision(), atSpeed(), removeMe()
};

struct Combat {
  std::vector<Side> sides;            // 順序敏感
  std::list<Shot> shots;              // erase-while-iterate
  std::list<Particle> particles;      // 純視覺，可不參與 lockstep
  std::list<Fragment> fragments;      // 純視覺
  std::vector<LandFormation> landFormations;
  Physics physics;                    // bodies 順序 = 地形→艦→腳→輪
  DeterministicRandom r;              // 種子來自 channel.seed（必須重現 java.util.Random）
  uint64_t randomSeed;
  int32_t simTick = 0, time = 0, netTick = 0, ticksSinceLastFrame = 0;
  // 鎖步：
  std::deque<Frame> frameQueue;
  std::optional<Snapshot> baseState;
  std::vector<Frame> networkFrameHistory;
  std::unordered_map<int,int> hashHistory;  // 不迭代，安全
};
```
- **把「模擬狀態」與「視覺/音效」徹底分開**：`particles/fragments/blasts/sounds/trails/shake/muzzleFlash` 全放到不參與 lockstep 的視覺層，由本地非確定 RNG 驅動（對應 `ANIM_R`）。模擬層只碰 `sides/ships/modules/tiles/crew/troops/shots/landFormations/physics`。

### 5.2 固定步長迴圈設計

- **核心步長恆為 16 ms**（`TICK_LENGTH`），絕不用可變 dt 進模擬。對應原版 `doTick(16,…)`。
- 把「現實時間 → sim tick」與「sim tick → 模擬」解耦：
  - 單機：累積真實 dt，每滿 16 ms 跑一次 `doGenericTick(16)`（含速度倍率時跑多次）。
  - 多人：照 §1.1 的 `localMsAccum` 橡皮筋邏輯 + §3.2 的 `ticksSinceLastFrame == 64*mult/16` 消化網路幀。**模擬永遠 16 ms/步**。
- `doGenericTick` 內部嚴格照 §1.2 表的階段順序（time 推進在物理/開火/命中之前）。

### 5.3 確定性策略

- **採用 IEEE-754 雙精度 + 移植 StrictMath（fdlibm）**，不要用編譯器內建 `sin/cos/atan2`（跨平台不保證逐位元）。編譯旗標：`-ffp-contract=off -fno-fast-math -frounding-math`（或 MSVC `/fp:strict`）。
- **重現 `java.util.Random`**（48-bit LCG）逐位元：`nextInt(bound)`（含 2 的冪特例與拒絕取樣）、`nextDouble`、`nextLong`、`nextBoolean`。這是模擬 RNG (`Combat.r`) 的唯一來源，必須精確。
- **容器順序**：所有驅動模擬的集合用 `std::vector`/`std::list` 並保持與 Java 完全相同的 insert/remove 時機（特別是 physics.bodies 的建立順序 §1.2 #12-13、shots 的 erase-while-iterate）。查詢型集合才用 `unordered_map/set`。
- **checksum**：照抄 `cheapHash` 的乘法常數鏈與涵蓋欄位（座標/速度/HP 的 double 位元 hash），每 1024 ms（64 tick）一次，方便跨實作互檢與抓回歸。
- 保留 Body setter 的 NaN/Inf 斷言，能在開發期立即定位非確定/數值爆炸。

### 5.4 序列化

- 原版用 JSON（`toJSON`/JSONObject ctor，`Combat.java:1488-1565,1567+`），`netVersion=1212000` 握手。Shot/實體用 (sideIndex, shipIndex, moduleIndex) 索引互參。
- C++ 建議：**指令/網路幀**用 JSON（與既有伺服器相容、易 debug、量小）；**全狀態快照（baseState / 存檔 / desync 回報附件）**可用 JSON 或自訂二進位，但若要與原版錄影相容必須沿用 JSON 結構與欄位名。索引式參照在 C++ 同樣可行，但要保證序列化/反序列化兩端的 vector 順序一致。

### 5.5 網路層抽象

- Server 是**純中繼**：可直接沿用原協定（4-byte 長度前綴 + UTF-8 JSON、messageID `###` + ack + 去重、64 ms digest 廣播、29142/29143 雙埠）→ **C++ 客戶端能與現有 Java 伺服器互通**（只要模擬逐位元一致）。
- 抽象出 `INetTransport`（poll/send 訊息）+ `IFrameSource`（給模擬餵 frame）；把 `getTickCommands` 的緩衝/消化邏輯（§3.2）放在傳輸無關的 `Combat` 層。
- 重連靠 `uniqueID` + `unAcknowledgedMessages` 重送（§3.6），C++ 照搬即可。

### 5.6 移植風險與陷阱清單（最關鍵）

1. **`ANIM_R` vs `Combat.r` 混用**：粒子/碎片/槍口火光/地形抖動/閃電視覺/墜毀區用 `ANIM_R`（不可重現），TOD 切換/武器初始相位/閃電目標選擇/AI/Shot 計算用 `Combat.r`（必須重現）。**搞錯任何一個都會 desync 或反之引入不該有的隨機**。
2. **超越函數逐位元一致**：標準庫 `sin/cos/atan2` 跨平台不保證一致，必須移植 StrictMath/fdlibm，否則 checksum 立刻分歧。
3. **容器迭代順序**：physics.bodies 插入順序、sides/ships/modules 索引穩定（Shot 序列化依賴）、erase-while-iterate 語義。
4. **time 推進時機**：`time += ms` 在 #10，早於物理/開火/命中——所有子系統看新 time。
5. **`64*serverTickMult/16` 對齊**：sim 步長恆 16、網路幀 64 ms、速度倍率只改消化率不改步長。
6. **`execCommand` 移除 `t`**：避免時間戳污染確定性 hash；單機 `frameNumber=-1`。
7. **NaN/Inf 防呆**：Body setter 會擲例外——數值爆炸在原版是硬錯誤，C++ 也應如此（用斷言）。
8. **strictfp 全覆蓋**：所有模擬類別都是 strictfp；C++ 須全程嚴格 IEEE-754、禁 FMA 融合。
```

---

## 附錄：關鍵 file:line 索引

- Tick 入口：`Combat.java:975`(tick) → `:1008`(doTick) → `:1026`(doGenericTick)
- 物理四階段：`Physics.java:64`(tick)→`:85`(tick2 積分+碰撞)→`:159`(tick3 group)→`:201`(tick4 套用)
- RNG：`GuardedRandom.java:8`；`Combat.r` 宣告 `Combat.java:123`、種子 `:735`；`AGame.ANIM_R` `AGame.java:118`
- 鎖步消化：`Combat.java:257`(getTickCommands)、消化條件 `:279`、baseState `:269`、checksum 送出 `:271-276`、checksum 比對 `:2096-2112`、cheapHash `:914`
- 指令：`giveCommand :309`、`execCommand :450`(移除 t `:451`)、EXECS 註冊 `:197`
- 常數：`Combat.java:99-116`、`Server.java:29-36`、`AGame.java:117`
- 實體：`Shot.java:258`(tick)、`Particle.java:88`(tick)、`Fragment.java:67`(tick)、`LandFormation.java:995`(tick)、`Body.java:13`、`cheapHash` `Airship.java:5854`/`Crewman.java:234`
- 網路：`Client.java:289`(tick 狀態機)、重連 `:325`/`:382`；`Server.java:1073`(sendDigests)、`processMessage :770`、`Reconnector :578`、Channel.seed `:1042`
- 計時校準：`CombatIntent.java:82`、`CombatRunner.java:20`、`CombatSpeed.java:9`
- 網路參數：`launch_settings.json:16-28`
