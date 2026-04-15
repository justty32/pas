# 03 - 深入核心與 Bonus 系統

當數據與腳本無法滿足需求時，你需要深入 `VCMI_lib`。作為資深工程師，掌握 **加成系統 (Bonus System)** 是最關鍵的一步。

## 1. 萬物皆 Bonus：核心設計模式

VCMI 的設計哲學：幾乎所有的數值變動（技能、寶物、法術、地形、甚至是 Mod 額外加入的規則）都被抽象化為 `Bonus`。
- **節點結構 (`CBonusSystemNode`)**: 每個地圖物件（英雄、城鎮、單位）都是一個節點。
- **圖形傳遞**: 加成會在節點樹中傳播。例如：英雄佩戴加攻擊的寶物 -> 英雄節點獲得 Bonus -> 傳遞到英雄率領的單位節點。

### Bonus 的組成項目：
- **Type**: 例如 `Bonus::ATTACK_VALUE`, `Bonus::MORALE`。
- **Limiter**: 限制加成僅對特定兵種或環境有效。
- **Propagator**: 控制加成如何在樹中向下傳播。

## 2. 網路通訊與同步 (`NetPack`)

VCMI 是一個狀態同步的引擎。所有的遊戲操作（移動、攻擊、建造）都必須序列化為 `NetPack`。
- **路徑**: `lib/networkPacks/`。
- **自定義協議**:
    1. 在 `NetPack` 類別中定義資料成員。
    2. 實作序列化介面。
    3. 在 `server/CGameHandler.cpp` 中處理該封包並修改 `CGameState`。
    4. 伺服器會自動廣播更新後的狀態變更給所有客戶端。

## 3. 並行處理與效能 (Intel TBB)

VCMI 廣泛使用 TBB 以最大化多核效能：
- **AI 運算**: `Nullkiller` AI 在計算最佳行動路徑時會大量調用 `tbb::parallel_for`。
- **RMG (隨機地圖生成器)**: 獨立地塊的生成與渲染在背景執行緒中並行處理。
- **影像處理**: 客戶端在加載與縮放高清資產時，會利用 TBB 執行緒池防止主執行緒 (MainGUI) 凍結。

## 4. 關鍵類別地圖

- `CGameState`: 權威狀態。
- `CGObjectInstance`: 地圖實體基類。
- `CBonusSystemNode`: 紅利系統掛載點。
- `CNetHandler`: 處理 Boost.Asio 通訊底層。

---
**下一章**: [`04-workflow-and-debugging.md`](04-workflow-and-debugging.md) - 開發環境與調試技巧。
