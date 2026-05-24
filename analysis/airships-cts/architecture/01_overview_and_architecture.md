# Airships: Conquer the Skies — 架構總覽 (Level 1-2)

> 分析對象：Steam 安裝版 `~/.local/share/Steam/steamapps/common/Airships Conquer the Skies`
> 反編譯原始碼：`projects/airships-cts/src/`（由 CFR 0.152 從 `game.jar` + `CatEngine.jar` + `CatSlick.jar` 反編譯）
> 作者：David Stark (zarkonnen)；模組指南 http://zarkonnen.com/airships/modding_guide

---

## 1. 這是什麼遊戲

「Airships: Conquer the Skies」是一款**飛行戰艦建造 + 即時戰術戰鬥 + 輕量 4X 戰略**的獨立遊戲。玩家用方塊化的模組（武器、引擎、懸浮晶體 Suspendium、船員艙…）拼出自己的飛艇／陸行艦（landship），在 2D 側視戰場上指揮它們作戰，並在策略地圖上征服城市、擴張帝國。

遊戲自述（`data/help_en/__Airships.txt`）：
> Airships are massive flying war machines held aloft by powered Suspendium crystals... used to conquer territory, defend towns and cities, defeat monsters and quell unrest.

戰鬥定位（`data/help_en/Combat.txt`）：船艦會**自動開火、修理、救火、抵抗跳幫**；玩家的職責是**走位、設定優先權、下達衝撞／跳幫等重大指令**。是「半自動指揮官」式的即時戰術。

---

## 2. 技術棧 (Level 1)

| 層級 | 技術 | 位置 |
|------|------|------|
| 語言 / 執行 | Java（`strictfp` 全程使用，為了浮點確定性）| `game.jar`，主類 `com.zarkonnen.airships.Main` |
| 自製引擎 | **CatEngine** / **CatSlick** | `lib/CatEngine.jar`、`lib/CatSlick.jar`（`com.zarkonnen.catengine.*`）|
| 底層渲染 / 輸入 / 音效 | **Slick2D** + **LWJGL**（OpenGL）| `lib/slick.jar`、`lib/lwjgl.jar`、`lib/native/*.so` |
| Shader | GLSL（`.frag` / `.vert`）| `data/*.frag`、`data/*.vert`（bevelled/lit/masked/flag…）|
| 序列化 | `org.json`（內嵌於 `game.jar` 的 `org/json/`）| 所有資料與存檔皆 JSON |
| Steam 整合 | steamworks4j | `lib/steamworks4j-*.jar`、`libsteam_api.so` |
| 音樂 / 音效 | ibxm（tracker）、jorbis/jogg（Ogg Vorbis）| `lib/` |
| 其他 | joda-time、commons-io/codec、jinput | `lib/` |

啟動設定 `config.json`：`mainClass = com/zarkonnen/airships/Main`，VM 參數 `-Xmx1024m -Dsteam=true -Djava.library.path=lib/native`。

**規模**：`game.jar` 約 10.5 MB，`com.zarkonnen.airships` 套件**單一扁平命名空間**下有 **629 個頂層類別**（含內部類別共 2510 個 `.class`）。`data/` 約 1.4 GB（含貼圖），是高度資料驅動的設計。

---

## 3. 引擎抽象層 CatEngine (Level 2)

CatEngine 是作者自製的薄抽象層，把 Slick2D/LWJGL 包成乾淨的介面，讓遊戲邏輯不直接依賴底層 API。

- `com.zarkonnen.catengine.Engine`（介面）：`setup(Game)` / `runUntil(Condition)` / `destroy()` / `setExceptionHandler()` — **主迴圈在 `runUntil` 內**。
- `com.zarkonnen.catengine.Game`（介面）：只有兩個方法 `input(Input)` 與 `render(Frame)`。整個遊戲就是實作這個介面。
- `com.zarkonnen.catengine.SlickEngine`：以 Slick2D 實作 `Engine`，是真正驅動 OpenGL 視窗、輸入、音效的地方。
- 其他：`Frame`（繪製目標）、`Draw`（繪圖 API）、`Img`（貼圖）、`Input`（輸入）、`Fount`（字型）、`Hooks/Hook`、`Loop`（**音效**循環，非主迴圈）、`util/`。

**遊戲端入口**：`com.zarkonnen.airships.AirshipGame implements catengine.Game, ExceptionHandler, SlickEngine.ReportHandler`。
它持有當前畫面 `public Screen s;`——即整個 UI 是一台**畫面狀態機**。

---

## 4. 畫面狀態機：Screen 模式

