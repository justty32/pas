# Airships: Conquer the Skies — 資料驅動核心 `Loadable` 系統分析

> 事實來源：`projects/airships-cts/src/com/zarkonnen/airships/*.java`（CFR 反編譯）。
> 原始資料：`~/.local/share/Steam/steamapps/common/Airships Conquer the Skies/data/`。
> 本文件面向「用 C++ 從頭重寫」的重新實作者。所有主張標註 `檔名.java:行號` 或 `data/路徑`。

---

## 0. 總覽：這個子系統做什麼

`Loadable` 是整個遊戲「資料驅動」的地基。所有可以被資料 / 模組定義的型別（武器模組、裝甲、船員、科技、難度、天氣、雲、心情值 Bonus……）都繼承自 `Loadable`（`Loadable.java:105`），並從磁碟上的 JSON 檔案載入。

核心三件事：
1. **型別註冊表** — 一個靜態 `Class[] LOADABLES` 列出全部 71 種可載入型別（`Loadable.java:111`）。
2. **反射式載入** — 對每個型別呼叫其 `(JSONObject)` 建構子（`Loadable.java:380` `clazz.getDeclaredConstructor(JSONObject.class)`），把 JSON 物件變成實例。
3. **三層覆寫合併** — base data → expansions → mods，後者覆寫前者同 `name` 的條目（`Loadable.load()` @ `Loadable.java:181`）。

關鍵欄位（`Loadable.java:107-115`）：
- `public final String name`（`107`）— 主鍵；JSON 必填 `"name"`。
- `public final int sort`（`108`）— 排序權重；JSON 選填 `"sort"`，預設 0。
- `public Expansion sourceExpansion` / `public Mod sourceMod`（`109-110`）— 來源追蹤（base 資料兩者皆 null）。
- `static HashMap<Class, HashMap<String, Object>> map`（`112`）— 主查找表：型別 → (name → 實例)。
- `static HashMap<Class, ArrayList> alls`（`113`）— `all(clazz)` 的排序快取。
- `static HashMap<Class, ArrayList<String>> errorLogs`（`114`）— 每型別載入錯誤。
- `static HashMap<Class, HashMap<String, JSONObject>> baseEntries`（`115`）— 每型別「目前已知條目的原始 JSON」，供 `deriveFrom`/`patch` 取用。

---

## 1. 型別註冊表（LOADABLES 71 種）

完整列表來自 `Loadable.java:111`，依陣列順序（**載入順序＝陣列順序**，極為重要，見 §2）。下表分類並標出哪些型別在 `data/` **沒有 base 目錄**（純由「英雄與惡棍 Heroes & Villains」資料片 / EHeroes 提供，目錄在 `data/crossplay/heroes/<型別名>/`）。

