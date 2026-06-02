# Session Resume: RimWorld Analysis — 核對完成，準備實作

*更新日期：2026-06-01（原稿：2026-05-08）*
*狀態：全部文件核對完畢，分析資料夾已整備完成。*

---

## 當前理解

五個子系統 Mod 藍圖設計完成（2026-05-08），隨後對全部 67 份 .md 文件進行了三輪 1.6/Odyssey 源碼核對，發現並修正 20+ 個 API 錯誤與杜撰方法，現已可進入實作階段。

---

## 已完成項目

### 設計階段（2026-05-08）
- 五個子系統設計藍圖：魔紋、ARPG、哨站、地緣/世界、生活/政治
- others/ 14 份構想、details/ 15 份 C# 實作、tutorial/ 29 份、architecture/ 8 份

### 核對階段（2026-05-23 ~ 2026-06-01）
- details/ × 15：找出 13 個問題，全部回寫修正
- architecture/ × 8（+2 新增）：找出 3 個問題，全部回寫修正
- tutorial/ × 29：找出 4 個問題，全部回寫修正
- others/ × 14：找出 2 個問題，全部回寫修正
- answers/ × 2：核對完成

### 補充產出（2026-06-01）
- `answers/api_changes_1_6.md`：20+ 條 API 速查表，10 分類
- `architecture/def_system.md`：Def 載入管線完整分析（~450 行，全部源碼核對）
- `html/`：暗色系導覽層（index.html + 5 分類頁 + _shared.css，涵蓋 67 份 .md）
- `README.md`：資料夾入口說明文件

---

## 剩餘待辦

- `others/` 分組重組（14 份平鋪，可按子系統建子資料夾或僅在 HTML 層分組）
- 開始五個子系統的實際 Mod 實作（尚未決定從哪個子系統開始）

---

## 核心上下文摘要

**關鍵 API 陷阱**（實作前必看 `answers/api_changes_1_6.md`）：
- `PlanetTile` 取代裸 `int`（世界格 ID）
- `BiomeWorker.GetScore` 多了第一個 `BiomeDef` 參數
- `AddHumanlikeOrders` 已移除 → 改用 `FloatMenuOptionProvider`
- `GenRadial.RadialPawnsAround` 不存在 → LINQ 手動篩
- `Scribe_Values` 不支援陣列 → `Scribe_Collections`
- Pawn 集合存檔用 `LookMode.Reference`（非 Deep）
- `Find.CurrentMap.resourceCounter`（Map 非靜態類別）

**哨站封存**：推薦路線 C（銷毀+重生成新圖），臨時展開用 PocketMap（見 `architecture/outpost_archiving_strategy.md`）。

**ResourceCounter.AllCountedAmounts**：只統計儲存區，非全圖快照。
