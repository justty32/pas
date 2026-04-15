# 地形生成層級與流體物理深度分析 (Analysis)

## 1. 地形生成管線 (`world/src/layer/mod.rs`)
Veloren 的世界並非一次性生成，而是透過多個層級 (Layers) 的疊加。

### 核心子模組職責：
- **`cave` / `rock`**：構建世界的骨架。
- **`apply_paths_to`**：讀取歷史模擬產出的路徑數據，將體素塊替換為泥土，並清理上方空間。
- **`apply_trains_to`**：利用三次貝茲曲線 (`CubicBezier3`) 規劃鐵軌路徑，實現平滑的曲線軌跡。
- **`apply_coral_to`**：基於水深 (`water_depth`) 與光照條件，程序化地在海底生成珊瑚。

## 2. 流體與環境交互 (`common/src/comp/fluid_dynamics.rs`)
### 物理機制：
- **浮力與阻力**：計算實體體積與流體密度的關係，影響移動速度與垂直加速度。
- **狀態觸發**：當實體高度低於 `water_level`，物理系統會標記 `InFluid` 狀態，進而觸發氧氣消耗或游泳動畫。

---
*本文件由分析任務自動生成。*