| # | 型別 | 分類 | base data? | 備註 |
|---|------|------|-----------|------|
| 1 | LoadingQuote | 設定/介面 | ✅ | 載入畫面引言 |
| 2 | FrequencySetting | 戰略設定 | ✅ | 事件頻率 |
| 3 | **CrewExperienceLevel** | 戰鬥 | ❌ DLC | `crossplay/heroes/CrewExperienceLevel/levels.json` |
| 4 | Shouts | 外觀/音效 | ✅ | 船員喊話 |
| 5 | VariantType | 外觀 | ✅ | 變體分類（見 §3.4） |
| 6 | GenericFragment | 外觀 | ✅ | 通用碎片貼圖 |
| 7 | CityName | 戰略 | ✅ | 城市命名池 |
| 8 | Tincture | 外觀/紋章 | ✅ | 紋章顏色 {r,g,b}（見 §3.3） |
| 9 | PaintType | 外觀 | ✅ | 塗裝 |
| 10 | GameSetting | 設定 | ✅ | 全域數值（見 §3 範例） |
| 11 | MapSize | 戰略設定 | ✅ | |
| 12 | EmergentMapFeature | 戰略 | ✅ | 地圖湧現特徵 |
| 13 | Bonus | 戰鬥/戰略 | ✅ | 心情/科技開關（見 §3.2 核心） |
| 14 | DifficultyLevel | 設定 | ✅ | |
| 15 | EmpireStat | 戰略 | ✅ | 帝國數值（多 BonusableValue） |
| 16 | StrategicEra | 戰略 | ✅ | 戰役時代 |
| 17 | TakeoverMethod | 戰略 | ✅ | 占領手段 |
| 18 | CityUpgradeType | 戰略 | ✅ | 城市升級 |
| 19 | DiplomacyPersonality | 戰略 | ✅ | 外交 AI 個性 |
| 20 | SpritesheetBundle | 外觀 | ✅ | 貼圖集 + bump + fragments（衍生資料來源） |
| 21 | ParticlePictureType | 外觀 | ✅ | 粒子圖片 |
| 22 | ArmsLayout | 外觀/紋章 | ✅ | 紋章佈局（addToHeraldicStyles，見 §5） |
| 23 | Cursor | 介面 | ✅ | |
| 24 | CloudType | 外觀 | ✅ | |
| 25 | Backdrop | 外觀 | ✅ | |
| 26 | BackdropType | 外觀 | ✅ | |
| 27 | BackgroundFloatieType | 外觀 | ✅ | 背景漂浮物 |
| 28 | BirdType | 外觀 | ✅ | |
| 29 | CombatBackgroundFlavor | 外觀 | ✅ | |
| 30 | TerrainFeatureType | 戰略 | ✅ | |
| 31 | ParticleType | 外觀 | ✅ | 粒子 |
| 32 | WeatherEffect | 外觀/戰鬥 | ✅ | |
| 33 | TimeOfDay | 外觀 | ✅ | 燈光烘焙來源（lightmap） |
| 34 | Season | 戰略 | ✅ | |
| 35 | Moon | 外觀 | ✅ | |
| 36 | LandBlockType | 戰略/地形 | ✅ | |
| 37 | LandscapeType | 戰略/地形 | ✅ | |
| 38 | BodyPlan | 戰鬥/生物 | ✅ | 怪物身體規劃 |
| 39 | AnimationBundle | 外觀 | ✅ | |
| 40 | AnimationAppearance | 外觀 | ✅ | 船員動畫外觀 |
| 41 | CrewType | 戰鬥 | ✅ | 船員/飛機/怪物（見 §3.1 複雜範例） |
| 42 | DecalCategory | 外觀 | ✅ | |
| 43 | DecalType | 外觀 | ✅ | 貼花（支援 flip/variant） |
| 44 | ArmourType | 戰鬥 | ✅ | 裝甲（BonusableValue + variants，見 §3） |
| 45 | ModuleCategory | 戰鬥 | ✅ | 模組分類 |
| 46 | ModuleType | 戰鬥（最複雜） | ✅ | 船體模組（flippedFrom/variants，見 §3.4） |
| 47 | Substitution | 戰略 | ✅ | 文本替換 |
| 48 | Tech | 戰略 | ✅ | 科技樹（postLoad 排佈局，見 §3.5） |
| 49 | Charge | 外觀/紋章 | ✅ | 紋章圖徽 |
| 50 | HeraldicStyle | 外觀/紋章 | ✅ | 紋章風格（接收 addTo… 增量，見 §5） |
| 51 | ConstructionName | 戰略 | ✅ | 建造命名 |
| 52 | ConstructionStrategy | AI/戰略 | ✅ | AI 造船策略 |
| 53 | PortraitMessageType | 介面 | ✅ | 肖像訊息 |
| 54 | MonsterNestType | 戰略/生物 | ✅ | 怪物巢（支援 `remove`，見 `Loadable.java:177`） |
| 55 | MusicAffinity | 音效 | ✅ | |
| 56 | PlagueLevel | 戰略 | ✅ | 瘟疫等級 |
| 57 | EraModifier | 戰略 | ✅ | |
| 58 | MiscCombatSound | 音效 | ✅ | |
| 59 | GUISetting | 介面 | ✅ | |
| 60 | Splinter | 外觀 | ✅ | 木屑碎片 |
| 61 | MonsterSetting | 戰略 | ✅ | |
| 62 | SeaLevelSetting | 戰略設定 | ✅ | |
| 63 | TechSpeedSetting | 戰略設定 | ✅ | |
| 64 | **Edict** | 戰略 | ❌ DLC | `crossplay/heroes/Edict/edicts.json` |
| 65 | **HeroType** | 戰略/角色 | ❌ DLC | `crossplay/heroes/HeroType/{captains,governors,incidents}.json`；載入有額外守門：`if (clazz == HeroType.class && !EHeroes.it.enabled) continue;`（`Loadable.java:195`） |
| 66 | **IncidentType** | 戰略/角色 | ❌ DLC | `crossplay/heroes/IncidentType/incidents.json` |
| 67 | **MedalPart** | 外觀/角色 | ❌ DLC | `crossplay/heroes/MedalPart/layer{1..4}.json` |
| 68 | **MedalMetal** | 外觀/角色 | ❌ DLC | `crossplay/heroes/MedalMetal/metals.json` |
| 69 | **MedalEffect** | 角色 | ❌ DLC | `crossplay/heroes/MedalEffect/level{1..4}.json` |
| 70 | **MedalRibbonLayout** | 外觀/角色 | ❌ DLC | `crossplay/heroes/MedalRibbonLayout/layouts.json` |
| 71 | **ExpansionMusic** | 音效 | ❌ DLC | `crossplay/heroes/ExpansionMusic/music.json`；`Expansion.afterLoad()` @ `Expansion.java:137` 依 forCombat/forEditor/forStrategic 註冊到 AGame 音樂池 |

