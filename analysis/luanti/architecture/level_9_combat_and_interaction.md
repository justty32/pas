# Level 9: 戰鬥與互動系統深度分析 (特效、投射物與陷阱)

## 1. 特效系統：粒子發射器 (Particle Spawners)
Luanti 提供了一套由 C++ 驅動、Lua 控制的高效能粒子系統：
- **原始碼位置**：`src/script/lua_api/l_particles.cpp` (行號 153, `l_add_particlespawner`)。
- **參數結構**：`ParticleSpawnerParameters`。
    - **隨機性**：所有物理量（pos, vel, acc, exptime, size）都支援 `min` 與 `max` 定義，引擎會自動在區間內取隨機值。
    - **物理交互**：支援 `collisiondetection`（碰撞偵測）與 `collision_removal`（碰撞後移除），這讓粒子看起來更真實，例如挖掘時噴出的碎屑會掉落在地面上。
    - **附著機制**：可以透過 `attached` 參數將粒子發射器綁定到玩家或實體上。

## 2. 投射物系統 (Projectiles)
投射物在引擎底層被視為動態實體 (`ACTIVEOBJECT_TYPE_LUAENTITY`)：
- **物理模擬**：通常在 Lua 端的 `on_step` 中進行。
- **命中檢測**：
    - **方塊碰撞**：利用實體本身的 `physical = true` 屬性，或透過 `core.line_of_sight` 預測路徑。
    - **實體命中**：在 `on_step` 中掃描周圍的小範圍實體 (`core.get_objects_inside_radius`) 並呼叫 `punch` 方法。

## 3. 陷阱與區域觸發機制
Luanti 提供了多種實作區域觸發的方法：
- **方塊傷害 (Static Traps)**：在方塊定義中使用 `damage_per_second`。
    - **原理**：伺服器環境 (`ServerEnvironment`) 在每秒的步進中會檢查玩家是否位於具備此屬性的節點內，並直接扣除生命值。
- **邏輯觸發器 (Logic Triggers)**：
    - **LBM (Loading Block Modifier)**：當含有特定方塊的區塊載入時觸發（適合一次性陷阱）。
    - **ABM (Active Block Modifier)**：週期性掃描（適合持續性環境效果）。
    - **玩家步進偵測**：在 `core.register_on_step` 中全域檢查所有玩家的位置與下方的方塊 ID。
