# Unciv 深度剖析專題五：定點數運算庫與決定性模擬機制

## 1. 定點數核心：Base 30 系統
Unciv 不使用 `Float` 處理移動與戰鬥邏輯，而是透過 `FixedPointMovement`（一個基於 `Int` 的 Value Class）來實現。

### 為何選擇 30？
- **整除性**: 30 是 `2, 3, 5, 6, 10, 15` 的公倍數。
- **移動力映射**: 
    - 1 點移動力 = 30 定點單位。
    - 森林消耗 (2 點) = 60 單位。
    - 道路消耗 (1/2 點) = 15 單位。
    - 鐵路消耗 (1/10 點) = 3 單位。
- **無誤差**: 所有的常見移動消耗在 Base 30 下都是整數運算，從根本上消除了跨平台（Android vs PC）因浮點數實作差異導致的 Desync（非同步）。

---

## 2. 算術運算與精度控制
`FixedPointMovement` 重新定義了標準運算子，確保計算過程中的位數正確：

- **加減法**: 直接對內部 `bits` (Int) 進行整數加減。
- **乘法**: `(bits.toLong() * other.bits / 30).toInt()`。需轉換為 Long 防止中間溢位，並在乘法後除以基數以維持定點位置。
- **除法**: `(bits.toLong() * 30 / other.bits).toInt()`（注意：源碼中 `div` 實作略有不同，傾向於處理 multiplier）。
- **四捨五入 (fpmFromMovement)**: 透過 `(plusOneBit shr 1) + (plusOneBit and 1)` 實現高效的 `HALF_UP` 捨入。

---

## 3. 決定性模擬 (Deterministic Simulation)
為了保證錄像重播 (Replay) 與多人連線的一致性，Unciv 採取了以下措施：

### A. 狀態隨機種子 (State-Based Random)
- AI 與邏輯運算不使用全局 `Random`，而是使用 `civInfo.state.stateBasedRandom(callerName)`。
- 種子由遊戲狀態決定，確保在相同輸入下，不同設備產出的隨機序列（如戰鬥傷害、AI 科技選擇）完全一致。

### B. 資料結構壓縮與 BitSet
- **RouteNode 壓縮**: 尋路節點狀態被壓縮進一個 `Long` 中，存儲在 `LongArray` 裡。
- **BitSet 優化**: 使用 `nodesNeedingNeighbors` (BitSet) 追蹤尋路邊界，減少物件分配 (GC)，這在 C++ 重構中可直接映射為 `std::bitset`。

### C. 尋路一致性 (A* Determinism)
- 尋路成本完全基於 `FixedPointMovement`。
- `PathingMapCache` 支援 `forkForPathfinding`，允許在多線程環境下進行決定性的路徑預計算，而不會互相干擾。

---

## 4. 重構建議 (Refactoring Insights)
如果你要將此系統重構為 C++：
- **類別設計**: 使用 `enum class FixedPointMovement : int32_t` 或包裝類，重載運算子。
- **常數定義**: `#define MOVE_SPEED_BASE 30`。
- **序列化**: 由於內部只是 `int32_t`，可以直接進行二進位序列化，保證存檔的跨平台相容性。
- **驗證**: C++ 實作必須與 Kotlin 的捨入邏輯（`HALF_UP`）嚴格對齊，特別是在 `fpmFromMovement(Float)` 轉換時。

*本專題揭示了 Unciv 如何透過數學上的精巧設計 (Base 30)，在不穩定的浮點數環境中建立起穩固的決定性模擬系統。*
