# 教學：如何實作 LOD (多層次細節) 與可見性管理

在製作如「上古卷軸：天際」這樣的大型開放世界時，LOD (Level of Detail) 是保持遊戲幀數 (FPS) 的絕對關鍵。Godot 4 提供了非常強大的自動化 LOD 工具。本教學說明如何設定它們。

## 1. 自動網格 LOD (Automatic Mesh LOD)

Godot 4 導入模型時，預設會自動生成網格的簡化版本。當物體距離相機越遠，GPU 渲染的多邊形就越少。

### 實作步驟：
1. **檢查匯入設定**：
   - 在 `FileSystem` 面板雙擊您的 `.glb` 或 `.gltf` 模型檔案。
   - 確保 `Meshes -> Generate LODs` 是勾選的（預設為開啟）。
2. **場景設定**：
   - 將模型放入場景，成為 `MeshInstance3D`。
   - 只要設定正確，引擎會**全自動**處理，您無需寫任何程式碼。
3. **效能微調**：
   - 在 `Project Settings -> Rendering -> Mesh LOD` 中，您可以調整 `LOD Change -> Threshold` 來控制模型在哪個距離開始降低面數。

---

## 2. 距離剔除 (Visibility Range / HLOD)

自動 LOD 雖然減少了面數，但遠處的物體仍然在消耗 CPU 計算（如 Draw Calls）。對於地上的小石頭、草叢或小物件，距離一遠我們應該**完全不渲染它**。

### 實作步驟：
1. 選取場景中的 `MeshInstance3D`（例如一個 `CogitoStaticInteractable` 的木桶）。
2. 在 Inspector 中找到 **Geometry -> Visibility Range**。
3. 設定參數：
   - **Begin**：物體開始出現的最近距離（通常設為 0）。
   - **End**：物體完全消失的最遠距離（例如設為 50 公尺）。
   - **Begin Margin / End Margin**：設定一個過渡區間（例如 5 公尺）。Godot 會使用 `Dither` (像素網點) 效果讓物體平滑地淡出，而不是生硬地「閃爍」消失。

---

## 3. 處理 NPC 與複雜物件的 LOD (腳本控制)

對於 NPC，他們不僅有模型，還有 `_physics_process`、狀態機與動畫樹 (`AnimationTree`)。當 NPC 在 100 公尺外時，我們不僅不該渲染他，更不該計算他的 AI 與骨架動畫。

### 實作步驟：使用 `VisibleOnScreenEnabler3D`
1. 在 NPC (`CogitoNPC`) 節點下加入一個 `VisibleOnScreenEnabler3D`。
2. 調整其 AABB 範圍包覆整個 NPC。
3. 設定其行為：
   - 預設情況下，當此節點不在畫面上（或距離太遠），它會自動停用父節點的渲染。
   - 勾選 `Enable Node -> Process` 與 `Physics Process`。這樣當 NPC 離開視線或距離過遠時，Godot 會自動暫停該 NPC 的 `_physics_process` 與狀態機更新，大幅節省 CPU 資源。
4. **注意**：對於開放世界，NPC 即使在遠處也可能需要「模擬」移動（例如 Skyrim 的旅行商人）。若需如此，請不要停用 `Physics Process`，而是手動在腳本中檢查距離，若大於某個值，改用極簡化的路線推算，而不呼叫昂貴的 `move_and_slide()` 與動畫更新。
