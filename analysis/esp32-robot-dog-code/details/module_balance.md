# 深度模組分析：平衡控制 (Static Balance)

## 1. 模組定位
`libs/balance/balance.cpp` 的目標是維持機器狗在移動過程中的穩定性。它透過計算當前系統的重心 (Center of Mass, CoM)，反向調整身體的座標。

## 2. 靜態重心計算 (`getCenter`)
專案採用了極度簡化的**靜態平衡 (Static Balance)** 策略：
1.  **遍歷所有腿**：檢查 `_leg->sensor.onGround` 狀態。
2.  **加總與平均**：將所有處於「支撐相 (Stance)」的腿部坐標 $(X, Y, Z)$ 加總，然後除以在地的腿數 `_legsOnGround`。
3.  **疊加偏移量**：加上手動設定的 `_offset`（通常用於補償電池等重物的非對稱放置）。
```cpp
_CoM.x = _CoM.x / _legsOnGround + _offset->x;
_CoM.y = _CoM.y / _legsOnGround + _offset->y;
```
最後，`setBody(CoM)` 將身體坐標設定為計算出的中心點上方，確保身體投影落在「支撐多邊形」內。

## 3. 缺陷與改進建議
1.  **缺乏動態慣性模型**：這種方法僅適用於極低速的「爬行 (Creep)」步態（隨時保持 3 條腿著地）。對於 Trot（對角線兩腿同時離地）步態，靜態重心會瞬間移向支撐線的中心，這會導致極為嚴重的晃動，無法抵消動態產生的慣性力矩。
2.  **Z 軸處理錯誤**：作者在註解中承認 `// TODO... can we ignore Z?`。直接平均 Z 軸高度在崎嶇地形會導致身體傾斜。
3.  **遷移建議**：在 ESP-IDF 移植後，由於引入了 IMU，可以實作更進階的 **PID 姿態補償**。利用 IMU 回報的 Roll/Pitch 誤差，直接計算出身體需要反向補償的角速度，而非依賴粗糙的幾何平均。
