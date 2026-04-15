# AI 決策鏈與行為樹深度分析 (Analysis)

## 1. 行為樹架構 (`server/agent/src/action_nodes.rs`)
Veloren 的 AI 核心在於其高度組合化的行為樹。

### 核心函數拆解：
- **路徑尋找 (`fn path_toward_target`)**：
    - **位置**：`server/agent/src/action_nodes.rs` (約 120 行)
    - **邏輯**：利用 A* 算法 (`common/src/astar.rs`)。它會根據目標距離與障礙物密度動態選擇 `Full` (完整路徑) 或 `Partial` (部分路徑) 模式。若路徑被阻斷，會嘗試 `Separate` 策略來繞過障礙。
- **閒置與 RTSim 連接 (`fn idle`)**：
    - **位置**：`server/agent/src/action_nodes.rs` (約 215 行)
    - **邏輯**：AI 在閒置時並非完全隨機，而是會讀取 `agent.rtsim_controller.activity`。這是一個關鍵的橋樑，將宏觀的經濟/社會模擬指令（如 `NpcActivity::Goto`）轉發給微觀的行動節點。

## 2. 戰鬥 AI 行為 (`server/agent/src/attack.rs`)
### 核心函數拆解：
- **基礎近戰 (`fn handle_simple_melee`)**：
    - **位置**：`server/agent/src/attack.rs` (約 60 行)
    - **邏輯**：
        ```rust
        if attack_data.in_min_range() && attack_data.angle < 30.0 {
            controller.push_basic_input(InputKind::Primary); // 觸發攻擊
        }
        ```
    - 這裡展示了 AI 的反應速度與「翻滾」(`InputKind::Roll`) 的隨機性觸發（2% 機率），提升了怪物的真實感。
- **飛行 AI (`fn handle_simple_flying_melee`)**：
    - **位置**：`server/agent/src/attack.rs` (約 90 行)
    - **邏輯**：利用比例控制器維護高度。透過 `terrain.ray` (約 115 行) 感知與地面的距離，並依此控制 `move_z` 進行俯衝或拉升。

---
*本文件由分析任務自動生成。*
