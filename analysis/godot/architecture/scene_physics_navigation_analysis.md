# Scene 物理與導航系統分析 - Level 2 & 3

## 1. 物理系統架構
Godot 的物理系統在場景層級主要由 `CollisionObject` 及其衍生類別組成，它們是與底層 `PhysicsServer` 通訊的橋樑。

### 核心類別：CollisionObject2D/3D (`scene/3d/physics/collision_object_3d.h`)
- **`RID rid`**：在 `PhysicsServer` 中對應的實體 ID。
- **碰撞管理**：
    - `collision_layer`：物件所屬的層級。
    - `collision_mask`：物件會掃描並與之碰撞的層級。
- **形狀所有者 (`ShapeData`)**：一個 `CollisionObject` 可以擁有多個 `Shape` (如 `BoxShape`, `SphereShape`)，透過 `shapes` 映射管理。
- **輸入拾取 (`Ray Pickable`)**：支援透過滑鼠點擊或射線檢測選取 3D 物件。

### 物理體類型：
- **`StaticBody`**：不主動移動的物體（如地板、牆壁）。
- **`AnimatableBody`**：由代碼或動畫驅動移動的靜態體。
- **`RigidBody`**：由物理引擎模擬受力與碰撞的物體。
- **`CharacterBody`**：專為玩家角色設計的物理體，提供 `move_and_slide()` 等高級運動 API。
- **`Area`**：僅用於檢測重疊與進入/退出事件，不參與碰撞排斥。

## 2. 導航系統架構
導航系統負責路徑尋找 (Pathfinding) 與空間代理 (Agents)。

### 導航區域：NavigationRegion2D/3D (`scene/3d/navigation/navigation_region_3d.h`)
- **`NavigationMesh`**：核心資源，定義了可行走區域的幾何資訊（導航網格）。
- **`RID region`**：在 `NavigationServer` 中對應的區域 ID。
- **開銷管理**：`enter_cost` 與 `travel_cost` 用於調整路徑尋找時的權重（例如泥濘路面開銷較高）。
- **烘焙機制 (`bake_navigation_mesh`)**：支援在執行時或編輯器中根據場景幾何動態生成導航網格。

### 導航代理與連結：
- **`NavigationAgent`**：掛載於 Node 上，負責向 `NavigationServer` 請求路徑並處理動態避障 (Avoidance)。
- **`NavigationLink`**：定義兩個導航點之間的傳送或跳躍連結。
- **`NavigationObstacle`**：動態障礙物，用於 RVO 避障計算。

## 3. 跨系統協作
- **物理與導航的連結**：導航網格的烘焙通常需要讀取物理碰撞形狀 (`CollisionShape`) 作為輸入源。
- **伺服器模式**：兩者都遵循「場景節點提供資料 -> 伺服器進行重度運算 -> 場景節點接收結果」的模式。

---
*檔案位置：`scene/3d/physics/collision_object_3d.h`, `scene/3d/navigation/navigation_region_3d.h`*
