# 教學：如何自訂互動提示 (Interaction) 與 HUD

本教學將引導您如何修改玩家在場景中看到的互動文字、準心 (Crosshair) 以及屬性條外觀。

## 前置知識
- 已閱讀 [Level 1: 初始探索](../architecture/level1_overview.md) 中關於 `Player_HUD` 的說明。
- 瞭解 `InteractionComponent` 如何觸發提示訊號。

## 原始碼導航

主要相關檔案位於：
- `addons/cogito/PackedScenes/Player_HUD.tscn` (全域 HUD 容器)
- `addons/cogito/Scripts/player_hud_manager.gd` (HUD 控制邏輯)
- `addons/cogito/Components/UI/UI_PromptComponent.tscn` (互動提示單個條目)
- `addons/cogito/Components/UI/UI_PromptComponent.gd` (提示顯示邏輯)
- `addons/cogito/Theme/stylebox_prompts.tres` (提示背景樣式)

## 實作步驟

### 1. 修改互動文字的外觀
當玩家看向一個開關或門時，畫面中央會跳出提示（例如："[E] 打開"）：
1. 打開 `addons/cogito/Components/UI/UI_PromptComponent.tscn`。
2. 修改 `Panel` 節點的 `Theme Overrides` 以更換背景框顏色或形狀。
3. 修改 `HBoxContainer/InputLabel` (Label) 以調整按鍵提示的字體（預設會被 `input_helper` 自動替換成對應圖示）。
4. 修改 `HBoxContainer/PromptLabel` (Label) 以調整互動動作名稱的樣式。

### 2. 更換準心 (Crosshair)
COGITO 支援「預設準心」與「互動準心」切換：
1. 選取場景中的 `Player_HUD` 節點（或查看 `player_hud_manager.gd`）。
2. 在 Inspector 的 `HUD` 分組中，您可以直接更換：
   - `Default Crosshair`: 平時的準心。
   - `Interaction Crosshair`: 當射線掃到可互動物件時的準心。
3. 若要修改準心的縮放或動畫，請在 `Player_HUD.tscn` 中尋找 `Crosshair` 節點。

### 3. 修改屬性條 (Health, Stamina, etc.)
屬性條是由 `ui_attribute_prefab` 動態生成的：
1. 預設預製檔案通常位於 `addons/cogito/Components/UI/UI_AttributeComponent.tscn`（請在專案中確認此路徑）。
2. 修改該場景中的 `ProgressBar` 樣式。
3. 若要調整屬性條在螢幕上的排列位置，請修改 `Player_HUD.tscn` 中的 `MarginContainer_BottomUI/PlayerAttributes` 容器。

### 4. 調整互動名稱組件 (Object Name)
當玩家看向物件時，物件名稱顯示在特定位置：
- 修改 `addons/cogito/Components/UI/UI_ObjectNameComponent.tscn`。
- 這個組件由 `player_hud_manager.gd` 實例化，並根據物件的 `prompt_pos_mode` 決定顯示位置。

## 驗證方式
1. 運行遊戲並走向任何一個 `CogitoDoor` 或 `CogitoSwitch`。
2. 檢查跳出的互動提示是否符合您在 `UI_PromptComponent.tscn` 設定的新樣式。
3. 觀察準心在看向物件與看向牆壁時是否正確切換。
