# 哨站封存：技術選型 (Outpost Archiving Strategy)

> 對照基準：`projects/rimworld/`（1.6 / Odyssey）。
> 目的：整個「帝國藍圖」（軍事 / 事件重定向 / 地緣 / 物流…）都建立在「把分基地封存、不吃 CPU」這個地基上，但 RimWorld **沒有官方的地圖快照/還原 API**。本文先把引擎真實的地圖生命週期攤開，再給三條路線的取捨與**推薦做法**。

---

## 1. 問題本質

「封存哨站＝拆掉地圖、只留數值，要用時再展開」——聽起來像「暫停一張地圖」。但引擎沒有「凍結地圖」這個概念，只有「**有地圖**」或「**沒地圖（只剩 WorldObject 數值）**」兩態。所以真正要決定的是：**封存後那張地圖的狀態怎麼處理？**

---

## 2. 引擎事實（決定可行性的硬約束）

| 事實 | 出處 | 對設計的意義 |
| :--- | :--- | :--- |
| **每張在 `Game.Maps` 的地圖都會被 tick** | `Verse/TickManager.cs:362 MapPreTick` / `:450 MapPostTick` | 「留著地圖」就一定吃 CPU，沒有「在清單裡但不 tick」的官方開關。 |
| **地圖數量上限 128** | `Verse/Game.cs:360`（`maps.Count > 127` 即報錯） | 「每個哨站留一張地圖」最多 ~127 個，且每個都吃 tick；數百人帝國會撞牆。 |
| **存檔時整個 `maps` 深度序列化** | `Verse/Game.cs:403, :589`（`Scribe_Collections.Look(ref maps, "maps", LookMode.Deep)`） | 在 `Game.Maps` 裡的地圖會自動存檔（也讓存檔變大）；**移出清單的地圖不會被存**，要自己 Scribe。 |
| **移除地圖＝`MapDeiniter.Deinit` 徹底拆除** | `Verse/Game.cs:723`→`Verse/MapDeiniter.cs Deinit` | 拆除是不可逆的，沒有還原。 |
| **拆除時小人會 `PassPawnsToWorld`（保留為 WorldPawn）** | `Verse/MapDeiniter.cs`（`PassPawnsToWorld` 段）；另 EndAllSustainers / `areaManager`·`lordManager`·`deferredSpawner`.Notify_MapRemoved | **人保得住**（變成世界小人），但建築/物品/地形/區域/Lord 狀態全失。 |
| **既有「離開後自動釋放地圖」機制** | `RimWorld.Planet/MapParent.cs:104 ShouldRemoveMapNow`（base 回 false）、`:317` 觸發 `DeinitAndRemoveMap`；`RimWorld.Planet/Settlement.cs:212` 覆寫（非主基地、無阻擋建築/小人/運輸艙時釋放） | 「離開聚落→稍後釋放地圖」是**原版就在做的事**，重進時是**重新生成**，不是還原。 |
| **PocketMap：官方的「臨時地圖」生成/銷毀** | `Verse/PocketMapUtility.cs:11 GeneratePocketMap` / `:21 DestroyPocketMap`；`Verse/GetOrGenerateMapUtility.cs:26`；**先例**：Anomaly 迷宮 `RimWorld/CompObelisk_Abductor.cs:227`（生成）/`:247`（銷毀） | 「需要時臨時開一張、用完銷毀」有現成、乾淨、被官方內容驗證過的 API。 |

**一句話**：引擎的設計傾向是「離開就拆、要用再重生成」，**人保留、場景丟棄**。

---

## 3. 三條路線

### 路線 A — 保留 Map 物件（不 tick）
- **想法**：封存時別銷毀地圖，只是「暫停」它。
- **現實**：沒有官方「暫停」。要嘛留在 `Game.Maps`（照樣 tick、照樣佔 128 名額之一、毫無效能收益），要嘛移出清單——但移出後**不會被存檔**（§2 序列化），得自己維護引用＋自寫 `Scribe_Deep` 持久化，還要想辦法不被 tick 迴圈掃到。等於跟引擎作對。
- **效能**：留在清單＝零收益；移出清單＝省 CPU 但**仍佔滿記憶體**（整張地圖物件不釋放）。
- **判定**：❌ **不推薦**。脆弱、吃記憶體、與其他 Mod 高度衝突，且違反「支援數百人帝國」的初衷。

