# Loading Progress 擴充接點（純 XML vs 必須 C#）

> 結論：純 C# 工具 mod，**無資料層、對外無純 XML 擴充面**。它的 create 價值是「技術參考範例」，不是被擴充的平台。

## 純 XML vs 必須 C# 二分表

| 需求 | 純 XML？ | 說明 |
|---|---|---|
| 視窗位置等顯示選項 | ✅（非 XML，設定 UI） | `Settings`（`LoadingWindowPlacement`），無 def、mod 無法以 XML 預設 |
| 加新的「載入階段」追蹤 | ❌ C# | 須新增對應 Harmony patch ＋擴 `LoadingStage` enum ＋ `LoadingDataTracker` |
| 改進度視窗外觀 | ❌ C# | `LoadingProgressWindow` / `Widgets_Progressbar` |
| 逐 mod 耗時量測 | ❌ C# | `StartupImpact.ModInfo` |
| 加自訂內容（建築/物品/事件） | — | 本 mod 與內容擴充無關 |

## 對 Create 的意義（技術參考用途）

雖然不能「在它上面用 XML 加東西」，但開源（MIT/Apache，GitHub `ilyvion/loading-progress`）且程式碼是兩個實用技術的乾淨範例：

1. **如何 instrument RimWorld 啟動管線**：鉤住 `LoadedModManager.CombineIntoUnifiedXML`、`XmlInheritance.*`、`DirectXmlToObjectNew.DefFromNodeNew`、`DirectXmlCrossRefLoader.ResolveAllWantedCrossReferences`、`LongEventHandler.*` 等內部載入器——若未來要做「載入期診斷/優化」類 mod 可直接參考其 patch 點。
2. **如何在 LongEventHandler 載入畫面期間畫自訂 UI**（`Verse_LongEventHandler_DrawLongEventWindowContents_Patch`）。
3. **逐 mod 載入耗時量測（StartupImpact）**：找「哪個 mod 拖慢啟動」的做法。

→ 衍生只有一條路：fork DLL 改 C#。它更適合當「閱讀學習」對象而非衍生基座。
