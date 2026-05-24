# Airships: Conquer the Skies — C++ 重寫路線圖（統整）

> 本檔是面向「用 C++ 從頭重寫本遊戲」的總入口，統整 5 份子系統深掘文件。
> 分析基於 CFR 反編譯原始碼 `projects/airships-cts/src/`（事實來源）+ Steam 安裝資料 `data/`。
> ⚠️ 反編譯碼含偽變數（如 `void var19_33`）與 CFR 還原痕跡，**理解語意、勿照抄字面**。

## 0. 文件索引（建議閱讀順序）

| # | 文件 | 內容 | 重寫優先序 |
|---|------|------|-----------|
| 1 | [`01_overview_and_architecture.md`](01_overview_and_architecture.md) | 技術棧、雙層結構、CatEngine、Screen、Loadable、鎖步總覽 | 先讀 |
| 2 | [`data_loadable_system.md`](data_loadable_system.md) | 71 型別註冊表、JSON 載入、mod 覆寫、校驗碼 | **P0 地基** |
| 3 | [`ship_module_crew_model.md`](../details/ship_module_crew_model.md) | 船艦/模組/船員、火焰物理、升力、加成系統 | **P0 核心模型** |
| 4 | [`combat_simulation.md`](../details/combat_simulation.md) | tick 管線、確定性、鎖步協定、戰鬥實體 | **P1 模擬核心** |
| 5 | [`strategic_and_ai.md`](strategic_and_ai.md) | CampaignWorld/Empire/City、評分式 AI、autoresolve | P2 戰略層 |
| 6 | [`engine_rendering.md`](engine_rendering.md) | 引擎抽象、Screen、繪圖、資產管線、shader | P3 引擎/呈現 |

---

## 1. 最重要的一件事：確定性契約 (Determinism Contract)

**這是整個重寫的成敗關鍵。** 本作是**確定性鎖步多人**——Server 只當訊息中繼（`Server.java:1073`），每個 client 用「相同 seed + 相同指令序列 + 相同浮點」各自跑出逐位元相同的模擬，每 1024 ms 互比 checksum（`Combat.java:271, 2096-2112`）。任何一處不一致就 desync。三個獨立 agent 在 combat / ship / strategic 都各自得出同一結論，茲統一列出 C++ 必守規則：

1. **復刻 `java.util.Random` 的 48-bit LCG**。模擬用 RNG 是 `GuardedRandom`（包 `java.util.Random`），戰鬥種子來自 server channel.seed（`Combat.java:123, 735`），戰略種子是 `WorldMap.r`。C++ 必須**逐位元重現** Java LCG（`seed = (seed*0x5DEECE66D + 0xB) & ((1<<48)-1)`，含 `nextInt(bound)` 的拒絕取樣、`nextDouble` 的 26+27 bit 組合）。直接用 `<random>` 的 `mt19937` 會全盤 desync。
2. **模擬 RNG 與視覺 RNG 必須分流**。視覺用的是另一條無種子、吃系統時間的 `AGame.ANIM_R`（`AGame.java:118`），驅動粒子/碎片/槍口火光/地形抖動/閃電。**這條絕不可進入模擬狀態**，否則引入不可重現性。重寫時務必兩條 RNG 物理隔離。
3. **浮點：`strictfp` + `StrictMath`（fdlibm）全覆蓋**。所有模擬類別宣告 `strictfp`（`Combat.java:96` 等），超越函數走 `StrictMath.*`。checksum 用 `Double.hashCode()` 比對 IEEE-754 位元（`Combat.java:914-942`）——差最後一個 bit 就會被抓到。C++ 對策：
   - 編譯旗標 `-ffp-contract=off`、禁 `-ffast-math`、禁 FMA 融合、固定 SSE2 浮點模式（x87 80-bit 會出事）。
   - 自行移植 fdlibm（sin/cos/sqrt/pow/atan2…），**不可**用各平台標準庫的超越函數（結果不保證一致）。
   - 或更穩：模擬層全面改用整數定點數（須評估對既有平衡數值的影響）。
