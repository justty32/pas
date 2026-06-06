# 靜態健檢結果

執行：`python3 tests/healthcheck.py`（離線，不啟動遊戲）。

## 檢查項目
1. 每個 `<li Class="...">` 型別存在於 CQF 反編譯碼 或 原版 Assembly-CSharp（`monodis --typedef`，11712 筆原版型別）。
2. CQF 型別的子欄位（`message`/`type`/`signal`/`addQuestPrefix`/`actions`）為真實 public 成員（從反編譯源逐 class 抽欄位比對）。
3. 引用 defName：`Silver`(ThingDef)、`PositiveEvent`(MessageTypeDef) 對照原版 `Data/` 確認存在。
4. `ThingSetMakerDef` cross-ref（`CQFCaravanRedemption_RewardSilver`）在本 mod 內已定義。
5. `IntRange/FloatRange` 用 `min~max`；全 XML well-formed。

## 結果：全綠
```
全部檢查通過：未發現臆造型別 / 欄位 / defName 問題。
```

## 健檢過程中防止的臆造/取捨
- **未用 `CQFAction_Spawn` 發獎**：反編譯確認其 `RealWork` 依賴 `targets` 內的有效地圖格，而任務生成階段 `QuestPart_DoCQFActions` 傳入空 `targets`，會靜默不生成 —— 改用原版 `QuestNode_GenerateThingSet → QuestNode_DropPods`。
- **未在 `QuestNode_DropPods.contents` 直接寫字面物品清單**：`SlateRef<T>` 內部只存字串（Assembly-CSharp 反組譯確認），字面 `<li>` 清單無法被解析，必須經 slate 變數，故插入 `QuestNode_GenerateThingSet`。
- **`customLetterLabel`/`customLetterText` 不寫翻譯 key**：這兩個欄位走 QuestGen 規則文字（`MergeRules`），非 `Translate()` key，若填 key 會原樣顯示，故直接給可讀文字。
- **`CQFAction_Message.message` 確認走 `Translator.Translate`**（`decompiled.cs:680`），故填翻譯 key 並提供雙語 Keyed。

## 未涵蓋（需遊戲內人工確認）
靜態健檢無法證明 runtime 行為，僅證明「不會因型別/欄位/defName 缺失而紅字」。實際「訊息有跳出、白銀有降落、任務可被說書人/Dev 觸發」需在遊戲內 Execute quest 並掃 Player.log，詳見 PROJECT.md 完成定義。
