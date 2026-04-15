# 具體資產實例分析報告 (Case Study)

## 1. 武器資產分析 (`assets/common/items/weapons/sword/starter.ron`)
Veloren 的武器不僅是數值，還決定了玩家的行為模式。

### 關鍵字段拆解：
- **`kind: Tool`**：將物品分類為工具/武器類，並進一步細分為 `Sword`。
- **`stats` 塊**：
    - `power`: 基礎攻擊力的乘數。
    - `speed`: 攻擊速度係數，影響動畫播放速率。
    - `energy_efficiency`: 影響技能消耗的能量。
- **動畫聯動**：`hands: Two` 確保了當玩家裝備此劍時，`voxygen/anim` 會自動載入雙手武器的骨架偏移。

## 2. 載具清單分析 (`assets/common/manifests/ship_manifest.ron`)
載具在 Veloren 中是高度組件化的實體。

### 關鍵設計：
- **層級化模型**：透過 `central: "airship_human.structure"` 等引用具體體素模型。
- **交互點映射**：`custom_indices` 將體素位置與邏輯功能綁定。例如在特定座標放置 `CraftingBench` (製作台) 或 `CookingPot` (烹飪鍋)，使得飛船可以變成移動基地。
- **多樣性支援**：同一個清單內定義了 `DefaultAirship`, `SailBoat`, `Submarine`, `Train` 等多種完全不同的交通工具。

---
*本文件由分析任務自動生成。*