4. **容器走訪順序固定**。模擬迴圈一律用有序結構（`ArrayList`/`LinkedList` → C++ `std::vector`）。`physics.bodies` 插入順序硬性為 地形→艦→腳→輪（`Combat.java:1145-1186`）；Shot 互參用 sideIndex/shipIndex/moduleIndex。**禁止**在影響模擬的迴圈用 `std::unordered_map` 迭代（Java `HashMap` 迭代序在此處要嘛沒進模擬、要嘛已先排序）。資料載入的 `directory_iterator` 結果也必須明確 `std::sort`（否則破壞 checksum，見 `data_loadable_system.md`）。
5. **指令時間戳要剝除**。`execCommand` 會移除指令的 `t` 欄位再套用（`Combat.java:451-453`），避免污染 hash；單機指令 `frameNumber=-1`。

> 補充：`GuardedRandom.check()` 在發行版是空 no-op（曾為除錯護欄），別誤以為它在做事——真正的確定性靠上述 1-5。

---

## 2. 建議的 C++ 模組分解

對應原架構，建議切成這些 library（由下而上、依賴單向）：

```
acts-core/        # 純邏輯，零渲染、零 I/O 之外相依，可單獨跑 headless 模擬與測試
├── platform/     # 固定點數或嚴格浮點數學、fdlibm 移植、JavaRandom(LCG 復刻)、雜湊
├── data/         # Loadable 註冊表：LoadableTypeId(71) + 每型別 from_json/postLoad；name→實例查找；CRC32 校驗
├── model/        # ModuleType/Module、Airship、Crewman、BonusableValue/BonusSet、Wheel/Leg/Tentacle
├── sim/          # Combat tick 管線、Physics、Shot/Particle/Fragment、LandFormation
├── strategic/    # CampaignWorld/WorldMap/Empire/City、Mission
└── ai/           # StrategicAI/TacticalAI/DiplomacyAI/CityAI/FleetAI/HeroManagementAI（評分函式）

acts-net/         # 鎖步：frame 佇列、指令序列化、Server(中繼)/Client、checksum 交換、重連
acts-render/      # 引擎後端(SDL2/SFML/bgfx 之一)、Frame/Draw 原語、SpriteSheet/.tex 載入、動畫、shader
acts-app/         # Screen 狀態機、各畫面、輸入分派、音效、Steam 整合(選配)
```

關鍵設計對應：

| Java 機制 | C++ 對應建議 |
|-----------|-------------|
| `Loadable` + `Class[]` 反射載入 | `enum class LoadableTypeId`（順序須同 `Loadable.java:111`）+ 註冊表 struct（dirName/dlcOnly/fromJson/postLoad）；無反射，逐型別寫 `from_json` |
| `BonusableValue<T>`（5 形態）| `std::variant`（NoBonus/Single/Set/ObjectVariant/Arith）+ `std::visit`；求值順序**先全加 delta、再全乘 mult/div、Int 最後 clamp**（`BonusableValue.java:740-752`）；`recalculateBonuses` 後快取每模組數值 |
| `BonusSet` | `std::bitset<N>`（位元＝`Bonus.ordinal()`，依載入排序索引）|
| `EnumMap<Resource,Integer>` | 固定大小 `std::array<int, RES_COUNT>`（序列化時攤平成 `"AMMO":n`，`Module.java:2068`）|
| transient 欄位 | 載檔後重建（maxHP、wheels/legs/tentacles、視覺暫態）——序列化時略過 |
| `org.json` | **nlohmann/json**（`value()`↔optX、`at()`↔getX、`is_array/is_object`↔instanceof，最合手寫多型解析；simdjson 不適合這層）|
| Screen 介面（單一當前、非堆疊）| 一個 `std::unique_ptr<Screen> current;` 直接替換（`AirshipGame.java:116`）；overlay 用「吃掉輸入」而非堆疊 |

---

## 3. 分階段移植計畫 (Milestones)

依「先地基、先可驗證」排序。每階段都要能 headless 跑 + 對拍 checksum。

- **M0 平台層**：JavaRandom LCG 復刻 + fdlibm 移植 + 雜湊。**驗收**：對同一 seed，C++ 產生的 `nextInt/nextDouble/sin/pow…` 序列與 Java 逐位元相同（寫對拍測試）。這是後續一切確定性的基礎。
- **M1 資料層**：71 型別註冊表 + JSON 載入 + CRC32 校驗。**驗收**：載入 `data/` 後算出的 checksum == `data/checksum`（實測 1237186232367）。
- **M2 模型層**：ModuleType/Module/Airship/Crewman/BonusableValue。**驗收**：載入 `default_ships/*.json`，重算 maxHP/升力/重量/指令點與 Java 一致。
- **M3 戰鬥模擬（單機）**：Combat tick 管線、Physics、火焰、傷害、解體、Shot/Particle/Fragment。**驗收**：載入一場錄製戰鬥（`recordEntireCombatState`）重播，每 1024ms checksum 全程吻合。← **整個專案的真正難關**
- **M4 鎖步網路**：frame 佇列、指令序列化、Server 中繼、Client、desync 偵測。**驗收**：兩個 C++ client 對戰全程不 desync；C++ ↔ Java client 互通（若要相容）。
- **M5 戰略層 + AI**：CampaignWorld/Empire/City、評分式 AI、autoresolve。**驗收**：AI vs AI 戰役在固定 seed 下可重現。
- **M6 引擎/呈現**：渲染後端、Screen、繪圖、資產管線、shader、音效。可與 M3-M5 平行開發（不影響模擬確定性）。

