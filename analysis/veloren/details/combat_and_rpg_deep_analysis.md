# 戰鬥系統與 RPG 屬性深度分析 (Analysis)

## 1. 命中判定與傷害計算 (`common/src/combat.rs`)
戰鬥是 Veloren 的靈魂，結合了精確的幾何計算。

### 核心邏輯拆解：
- **格擋與完美格擋 (`fn compute_block_damage_decrement`)**：
    - **位置**：`common/src/combat.rs` (約 170 行)
    - **邏輯**：格擋不再是簡單的機率。它檢查 `defender.look_vec` 與攻擊來源的夾角。完美格擋 (`is_parry`) 會獲得 5.0 倍的屬性加成 (`PARRY_BONUS_MULTIPLIER`)。
- **近戰命中偵測 (`common/systems/src/melee.rs`)**：
    - **位置**：`common/systems/src/melee.rs` (約 185 行)
    - **邏輯**：使用圓柱體檢測。如果目標在 `max_angle` (攻擊扇形) 內且中間沒有地形遮擋 (`is_blocked_by_wall`, 約 195 行)，則判定命中。

## 2. 技能觸發與分派 (`common/src/comp/ability.rs`)
### 核心邏輯拆解：
- **動態技能分派 (`fn activate_ability`)**：
    - **位置**：`common/src/comp/ability.rs` (約 145 行)
    - **邏輯**：透過 `AbilitySource::determine` 判斷玩家當前是在走路還是滑翔，進而決定 `Primary` 輸入是對應武器技能還是滑翔翼動作。這實現了「一套按鍵、多種狀態自適應」的設計。

---
*本文件由分析任務自動生成。*
