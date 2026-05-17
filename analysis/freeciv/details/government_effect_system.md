# 政府體制架構深化：全域效應修正機制 (源碼剖析)

Freeciv 的政府體制（如：民主、共和、專制）並非硬編碼的邏輯，而是透過一套精密的 **Effect (效應) 系統** 實現的全域動態修正。本文件深入剖析 `common/government.c` 與 `common/effects.c`，解構其權限校驗與產出修正模型。

## 1. 核心資料結構：`struct government`
定義於 `common/government.h`。

```c
struct government {
  struct name_translation name;
  struct requirement_vector reqs; /* 變更此體制的前置科技或條件 */
  bv_gov_flags flags;             /* 特殊標籤 (如: 是否有參議院阻礙) */
  /* ... AI 評估數據 ... */
};
```
- **解耦設計**: 政府體制本身不儲存「增加 10% 貿易」這種數值。具體的數值儲存在 ruleset 的 `[effect_...]` 區段，並將 `Requirement` 設定為「目前政府體制 == 某某」。

---

## 2. 產出修正流水線：`get_city_output_bonus()`
位於 `common/effects.c`。這是體制影響遊戲的最主要途徑。

### 2.1 需求上下文 (`req_context`)
當系統需要計算某城市的產出時，會建立一個上下文：
```c
struct req_context context = {
  .player = city_owner(pcity),
  .city = pcity,
  .government = government_of_player(pplayer) /* 注入目前體制 */
};
```

### 2.2 效應過濾與加總
系統遍歷所有相關的 `EFT_` 類型（如 `EFT_OUTPUT_BONUS`）：
1. **匹配**: 檢查該 Effect 的需求 (Requirements) 是否包含當前政府。
2. **計算**: 
    - **加法型**: `sum += effect_value`
    - **乘法型**: `sum *= (100 + effect_value) / 100`
3. **典型體制效應**:
    - **專制 (Despotism)**: 觸發 `EFT_OUTPUT_PENALTY_TILE` (產能超過 2 則扣 1)。
    - **共和 (Republic)**: 觸發 `EFT_OUTPUT_INC_TILE` (每格貿易 +1)。

---

## 3. 政治行為約束：`gov_flags`
除了經濟數值，體制透過標籤直接鎖定或開啟某些代碼路徑：

- **`GOVF_SENATE` (參議院)**:
  - 在 `server/diplomats.c` 中，若玩家嘗試宣戰，代碼會檢查此 flag。
  - 邏輯：`if (government_has_flag(gov, GOVF_SENATE) && !has_casus_belli()) { block_war(); }`
- **`GOVF_REVOLUTION_WHEN_UNHAPPY` (動亂倒閣)**:
  - 若具備此標籤，當多個城市連續數回合處於 `Disorder` 時，系統會強制觸發無政府狀態（Anarchy）。

---

## 4. 工程見解
- **高度數據驅動**: 體制系統完全由數據驅動。如果你想在 Ruleset 中新增一個「數位獨裁」體制，只需定義名稱並添加一系列 Effect 即可，底層 C 代碼完全不需要修改。
- **上下文注入**: Effect 系統的強大在於 `req_context`。透過將「政府體制」作為 Requirement 的一個維度，Freeciv 實現了將政治因素滲透到從戰鬥力、科研速度到建築成本的每一個角落。
