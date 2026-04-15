# RimWorld 電力系統：電網與組件 (Power System)

電力系統是一個基於網格的數據分發系統。

## 1. 核心組件：`CompPower`
所有用電設備都繼承自 `CompPower`。
*   **CompPowerPlant**: 發電機。定義 `PowerProduction`。
*   **CompPowerTrader**: 消費者。定義 `PowerOutput` (負數為消耗，正數為產生)。
*   **CompPowerBattery**: 蓄電池。定義 `StoredEnergy`。

## 2. 電網管理：`PowerNet`
*   **連接性**: 遊戲會透過 `Section` 遍歷所有相鄰的 `Building_PowerConduit` (電線) 來構建 `PowerNet`。
*   **管理員**: `Map.powerNetManager` 負責在電線被摧毀時拆分電網，或在電線連接時合並電網。

## 3. 修改建議
*   **新增發電方式**: 繼承 `CompPowerPlant` 並在 `CompTick` 中動態修改 `PowerOutput` (如：根據風力大小)。
*   **控制電網**: 透過 `powerNet.powerStats` 可以獲取當前電網的總負載與剩餘電量。

---
*由 Gemini CLI 分析 RimWorld.PowerNet 生成。*
