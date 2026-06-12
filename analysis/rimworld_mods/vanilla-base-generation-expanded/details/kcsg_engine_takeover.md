# KCSG 引擎接管機制（原「待驗證」項，2026-06-12 反編譯坐實）

> 反編譯來源：VFE Core（workshop 2023507013）`1.6/Assemblies/KCSG.dll`（1.6 起 KCSG 已從 VFECore.dll 拆出獨檔），9464 行 →
> `projects/rimworld_mods/vanilla-base-generation-expanded/decompiled-framework/KCSG.decompiled.cs`。
> 引擎 XML（MapGeneratorDef/RuleDef）在 VFE Core mod 目錄 `1.6/Defs/CustomStructureGeneration/`。
> 本檔回答先前標「待驗證」的四個問題；行號皆指 `KCSG.decompiled.cs`。

## 一、接管機制＝「Harmony Postfix 偷換 MapGeneratorDef」（三選一答案揭曉）

先前猜想三條路：patch `SymbolResolver_Settlement`／自有 GenStep 插隊／換 MapGeneratorDef。**答案是第三條**，且完全站在原版 BaseGen 符號系統之上：

1. **`Postfix_Settlement_MapGeneratorDef`（:420-448）**：Postfix `Settlement.MapGeneratorDef` getter。
   - 玩家派系／無派系早退（:428）→ **不影響原版與其他 mod 的聚落**。
   - 聚落派系 `FactionDef` 有 `CustomGenOption` mod extension → `__result = KCSG_Base_Faction`（:435）。
   - 否則掃同 tile 任一 `WorldObject` 的 **def** 帶 `CustomGenOption` → `__result = KCSG_WorldObject`（:439-444）。
2. **`Postfix_MapParent_MapGeneratorDef`（:354-377）**：Postfix `MapParent.MapGeneratorDef` getter，同樣做「同 tile world object def 掃描」→ `KCSG_WorldObject`。
3. 兩個 MapGeneratorDef（`Defs/CustomStructureGeneration/MapGeneration/MapGenerators.xml`）都是
   `ParentName="MapCommonBase"` ＋ `RocksFromGrid` ＋ 自家 GenStep（order 599、nearMapCenter）：
   - `KCSG.GenStep_Settlement : RimWorld.GenStep_Settlement`（:324-338）：`CanScatterAt` 恆 true，`ScatterAt` → 從 **`map.ParentFaction.def`** 取 ext 呼叫 `CustomGenOption.Generate(loc, map)`。
   - `KCSG.GenStep_WorldObject`（:339-353）：同款，但從 **`map.Parent.def`**（WorldObjectDef）取 ext。

## 二、非-Settlement MapParent？——**認**（idea 9 關鍵答案）

`CustomGenOption` 掛在**自訂 WorldObjectDef** 上即可被 `Postfix_MapParent_MapGeneratorDef` 接住，走 `KCSG_WorldObject` 生成——**自寫輕量 `:MapParent`/`:WorldObject` 的 outpost 不必繼承 `Settlement`，零 C# 即可吃 KCSG 佈局**。注意：

- 同 tile 掃描是「找到第一個含 ext 的 world object 就用」（:367-374）——同格疊多個帶 ext 物件時不確定取哪個，設計上應保持一格一物。
- `Prefix_WorldObjectsHolder_Add`（:397-410）：派系 `CustomGenOption.canSpawnSettlements == false` 時直接擋 `WorldObjectsHolder.Add`——可用來做「此派系不自然增生聚落」。

## 三、`CustomGenOption.Generate` 流程（:2569-2622）

```
GenOption.customGenExt = this（靜態全域！）
→ tiledStructures 有值：隨機抽一個 TiledStructureDef.Generate（quest 可縮放）
→ 否則 chooseFromlayouts（單棟）或 chooseFromSettlements（聚落）隨機抽
→ faction = map.ParentFaction（玩家/null 則 RandomEnemyFaction）
→ rect 置中於 loc（tryFindFreeArea 可改找空地，失敗僅 Warning）
→ preGenClear → LayoutUtils.CleanRect 清地（fullClear 連地形）
→ BaseGen.symbolStack.Push(symbolResolver ?? "kcsg_settlement", rp) → BaseGen.Generate()
```

`kcsg_settlement`（`SymbolResolver_Settlement` :6213-6262）再疊 push：
`kcsg_scatterpropsaround`／`kcsg_settlementpower`／`kcsg_generateroad`／（`defenseOptions.addEdgeDefense` 時 `kcsg_edgeDefense`）／`kcsg_runresolvers`（執行 `CustomGenOption.symbolResolvers` 清單），最後 `SettlementGenUtils.Generate` 鋪建築。

## 四、pawn 生成＝隨機 PawnGroupMaker，**無「綁既有具名 pawn」欄位**（坐實舊結論）

`AddHostilePawnGroup`（:6264 起）：`LordMaker.MakeNewLord(LordJob_DefendBase…)`（不吃飯種族用變體 `LordJob_DefendBaseNoEat`），pawn 按 `PawnGroupKindDefOf.Settlement`＋points 隨機生成。
→ idea 9「家族 NPC 精準對應房舍」仍須**自寫後處理 GenStep**（KCSG 之後跑、讀已生成建築分房），原推薦不變。

## 五、已註冊符號（`symbolResolvers` 只能填這 18 個）

`Defs/CustomStructureGeneration/RulesDefs/Rules_Complex_CSG.xml`（RuleDef → symbol → resolver class）：
`kcsg_settlement`、`kcsg_roomsgenfromstructure`、`kcsg_settlementpower`、`kcsg_generateroad`、`kcsg_runresolvers`、`kcsg_storagezone`、`kcsg_thingsetonlyroofed`、`kcsg_thingroofed`、`kcsg_randomdamage`、`kcsg_randomfilth`、`kcsg_randomterrainremoval`、`kcsg_randomroofremoval`、`kcsg_randomitemremoval`、`kcsg_removeperishable`、`kcsg_destroyrefuelablelightsource`、`kcsg_scatterstuffaround`、`kcsg_edgeDefense`、`kcsg_scatterpropsaround`。
想加新 resolver＝改 VFE Core C#（先前 extension_points.md 的判斷坐實）。

## 六、順手發現（與本群組其他分析的交叉點）

- **`GenStep_CustomStructureGen`（:4035）**：quest/site 用的另一條入口（`GenStepDef` 直接引用、structureLayoutDefs 清單），與聚落路徑共用 `GenOption` 全域——AUR/CQF 型「召喚預製場景」可參照。
- **`GenStep_BiomeStructures`（:222）**：依 BiomeDef 散佈結構＋礦脈，order 400。
- **`SettlementUtility.Attack` postfix（:380-395）**：攻打 CustomGenOption 派系聚落時 `RotAllThing()`（食物腐壞），風味處理。
- **風險備註**：`GenOption.customGenExt`/`structureLayout`/`settlementLayout` 是**靜態全域**（:2584,2593,2597），生成流程非可重入——自寫嵌套/並行生圖（如 idea 9 後處理再觸發生成）須避免重設這些全域。

## 七、對既有文件的修訂

- `architecture/00_overview.md`／`details/extension_points.md` 的「引擎內部待驗證」標記由本檔解除。
- `_mod_ideas/world_map_grand_strategy/04_settlement_map_generation.md` §8.1 前兩項已可定案：
  **B 路線（KCSG）對自訂 WorldObject 可行**，§6.1 的 (i)（掛 ext 即接管）成立、不必繼承 Settlement。
