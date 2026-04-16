# 深度模組分析：逆向運動學 (Inverse Kinematics - IK)

## 1. 模組定位
`libs/IK/IK.cpp` 是整個系統的數學核心。它的唯一職責是：接收期望的足端 3D 坐標 $(X, Y, Z)$ 與當前身體位姿，計算出對應腿部的三個關節角度 ($\alpha, \beta, \gamma$)。

## 2. 幾何推導過程 (`IK::solve`)

### A. 全局到局部的坐標轉換 (Yaw 補償)
機器狗的身體可能處於旋轉狀態（存在 Yaw 角）。為了簡化腿部平面的計算，代碼首先套用 2D 旋轉矩陣，將目標足端坐標「反向旋轉」，使其對齊腿部自身的局部坐標系：
```cpp
double tmpSin = sin(_body->orientation.yaw * -1);
double tmpCos = cos(_body->orientation.yaw * -1);
// X' = X * cos - Y * sin
// Y' = X * sin + Y * cos
```
這個技巧將 3D 空間問題降維成了「1 個側向旋轉 + 1 個 2D 平面」的解算。

### B. Alpha 角度 (Hip / 側向旋轉)
利用足端相對於腿部基準點的局部偏移 `lx`，結合腿長 `l1`，利用餘弦定理求出側向偏角 $\alpha$。
```cpp
angle.alpha = M_PI - ikAsin(lx/sqrta) - ikAcos(_leg->size.l1/sqrta);
```

### C. Beta 與 Gamma 角度 (Thigh & Calf / 縱向平面)
在確定了側向旋轉後，剩下的問題就是一個標準的 2 DoF 平面機械臂問題（大腿 `l2` 與小腿 `l3`）：
*   **斜邊計算**：計算髖關節到足端的直線距離平方 (`dyz`)。
*   **餘弦定理**：
    *   $\gamma$ (小腿角)：利用 $c^2 = a^2 + b^2 - 2ab\cos(\theta)$ 求得。
    *   $\beta$ (大腿角)：由斜邊的仰角加上大腿與斜邊的夾角組成。
```cpp
angle.beta  = M_PI_2 - ikAcos( (l3p2 - l2p2 - dyz) / (-2 * sqrt(dyz) * _leg->size.l2)) - ikAsin(ly/sqrt(dxz));
angle.gamma = ikAcos( (dyz - l2p2 - l3p2) / (-2 * _leg->size.l2 * _leg->size.l3) );
```

## 3. 潛在缺陷與改進建議
1.  **數值不穩定 (NaN 崩潰)**：代碼直接呼叫 `acos` 與 `asin`。如果計算出的距離 `sqrt(dyz)` 大於 `l2 + l3`（即目標點太遠，腿不夠長），傳入 `acos` 的值會大於 1，導致回傳 `NaN`。**遷移至 ESP-IDF 時，必須封裝一個具備 `clamp(val, -1.0, 1.0)` 的安全三角函數。**
2.  **效能最佳化**：ESP32 支援 FPU (硬體浮點運算單元)，在 ESP-IDF 中開啟對應的 Config 可以加速這些三角函數運算。
