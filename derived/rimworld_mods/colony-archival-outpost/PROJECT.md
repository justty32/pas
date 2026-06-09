# 殖民地封存哨站（Colony Archival Outpost）

## 衍生目標
大戰略軌（`analysis/rimworld_mods/_mod_ideas/world_map_grand_strategy/`）拆出的**第一個子 mod**。把報告 `06_colony_archival_to_outpost.md` 的「採樣 → 封存 → 抽象產出」落地成可玩的 RimWorld 1.6 mod。

玩家在一座成熟殖民地點「開始採樣」，經營一段時間後點「封存」：地圖被銷毀、地圖上所有 pawn 轉為抽象 outpost 占用者、儲存物資隨之帶走，世界地圖留一個圖標據點，按採樣到的**淨庫存增長率**持續送資源回最近的主基地。

## 範圍（v1）
- 路線 **A 純抽象**：封存後 outpost 不可再訪問（不做混合、不做同圖還原）。
- 採樣法＝**儲存區 delta**（`ResourceCounter` 期初/期末快照相減）。
- 產出引擎＝**子類化借 VOE**（`Outpost_Sampled : Outpost`，override `ResultOptions`）。
- 採樣窗口＝**玩家手動開始/結算**。

### v1 砍掉（YAGNI）
製作/`RecordsTracker` 採樣、重新採樣/解封、帶物資的選擇 UI、技能成長/產能衰減、可再訪問/混合路線。

## 技術棧
- C#（net48）＋少量 XML Def；Harmony（注入 Settlement gizmo）。
- **硬相依**：Vanilla Outposts Expanded（VOE）＋ Vanilla Expanded Framework（VEF）＋ Harmony；`loadAfter` VOE。
- defName 前綴 `pas.archival.*`。

## 對應 RimWorld 版本
1.6（反編譯權威源 `projects/rimworld/`；VOE 引擎 `projects/rimworld_mods/vanilla-outposts-expanded/decompiled-framework/Outposts.decompiled.cs`）。

## 完成定義（v1）
- [ ] 採樣：玩家 Settlement gizmo「開始採樣」記錄期初庫存快照＋tick。
- [ ] 封存：gizmo「封存成哨站」算淨日均率→建 `Outpost_Sampled`→搬所有 pawn＋儲存物資→銷毀地圖。
- [ ] 產出：VOE 子類動態 `ResultOptions` 按 snapshot 持續投遞回主基地。
- [ ] 唯一基地防呆：最後一張家園地圖不可封存。
- [ ] 存讀檔：snapshot＋outpost 往返不壞。
- [ ] 靜態健檢全綠 + 實機端到端驗證（採樣→封存→投遞→存讀檔）。

## 關鍵文件
- `docs/2026-06-09-design.md`：v1 設計 spec（權威）。
- `docs/2026-06-09-implementation-plan.md`：實作計畫（待 writing-plans 產出）。

## 來源報告
- `analysis/rimworld_mods/_mod_ideas/world_map_grand_strategy/06_colony_archival_to_outpost.md`（可行性與源碼坐實）
