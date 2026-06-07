# Walk the World 擴充接點（純 XML vs 必須 C#）

> 結論：**純 C# 機制 mod，無資料層，對外無純 XML 擴充面**。所有衍生都要改 C#；玩家層級的調整已開在遊戲內設定。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 說明 |
|---|---|---|
| 調離開方式 / 途中事件過濾 / 鏡頭 | ✅（非 XML，遊戲內設定） | `WalkTheWorldModSettings`：`LeavingType` / `RandomEventsFilterType` / `CameraFocusMode` 三個 enum，設定 UI 調，**非 def、mod 無法以 XML 預設** |
| 改「走到邊緣就跨格」的機制 | ❌ C# | `WalkTheWorld:GameComponent` ＋ `ExitMapGrid_*_Patch`（把四邊設為出口） |
| 相鄰格地圖如何生成/是否保留 | ❌ C# | `MapGenerator:910`（離開重置是寫死行為） |
| 徒步交易 / 攻打聚落判定 | ❌ C# | `TraderTracker`/`TradeDeal`/`SettlementDefeatUtility` 系列 patch |
| 加自訂內容（建築/物品/事件） | — | 本 mod 不提供任何 Def，與內容擴充無關 |

## 對 Create 的意義

- 本 mod 是**純玩法機制改造**，不是內容/框架平台，幾乎沒有「在它上面用 XML 加東西」的空間。
- 想做衍生只有兩條路：① fork DLL 改機制（C#）；② 它與其他「地圖/世界移動」mod（如 RV-with-PD、MultiFloors 的 PocketMap/MapPortal 家族）在「離開地圖/跨地圖」這件事上可能有 patch 衝突，做相容時需注意 `ExitMapGrid` 相關 patch。
