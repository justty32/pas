# 擴充接點與邊界（extension_points）

> 核心問題：**純資料（XML）能做到「自製一套全新派系聚落外觀」嗎？哪些一定要 KCSG 引擎（C#）支援？**
> 結論先講：**外觀／佈局／物資／掛接 100% 純資料可成**（VBGE 本身就是活生生的證明——它沒有任何 .cs）。**只有「新的生成行為原語」才需要動 KCSG 引擎 C#**，而那些原語 VFE Core 已內建一大票，多數情況不必碰。

---

## 一、純資料能做的（不寫任何 C#）

| 想做的事 | 怎麼做（純 XML） | 對應 def / 接點 |
|---|---|---|
| 畫一棟新建築/房間 | 新增一個 `KCSG.StructureLayoutDef`，填 `terrainGrid`/`layouts`/`roofGrid`，掛一個 `tags` | 見 `01_kcsg_data_model.md` 第 2 層 |
| 讓多棟同類建築隨機變化 | 多個 StructureLayoutDef 共用同一個 `tags` 值，引擎自動抽選 | 如 `VGBE_PiratesDefence1~5` 共享 tag `VGBE_PiratesDefence` |
| 定義一座新聚落的版面 | 新增 `KCSG.SettlementLayoutDef`，填 `settlementSize` + `centerBuildings/peripheralBuildings.allowedStructures`（tag+count） | `Pirates.xml:3`、`Tribals.xml:3` |
| 控制倉庫掉落物 / 守軍強度 | `stockpileOptions.fillWithDefs`、`defenseOptions.pawnGroupMultiplier` | `Pirates.xml:46-69` |
| 生屍體 / 奴隸 / 帶旗標的單位 | 用既有 `KCSG.SymbolDef` 欄位（`pawnKindDef`/`spawnDead`/`isSlave`/`numberToSpawn`…）並在 grid 引用其 defName | `GenericKitchen.xml:405`、`GenericPrison.xml:3` |
| 把整套藍圖掛到某派系 | `Patches/Settlements.xml` 用 `PatchOperationAddModExtension` 把 `KCSG.CustomGenOption` 注入該 `FactionDef`，`chooseFromSettlements` 列出你的 SettlementLayoutDef | 見下節「掛接層」 |
| 條件式相容其他 mod 的家具 | grid token 或 props 用 `MayRequire="packageId"` 屬性 | `Tribals.xml:62-68`（`MayRequire="VanillaExpanded.VFEPropsandDecor"`） |
| 全新派系的聚落 | 同上：對你自訂的 `FactionDef` 掛 `CustomGenOption` 即可，無需 C# | — |

→ **「自製一套全新派系聚落外觀」是純資料任務。** 你需要的只是：(a) 一批 StructureLayoutDef（畫圖）、(b) 一個 SettlementLayoutDef（版面）、(c) 一條 Patch（掛到 FactionDef）。

### 掛接層細節（`1.6/Patches/Settlements.xml`）
VBGE 用兩種 PatchOperation 把生成藍圖綁到派系：

- **無條件注入**（`:25-39` 對 TribeBase、`:41-56` 對 OutlanderFactionBase、`:58-77` 對 PirateBandBase）：
  ```xml
  <Operation Class="PatchOperationAddModExtension">
    <xpath>/Defs/FactionDef[@Name="PirateBandBase"]</xpath>
    <value>
      <li Class="KCSG.CustomGenOption">
        <chooseFromSettlements>          <!-- 引擎隨機選其一當這次的聚落版面 -->
          <li>VBGE_PirateSlavery</li>
          <li>VBGE_PiratesDefence</li>
        </chooseFromSettlements>
        <preventBridgeable>true</preventBridgeable>
        <symbolResolvers><li>kcsg_randomfilth</li></symbolResolvers>   <!-- 引擎內建的 symbol resolver -->
        <filthTypes><li>Filth_Dirt</li>...</filthTypes>
      </li>
    </value>
  </Operation>
  ```
- **條件注入**（`:3-23`）：`PatchOperationFindMod` 包住 `PatchOperationAddModExtension`，僅當 `Royalty` DLC 存在時才把 5 種帝國聚落掛到 `Empire` FactionDef（因 Empire 是 Royalty 內容）。

要點：
- 掛接靠的是 RimWorld 原生 `PatchOperation`（純資料機制），**不是** KCSG 專屬。
- `KCSG.CustomGenOption` 是 VFE Core 定義的 `DefModExtension`；VBGE 只是「填值」。`symbolResolvers`（如 `kcsg_randomfilth`）、`preventBridgeable`、`filthTypes` 等都是 **CustomGenOption 暴露給資料的旋鈕**。