**結論**：8 個型別（# 3, 64-71）沒有 base 目錄，純由 heroes 資料片提供。其餘 63 個型別在 `data/<型別名>/` 都有 base 目錄（已用腳本逐一驗證）。注意 heroes 資料片同時也**擴充**許多既有型別（如它的 `crossplay/heroes/CrewType/`, `Bonus/`, `Charge/`…，會在載入時覆寫/新增到既有型別）。

> 反射依賴：`LOADABLES` 是 `Class[]`，`load()` 用 `clazz.getSimpleName()` 當成資料夾名（`Loadable.java:340,446`），用 `clazz.getDeclaredConstructor(JSONObject.class)` 當建構入口（`Loadable.java:380`）。C++ 沒有這個——見 §6。

---

## 2. 載入流程（`Loadable.load()` @ `Loadable.java:181-329`）

### 2.1 精確順序

整個 `load()` 是一個 try/catch 包住的單一函式，外層 catch 會把所有 mod 永久停用並回報崩潰（`Loadable.java:319-328`）。

**步驟 A — 清空（`183-191`）**：
- 對 `map` 中所有現存實例呼叫 `close()`（`183-187`）。
- `map.clear()`、`alls = null`、`errorLogs.clear()`、`baseEntries.clear()`（`188-191`）。

**步驟 B — 取得啟用的 mods（`192`）**：`Mod.getEnabledMods()`。

**步驟 C — 對每個型別 `clazz`（依 `LOADABLES` 陣列順序）做（`193`）**：
> 順序是**確定性的**且重要：`CrewType` 在 `AnimationAppearance` 之後（`CrewType` 建構子會 `AnimationAppearance.ofName(...)`，依賴對方先載入）；`Tech` 在 `Bonus` 之後（`Tech.Choice` 解析 `Bonus.ofName`）。重寫時必須照抄這個順序。

1. **DLC 守門**：`HeroType` 若 `!EHeroes.it.enabled` 直接跳過（`195`）。
2. **載入 base**：`Loadable.loadBase(clazz)`（`199`，定義 @ `339-350`）：
   - 目錄 `data/<SimpleName>/`（`340`）。
   - 建立空 `prevEntries` 並存進 `baseEntries.put(clazz, prevEntries)`（`341-342`）—— **這是 deriveFrom/patch 的來源**。
   - `loadDir(...)` 把結果存進 `map.put(clazz, lr.loaded)`、`errorLogs.put(clazz, lr.log)`（`344-345`）。
   - 處理 base 內部的 `remove`（`346-348`）。
   - 回傳 `baseFailures`（建構失敗但暫不致命的條目，可能被後續層修復）。
   - **若 base 有 log 錯誤**（`errorLogs.get(clazz)` 非空，`200`），全部 mod 標記 `loadFailed` 並 `return false`（致命）。
3. **疊加 expansions**（`206-230`，依 `Expansion.enableds()`）：
   - `loadDir(clazz, new File(ex.getDataDir(), SimpleName), baseEntries.get(clazz))`（`207`）。`getDataDir()` = `data/crossplay/<expansionName>/`（`Expansion.java:78-80`）。
   - 任何 log 錯誤即 `return false`（`208-214`）。
   - 載入的實例標 `sourceExpansion = ex`（`215-217`）。
   - **覆寫合併**：對 `p.removed` 與 `p.loaded` 的每個 key，若 `map` 已有同名，先 `close()` 再 `remove`（`218-227`），最後 `map.putAll(p.loaded)`（`228`）。
   - `baseFailures.putAll(p.failures)`（`229`）。
4. **疊加 mods**（`231-272`，依 `mods`）：
   - `loadDir(clazz, new File(mod.dir, SimpleName), baseEntries.get(clazz))`（`233`）。
   - log 錯誤 → `mod.loadFailed`, `return false`（`234-239`）。
   - 實例標 `sourceMod = mod`（`240-242`）。
   - **覆寫合併**：對 removed/loaded 同名先 `close()`+remove，並從 `baseFailures` 移除（即 mod 可修復 base 的失敗條目，`243-254`）。
   - **mod 的建構失敗是致命的**：`p.failures` 非空 → `mod.loadFailed`, `setPermanentlyEnabled(false)`, `return false`（`255-265`）。
   - `map.putAll(p.loaded)`（`266`）。
   - **ModuleType 特例**：載完後跑 `ModuleType.checkForRefProblems()`（`267`），檢查 `flippedFrom` 指向的模組是否存在（`ModuleType.java:1003-1015`），有問題即致命。
5. **base 殘留失敗檢查**：跑完該型別所有層後，若 `baseFailures` 仍非空（沒被任何 mod/expansion 修復），則致命（`273-288`）。

