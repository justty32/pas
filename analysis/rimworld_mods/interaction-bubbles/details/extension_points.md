# Interaction Bubbles 擴充點（做 create 怎麼最省力）

## 一句話結論

**這是純 UI/C# mod，沒有資料層可擴充。** 純 XML 能動的只有「換貼圖 + 翻譯」；任何行為/外觀邏輯改動都得 fork C#。它對 create 真正的價值是**兩個可複用的技術範式**，而非「在它上面加內容」。

## 純 XML 可做的（極有限）

| 想做的事 | 做法 | 限制 |
|---|---|---|
| 換泡泡外觀貼圖 | 另開 mod 覆蓋 `Bubbles/Inner`、`Bubbles/Outer`（9-slice atlas，四角各佔 25%）、`Bubbles/Icon` | 只能換圖，9-slice 切法寫死在 `Bubble.DrawAtlas()`（`:323`） |
| 翻譯/在地化 | 提供 `Keyed` 語言檔覆蓋 `Bubbles.*` 鍵（實裝 `Languages/English/Keyed/Bubbles.xml` 共 **31 個鍵**：`Bubbles.DoTextColors`/`Bubbles.AltitudeBase`/`Bubbles.OffsetDirections`…） | 純文字 |
| 調整預設行為 | **不行用 XML**——設定全走 `ModSettings`（存檔不是 Def），只能玩家在設定頁手調或改存檔 | 無 def 預設覆蓋面 |

> **沒有任何 Def**（grep 全檔零 `Def` 型別），所以常見的「複製 Def 改 defName」「PatchOperation 注入」路徑在此**完全不適用**。

## 必須 C# 的（幾乎全部）

- 泡泡顯示**哪些互動**：判斷在 `Bubbler.Add()`（`:529`）寫死（型別判斷 + 設定過濾）。想「只顯示特定 `InteractionDef`」「給戰鬥日誌也加泡泡」「改文字來源」都要改這裡。
- 泡泡**外觀/排版/淡出**：`Bubble.Draw()`/`DrawAtlas()`/`GetFade()`、`Bubbler.DrawBubble()` 全 C#。
- 新增**設定項**：得加 `static readonly Setting<T>` 欄位 + 在 `SettingsEditor.DrawSettings()`（`:962`）畫 UI。
- 新增**相容對象**：仿 `Compatibility`（`:725`）反射呼叫第三方。

## 對 create 的真正價值：兩個可複用範式

### 範式 A：`PlayLog.Add` 是「互動發生」的通用捕獲點

```csharp
// Bubbles.decompiled.cs:1100
[HarmonyPatch(typeof(PlayLog), "Add")]
public static class Verse_PlayLog_Add {
    private static void Postfix(LogEntry entry) => Bubbler.Add(entry);
}
```

任何想「在小人社交互動發生時做點事」的衍生 mod（浮動文字、音效、統計、觸發事件、把對話餵給外部系統），都可照抄這個 Postfix——它比鉤個別 `InteractionWorker` 全面，且**自動吃到別的 mod（含 SpeakUp）新增的互動文字**，因為大家都往同一個 `PlayLog` 寫。
- 取雙方：`entry is PlayLogEntry_Interaction` → 反射讀 `initiator`/`recipient`。
- 取單方：`entry is PlayLogEntry_InteractionSinglePawn` → 反射讀 `initiator`。
- 取在地化文字：`entry.ToGameStringFromPOV((Thing)pawn, false)`（這是關鍵——不必自己組字串）。

### 範式 B：在小人頭上畫世界座標跟隨的浮動 UI

`MapInterface.MapInterfaceOnGUI_BeforeMainTabs` Postfix + `GenMapUI.LabelDrawPosFor(thing, zOffset)` 取螢幕座標 + 依 `CameraDriver.rootSize` 換算縮放，是「跟著小人飄的 UI」標準寫法（`Bubbler.Draw()`/`DrawBubble()`，`:638`/`:660`）。兩個值得抄的工程細節：
1. **繪製包 try/catch 自我停用**（`:1069`）：UI patch 每 frame 跑，出錯會刷爆 log，所以一旦 throw 就 `Settings.Activated=false` 停掉，避免拖垮整局。
2. **9-slice atlas**（`DrawAtlas`，`:323`）：用單張貼圖四角不縮放、邊與中央拉伸，做任意大小圓角框，比 `Widgets.DrawBox` 漂亮。

### 範式 C：反射驅動的零樣板設定系統

`Setting<T> where T:struct` + `Settings.AllSettings`（反射列舉自身欄位）+ 統一 `Scribe()`（`:208`/`:879`/`:231`）：新增設定只要加一個欄位，存讀檔自動處理。同 Taranchuk 系的 `SimpleSettings` 解決同類問題（見 simple-warrants），是輕量替代。

## 與群組內其他 mod 的關係

- **SpeakUp**（同群組）：上游內容提供者。SpeakUp 用 `GrammarResolver` 生成更口語的互動文字寫進 PlayLog，Bubbles 原樣顯示。要「讓泡泡更聰明」應改 SpeakUp（文字來源），不是改 Bubbles（顯示層）。
- 想做「LLM 對話泡泡」：正確接法是在**範式 A** 捕獲互動 + 自訂文字來源，**不要**改 Bubbles 本身。