### 路線 B — 銷毀 ＋ 自序列化（快照還原原貌）
- **想法**：拆地圖前，把整張地圖狀態自己序列化成一塊資料，解封時還原成**一模一樣**的地圖。
- **現實**：地圖深度序列化的能力引擎本來就有（`LookMode.Deep`），但它**綁在 `Game.Maps` 的 ExposeData 流程**裡；要「存到旁邊一塊 blob、之後還原」等於自己重寫一套地圖序列化容器，並處理 `MapParent`、所有 `Thing`、`ThingComp`、Lord、區域、電網、溫度等的 cross-reference。
- **效能/風險**：存檔暴肥；跨版本/跨 Mod 極脆（任何 Def 變動都可能讓還原炸掉）；維護成本最高。
- **判定**：⚠️ **保真度最高，但通常不值得**。除非「必須還原原貌」是核心賣點（本藍圖並非如此）。

### 路線 C — 銷毀 ＋ 重生成新圖（抽象化）★推薦
- **想法**：封存＝跑採樣→把結果濃縮成數值（產能/防禦/醫療/外交…）存到哨站的 `WorldObjectComp`→`DeinitAndRemoveMap` 拆地圖（人自動進世界小人池）。日常用數值結算。需要進戰場/親自處理時，**重新生成一張新圖**，用存下的數值決定敵我配置與內容。
- **為何最順**：這正是引擎已支援、且被官方內容跑過的路徑——
  - 拆除：`MapDeiniter.Deinit`（人保留，§2）。
  - 重生成：`MapGenerator.GenerateMap` 或 `PocketMapUtility.GeneratePocketMap`（Anomaly 迷宮即此，`CompObelisk_Abductor.cs:227/247`）。
  - 釋放時機：照搬 `Settlement.ShouldRemoveMapNow`（`Settlement.cs:212`）的判定，避免在有運輸艙/阻擋時誤拆。
- **代價**：戰場是**重生成的新圖、非原貌**。但對「哨站＝數值化的邊境據點」來說這完全可接受，也是業界 **Outposts** Mod 的作法。
- **判定**：✅ **推薦預設**。風險最低、引擎友善、對 Mod 相容性好、能真正支撐數百人規模。

---

## 4. 推薦架構（路線 C 的落法）

```
[採樣期] 玩家正常經營分基地 N 天
   └─ 結束時：掃描產出/防禦/技能…濃縮成數值
              （產能用「理論產出/工作量」較準，見 productivity_profiling_logic.md §1B；
                注意 ResourceCounter 只算儲存區，見 simplified_outpost_logic.md 修正）

[封存] 把數值寫進 OutpostComp(WorldObjectComp)；
        Current.Game.DeinitAndRemoveMap(map)  // 人自動 PassPawnsToWorld，記下哪些 WorldPawn 屬本哨站

[日常] OutpostComp.CompTick / 每季結算：產出、外交、技能成長…全部數值運算，零地圖、零 tick 成本

[臨時展開] 玩家要親自打防禦戰 / 手動招募訪客時：
        PocketMapUtility.GeneratePocketMap(...) 開一張臨時圖（用存下的防禦數值佈置敵我）
        → 戰後 PocketMapUtility.DestroyPocketMap(...) 收掉，更新數值
```

要點：
- **狀態載體**：自訂 `WorldObjectComp`（或自訂 `WorldObject` 子類）持有快照數值，走標準 `IExposable` 存檔，無 §2 的自序列化難題。
- **人員**：靠 `PassPawnsToWorld` 自動保留為 WorldPawn，哨站只需記 `List<Pawn>` 引用（`LookMode.Reference`）。
- **臨時圖優先用 PocketMap**：它有官方銷毀流程、不污染大地圖、有 Anomaly 先例。

---

## 5. 對下游文件的連帶影響

- `military_outpost_extension.md` §2B「手動防禦」→ 採路線 C：用 PocketMap 開**新**戰場（已於該檔修正）。
- `event_routing_extension.md` §4.2「臨時展開」→ 同樣用 PocketMap 開臨時轉運站圖。
- 任何提到「重新封存 / 解封重採樣」→ 在路線 C 下等於「重生成一張圖、重跑一次採樣」，語義一致、無矛盾。

---

## 6. 結論

| 路線 | 保真度 | 效能 | 風險/維護 | 判定 |
| :--- | :--- | :--- | :--- | :--- |
| A 保留 Map | 高 | 差（仍 tick 或仍佔記憶體） | 高（跟引擎作對） | ❌ |
| B 自序列化還原 | 最高 | 中（存檔暴肥） | 最高（跨版本脆） | ⚠️ 非必要不採 |
| **C 重生成新圖（抽象化）** | 中（場景非原貌） | **最佳（純數值）** | **最低（引擎原生路徑）** | ✅ **推薦** |

**先採路線 C 把地基釘死**，軍事/事件/地緣那幾份的細節才談得上落實。若日後真有「必須還原原貌」的單一場景，再對該場景局部引入路線 B，不要全盤自序列化。

---
*文件路徑: analysis/rimworld/architecture/outpost_archiving_strategy.md*
*撰寫日期: 2026-05-23 — 對照 projects/rimworld (1.6/Odyssey)*