**步驟 D — postLoad 階段（`289-313`）**：
- `alls = new HashMap()`（`289`）啟用排序快取。
- 依序呼叫各型別的 `postLoad`（建立衍生索引、解析交叉引用）：`CrewType.postLoad`（`290`，分類 worker/guard/boarder 等並排序）、`ArmourPlate.updateAppearances`、`CoatOfArms.updateAppearances`、`Charge.postLoad`、`TimeOfDay.postLoad`、`Resource.updateAppearances`、`ModuleType.postLoad`（`296`，解析 flip/vertical-flip/variant）、`DecalType.postLoad`、`DecalCategory.postLoad`、`ArmourType.postLoad`（`299`，建 variant group）、`Challenge.updateTypes`、`SettingsScreen.postLoad`、`Bonus.postLoad2`（`302`，建 standardSet + bonusConstructions）、`LandBlockType.postLoad`、`HeroType.postLoad`、`CityUpgradeType.postLoad`、`Tech.postLoad`（`306`，失敗則致命）、`MonsterNestType.postLoad`。
- 對每個 expansion 跑 `afterLoad()`（`311-312`，註冊 ExpansionMusic）。
- 回傳 `true`（`317`）。

> postLoad 等於 C++ 中的「第二趟（two-pass）」：第一趟反序列化、第二趟綁定交叉引用與建快取。重寫時這個兩趟架構要保留。

### 2.2 `loadDir` / `loadFile`（檔案層級）

**`loadDir`（`352-375`）**：
- `dir.listFiles()`，**`Collections.sort(fsL)`**（`360`）—— 檔名字典序，確保跨平台確定性。
- 跳過 `.` 開頭與非 `.json` 檔（`362`）。
- 對每檔 `loadFile`，把結果 putAll。重複 key 只印 stdout 警告，不致命（`366-368`）。

**`loadFile`（`377-436`）**：
- 取得 `(JSONObject)` 建構子（`380`），失敗丟 RuntimeException。
- 整個檔是一個 **JSONArray**（`390` `new JSONArray(...)`，UTF-8）；逐元素：
  - `"remove": true` → 加入 removed set，不建實例（`393-396`）。
  - `"patch": true` 或有 `"deriveFrom"` → 繼承既有條目欄位（見 §4.2）（`397-413`）。
  - `cons.newInstance(o)` 建實例（`416`）。建構失敗時：若無 `"name"` 跳過（容錯），否則記入 `failures`（`418-422`）。
  - **每個成功建構的條目把它最終的 JSON 寫回 `prevEntries.put(t.name, o)`**（`423`）—— 這就是為何後面的層能 `deriveFrom`/`patch` 前面層的條目。
  - `map.put(t.name, t)`（`427`），同名印警告。

### 2.3 排序 / compareTo

- `compareTo`（`Loadable.java:131-136`）：先比 `sort`（升冪），相等再比 `name`（字典序）。
- `all(clazz)`（`152-171`）：從 `map.values()` 複製、`Collections.sort`、快取進 `alls`，回傳**複本**（防外部改動）。
- `ofName`（`138-146`）/`hasOfName`（`148-150`）：直接查 `map`，找不到丟 `NotFoundException`（`503-513`）。
- `remove(MonsterNestType)`（`177-179`）：唯一的執行期移除 API（怪物巢被消滅時）。

---

## 3. JSON 解析慣例

每個子類別建構子手寫 `o.optX("key", default)` / `o.getX("key")`。**沒有 schema 檔，schema 就是建構子程式碼。** 通用慣例：

### 3.0 標量欄位
- 必填：`o.getString("name")`、`o.getInt("maxHP")`（`CrewType.java:295,315`）—— 缺值丟例外 → 建構失敗。
- 選填+預設：`o.optBoolean("doesWork", false)`（`CrewType.java:297`）、`o.optInt("commandPointsRequired", 50)`（`300`）、`o.optDouble("crewEffectiveness", 1.0)`（`301`）、`o.optString("spawnCrewOnImpact", null)`（`487`）。
- `sort`：`o.optInt("sort", 0)`（如 `ArmourType.java:81`, `Tech.java:48`, `ModuleType.java:441`）。

### 3.1 巢狀物件、貼圖座標、列舉、條件分支（CrewType）
- **貼圖** `Img`：統一 helper `Loadable.img(o)`（`Loadable.java:438-440`）= `{src, x, y, w, h, flipped?}`（像素座標）。但很多型別自行解析且**單位不同**：
  - `CrewType.simpleLook`：若有 `simpleLookImg` 用像素座標；否則 `simpleLook` 用 **16px 格座標**（`x*16, y*16, 16, 16`）（`CrewType.java:313`）。ModuleType 的 `D_App.frame` 也是 `x*16`（`Mod.java:1202`）。**重寫須注意「像素 vs 格」兩種座標慣例並存。**
