# SimplePortal 擴充接點（extension_points）

> 二分：**A 純資料（XML）能做的** vs **B 一定要碰 C# 的**。每項附具體接點、行號依據、風險。

## 結論速覽（做傳送門變體最省力路徑）

- **只想要新外觀 / 新成本 / 新研究 / 新運作參數（吃不吃電、能不能拆、可搬次數、溫度同步、可連結對象白名單）的傳送門變體 → 純 XML，最省力。** 新增一個 `ParentName="SimplePortal_PortalBase"` 的 `ThingDef`，調整 `graphicData / costList / comps / CompProperties_SimplePortal` 欄位即可，零編譯。現有 4 種變體就是這樣做出來的（`ThingDef_Building.xml`）。
- **想改傳送「行為」本身**（傳送條件、傳送什麼、傳到哪、傳送特效/代價、單向、群體規則）→ **必須 C#**：核心邏輯硬編在 `SimplePortal_Building` / `CompSimplePortal` / `JobDriver_EnterSimplePortal`，無資料化開關。

---

## A. 純資料（XML）能做什麼

### A1. 新傳送門變體（最常見需求）
新增 `ThingDef ParentName="SimplePortal_PortalBase"`（繼承自帶抽象父，`ThingDef_Building.xml:8`），即自動獲得 `SimplePortal_Building` thingClass、連結 Verb、`ITab_ContentsMapPortal`。可自由改：

| 想改 | XML 接點 | 依據 |
|---|---|---|
| 外觀/尺寸/著色 | `graphicData` / `activeGraphicData` / `openGraphicData` | `Portal`/`Obelisk` def；`CompProperties_SimplePortal.cs:21-22` |
| 建造成本/材料 | `costList` `statBases` `researchPrerequisites` | `ThingDef_Building.xml:107,247` |
| 可否通行 | `passability`（Standable / Impassable） | `:92,237,426` |
| 是否吃電 | `needEnergy`（CompProperties）+ 是否掛 `CompProperties_Battery` | `CompProperties_SimplePortal.cs:25`；`SimplePortal_Building.cs:223` |
| 燃料 | `CompProperties_Refuelable`（換 `fuelFilter`/容量/速率） | `ThingDef_Building.xml:220-233` |
| 溫度同步 | `syncTemperature`（true/false） | `CompProperties_SimplePortal.cs:24`；`CompSimplePortal.cs:378` |
| 可搬移次數 | `replaceCount`（-1 無限 / N 次） | `CompProperties_SimplePortal.cs:23`；`SimplePortal_Building.cs:302-304,357-398` |
| 可否拆除 | `canUninstall` | `CompProperties_SimplePortal.cs:27`；`SimplePortal_Building.cs:306,318` |
| 可否手動連結 | `canManualLink` | `CompProperties_SimplePortal.cs:28`；`CompSimplePortal.cs:436` |
| **限制可連結對象** | `allowConnnectThing`（型別全名字串清單，如只能連同型） | `CompProperties_SimplePortal.cs:26`；`CommandLinkThePortals.cs:33-39` |
| 開關 / EMP / 發光 / 冥想焦點 / 特效 | 加掛對應原版 Comp（Flickable/Stunnable/Glower/MeditationFocus/Effecter） | 見 `Obelisk` def `:379-424` |

### A2. 給其他 mod 的 Thing 加上「傳送門能力」
仿 `Patch_Vehicles.xml`：用 `PatchOperationFindMod` + `PatchOperationAdd` 把 `<li Class="SimplePortalLib.CompProperties_SimplePortal">` 塞進別人的 ThingDef/VehicleDef 的 `<comps>`（`Patch_Vehicles.xml:21-28`）。注意：對「非 `SimplePortal_Building` thingClass」的物件，只獲得 Comp 提供的連結/進入 Gizmo（`CompGetGizmosExtra`），不會有建築層的能量/燃料橋接（那些在 `SimplePortal_Building` override 裡）。

### A3. 研究/圖鑑接合
新研究項 → `ResearchProjects_Anomaly.xml`；塞進 DLC 圖鑑解鎖 → 仿 `Patch_EntityCodexEntryDef.xml`。

### A4. 在地化文字
所有 `XXX.Translate()` key（如 `SimplePortalGate.Linked`、`EnterPortal`、`SimplePortalGate.Reason.*`）可在 `Languages/<語言>/Keyed/` 補。源碼用 `LanguageDatabase.activeLanguage.HaveTextForKey` 做可選 key（`CompSimplePortal.cs:505,512`），新增 key 即生效。