`com.zarkonnen.airships.Screen`（介面）定義：
```
void input(Input, MyDraw.State, Pt, Pt, int)
void render(MyDraw, ScreenMode, Hooks, Pt)
ArrayList<String> music()
String appearancePostfix()      // 用來切換貼圖主題（如冬季）
boolean alwaysUseAppearancePostfix()
```

`AirshipGame.s` 一次只跑一個 Screen；切換畫面＝換掉這個欄位。具體 Screen 約 30 個（`*Screen` 命名），代表性者：
- `MainMenu`、`GameSetupScreen`、`FileScreen`（存讀檔）、`ResumeScreen`
- `StrategicScreen`（**最大類別，306 KB**）—— 戰略地圖主畫面
- `StrategicLobbyScreen`、`HostOrJoinStrategicScreen`、`HostOrJoinGameScreen`（多人）
- `UniScreen`（通用容器）

UI 還用了一套元件命名模式（數量＝粗略複雜度指標）：
`Button`(49) / `Layer`(31) / `Screen`(30) / `Intent`(33) / `Overlay`(25) / `Mission`(19) / `Adapter`(12) / `Chrome`(11) / `Process`(10)。
- **Intent**：玩家「意圖／動作」物件（`CombatIntent`、`EditShipIntent`、`BuildShipMission`…），把一次互動封裝成可執行、（多人時）可透過網路傳遞的指令。
- **Chrome / Overlay / Layer**：分層繪製的 HUD 與面板（`AmmoDistOverlay`、`BlockingModulesOverlay`、`AIDebugLayer`…）。
- **Adapter**：把資料模型接到 UI 列表（`EmpiresAdapter`、`CityClaimAdapter`…）。

---

## 5. 雙層遊戲結構：戰術 Combat × 戰略 Campaign

這是本作架構的主軸——和許多 4X／戰役遊戲一樣分成兩層，但兩層共用同一套船艦／模組模型。

### 5.1 戰術層 `Combat`（`Combat.java`，79 KB）
即時側視戰場。`Combat implements JSONAble, ShipList`，核心欄位：
- `ArrayList<Combat.Side> sides`：對戰陣營
- `LinkedList<Shot> shots` / `Particle particles` / `Fragment fragments`：彈藥、粒子、碎片
- `ArrayList<LandFormation> landFormations`：地形
- 固定步長模擬：`TICK_LENGTH`、`simTick`
- **確定性鎖步多人**（見 §7）：`GuardedRandom r`、`Client mpClient` / `Server mpServer`、`frameQueue`、`hashHistory`、`netTick`

### 5.2 戰略層 `CampaignWorld` / `WorldMap` / `Empire`
- `CampaignWorld`（68 KB）：戰役世界狀態（回到 Combat 由 `Combat.campaignWorld` 連回）。
- `WorldMap`（134 KB）：策略地圖。
- `Empire`（88 KB）：帝國（資源、城市、外交關係 `HasRelationships`）。
- AI 一族（11 個 `*AI`）：`DiplomacyAI`（76 KB）、`CityAI`、`FleetAI`、`HeroManagementAI`、`AIConstructionUtils`、`AIQuality`、`AIUtils`。
- 戰役系統由 `data/help_en/` 印證：Conquest、Alliance/Alliance_Victory、Autoresolve（自動解算戰鬥）、City Upgrades、Buildings、Unrest（民怨）、Monster Nests、Coats of Arms（紋章）。

兩層之間：戰略層產生一場戰役戰鬥 → 進入 `Combat` 模擬 → `CombatOutcome` 回寫戰略層（或 `Autoresolve` 直接估算）。

---

## 6. 資料驅動核心：`Loadable` 型別系統 (Level 2，重點)

**這是整個遊戲最關鍵的可模組化骨架。** `data/` 下每個目錄名（`ModuleType`、`BodyPlan`、`CrewType`、`ArmourType`、`ParticleType`…）對應一個 `Loadable` 子類別，目錄裡的 JSON 檔被載入成該型別的實例。

> 原始碼：`projects/airships-cts/src/com/zarkonnen/airships/Loadable.java`。`LOADABLES` 註冊表（`Loadable.java:111`）共列 **71 種**可載入型別——比 `data/` 目錄數還多，因為部分型別（`Edict`、`HeroType`、`IncidentType`、`MedalPart/Metal/Effect/RibbonLayout`、`Tincture`、`Charge`、`ExpansionMusic`…）只由**資料片**提供。