---

## 二、需要 KCSG 引擎（C#）支援、純資料碰不到的邊界

| 邊界 | 為什麼純資料不行 | 歸屬 |
|---|---|---|
| 新的 grid token 行為原語 | 例如想要「這格放一個會隨季節變色的特殊物件」「生成時依玩家財富動態增減建物」——SymbolDef 只認引擎反序列化得出的既有欄位（`pawnKindDef`/`thing`/`isSlave`/`spawnDead`…），新增欄位必須改 KCSG 的 C# 類別 | KCSG.SymbolDef（VFE Core）|
| 新的 symbol resolver | `symbolResolvers` 只能填引擎已註冊的 resolver 名（坐實：VFE Core `Defs/CustomStructureGeneration/RulesDefs/Rules_Complex_CSG.xml` 共 18 個 RuleDef，全清單見 `kcsg_engine_takeover.md` §五）。要新增一種程序化填充邏輯，得在 C# 寫並註冊 | KCSG resolver registry（已坐實）|
| 版面/擺放演算法 | 「結構不重疊、道路怎麼連、props 怎麼散」由 KCSG C# 決定；資料只能調暴露出來的參數（`spaceAround`/`scatterMinDistance`…），改演算法本身要動引擎 | KCSG `SettlementGenUtils`（已反編譯：Poisson 取樣選點 `KCSG.decompiled.cs:7269` + 權重抽 tag `:7425` + 中心地標 `:7620`）|
| 生成觸發時機 | 「世界聚落何時被實體化成地圖、entry 時才鋪 / 預生成」由 RimWorld + VFE Core 控制，非 VBGE 資料能改 | 引擎層（見 §三）|
| CustomGenOption 的可填欄位 | 只能填 VFE Core 在該 `DefModExtension` 上定義的欄位；想要新旋鈕得改 VFE Core C# | KCSG.CustomGenOption（VFE Core）|

---

## 三、生成觸發（2026-06-12 反編譯坐實，機制詳見 `kcsg_engine_takeover.md`）

層級理解（資料層可確認的部分 + 引擎推論）：
1. **世界生成**：原版在世界地圖上替各派系放聚落（World Object）。此時聚落只是地圖上一個點，**還沒有實際的 tile 地圖**。
2. **掛接已就緒**：因 `Patches/Settlements.xml` 已把 `CustomGenOption` 注入該派系的 `FactionDef`，引擎在需要生成此派系任一聚落地圖時，知道要去 `chooseFromSettlements` 抽一個 `SettlementLayoutDef`。
3. **地圖實體化（鋪設藍圖）**：當玩家帶商隊**攻打/進入**該聚落（World Object 被 enter → `GetOrGenerateMap`）時，KCSG 以 Harmony Postfix 偷換 `Settlement.MapGeneratorDef` getter 回傳自家 `KCSG_Base_Faction`（內含 `KCSG.GenStep_Settlement`，order 599），其 `ScatterAt` 呼叫 `CustomGenOption.Generate`：抽 SettlementLayoutDef → push `kcsg_settlement` 回原版 BaseGen → 鋪建築/道路/電力/守軍。**「進地圖才鋪」坐實＝原版 lazy `GetOrGenerateMap` ＋ getter 偷換，引擎不預生成。**

> 對 create 的意義：你的藍圖**何時被用**完全由引擎決定，你不需要也無法用資料改觸發時機；你只要保證「資料正確掛在對的 FactionDef 上」，引擎就會在玩家進該派系聚落時用到。

---

## 四、給 create 的接點清單（最短路徑）
1. 新 `KCSG.StructureLayoutDef`（畫圖，掛 tag）×N。
2. 新 `KCSG.SettlementLayoutDef`（版面，allowedStructures 引用上面的 tag）。
3. （需要時）新 `KCSG.SymbolDef`（只在要 spawnDead/isSlave 之類旗標時）。
4. 一條 `Patches/...xml` 的 `PatchOperationAddModExtension`，把 `KCSG.CustomGenOption{chooseFromSettlements:[你的 SettlementLayoutDef]}` 注入目標 `FactionDef`。
5. `About.xml` 宣告硬相依 `OskarPotocki.VanillaFactionsExpanded.Core` 且 `loadAfter` 它。

全程零 C#。教學見 `../tutorial/01_add_settlement_layout.md`。