- **列舉**：`ShipType.valueOf(af.getString(i))`（`ArmourType.java:117`）、`RecolorReplacement.valueOf(...)`（`CrewType.java:431`）—— 直接對應 Java enum 名稱字串。
- **顏色**：`{r,g,b}` 整數 0-255，常除以 255 轉 float：`o.getJSONObject("recolorOriginalA").getInt("r")/255.0f`（`CrewType.java:430`）。Tincture 用 `pureColour`/`moduleColour`（`data/Tincture/tinctures.json`）。
- **陣列**：`o.getJSONArray("animLooks")` 逐項 `ofName`（`CrewType.java:307-311`）；也支援單數捷徑 `animLook`（`304-305`）。
- **多型音效**：`deathSnd` 等可為字串（檔名+數量）或物件（`CrewType.java:364-372` try/catch 兩種形態）。
- **條件欄位群**：`canFly` 為真時才讀一整組空氣動力欄位（`getDouble` 必填），否則全部歸 0（`CrewType.java:495-550`）。
- **嵌套發射器**：`shotEmitter`/`exhaust` 解析成 `Particle.Emitter`/`ShotExhaustEmitter`（`465-486`）。

### 3.2 Bonus —— 整個資料系統的「條件鍵」
`Bonus`（`Bonus.java`）本身極簡（只有 `name` + `standard`，`37-41`），但它是所有 **BonusableValue** 的索引鍵。`Bonus.ordinal()`（`127-132`）= 在 `all(Bonus.class)` 排序後的索引，被當成 bitset 位置（`Tech.java:77` `e.bonuses().contains[ordinal]`）。`data/Bonus/bonuses.json` 從 `NO_BONUS` 開始定義所有遊戲開關（科技解鎖、心情、特殊）。

### 3.3 BonusableValue —— 隨「擁有的 Bonus 集合」而變的值
`BonusableValue<T>`（`BonusableValue.java:20`）是抽象值，`get(BonusSet)` 依當前 bonus 回傳不同結果。是裝甲/模組數值的核心。JSON 形態（`intFromJSON` @ `BonusableValue.java:351-403`）：
- **純數字** → `NoBonus`（固定值）（`342`）。
- **`{base, multipliers:{BONUS:x}, deltas:{...}, dividers:{...}}`** → `IntArithmeticBonus`：對每個擁有的 bonus 套乘/加/除（`352-381`）。
  - 例 `data/ArmourType/20_LT_Steel.json`：`"hp": { "base": 40, "multipliers": { "GRACILE": 0.25, "HAMMER": 1.75 } }`。
- **`{base, cases:[{bonuses:[...], value:v, description?}]}`** → `SetBonus`：第一個 bonus 集合完全符合的 case 生效（`383-396`）。
  - 例同檔 `"cost": { "base": 2, "cases": [ {"bonuses":["CHEAP_STEEL"],"value":1} ] }`。
- **`{base, BONUS_NAME:v}`** 捷徑 → `SingleBonus`（`398-401`）。
- 物件版 `objectFromJSON`（`267-293`）支援 `base`+`cases`，或直接列舉 bonus 名當 key（`ObjectVariantBonus`）。
- 也有 `intFromJSONWithDivAndMinAndMax`（`339`，CrewType.weaponReload 用 div=1000 把秒轉毫秒，`CrewType.java:342`）。
- `derive`（`101-132`）：把一個 BonusableValue 映射成另一個（保留 bonus 結構），如 `ArmourType.fragments`（`ArmourType.java:99`）。

### 3.4 翻轉 / 變體（flippedFrom / variants / variantType / verticallyFlippedVersion）
- **`flippedFrom`（ModuleType/ArmourType/DecalType 專屬）**：JSON 只給 `{name, flippedFrom}`，建構子讀到後**直接 return**、不解析其他欄位（`ModuleType.java:446-448`）。真正的鏡像在 `ModuleType.postLoad`（`1026-1027` `deriveFlipped(ofName(flippedFrom))`）/`checkForRefProblems`（`1003-1015`，找不到來源即致命）。
  - 例 `data/ModuleType/BALLISTA.json` 第一條 `{"name":"FLIPPED_BALLISTA","flippedFrom":"BALLISTA"}`。
- **`verticallyFlippedVersion`**：name 字串，`postLoad` 雙向連結（`ModuleType.java:1020-1023`）。
- **`variants`**：字串陣列。ModuleType 把自身也加入 variantNames（`452-456`）；ArmourType `postLoad` 建 variant group，第一個是 head（`ArmourType.java:122-133`）。
- **`variantType`**：`VariantType.ofName` 或 `getDefault()`（`ModuleType.java:458`, `ArmourType.java:112`）。
- **deriveFrom 與 flip/variant 的交互**：在 `loadFile` 的 deriveFrom 複製欄位時，**故意不複製** `variants`/`verticallyFlippedVersion`/`flippedFrom`/`variantType`/`flippedVersion`（僅當 class 是 ModuleType/ArmourType/DecalType 且非 patch 時，`Loadable.java:410`）—— 避免衍生條目誤繼承翻轉/變體關係。

