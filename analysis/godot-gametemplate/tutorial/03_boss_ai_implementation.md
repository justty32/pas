# 教學 03: 實作複雜 Boss AI 行為與 GDExtension 效能優化

本教學將剖析 Big Jelly Boss 的實作細節，並展示如何將頻繁的距離計算與決策邏輯遷移至 C++ 以提升大規模戰鬥下的效能。

## 1. Boss AI 的「事件驅動」架構
不同於小怪每幀尋路，Boss 採用的是**事件驅動狀態機**：
- **決策中心**: `BigJellyAi.gd` 中的 `_state_update()`。
- **觸發機制**: 當前動作（如 `chase.finished` 或 `shoot_slime.done`）完成後，才回呼決策中心決定下一個動作。
- **優點**: 極大地降低了 CPU 負擔，且易於加入動作間的延遲 (`Tween` 延遲)。

## 2. 核心行為實作

### 2.1 距離補償與 2.5D 透視
由於遊戲使用 2.5D 視覺，Y 軸距離在視覺上看起來較短。
- **實作關鍵**: 在 C++ 或 GDScript 中計算距離時，必須先乘以 `axis_multiplication` 資源中的向量，將其轉換回「真實空間」再計算長度。

### 2.2 跳躍壓殺 (Area Receiver 隱藏)
- **跳躍中**: 將 `AreaReceiver2D` 的 `collision_layer` 設為 0，使 Boss 在空中時處於無敵/不可選取狀態。
- **著地時**: 觸發 `ShapeCastTransmitter2D`，這是一個圓形碰撞掃描，用於一次性對範圍內所有目標造成傷害。

## 3. GDExtension 優化：AI 決策加速
當場景中有大量分裂出的子實體或多個 Boss 時，距離判斷會變得昂貴。

### 3.1 遷移目標：`_need_move_in_range`
將以下 GDScript 邏輯遷移至 C++：
```cpp
// C++ 實作範例
bool BigJellyAiNative::need_move_in_range(Vector2 player_pos, float out_of_range_dist) {
    Vector2 diff = player_pos - get_owner()->get_global_position();
    // 考慮 2.5D 軸向補償
    diff.y *= axis_multiplication.y; 
    return diff.length() > out_of_range_dist;
}
```

### 3.2 遷移步驟
1. 在 `godot-cpp` 專案中定義 `BigJellyAiNative` 類別。
2. 綁定 `axis_multiplication` 為 `Vector2` 屬性。
3. 將原本在 `BigJellyAi.gd` 中的計算部分替換為呼叫 Native 方法。

## 4. 教學練習：自定義 Boss 行為
1. **修改分裂邏輯**: 在 `BigJellySlimeSpawner.gd` 中，嘗試修改 `angles` 陣列，讓 Boss 在死亡或分裂時以不同的角度散射子彈或敵人。
2. **加入二階段**: 在 `_state_update()` 中檢測 `HealthResource`。當 HP 低於 50% 時，縮短 `tween_wait` 的延遲時間，進入「狂暴模式」。
