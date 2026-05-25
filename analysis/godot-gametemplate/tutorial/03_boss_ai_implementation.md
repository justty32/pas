# 教學 03: 實作複雜 Boss AI 行為與 GDExtension 效能優化

> 核對於 2026-05-25（Claude Code, Opus 4.7）：事件驅動狀態機、跳躍壓殺、分裂機制皆與源碼一致；本次修正了 2.5D 補償的實際算法（`axis_compensation = ONE / axis_multiplication`）與相關行號引用。

本教學將剖析 Big Jelly Boss 的實作細節（`addons/top_down/scripts/actor/boss/`），並展示如何將頻繁的距離計算與決策邏輯遷移至 C++ 以提升大規模戰鬥下的效能。

## 1. Boss AI 的「事件驅動」架構
不同於小怪每幀尋路，Boss 採用的是**事件驅動狀態機**（`BigJellyAi.gd`）：
- **決策中心**: `BigJellyAi.gd` 中的 `_state_update()`（`:39-57`）。
- **觸發機制**: 當前動作完成後才回呼決策中心：`chase.finished.connect(_state_update.call_deferred)`（`BigJellyAi.gd:29`）；`BigJellyChase.finished` 由著地恢復 Tween 在 `landing_recovery_time` 後發出（`BigJellyChase.gd:45-54`）。
- **決策順序**: 若 `close_in_counter > 0 && _need_move_in_range()` 先靠近跳躍（`BigJellyAi.gd:42-46`）；否則嘗試 `shoot_slime.shoot()`，成功則以 `tween_wait` 延遲 2 秒再回呼自身（`:48-54`）；都不成立則一般跳躍追擊（`:56-57`）。
- **優點**: 極大地降低了 CPU 負擔，且易於加入動作間的延遲 (`Tween` 延遲)。

## 2. 核心行為實作

### 2.1 距離補償與 2.5D 透視
由於遊戲使用 2.5D 視覺，Y 軸距離在視覺上看起來較短。
- **實際算法**（`BigJellyChase.gd`）: 距離計算發生在 `target_calculation()`（`:37-43`）。它先算 `axis_compensation = Vector2.ONE / axis_multiplication.value`（`:30`），把世界向量乘上 `axis_compensation`**還原**為等比空間後再 `.length()` 取得 `distance_length`（`:40-41`）；跳躍方向 `direction` 則反向乘回 `axis_multiplication.value`（`:42`）。
- `BigJellyAi._need_move_in_range()` 並不自行算距離，而是呼叫 `chase.target_calculation(..., 9999.0)` 後讀 `chase.distance_length` 與 `out_of_range_distance` 比較（`BigJellyAi.gd:61-65`）。

### 2.2 跳躍壓殺 (Area Receiver 隱藏)
- **跳躍中**: 將 `AreaReceiver2D` 的 `collision_layer` 設為 0，使 Boss 在空中時處於無敵/不可選取狀態。
- **著地時**: 觸發 `ShapeCastTransmitter2D`，這是一個圓形碰撞掃描，用於一次性對範圍內所有目標造成傷害。

## 2.2 跳躍壓殺與分裂機制
- **跳躍壓殺**: 跳躍由 `JumpMove.gd` 驅動，著地時 `BigJellyChase._on_landing()` 生成著地 VFX（`landing_vfx.instance(...)`，`BigJellyChase.gd:49-51`）。傷害判定可搭配 `ShapeCastTransmitter2D` 做一次性範圍掃描。
- **分裂機制**: `BigJellySlimeSpawner.gd` 在綁定的 `projectile.prepare_exit_event` 觸發時（`:17`），依 `angles:Array[float]` 對每個角度旋轉方向、乘 `axis_multiplication` 後生成子實體，並呼叫 `ActiveEnemy.insert_child(inst, active_enemy_branch)` 把子實體掛入靜態血脈樹（`:23-30`），確保整株消滅才計為一次擊殺。

## 3. GDExtension 優化：AI 決策加速
當場景中有大量分裂出的子實體或多個 Boss 時，距離判斷會變得昂貴。最適合下沉至 C++ 的是 `BigJellyChase.target_calculation()` 中的純向量運算（無節點樹依賴，僅讀 `character_body.global_position`）。

### 3.1 遷移目標：`target_calculation`（含 2.5D 補償）
將下列等比空間距離計算遷移至 C++（對應 `BigJellyChase.gd:37-43`）：
```cpp
// C++ 實作範例：以 axis_compensation = ONE / axis_multiplication 還原等比空間
float BigJellyChaseNative::compute_distance(Vector2 target_pos, Vector2 target_vel, float max_distance) {
    Vector2 target = target_pos + target_vel * jump_time + target_offset;
    // 還原 2.5D 透視：除以 axis_multiplication（等同乘 axis_compensation）
    Vector2 diff = (target - character_body->get_global_position()) * axis_compensation;
    distance_length = MIN(diff.length(), max_distance);
    direction = diff.normalized() * axis_multiplication; // 反向乘回，用於實際跳躍方向
    return distance_length;
}
```
> 注意：補償是「除以」`axis_multiplication`（即乘上 `axis_compensation`），而非乘上 `axis_multiplication`；方向向量才需要再乘回 `axis_multiplication`。

### 3.2 遷移步驟
1. 在 `godot-cpp` 專案中定義 `BigJellyChaseNative` 類別。
2. 綁定 `axis_multiplication`（Vector2）並於初始化算出 `axis_compensation`。
3. 將 `BigJellyChase.gd` 的 `target_calculation` 計算部分替換為呼叫 Native 方法，GDScript 端僅保留信號/Tween 流程。

## 4. 教學練習：自定義 Boss 行為
1. **修改分裂邏輯**: 在 `BigJellySlimeSpawner.gd` 中修改 `angles` 陣列，讓 Boss 分裂時以不同角度散射子實體（`:23`）。
2. **加入二階段**: 在 `_state_update()` 中檢測 `HealthResource`（透過 `resource_node`）。當 HP 低於 50% 時，縮短 `tween_wait` 的延遲（目前固定 2.0 秒，`BigJellyAi.gd:53`），進入「狂暴模式」。