`com.zarkonnen.airships.Loadable`（抽象類，`implements Comparable<Loadable>`）：
```java
public final String name;              // 主鍵（如 "BALLISTA"）
public final int sort;                 // 排序權重
public Expansion sourceExpansion;      // 來源：資料片
public Mod sourceMod;                  // 來源：模組（出處追蹤）
public static final Class[] LOADABLES; // 所有可載入型別的註冊表
public static HashMap<Class, HashMap<String, Object>> map;   // 型別→(name→實例)
public static HashMap<Class, ArrayList>               alls;  // 型別→全部實例
public static HashMap<Class, ArrayList<String>>       errorLogs;
// 查找 API
static <T extends Loadable> T            ofName(Class<T>, String);
static <T extends Loadable> boolean      hasOfName(Class<T>, String);
static <T extends Loadable> ArrayList<T> all(Class<T>);
// 載入流程
static boolean    load();
static LoadResult loadDir(Class, File, ...);
static LoadResult loadFile(Class, File, ...);
static <T> Map<...> loadBase(Class<T>);     // 先載基礎遊戲
static long       getDataChecksum();        // 全資料校驗碼（多人同步用）
```

設計要點：
1. **目錄即型別**：新增一個 `data/ModuleType/MY_GUN.json` 就新增一種武器，無需改程式。
2. **載入順序（`load()` @ `Loadable.java:181`）＝ base → expansions → mods**：
   - 先 `loadBase`（`:199`、`:339`）載官方 `data/<Type>/`；
   - 再依序載各資料片目錄並標記 `sourceExpansion`（`:207-216`）；
   - **最後**載各模組目錄並標記 `sourceMod`（`:233-241`）——因為 mod 最後載入，所以能覆寫／擴充先前的同 `name` 條目（見 `data/Modding Notes.txt` 的 `addToHeraldicStyles` 等增量欄位）。
3. **出處追蹤**：`sourceMod`（`Loadable.java:110`）/ `sourceExpansion`（`:109`）記錄每筆資料來自哪個模組／資料片。
4. **查找與防呆**：`ofName(Class, name)` 查不到會丟 `NotFoundException` 並走 `Lang._t` 多語系錯誤訊息（`Loadable.java` ofName）；`errorLogs` 收集各型別載入失敗紀錄。
5. **資料校驗**：`getDataChecksum()`（`Loadable.java:442`）算出全部資料的雜湊（對應 `data/checksum` 檔與 `AirshipGame.dataChecksum/expectedDataChecksum`），多人連線時雙方資料必須一致，否則會去同步。

`data/` 內容規模（節錄）：`ships`(1115) / `buildings`(677) / `landships`(289) / `images`(886) / `sounds`(270) / `ModuleType`(214) / `monsters`(77) / `DecalType`(71) / `help_en`(46)；`generated/`(203) 為**預打包貼圖圖集** `.png.tex`（含 `DAY` 日間、`DAMAGED` 損毀、`FRAGMENTS` 碎片、`bump` 法線貼圖等變體）。

---

## 7. 確定性鎖步多人 (Level 3，重點)

`Combat` 的欄位明確指向**deterministic lockstep**（與多數 RTS 相同）。原始碼：`projects/airships-cts/src/com/zarkonnen/airships/Combat.java`。

- `GuardedRandom r`（`Combat.java:123`，種子化於 `:812` `new GuardedRandom(this.randomSeed)`）：包一層 `java.util.Random`，有 `guard` 旗標與私有 `check()`。設計意圖是攔截「在確定性模擬之外」呼叫 RNG 的行為。
  - ⚠️ **校正（讀原始碼發現）**：在此發行版中 `GuardedRandom.check()` **是空的 no-op**（`GuardedRandom.java`），`guard` 旗標形同未啟用——應是 release 時關閉的除錯機制。重寫時這層可視為「曾用於除錯的確定性護欄」，真正的確定性靠下列其他機制。
- `simTick`（`Combat.java:138`）vs `netTick`（`:137`）、`TICK_LENGTH`：模擬以固定步長前進（`tick()` @ `Combat.java:975`，每跑一步 `++this.simTick` @ `:1121`）；網路幀（玩家指令）排入 `frameQueue`，所有客戶端跑相同模擬。指令以 `{command, frameNumber, time, simTick}` 形式記錄（`:462`）。
- `baseState` + `networkFrameHistory` + `INITIAL_QUEUE_SIZE` + `initialQueueFilled`：初始狀態 + 後續輸入幀＝可重建整場戰鬥（`recordEntireCombatState` 設定）。
- **去同步偵測**：`HASH_EVERY = 1024`（`Combat.java:110`）。每 1024 個 time 單位（`:271` `this.time % 1024 == 0 && !this.desyncConfirmed`）對模擬狀態取雜湊存入 `hashHistory`；當收到的雜湊與本地不符即 `desyncConfirmed = true`（`:2102-2108`）。
- `全程 strictfp`：強制跨平台浮點一致，是確定性模擬的必要條件。**C++ 重寫須特別注意**：要嘛全程用整數定點數，要嘛嚴格控制浮點（`-ffp-contract=off`、避免 `fma`/快速數學、固定編譯器與 SSE 模式），否則無法重現 Java `strictfp` 的逐位元結果。

