# 教學：如何調整對話 (Dialogue) 介面

COGITO 本身不內建複雜的對話系統，而是透過組件橋接兩大熱門插件：**Dialogic** 與 **Dialogue Nodes**。本教學說明如何修改這些對話的顯示外觀。

## 前置知識
- 已閱讀 [Level 5F: 對話整合](../architecture/level5f_dialogue.md)。
- 您的 Godot 專案必須已安裝並啟用對應的對話插件。

## 原始碼導航

COGITO 的橋接腳本位於：
- `addons/cogito/Components/Interactions/DialogicInteraction.gd` (Dialogic 整合)
- `addons/cogito/Components/Interactions/DialogueNodesInteraction.gd` (Dialogue Nodes 整合)

## 實作步驟

### 1. 修改 Dialogic UI 外觀
若您使用的是 Dialogic (v2+)：
1. COGITO 僅呼叫 `Dialogic.start(timeline_name)`。對話介面的外觀**完全由 Dialogic 插件控制**。
2. 在 Godot 頂部選單點擊 **Dialogic** 標籤。
3. 前往 **Styles** 分頁。在這裡您可以建立或修改「對話佈局 (Layout)」。
4. 您可以修改背景框、字體、頭像位置以及選項按鈕的樣式。

### 2. 修改 Dialogue Nodes UI 外觀
若您使用的是 Dialogue Nodes：
1. COGITO 預設會尋找一個名為 `dialogue_bubble` 的全域變數或場景節點。
2. 尋找插件提供的預設 UI 場景（通常在 `addons/dialogue_nodes/objects/` 下）。
3. 打開該 UI 場景，直接修改其 `Control` 節點、`Panel` 樣式或 `RichTextLabel` 配置。

### 3. 在 COGITO 中觸發對話 UI 顯示時隱藏 HUD
當對話開啟時，通常需要隱藏準心或停用玩家移動：
- 檢查 `DialogicInteraction.gd` 中的 `_on_timeline_started` 訊號連線。
- COGITO 會發射 `toggled_interface(true)` 訊號。
- 玩家的 `player_hud_manager.gd` 會監聽此訊號並自動隱藏準心與相關提示。
- 若要自訂此行為，請在 `player_hud_manager.gd` 的 `_on_toggled_interface` 函數中增加邏輯。

## 驗證方式
1. 確保已在 NPC 上掛載 `DialogicInteraction` 並設定好 Timeline。
2. 與 NPC 互動。
3. 確認對話視窗出現時，COGITO 的準心與互動提示已自動消失。
4. 檢查對話文字的樣式是否反映了您在插件設定中所做的修改。
