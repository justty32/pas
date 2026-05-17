# Freeciv 經濟產出深度分析：食物、產能與貿易 (源碼剖析)

Freeciv 的經濟系統是建立在方格 (Tile) 產出的累加與修正之上的。本文件解構了從地形基礎到最終產出的計算流水線。

## 1. 經濟原子：`Output_type_id`
定義於 `common/fc_types.h`。Freeciv 區分六種核心產出：
- `O_FOOD` (食物): 人口成長與維持。
- `O_SHIELD` (產能/護盾): 建造單位與建築。
- `O_TRADE` (貿易): 轉化為金錢、科研與奢華度的基礎。
- `O_GOLD`, `O_LUXURY`, `O_SCIENCE`: 貿易額經過稅率轉化後的最終形式。

## 2. 產出計算流水線：`city_tile_output()`
位於 `common/city.c:1340`。這是計算單一方格產出的核心函數。

### 第一階段：基礎值 (Base Yield)
```c
prod = pterrain->output[otype];
if (tile_resource_is_valid(ptile)) {
    prod += tile_resource(ptile)->data.resource->output[otype];
}
```
- **地形產出**: 讀取 `terrain.ruleset` 定義的基礎值（如：草原食物 2，沙漠產能 0）。
- **戰略資源**: 若方格上有有效的資源（如：煤、馬），則加上資源額外提供的產出。

### 第二階段：土地開發修正 (Improvements)
根據方格上的附加物（Extras）進行加成：
- **灌溉 (Irrigation)**: 
    - 增加食物產出 (`pterrain->irrigation_food_incr`)。
    - 受技術效果 `EFT_IRRIGATION_PCT` 修正（如：冷藏技術可提升灌溉效率）。
- **礦坑 (Mine)**: 
    - 增加產能 (`pterrain->mining_shield_incr`)。
    - 受 `EFT_MINING_PCT` 修正。
- **道路與鐵路**: 
    - 呼叫 `tile_roads_output_incr()` 增加基礎貿易。
    - 呼叫 `tile_roads_output_bonus()` 進行百分比加成（如：鐵路增加產能 50%）。

### 第三階段：全域效果與慶典 (Effects & Celebration)
- **慶典加成 (`is_celebrating`)**: 若城市處於慶典狀態，會觸發 `EFT_OUTPUT_INC_TILE_CELEBRATE`，通常用於增加貿易額或金錢。
- **懲罰機制 (`EFT_OUTPUT_PENALTY_TILE`)**: 
    - 用於模擬專制體制（Despotism）下的「產能懲罰」。
    - 如果某格產出超過一定數量，會被強行扣除一部分（典型的「Despotism Penalty」）。

### 第四階段：市中心保障 (City Center Minimum)
```c
if (pcity != nullptr && is_city_center(pcity, ptile)) {
    prod = MAX(prod, game.info.min_city_center_output[otype]);
}
```
- 確保市中心至少具備基本的食物與產能，防止城市因貧瘠地形而無法起步。

## 3. 資源點與經濟評估 (AI Perspective)
AI 如何看待這些產出？

### 3.1 資源權重
AI 內部對不同產出有不同的估值（以「Want」表示）：
- **食物**: 初期權重極高（為了人口擴張）。
- **產能**: 中期權重提升（為了戰爭機器與基建）。
- **貿易**: 稅率決定其動態價值（見 AI 專題 1）。

### 3.2 土地利用預測 (`tile_virtual_new`)
AI 會建立「虛擬方格」來預測：
- 「如果我在這格蓋礦坑，我的產能會增加多少？」
- AI 會呼叫 `city_tile_output` 進行前後比對，以此決定工人的開發優先級。

## 4. 工程見解
- **規則集驅動 (Ruleset-Driven)**: 所有的基礎數值（2, 1, 0 等）均不在 C 代碼中寫死，而是從 `terrain.ruleset` 讀取。這使得 Freeciv 具備極強的 Mod 兼容性。
- **原子化計算**: `city_tile_output` 只關下方格產出，不考慮腐敗 (Corruption) 與浪費 (Waste)。腐敗是在城市層面（`common/city.c` 的其他部分）計算完總貿易額後才統一扣除的，這保持了計算邏輯的清晰。
- **位元向量優化**: 透過 `bv_extras` 快速判斷方格是否具備灌溉、礦坑等狀態，極大提升了數百個城市、數千個方格每回合的產出計算效能。
