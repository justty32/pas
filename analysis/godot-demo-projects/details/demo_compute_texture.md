# 深入剖析：`compute/texture`（Compute Shader 即時填充材質）

## 為何選它
這是 repo 中最完整的 **compute shader** 範例：用 GPU compute 即時計算水面漣漪，並把結果材質回灌到一般渲染管線當作 displacement/法線輸入。涵蓋 `RenderingDevice` 低階 API、push constant、ping-pong 多緩衝、以及「在 render thread 上執行」這些進階主題。比入門的 `compute/heightmap` 深一階。

## 檔案組成

| 檔案 | 角色 |
|---|---|
| `compute/texture/main.gd` | 場景控制（UI 滑桿、旋轉），無核心邏輯（`main.gd:3` 明說真正實作在 water_plane） |
| `compute/texture/water_plane/water_plane.gd` | **核心**：compute 初始化、每幀分派、資源釋放 |
| `compute/texture/water_plane/water_compute.glsl` | compute shader（GLSL，漣漪計算） |
| `compute/texture/water_plane/water_shader.gdshader` | 一般材質著色器，取用 compute 輸出的 `Texture2DRD` |

## 執行緒模型（最重要的概念）
`water_plane.gd:9-13` 註解點出：若 thread model 為 Multi-Threaded，compute 程式碼會跑在**渲染執行緒**上，因為要把邏輯接進該執行緒的正常渲染流程。

實作上用 `RenderingServer.call_on_render_thread(...)`（`water_plane.gd:39, 55, 129`）把以下三件事都丟到 render thread：
1. `_initialize_compute_code`（建立 shader / pipeline / 紋理）
2. 每幀 `_render_process`（分派 compute）
3. `_free_compute_resources`（釋放）

`water_plane.gd:131-132` 之後的所有函式都標註「設計成在 render thread 執行」。這是寫 Godot compute shader 必須理解的執行緒邊界。

## 核心流程剖析

### 1. 初始化（render thread）`_initialize_compute_code`
`water_plane.gd:154-195`：
- 取得主渲染裝置 `rd = RenderingServer.get_rendering_device()`（`water_plane.gd:157`）——用主 RD 才能把結果接進主渲染。
- 載入 `.glsl` → 取 SPIR-V → 建 shader 與 compute pipeline（`water_plane.gd:160-163`）。
- 建立 **3 張 R32_SFLOAT 紋理**（`water_plane.gd:166-185`），usage 同時允許 sampling / storage / copy。
- 為 3 張紋理建立 9 組 uniform set（`water_plane.gd:188-195`）——對應 ping-pong 的三種角色組合。

### 2. Ping-pong 三緩衝
`water_plane.gd:139-143` 註解：用 3 張紋理——一張寫入、一張上一幀、一張上上幀。漣漪是二階波方程，需要前兩幀狀態才能算下一幀。

每幀在 `_process` 推進索引：`next_texture = (next_texture + 1) % 3`（`water_plane.gd:117`），並把當前要顯示的 RID 指給材質的 `Texture2DRD`（`water_plane.gd:122-123`）。

### 3. 每幀分派（render thread）`_render_process`
`water_plane.gd:198-243`：
- **手動組 push constant**：因無 struct，用 `PackedFloat32Array` 依序 push 波點座標、紋理尺寸、阻尼，並補一個 0 對齊到 8 個 float（`water_plane.gd:201-210`）。
- **計算 dispatch group 數**：`(tex_size.x - 1) / 8 + 1`（`water_plane.gd:217-220`），對應 shader 內 8×8 local work group，並用 shader 內 discard 確保非整除尺寸也覆蓋完整。
- 綁三組 uniform set（current/previous/next）+ push constant，呼叫 `compute_list_dispatch`（`water_plane.gd:231-238`）。
- 註解（`water_plane.gd:240-243`）說明：一般情況靠 Godot 預設 barrier 即可；若要把一個 compute 輸出餵給下一個 compute，才需手動加 barrier。

### 4. 輸入：滑鼠射線打到水面
`_check_mouse_pos`（`water_plane.gd:70-92`）用相機把滑鼠位置投成射線，對水面 Area3D 做 `intersect_ray`，命中點換算成紋理座標當作加波點；`add_wave_point.w` 兼作「滑鼠是否在水面上」旗標（`water_plane.gd:88`）。沒滑鼠互動時則隨機落雨點（`water_plane.gd:104-110`）。

### 5. 資源釋放 `_exit_tree` / `_free_compute_resources`
`water_plane.gd:50-55, 246-257`：離開時把材質的 `texture_rd_rid` 清成空 RID，再到 render thread 釋放紋理、uniform set、shader。註解指出 set 與 pipeline 是依賴關係會自動清理（`water_plane.gd:247`）。

## 可遷移的設計重點
1. **compute 要接進渲染就用主 RD + `call_on_render_thread`**，並把所有 RD 操作鎖在 render thread。
2. **`Texture2DRD`** 是 compute 輸出回灌材質的橋樑：改它的 `texture_rd_rid` 就切換材質顯示的紋理。
3. **ping-pong 多緩衝**處理需要歷史幀的迭代演算法（波、流體、生命遊戲）。
4. **push constant 手動對齊**到 16 byte 邊界（此處湊 8 個 float = 32 byte）。
5. **dispatch group = (N-1)/local_size + 1**，搭配 shader 內邊界 discard。

## 對照學習
- 入門級（不接渲染，純算高度圖）：`compute/heightmap`。
- Compositor 後處理：`compute/post_shader`。
