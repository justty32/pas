# Godot 動畫資源深度架構分析 - Level 3 & 4

動畫系統是 Godot 最強大的部分之一，其核心在於 `Animation` 資源的高度靈活性與效能優化。

## 1. 動畫資料模型 (`scene/resources/animation.h`)
`Animation` 資源本質上是一個 **軌道 (Track)** 的集合。每個軌道獨立控制場景中特定節點的一個或多個屬性。

### 1.1 軌道類型與專用優化
為了提升 3D 動畫效能，Godot 區分了不同類型的軌道：
- **`TYPE_POSITION_3D`, `TYPE_ROTATION_3D`, `TYPE_SCALE_3D`**：
    - 使用專用的 `PositionTrack`, `RotationTrack` 等結構儲存。
    - 使用 `Quaternion` 儲存旋轉，避免萬向鎖 (Gimbal Lock)。
    - **優化**：支援軌道壓縮 (Compressed Tracks)，這對大型角色動畫極其重要。
- **`TYPE_VALUE` (屬性軌道)**：
    - 最通用的軌道，儲存 `Variant` 資料。
    - 支援 `CONTINUOUS` (平滑插值) 或 `DISCRETE` (瞬間切換) 更新模式。
- **`TYPE_METHOD` (方法軌道)**：
    - 儲存方法名稱與參數，用於在動畫特定時間點觸發函數回呼。

### 1.2 數據結構：Keyframes
每個軌道內部維護一個排序好的 `Key` 向量：
- **`TKey<T>`**：
    - `time`：雙精度浮點數，表示時間點。
    - `transition`：緩動曲線係數。
    - `value`：實際的數據（Vector3, Quaternion, float 或 Variant）。

## 2. 採樣與混音邏輯 (`AnimationMixer`)
當動畫播放時，`AnimationMixer` 會執行以下流程：
1. **時間計算**：根據 Delta 時間與播放速度更新當前播放位置。
2. **尋找 Key**：在每個軌道中使用二分搜尋 (`find_key`) 找到當前時間點前後的兩個關鍵幀。
3. **插值運算**：
    - 根據 `InterpolationType` 進行運算。
    - 對於旋轉軌道，使用 `Slerp` (球面線性插值) 以確保最短路徑旋轉。
4. **屬性套用**：透過 `Object::set()` 或直接操作伺服器（對於 3D 變換）將結果寫回目標物件。

## 3. 重要發現
- **路徑緩存**：`AnimationMixer` 在播放前會先解析 `NodePath` 並快取目標物件的指標，避免每幀執行字串解析。
- **多執行緒安全**：`AnimationMixer` 支援非同步處理，這對於擁有數百個骨架角色的遊戲至關重要。

---
*檔案位置：`scene/resources/animation.h`, `scene/animation/animation_mixer.cpp`*
