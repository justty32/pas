# 深度模組分析：步態引擎 (Gait Engine)

## 1. 模組定位
`libs/gait/gait.cpp` 與 `gait.ino` 共同構成了步態協調系統。它的職責是：根據時間（Ticks）推進，管理每條腿處於「支撐相 (Stance)」還是「擺動相 (Swing)」。

## 2. 步態時鐘與狀態機 (`gait.ino`)

### A. 全域時鐘推進
運動控制迴圈（250Hz）每執行一次，就會觸發 `updateGait()`。
*   **Tick 計數**：`ticksToNextGaitItem` 每次遞減，計算出當前步態項目的進度 `gaitItemProgress` (0.0 ~ 1.0)。
*   **狀態切換**：當倒數至 0 時，切換至下一個步態項目 (`currentGait++`)。

### B. Trot 步態配置
在 `GAIT_CONFIG` 中，定義了一個 Trot 步態序列：
```cpp
{ SWING,  STANCE, STANCE, SWING  }, // 狀態 1：對角線 (左前、右後) 抬起
{ STANCE, SWING,  SWING,  STANCE }  // 狀態 2：對角線 (右前、左後) 抬起
```

## 3. 單腿步態控制 (`gait.cpp`)

每一條腿都有一個獨立的 `gait` 實例：
*   **`gait::start(from, to)`**：當腿進入 `SWING` 狀態時被呼叫。它將目標點交給 `transition` 類別，並重置該腿的 `ticksToStop`（擺動持續時間）。
*   **`gait::next()`**：在每個循環被呼叫。如果 `ticksToStop > 0`，它會根據進度 (progress) 從 `_transition.swing()` 獲取當前高度與平移坐標；若結束，則標記 `_leg->sensor.onGround = true`。

## 4. 缺陷與改進建議
1.  **開環控制 (Open-loop)**：目前 `onGround` 狀態完全是基於時間推算出來的，而非實體感測器回報。作者註解 `// TODO use real sesors and stop gait if leg touch the ground` 表明了未來的擴展方向（阻抗控制）。
2.  **固定頻率的局限**：目前的步態切換硬綁定了 `LOOP_TIME`。若要實現平滑的速度過渡，應改為基於相位角 (Phase Oscillator) 的連續步態生成器。
