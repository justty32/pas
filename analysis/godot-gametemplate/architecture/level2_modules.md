# Level 2 Analysis: 核心模組職責與架構模式

## 1. 架構核心概念：解耦與組合
Godot Game Template 採用了高度解耦的架構，核心在於**功能組件化**。

### 1.1 ResourceNode (資源依賴中介)
這是專案中最關鍵的模式。每個 Actor 或複雜組件都包含一個 `ResourceNode`，它充當「服務定位器」(Service Locator) 或「依賴注入」(DI) 的角色。
- **組件 (Mover, Weapon, States)** 不直接互連。
- 他們透過 `resource_node.get_resource("name")` 獲取所需的數據源（如 `input`, `movement_stats`）。

## 2. 關鍵模組剖析

### 2.1 MoverTopDown2D (移動核心)
- **檔案路徑**: `addons/top_down/scripts/actor/MoverTopDown2D.gd`
- **職責**: 
    1. 接收輸入軸 (`input_resource.axis`)。
    2. 計算帶有加速度與摩擦力的速度。
    3. **2.5D 模擬**: 透過 `axis_multiplier_resource` 調整 Y 軸移動比例。
    4. **碰撞處理**: 繼承自 `ShapeCast2D`，手動實作 `move_and_slide` 並處理節點間的重疊 (Overlap Recovery)。

### 2.2 CharacterStates (狀態管理)
- **檔案路徑**: `addons/top_down/scripts/actor/CharacterState.gd`
- **職責**: 
    1. 根據輸入強度決定當前動畫狀態 (`IDLE`, `WALK`)。
    2. 操作 `AnimationPlayer` 進行視覺回饋。
    3. 與移動邏輯完全解耦。

### 2.3 戰鬥與傷害鏈
- **Weapon (`Weapon.gd`)**: 負責定義傷害數據 (`DamageDataResource`) 與發射邏輯。
- **Projectile (`Projectile2D.gd`)**: 
    - 支援對象池化 (`PoolNode`)。
    - 透過 `prepare_exit` 信號優化生命週期管理。
- **Damage Transmission**: 傷害並非直接調用函數，而是透過 `DamageDataResource.report_callback` 回傳給發射者或中央系統。

## 3. 啟動流程 (Bootstrapping)
- **BootPreloader**: 位於 `addons/top_down/scenes/ui/screens/boot_load.tscn`。
- 它確保在遊戲開始前完成兩件事：
    1. **材質編譯**: 防止遊戲中出現 Shader 造成的卡頓。
    2. **數據加載**: 從 `PersistentData` 恢復玩家存檔與配置。
