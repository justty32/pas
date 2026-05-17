# Wesnoth 技術全典：單位實體與特技引擎 (第十三卷)

本卷解構 `src/units/` 目錄，特別聚焦於 `unit.cpp` 與 `abilities.cpp`。Wesnoth 的單位並非靜態的數值載體，而是一個具備複雜事件過濾與區域光環 (Aura) 效果的動態實體。

---

## 1. 技能與光環引擎 (`abilities.cpp`)

這是 Wesnoth 最具特色的系統之一。單位的技能（如「領導」、「治癒」）通常不僅影響自己，還會動態影響周圍的六角格。

### 1.1 光環空間過濾 (Aura Spatial Filtering)
- **`unit::ability_affects_adjacent(ab, dist, dir, loc, from)`**: 
  - **工程解析**：判斷一個相鄰單位的技能 `ab` 是否能輻射到當前座標 `loc`。
  - **幾何約束**：除了計算距離 `dist`，WML 還能定義 `adjacent=n,ne,nw`。此函數會進行方向性拓撲檢查，實作如「只能治療背後友軍」的定向光環。

### 1.2 條件狀態編譯 (Conditional State Compilation)
- **`active_ability_list unit::get_abilities(tag_name, loc)`**: 
  - **狀態疊加**：單位的最終技能是其基礎兵種技能、身上裝備 (Items) 的特技、以及其他單位賦予的光環的**聯集**。
  - **WML 腳本過濾**：呼叫 `unit_ability_t::matches_filter`，動態評估 WML 中的 `[filter]`（例如：只在夜晚生效的隱形，或只對獸人有效的領導）。

### 1.3 遞歸防護機制 (Recursion Guard)
- **`unit_ability_t::guard_against_recursion(...)`**: 
  - **系統穩定性**：當單位 A 的技能依賴於周圍單位，而單位 B 的技能又依賴單位 A 時，會產生無限遞歸。此函數實作了一個呼叫堆疊鎖 (Call Stack Lock)，當偵測到技能相互查詢時，會中斷遞歸，保證遊戲引擎不會因錯誤的 Mod 崩潰。

---

## 2. 武器特效動態上下文 (`specials_context_t`)

在交戰時，單位的武器特效（Weapon Specials）會動態改變戰鬥參數。

- **`specials_context_t::specials_context_t(att, def)`**: 
  - **上下文構建**：將攻擊方與防禦方的狀態打包。
- **`get_single_ability_value(...)`**: 
  - **數值修改器 (Value Modifier)**：處理諸如「衝鋒 (Charge: 傷害 x2)」、「魔法 (Magical: 命中率鎖定 70%)」的邏輯。它會遍歷雙方武器上的 `[specials]`，根據優先級與乘法/加法規則，動態修改原始參數。
- **`overwrite_special_overwriter(...)`**: 
  - **規則覆寫**：處理極端情況，例如某武器特效宣告 `override=true`，它將強制無效化對手的某項防禦特技。

---

## 3. 單位動畫與視覺表現 (`animation_component.cpp`)

單位並非只有攻擊和移動動畫，其動畫系統是一個複雜的狀態機。

- **`unit_animation_component::set_standing(...)` / `set_idling()`**: 
  - **待機分發**：管理單位在原地時的呼吸或小動作動畫。
  - **時間抖動**：利用 `get_next_idle_tick()` 加入亂數延遲，確保畫面上一排同種類的單位不會像機器人一樣「完全同步」播放待機動畫，增添畫面的自然感。

---
*第十三卷解析完畢。Wesnoth 的單位系統是高度解耦且數據驅動的，其強大的 Filter 系統賦予了開發者用 WML 創造出千變萬化戰術組合的可能。*
*最後更新: 2026-05-17*
