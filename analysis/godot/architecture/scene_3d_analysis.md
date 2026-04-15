# Scene 3D 渲染系統分析 - Level 2 & 3

## 1. 空間基礎：Node3D (`scene/3d/node_3d.h`)
`Node3D` 是所有 3D 物件的基底類別，處理 3D 空間中的位置、旋轉與縮放。

### 關鍵機制：
- **變換更新與 Dirty 標記**：
    - `DIRTY_LOCAL_TRANSFORM`, `DIRTY_GLOBAL_TRANSFORM`, `DIRTY_EULER_ROTATION_AND_SCALE`。
    - 採用延遲更新策略，僅在讀取時才根據 Dirty 標記重新計算，大幅提升大量物件移動時的效能。
- **旋轉模式 (`RotationEditMode`)**：支援 Euler, Quaternion, Basis。這僅影響編輯與儲存方式，不影響底層運算邏輯。
- **物理插值 (Physics Interpolation)**：支援 FTI (Fixed Timestep Interpolation)，確保在變動影格率下 3D 物件移動的平滑度。
- **Gizmo 系統**：與編輯器整合，負責在視口中渲染 3D 操作軸。

## 2. 視覺實例：VisualInstance3D (`scene/3d/visual_instance_3d.h`)
繼承自 `Node3D`，是所有具備視覺表現之 3D 物件（如模型、燈光）的基類。

### 核心功能：
- **`RID instance`**：在 `RenderingServer` 中對應的渲染實例 ID。
- **包圍盒 (AABB)**：管理物件在 3D 空間中的軸對齊包圍盒，用於剔除 (Culling)。
- **層級遮罩 (Layer Mask)**：控制物件對哪些攝像機可見。
- **排序與剔除**：支援 `sorting_offset` 與 `extra_cull_margin`。

## 3. 幾何實例：GeometryInstance3D
繼承自 `VisualInstance3D`，專門處理具有幾何形狀的物件。

### 關鍵屬性：
- **陰影投射 (`ShadowCastingSetting`)**：控制是否投射或接收陰影。
- **GI 模式 (`GIMode`)**：定義物體如何與全域光照（VoxelGI, SDFGI, Lightmap）互動。
- **LOD (Level of Detail)**：支援根據距離自動調整細節層級。
- **材質覆蓋 (Material Override)**：允許動態更換整體的材質。

## 4. 重要 3D 節點類型
- **`MeshInstance3D`**：顯示 `Mesh` 資源的核心節點。
- **`Light3D`**：包含 `DirectionalLight3D`, `OmniLight3D`, `SpotLight3D`。
- **`Camera3D`**：定義觀察 3D 世界的視角與投影方式。
- **`Skeleton3D`**：處理骨架動畫與變形。
- **`VoxelGI` / `LightmapGI`**：負責全域光照計算。

---
*檔案位置：`scene/3d/node_3d.h`, `scene/3d/visual_instance_3d.h`*