### 3.5 跨引用與佈局運算（Tech 範例）
`Tech`（`Tech.java`）展示「postLoad 解析依賴 + 算版面」：建構子只存 `dependencyNames` 字串（`60-65`）；`postLoad`（`215-348`）把名字解析成 `Tech` 參照、建相依矩陣 `depMatrix`、並用迭代法排科技樹佈局座標。失敗（未知依賴）回 false → `load()` 致命（`Loadable.java:306-309`）。`Tech.Choice`（`389`）解析 `bonuses`（→ BonusSet）與 `img`。

### 3.6 GameSetting —— 寫入靜態全域
`GameSetting`（`GameSetting.java:15-26`）按 `name` 把 `value` 寫進 class 的 static 欄位（如 `minStructuralStress`）。是「資料覆寫硬編碼常數」的模式。重寫時對應到一張「設定名 → 全域變數位址」的表。

---

## 4. modding 機制

### 4.1 目錄結構
- 本地 mod：`<gameDir>/mods/<modName>/`；Steam Workshop：`<gameDir>/steam/mods/<id>/<modName>/`（`Mod.refreshMods` @ `Mod.java:305-380`）。
- 每個 mod 必須有 `info.json`（`Mod.loadInfo` @ `239`）：`{id, name:{locale:str}, description:{locale:str}, tags:[...]}`，外加選用 `logo.png`。
- mod 內以**型別名為子目錄**放 JSON（與 base 同結構）：`<mod>/ModuleType/*.json`、`<mod>/CrewType/*.json`…（`Loadable.java:233`）。
- 資源根：`<mod>/images/`、`<mod>/generated/`、`<mod>/sounds/`（`Mod.addLoadBases` @ `299-303`）。
- 衍生圖（lightmap/fragments/damaged）由遊戲在載入時生成到 `<mod>/generated/`（`Mod.doGenerateDerivedData` @ `757-805`），並寫 `generated/ssb_checksum.txt` 判斷是否需重生。

### 4.2 增量覆寫（不必整段重寫）
1. **整條覆寫**：mod 放一條同 `name` 的完整條目，覆蓋前層（`Loadable.load()` 的 putAll 覆寫，`Loadable.java:249-266`）。
2. **`"remove": true`**：把某 name 從 map 移除（`Loadable.java:393-396`）。
3. **`"deriveFrom": "OTHER_NAME"`**：複製 OTHER 的所有欄位、再用本條目欄位覆蓋（`Loadable.java:398-413`）。OTHER 必須已存在於 `baseEntries`（前一層或本檔較前的條目），否則致命（`401-406`）。
4. **`"patch": true`**：同 deriveFrom 但 deriveFrom 名 = 自己的 name（就地修補既有條目，`400`），且 patch 模式**會**複製 flip/variant 欄位（`410` 的條件僅排除非 patch 的情形）。
5. **`addTo…` 增量註冊**（`data/Modding Notes.txt`）：某些型別支援「掛載到既有條目」而不覆寫整個目標：
   - Tincture：`addToHeraldicStylesAsChargeTincture`/`addToHeraldicStylesAsLayoutTincture`: `["player","city","pirate"]`。
   - ArmsLayout / Charge：`addToHeraldicStyles: ["player"]`。
   - 這些由各型別建構子讀取後反向修改 `HeraldicStyle`（# 50），是「子條目反向擴充父條目」的模式。

### 4.3 sourceMod / sourceExpansion 追蹤
載入時實例被標記來源（`Loadable.java:216,241`），供：UI 顯示「來自某 mod」（`ArmourType.getDesc` @ `ArmourType.java:167-169`）、警告檢查（`Mod.getWarnings` @ `Mod.java:118-198`）、mod 載入失敗時的錯誤歸屬。

### 4.4 載入失敗與重試
`Mod.doLoadMods`（`Mod.java:505-527`）：若 `Loadable.load()` 失敗，會反覆移除出問題的 mod（被 `setPermanentlyEnabled(false)`）再重載，直到成功或無 mod 可載。

---

## 5. 校驗碼（getDataChecksum）