### A 的風險
- `allowConnnectThing` 比對的是 **`thing.GetType().FullName`**（`CommandLinkThePortals.cs:33-34`），填的是 C# 型別全名（如 `SimplePortalLib.SimplePortal_Building`），不是 defName——容易填錯。
- 移除 `CompProperties_Battery` 但忘了把 `needEnergy` 設 false，會導致 `IsEnterable` 永遠擋（`SimplePortal_Building.cs:223`）。
- PitGate 系變體吃 Anomaly DLC（`MayRequire`），無 DLC 不載入。

---

## B. 改碼（C#）能做什麼

### B1. 改變「傳送目的地」邏輯（單向門、隨機門、世界地圖門）
目的地完全由這兩個 override 決定：
- `SimplePortal_Building.GetOtherMap()`（`SimplePortal_Building.cs:187-192`）
- `SimplePortal_Building.GetDestinationLocation()`（`:194-199`）
以及 JobDriver 內 `otherMap = portal.linkedPortal.MapHeld`（`JobDriver_EnterSimplePortal.cs:75`）。要做「傳到世界地圖物件 / 隨機地點 / 單向不需對端」必須改這幾處或繼承後 override。風險：`IsEnterable` 仍要求 `linkedPortal != null`（`CompSimplePortal.cs:145`），單向門需一併放寬。

### B2. 改變「傳送什麼 / 傳送代價」
傳送本體 `JobDriver_EnterSimplePortal.cs:71-116`（`toil2.initAction`）。想加：傳送傷害/疲勞、保留庫存、阻止特定 pawn、傳送特效音效——都在此插。`Wait(90)` 的進入延遲也硬編在 `EnterDelay=90`（`:20,49`）。
> 風險：這是 instance 方法、非 virtual hook，沒有資料化開關；要嘛改原檔、要嘛 Harmony patch `MakeNewToils`（迭代器，patch 難度高），要嘛自做一個新 JobDef+JobDriver 並改 Gizmo 指向它。

### B3. 新 Comp 行為（推薦的乾淨擴充法）
新增自己的 `ThingComp` 掛在傳送門 ThingDef 上，靠 `CompTick`/`CompGetGizmosExtra` 加行為，不動原碼。可讀 `parent.TryGetComp<CompSimplePortal>()` 取得連結狀態。風險最低，但無法改傳送核心流程（只能旁掛）。

### B4. 改連結規則
`CommandLinkThePortals.ProcessInput`（`CommandLinkThePortals.cs:17-47`）。想做「連結需資源/距離限制/多對一」需改此處的雙向賦值與過濾。注意 `linkedPortal` 是單一引用（1:1），多對多需重構資料結構＋`PostExposeData`（`CompSimplePortal.cs:670`）。

### B5. 群體載入/排程行為
`EnterSimplePortalUtility.MakeLordsAsAppropriate`（`EnterSimplePortalUtility.cs:327`）、`FireSchedule`（`CompSimplePortal.cs:350-376`）。改自動發送條件/時間粒度（目前以小時 `GetDate`/`HoursOfDay=24` 為單位，`CompSimplePortal.cs:342,655`）需碰這裡。

### B6. 載具特判
目前以反射字串 `pawn.GetType().FullName == "Vehicles.VehiclePawn"`（`EnterSimplePortalUtility.cs:54`）判定載具並改用 `Moving` capacity。要支援其他載具型別/其他 framework 需擴充此判斷。

### B 的共通風險
- 核心類別多為 `sealed`-like 直接 new（如 Gizmo action 用 lambda 直呼），沒有預留 virtual 擴充點 → 多半得 fork 原碼或 Harmony。
- `MakeNewToils` 是 `IEnumerator`，Harmony Transpiler/Postfix 對迭代器處理繁瑣。
- 跨地圖引用＋地圖回收的既有保護（`Patch_BlockingMapRemoval`）若新增「傳到世界物件」類型，需自行確保不被 GC。

---

## 推薦擴充策略（給 create 模式）

| 需求 | 路徑 | 工作量 |
|---|---|---|
| 換皮/換參數變體 | A1 純 XML 新 ThingDef | 最小 |
| 給載具/別人 mod 物件加傳送能力 | A2 PatchOperationAdd | 小 |
| 旁掛新效果（不改傳送核心） | B3 新 ThingComp | 小～中 |
| 改傳送目的地/條件/代價 | B1/B2 改 `SimplePortal_Building` override 或新 JobDriver | 中～大 |
| 多對多 / 單向 / 動態連結 | B4 重構 `linkedPortal` 資料模型 + 存檔 | 大 |