連線設定在 `launch_settings.json`：`maxNetworkSendBytes`、`measureNetworkDelayEveryMilliseconds`、`tooMuchNetworkDelayMilliseconds`、`reconnectAttemptInterval`、`maxReconnectAttempts`…。
可自架伺服器（`How to run your own server.txt`）：`java -cp game.jar com.zarkonnen.airships.Server`，再於 `launch_settings.json` 設 `customMultiplayerServerAddress`。LAN 直連走 IP，免伺服器。

---

## 8. 船艦 / 模組執行期模型 (Level 2-3)

**定義（Type）vs 實例（Instance）分離**，是本作模擬的基礎：

- `ModuleType extends Loadable implements HasName`：模組「種類」的定義。大量欄位用 `BonusableValue<T>` 包裝（hp、weight、coal、ammo、moveDelay、fireHP、explodeDmg…），代表這些數值**可被加成系統（Bonus / Tech / EraModifier）動態修改**。
  - `BonusableValue<T>`（抽象）：`get(BonusSet)` 依當前加成解出實際值；`explain(BonusSet, ...)` 產生人類可讀的拆解（「HP 160（+20 來自 X）」），驅動遊戲內 tooltip。支援 `derive`/`list` 組合與 `*FromJSON` 載入。
  - 變體系統：`flippedFrom`/`flippedVersion`/`verticallyFlippedVersion`、`variants`/`variantType`（左右翻轉、外觀變體）。
- `Module`：放在 `Airship` 上某格 `(x, y)` 的執行期實例，`type` 指回 `ModuleType`。內含逐格模擬狀態：火焰蔓延（`FIRE_SPREAD_RATIO`、`FIRE_SPREAD_RATIO_DOORS`、blast armour 對火牆傷害的遞減）、爆炸機率（`EXPLODE_P`）、解體（`BREAK_APART_HP`）、`wheels`/`legs`/`tentacles`/`tether`（陸行艦輪腳、怪物觸手、繫纜）、相鄰加成（`ADJACENCY_BONUS`）。
- `Airship`（196 KB，第二大類）：整艘船，由眾多 `Module` 組成；負責物理（升力／重量／浮力）、船員 `Crewman`（93 KB，有尋路 `jumpPoint`/`walkPoint`、職務分派）。
- 武器資料範例見 `data/ModuleType/BALLISTA.json`：含 hp/weight/cost/crew、`reload`/`clip`/`penDmg`/`inaccuracy`/`fireArc`/`maxXRange`/`optimumRange`、`weaponAppearance`（spritesheet 座標 + 砲管逐幀動畫）、`fireSound`/`hitSound`（多層次、音量／音高隨機）。

存檔格式：整個遊戲狀態序列化成 JSON（見 `default_ships/*.json`，含 crew 的完整執行期狀態 `jobIndex`/`tile`/`weaponReload`…）。

---

## 9. 模組化 (Modding)

- 官方支援，指南見 `data/Modding Notes.txt` 與線上 modding_guide。
- 機制：丟 JSON 進對應 `data/<Type>/` 目錄即可新增／覆寫 `Loadable`。
- 增量覆寫：如 `addToHeraldicStylesAsChargeTincture`、`addToHeraldicStyles` 等欄位讓模組「附加」而非「整段重寫」。
- `sourceMod` 追蹤 + `getDataChecksum()` 確保多人雙方模組一致。

---

## 10. 後續可深入方向（待辦）

- [ ] `details/`：精讀 `Combat` 主迴圈（tick → 指令套用 → 物理 → 雜湊）與去同步偵測流程，標註反編譯行號。
- [ ] `details/`：`Airship` 升力／重量／升降物理與 `Crewman` 尋路。
- [ ] `details/`：`Loadable.load()` 完整載入順序（base → expansion → mod → 校驗碼）。
- [ ] `architecture/`：戰略層 `CampaignWorld`/`Empire`/`DiplomacyAI` 的回合與 AI 決策。
- [ ] `tutorial/`：如何寫一個新武器模組（最小可玩範例）。
