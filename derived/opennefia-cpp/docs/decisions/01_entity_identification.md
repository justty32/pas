# 決策 01 — 實體辨識：正向 tag，不用排除法

**日期**：2026-06-02
**狀態**：已採用
**相關程式碼**：`src/core/components/hero_component.h`、`src/core/systems/npc_ai_system.cpp`、`src/gbind/opennefia_world_gd.cpp`

## 脈絡

`npc_ai_system` 需要在 registry 中找出「英雄」實體，才能判斷視野 / 追蹤 / 攻擊目標。
最初圖省事，用「英雄是唯一有座標、但不是 NPC 的東西」這個假設：

```cpp
// 舊作法（已廢棄）
for (auto e : reg.view<SpatialComponent>(entt::exclude<NpcAiComponent>)) {
    hero_ent = e; break;
}
```

## 問題（實機 bug，F6）

這個假設是錯的：**物品實體也有 `SpatialComponent` 且沒有 `NpcAiComponent`**，因此同樣命中。
雪上加霜的是 **EnTT 單一 component 的 view 由 storage 尾端往前迭代**，而真機
（`setup_test_world`）的建立順序是「英雄 → NPC → 物品」，物品落在 pool 尾端 → 迭代
最先碰到的「非 NPC 有座標實體」其實是某個**物品**。

結果：`hero_ent` 指向沒有 `HealthComponent` 的物品，NPC 的攻擊 `try_get<HealthComponent>`
回 null、傷害打空，**英雄永遠不掉血**。單元測試一開始沒抓到，因為測試裡物品建在英雄
之前，反向迭代剛好先碰到英雄，矇混過關（這本身就是排除法脆弱性的鐵證）。

## 決策

**辨識特定實體一律用正向標記（tag component），不靠「缺少某 component」反推。**

- 新增空 tag `HeroComponent`（`std::is_empty_v == true`，EnTT snapshot 走空型別最佳化，
  只存 entity 不存 payload）。
- 系統改用 `view<HeroComponent, SpatialComponent>` 唯一鎖定，與建立順序、其他實體的
  component 組合完全無關。
- `HeroComponent` 列入 `serialize/all_components.h`，存讀檔後仍在；gbind 載入路徑也改用
  `view<HeroComponent>` 找回 `hero_entity_`（取代先前掃 `MetaDataComponent::proto_id == "hero"`）。

## 理由

1. **正確性**：正向標記表達的是「這個實體**是**英雄」，而非「它**不是**別的東西」——後者
   會隨著新增實體類型（物品、陷阱、投射物……）不斷被打破。
2. **抗迭代順序**：不依賴 EnTT view 的迭代方向或 pool 內排列。
3. **可序列化**：tag 進 `AllComponents` 後存讀檔自動保留，載入端辨識邏輯與執行期一致。
4. **成本趨近零**：空 tag 不佔 payload，snapshot 只多存一組 entity id。

## 推論準則（適用於未來所有實體辨識）

> 要找「某一類實體」時，給它一個正向 tag component，用 `view<Tag, ...>` 查；
> **不要**用 `exclude<...>` 列舉「它不是什麼」。

## 參照

- 事件全貌：`PROJECT.md §9`（2026-06-02 F6）、`docs/03_roadmap.md` F6 段。
- 藍本：medps 以 component 組合表達實體種類（`analysis/medps/architecture/02_core_patterns.md`）。
