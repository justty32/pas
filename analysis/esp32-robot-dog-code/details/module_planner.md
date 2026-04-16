# 深度模組分析：運動規劃器 (Motion Planner)

## 1. 模組定位
`libs/planner/planner.cpp` 的核心任務是「預測」。它接收來自使用者的遙測指令（如前進速度 $V_x$, 轉向速度 $\omega_{yaw}$），並計算出為了維持這個運動狀態，**下一個步態週期時，機器狗的身體位姿與足端著地點應該在哪裡**。

## 2. 預測邏輯 (`predictPosition`)

### A. 身體姿態預測
首先，根據輸入的速度向量計算預期的身體 Yaw 角：
```cpp
_predictedBody.orientation.yaw = _body->orientation.yaw + rotateInc * _vector->rotate.yaw;
```
接著，使用預期的 Yaw 角計算 2D 旋轉矩陣 (`tmpSin`, `tmpCos`)，推算出預期的身體 XY 坐標。

### B. 足端著地點預測 (Foot Placement)
為了保持平穩，機器狗在移動時，腿部必須落在相對於身體重心的合適位置。
代碼中針對四條腿，將它們的 `defaultFoot`（預設站立點）根據預測出的身體位姿與 Yaw 角進行旋轉平移疊加：
```cpp
_predictedLegLFfoot.x = _predictedBody.position.x + _legLF->defaultFoot.x * tmpCos - _legLF->defaultFoot.y * tmpSin;
// ...以此類推計算 Y 與 Z
```

## 3. 缺陷與改進建議
1.  **缺乏矩陣運算庫**：作者在註解中抱怨 `// This is terible (code)`。由於未使用標準的 4x4 齊次轉換矩陣 (Homogeneous Transformation Matrix)，代碼只能進行極度簡化的 2D (XY 平面) 預測，忽略了 Roll 和 Pitch 的影響。
2.  **動態捕獲點 (Capture Point) 缺失**：現代四足演算法（如 Raibert Heuristic）在計算落足點時，會考慮當前身體的加速度與質心速度，以產生一個「動態捕獲點」。本專案僅做了純幾何的靜態映射。
3.  **遷移建議**：在 ESP-IDF 遷移中，可以引入如 `Eigen` 或微型的 C++ 線性代數庫來重寫這部分，統一使用矩陣運算。