### 5.1 計算方式
`Loadable.getDataChecksum()`（`Loadable.java:442-466`）：
- 對 `LOADABLES` 每個型別的 `data/<SimpleName>/` 目錄（若存在）累加 `Mod.checksum(dir)`（`445-454`）。
- 再加 `data/lang` 目錄（`456`）。
- `Mod.checksum(File)`（`Mod.java:712-722`）：目錄則遞迴累加子項（跳過 `.` 開頭）；檔案則 `FileUtils.checksumCRC32`（CRC32）。**注意是相加（不是雜湊串接），對檔案順序不敏感。**
- 和為 0 時改成 1（`461-463`）。
- base 的期望值存在 `data/checksum`（純文字 long，本機實測 `1237186232367`）。

`Expansion.getDataChecksum()`（`Expansion.java:30-54`）同理，但掃 `getDataDir()/<SimpleName>` 再加 `strings`（不是 lang）；期望值在 `crossplay/<exp>/checksum`。

### 5.2 用途與一致性
- **防竄改**（單機）：`LoadingScreen`（`LoadingScreen.java:127-173`）載入時算 `g.dataChecksum = Loadable.getDataChecksum()`，與 `data/checksum` 比對；不符且非開發模式時 `reportError("Altered data", ...)`（`145`）。開發模式（`AGame.doWritechecksum()`）則改寫 checksum 檔。
- **多人一致性**：`AirshipGame.dataChecksum`/`expectedDataChecksum`（`AirshipGame.java:150-151`），`hasCorrectChecksum()`（`351`）= 兩者相等。多人連線時雙方比對此值（資料/DLC 不一致則拒連）。
- **Mod 校驗**（跨平台傳輸）：`Mod.getChecksum`（`Mod.java:586-600`，跳過 `generated`）+ `getSSBChecksum2`（`602-706`，對貼圖/模組外觀做帶質數權重的雜湊）。Steam 跨平台 mod 同步（crossplay）用它驗證快取 mod 完整性（`getCachedModF` @ `382-406`）。

> 重寫注意：base/expansion 用「CRC32 相加」這種**順序無關**的弱校驗（夠用於防意外竄改，非密碼學安全）；mod SSB 校驗則用質數乘權重（順序敏感）。多人一致性要嚴格復刻同一演算法，否則跨版本對戰會誤判。

---

## 6. C++ 重寫建議

Java 靠 `Class` 當 map key + 反射建構子。C++ 沒反射，建議如下設計。

### 6.1 型別 ID 與註冊表
用 `enum class LoadableTypeId { LoadingQuote, FrequencySetting, ... ExpansionMusic };`（71 項，**順序必須與 `Loadable.java:111` 完全一致**，因為它就是載入順序與 checksum 掃描順序）。

每型別提供：
```cpp
struct LoadableTypeInfo {
    LoadableTypeId  id;
    const char*     dirName;      // = Java getSimpleName()，用作 data/<dirName>/
    bool            dlcOnly;      // 8 個 heroes-only 型別為 true
    // 工廠：把一個 JSON 條目轉成 unique_ptr<LoadableBase>，失敗丟例外
    std::function<std::unique_ptr<LoadableBase>(const json&, LoadContext&)> fromJson;
    std::function<void()> postLoad;            // 第二趟，可為 nullptr
    // deriveFrom 時要排除複製的欄位（ModuleType/ArmourType/DecalType）
    std::span<const char* const> deriveExcludeKeys;
};
inline const std::array<LoadableTypeInfo, 71> LOADABLES = { ... };
```
用一個 `REGISTER_LOADABLE(Type, "DirName", fromJsonFn, postLoadFn)` 巨集或 `constexpr` 陣列集中宣告，取代 Java 的 `Class[]` + 反射。

### 6.2 name → 實例查找表
```cpp
class LoadableStore {
    // 每型別一張表；用 enum 當外層 key
    std::array<std::unordered_map<std::string, std::unique_ptr<LoadableBase>>, 71> map;
    std::array<std::unordered_map<std::string, json>, 71> baseEntries; // deriveFrom/patch 來源
    std::array<std::vector<std::string>, 71> errorLogs;
public:
    template<class T> const T& ofName(std::string_view name);   // 對應 Loadable.ofName
    template<class T> bool      hasOfName(std::string_view name);
    template<class T> std::vector<const T*> all();              // 排序後複本
};
```
- `ofName` 找不到丟自訂 `NotFoundException`（對應 `Loadable.java:503`）。
- `all()` 依 (sort, name) 排序，可快取（對應 `alls`）。
- 由於型別在編譯期已知，模板特化 + `LoadableTypeId` 對應即可，不需 `std::type_index`（但若想動態，也可用 `type_index` 當 key）。

