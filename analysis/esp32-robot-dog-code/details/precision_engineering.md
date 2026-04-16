# 深度技術剖析：分段線性舵機校準 (Precision Engineering)

## 1. MG90D 舵機的非線性問題
便宜的 9g 舵機（如 TowerPro MG90D）通常存在以下問題：
*   **電位器非線性**：給予 1500us 脈衝未必精確指向 90 度。
*   **個體差異**：即使是同一批次的舵機，在 30 度與 150 度的脈衝需求也不同。

## 2. 解決方案：Segmented Linear Mapping
專案在 `HAL_ESP32PWM.ino` 中實作了 `angleToPulse` 函數，這也是該專案最精華的底層邏輯：

```cpp
if (angleDeg < 30) return mapf(angleDeg, minAngle, 30, degMin, deg30);
if (angleDeg < 50) return mapf(angleDeg, 30, 50, deg30, deg50);
// ...以此類推
```

### 技術特點：
1.  **多點校準**：定義了 30, 50, 70, 90, 110, 130, 150 七個校準點。
2.  **局部線性化**：將 0-180 度的曲線切分為 8 個線性小段。這能大幅抵消廉價舵機的硬體缺陷。
3.  **動態 Profile**：這些參數存儲在 `servoMainProfile` 結構體中，並可透過 EEPROM 加載，實現了「單機校準，全域生效」。

## 3. 工具鏈支持
為了配合此算法，專案在 `tools/servoCalib` 中提供了一個物理模板與對應的 `.ino` 測試程式，讓開發者能以 10 度為單位手動讀取精確的 PWM 值。這種**軟硬體協同優化**是許多開源專案所欠缺的深度。