> 註：M6 雖最「看得見」，但**邏輯正確性與確定性（M0-M5）才是價值所在**；引擎可換、邏輯不能錯。建議先做 headless 模擬對拍，再貼皮。

---

## 4. 各子系統重點速查（細節見各文件）

- **資料層**：`load()` 依 `LOADABLES` 陣列順序逐型別跑 base→expansions→mods（順序＝依賴序，勿重排）；8 個型別純由 heroes 資料片提供（Edict/HeroType/IncidentType/Medal*…）；mod 增量機制有整條覆寫/`remove`/`deriveFrom`/`patch`。
- **模型層**：火焰四向蔓延機率含門（雙向 AND）與 blast armour 遞減（`Module.java:867-936`）；解體用 4 向 flood fill（物理 chunk 不看門、尋路 chunk 看門，`Airship.java:2330`）；升限 `pow((lift*800/mass-400)*30, 2/3)`（`Airship.java:5494`）；指令點 generated 對數遞減。
- **戰鬥**：固定 16ms tick，NORMAL 速度＝4 sim tick / 1 網路幀；多人用 `localMsAccum` 橡皮筋緩衝；傷害結算分散在三處（物理撞擊 / Side 開火 / Shot 命中）非單一階段。
- **戰略**：固定 16ms tick 即時推進（非回合制），收入/研究/建造皆時間累積式；AI 純評分制（`quality()` 函式），個性是 ~150 參數 JSON 權重表；AI vs AI 走靜默 autoresolve（`WorldMap.java:2266`），任一方含人類才建真實 Combat。
- **引擎**：`Game` 介面只有 input/render；渲染可變步 + VSync 60FPS、模擬固定 16ms（雙軌計時，用累加器橋接）；Screen 單一當前；`.png.tex` 是預烘焙裸 RGBA 跳過 PNG 解碼；核心 shader 是 2D 多方向法線光照（bump RG=朝向/B=shiny + 4 張光緩衝）。

---

## 5. 移植風險登記 (Risk Register)

| 風險 | 來源 | 對策 |
|------|------|------|
| **浮點不一致 → desync** | `strictfp`/StrictMath/Double.hashCode 比對 | M0 先做、fdlibm 移植、嚴格編譯旗標，或改定點數 |
| **RNG 不一致 → desync** | Java LCG、雙 RNG 分流 | M0 對拍測試，視覺/模擬 RNG 物理隔離 |
| **容器迭代序 → desync** | HashMap/directory_iterator 順序 | 模擬迴圈一律有序容器，載入結果明確 sort |
| 無反射難以複刻 Loadable | Java 用 Class 當 key | enum + 註冊表 + 手寫 from_json |
| 反編譯偽變數誤抄 | CFR 還原痕跡 | 理解語意再寫，勿照搬 `varNN_MM` |
| 光源渲染端未解明 | engine 文件待補（4 張光緩衝如何生成）| 列為 M6 待辦，先做採樣端 |
| 與 Java 版多人相容（若需要）| 協定/checksum 須完全一致 | 若不需跨版相容，可放寬，只要 C++↔C++ 一致 |

---

## 6. 後續待辦（尚未深掘）

- [ ] 光源渲染管線：4 張 `lightFrom*` 光緩衝如何生成（`engine_rendering.md` 風險 #2）。
- [ ] 存檔/讀檔完整 schema 與版本遷移（`default_ships/*.json` 已取樣，未窮舉）。
- [ ] 音效系統（CombatSound/MusicAffinity）與 ibxm/Ogg 解碼的 C++ 替代。
- [ ] `tutorial/`：最小可玩里程碑教學（如「載入一艘船並在 headless 跑 100 tick 對拍」）。