### 6.3 每型別 from_json 函式表（取代反射建構子）
每型別寫一個自由函式 `Type from_json(const json& o, LoadContext& ctx)`，內部就是把 Java 建構子逐行翻成 `o.value("key", default)`（nlohmann 的 `value()` 正好對應 `optX`）。封裝一組 helper 對齊 Java 慣例：
- `imgFromJson(o)` = `{src,x,y,w,h,flipped?}`（像素），與 `tileImgFromJson`（`x*16` 格座標）兩個版本。
- `colorFromJson(o)` = `{r,g,b}` 0-255。
- `BonusableValue<T>`：照 §3.3 復刻 NoBonus / IntArithmetic / SetBonus / SingleBonus / ObjectVariant 五種形態。建議做成 `std::variant` 或多型 class，`get(const BonusSet&)`。
- `BonusSet` 用 `std::bitset<N>`（N=Bonus 數量），`Bonus.ordinal()` = 載入排序索引（要在 Bonus 載完後固定）。

### 6.4 載入流程（確定性）
照抄 §2：
1. 依 `LOADABLES` 順序逐型別；DLC 型別檢查 expansion 啟用旗標。
2. 每型別：loadBase → 各 expansion → 各 mod，目錄項 `std::filesystem::directory_iterator` 收集後**自行排序**（`std::sort`，字典序，務必明確排序——`directory_iterator` 不保證順序，這會破壞確定性與 checksum）。
3. 每檔是 JSON array；逐項處理 `remove` / `patch` / `deriveFrom`；建構失敗收集到 failures（base 可被後層修復、mod 失敗即致命）。
4. 同名覆寫：後層 `insert_or_assign`。
5. 全型別載完後跑 postLoad（第二趟綁參照）。
- 建議把致命/可修復錯誤分流（對應 `errorLogs` vs `failures`）。

### 6.5 JSON 函式庫選擇
- **首選 nlohmann/json**：`o.value("key", default)` 直接對應 `optX`、`o.at("key")` 對應 `getX`（缺值丟例外，正好對齊 Java 行為）、`o.is_array()`/`o.is_object()` 對應 `instanceof JSONObject/JSONArray` 的多型判斷（BonusableValue 大量用到）。可讀性最高，最適合「逐行翻譯建構子」。
- simdjson 速度快但是只讀、惰性、API 不適合這種「到處 optX + 多型分支」的手寫解析；除非啟動時間是瓶頸，否則不建議用在這層。
- 折衷：用 nlohmann 做解析正確性，若量測到啟動慢再對最大檔（ModuleType/ArmourType）局部優化。

### 6.6 校驗碼策略
- base/expansion checksum：復刻 §5.1——遞迴目錄、對檔案 CRC32、**相加**（順序無關）、空則=1。C++ 用 zlib `crc32()` 即可。型別目錄掃描順序須與 `LOADABLES` enum 一致。
- 若要與 Java 原版多人/存檔相容，CRC32 與相加邏輯、跳過 `.` 開頭、加 `lang`/`strings` 目錄這些細節都要完全一致。若是全新生態（不需與原版連線），可換更強的雜湊（如 xxHash）但要自洽。
- mod SSB checksum（`Mod.getSSBChecksum2`）只在你要支援跨平台傳 mod 才需要，初期可省略。

### 6.7 兩個易踩雷點
1. **座標單位雙軌**：同一個型別內，有些貼圖是像素座標、有些是 16px 格座標（§3.1）。務必為每個欄位確認來源 Java 行。
2. **載入順序即依賴順序**：`LOADABLES` 陣列順序不是隨意的，後面型別的 `fromJson` 會 `ofName` 前面型別（CrewType→AnimationAppearance、Tech→Bonus、ArmourType→Bonus/VariantType）。重排會直接炸。

---

## 附錄：關鍵原始碼座標速查
- 型別陣列：`Loadable.java:111`
- 主查找表 / 快取 / 錯誤 / baseEntries：`Loadable.java:112-115`
- `compareTo`：`Loadable.java:131-136`；`ofName`：`138-146`；`all`：`152-171`
- `load()`：`Loadable.java:181-329`（DLC 守門 `195`、loadBase `199`、expansions `206-230`、mods `231-272`、postLoad `289-313`）
- `loadBase`：`339-350`；`loadDir`：`352-375`；`loadFile`：`377-436`（remove `393`、patch/deriveFrom `397-413`、prevEntries 回填 `423`）
- `img` helper：`438-440`；`getDataChecksum`：`442-466`
- BonusableValue 數值 schema：`BonusableValue.java:335-403`（intArithmetic/cases/single）
- Mod：`info.json` 解析 `Mod.java:239-297`；目錄發現 `305-380`；checksum `586-722`；衍生資料 `757-805`
- Expansion：`getDataDir` `Expansion.java:78-80`；checksum `30-54`；afterLoad `137-149`
- ModuleType flip/variant：建構子 `446-458`；`checkForRefProblems` `1003-1015`；`postLoad` `1017-1042`
- 多人/防竄改 checksum：`LoadingScreen.java:127-173`；`AirshipGame.java:150-151,351`
- 增量擴充慣例：`data/Modding Notes.txt`（addToHeraldicStyles 等）
