# Editor 待辦功能

## 待實作

### A. 隨機 Rate/s（平滑插值）

目標：讓筆刷每秒影響次數可以在隨機模式下平滑波動，而非跳變。

**需要的狀態欄位（`state.py`）：**
- `brush_rate_rand: bool = False`
- `brush_rate_min: float = 5.0`
- `brush_rate_max: float = 30.0`

**`_tick()` 邏輯（`app.py`）：**
- 維護 `_rate_current`（當前實際 rate）和 `_rate_target`（目標 rate）
- 每隔 `_rate_change_interval`（例如 1–2 秒，可用另一個隨機值）重新抽一個新的 `_rate_target`
- 每幀將 `_rate_current` 朝 `_rate_target` lerp，或用 cos 曲線過渡：
  ```
  # 方案一：lerp
  _rate_current += (target - current) * dt * smooth_factor
  # 方案二：cos 過渡（段內 t 從 0→1）
  actual_rate = rate_a + (rate_b - rate_a) * 0.5 * (1 - cos(t * π))
  ```

**UI 控件：**
- `Random Rate` 勾選框
- `Rate Min` / `Rate Max` 滑條（1.0–60.0）

---

### B. 草繪式山脈生成（Sketch-to-Ridge）

目標：使用者用滑鼠在 canvas 畫任意折線與分支，放開後程式沿這些線段自動產出山脈。

**設計：**
- 新工具模式 `"sketch_ridge"`（加入 `ToolName` Literal）
- 右鍵按下開始收集路徑點，拖曳時記錄每個經過的 hex 座標
- 放開右鍵後，依序對相鄰點對跑 `apply_ridge(state, q0, r0, q1, r1)`
- 支援分支：可在同一次操作中用某種方式（例如按住 Shift）從已有路徑點延伸新分支
- **預覽 overlay**：按住時在 canvas 上畫細線顯示目前路徑，放開後消失

**需要的狀態：**
- `sketch_points: list[tuple[int, int]]`：本次草繪收集的 hex 點（放開後清空）

**可調參數（複用現有）：**
- `brush_size`：山脊橫向寬度
- `brush_strength`：山脊高度強度

**改動位置：**
- `state.py`：加 `sketch_points`、擴充 `ToolName`
- `tools.py`：`apply_sketch_ridge(state, points)` 批次呼叫 `apply_ridge`
- `app.py`：`_on_mouse_click` / `_on_mouse_release` 處理 sketch 模式；`redraw_canvas` 加路徑預覽線
