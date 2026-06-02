# 教學：把 C++ 成員變數納入 ECS 存讀檔

> 核對於 2026-06-02（Claude Sonnet 4.6）。源碼位置：`derived/opennefia-cpp/`。

本教學說明一個常見問題：GDExtension 類別（如 `OpenNefiaWorld`）有許多 C++ 成員變數（`turn_count_`、`current_floor_`……），這些變數**不在 ECS registry 裡**，`opennefia::serialize::save()` 不會自動序列化它們。如何讓它們隨存檔持久化？

---

## 問題根源

```cpp
// opennefia_world_gd.h — 這些成員不在 ECS 中
class OpenNefiaWorld : public godot::Node {
    opennefia::EntityManager em_;  // ECS registry 在這裡
    entt::entity map_entity_;      // ← save/load 後失效！需要重建
    entt::entity hero_entity_;     // ← 同上
    int  turn_count_{ 0 };         // ← serialize::save() 看不到它
    int  current_floor_{ 1 };      // ← 同上
    bool game_over_{ false };      // ← 同上
};
```

- `opennefia::serialize::save()` 只序列化 **ECS registry 中所有有 component 的 entity**。
- `map_entity_` / `hero_entity_` 是 C++ 端的快取指標，`registry.clear()` 後舊 handle 失效。

---

## 解法：掛 StateComponent 到 ECS

**核心思想**：把需要持久化的 C++ 成員包成一個 `XxxStateComponent`，掛在已有的某個永久 entity（此處為 `map_entity_`）上，加入 `AllComponents` → 隨 snapshot 自動序列化。

### 步驟一：定義 Component

**`src/core/components/world_state_component.h`**（已有）：

```cpp
struct WorldStateComponent {
    int turn_count{ 0 };
    int current_floor{ 1 };

    template<class Archive>
    void serialize(Archive& ar) { ar(turn_count, current_floor); }
};
```

設計原則：
- 只放**純值欄位**（`int`, `float`, `bool`, `std::string`）。
- **不**放 `entt::entity`（存讀後 handle 失效，需用語義查詢重建）。
- **不**放執行期快取（如 `visible[]`）——這類資料在 `load()` 後重算即可。

### 步驟二：加入 AllComponents

**`src/core/serialize/all_components.h`**：

```cpp
using AllComponents = entt::type_list<
    MetaDataComponent,
    SpatialComponent,
    MapData,
    NpcAiComponent,
    HealthComponent,
    ItemComponent,
    CombatStatsComponent,
    WorldStateComponent   // ← 加在這裡，fold expression 自動序列化
>;
```

這樣，`entt::snapshot{reg}.get<WorldStateComponent>(out)` 就會被 fold expression 呼叫到。

---

## 存檔流程：存前同步

**`opennefia_world_gd.cpp`**，`save_game(path)` 實作（約 `cpp:479`）：

```cpp
bool OpenNefiaWorld::save_game(const godot::String& path_gd) {
    if (map_entity_ == entt::null || hero_entity_ == entt::null) return false;

    // 關鍵：存檔前把 C++ 成員同步到 ECS Component
    auto* ws = em_.registry().try_get<opennefia::WorldStateComponent>(map_entity_);
    if (ws) {
        ws->turn_count    = turn_count_;
        ws->current_floor = current_floor_;
    }

    // 序列化（此時 WorldStateComponent 已是最新值）
    std::filesystem::path path{ std::string(path_gd.utf8().get_data()) };
    opennefia::serialize::save(em_.registry(), path);
    return true;
}
```

---

## 讀檔流程：讀後重建

**`opennefia_world_gd.cpp`**，`load_game(path)` 實作（約 `cpp:494`）：

```cpp
bool OpenNefiaWorld::load_game(const godot::String& path_gd) {
    std::filesystem::path path{ std::string(path_gd.utf8().get_data()) };
    if (!std::filesystem::exists(path)) return false;

    // 1. 清空 registry（所有舊 entity handle 失效！）
    em_.registry().clear();
    map_entity_  = entt::null;
    hero_entity_ = entt::null;
    game_over_   = false;

    // 2. 反序列化（snapshot_loader 還原全部 entity + component）
    opennefia::serialize::load(em_.registry(), path);

    // 3. 重建 map_entity_（用「哪個 entity 持有 MapData」語義查詢）
    auto& reg = em_.registry();
    for (auto e : reg.view<opennefia::MapData>()) { map_entity_ = e; break; }

    // 4. 重建 hero_entity_（用 HeroComponent 正向 tag 語義查詢；F6 起確立）
    for (auto e : reg.view<opennefia::HeroComponent>()) {
        hero_entity_ = e;
        break;
    }

    // 5. 從 WorldStateComponent 還原 C++ 成員
    if (map_entity_ != entt::null) {
        if (const auto* ws = reg.try_get<opennefia::WorldStateComponent>(map_entity_)) {
            turn_count_    = ws->turn_count;
            current_floor_ = ws->current_floor;
        }
    }

    recompute_fov();
    emit_signal("world_changed");
    return true;
}
```

---

## 推廣：如果有更多成員需要持久化

同一個 `WorldStateComponent` 加欄位即可：

```cpp
struct WorldStateComponent {
    int turn_count{ 0 };
    int current_floor{ 1 };
    int hero_level{ 1 };       // ← 新增
    int total_kills{ 0 };      // ← 新增

    template<class Archive>
    void serialize(Archive& ar) { ar(turn_count, current_floor, hero_level, total_kills); }
};
```

> **注意**：`ar()` 的參數順序決定 binary 格式。若舊存檔使用舊格式而新版本加了欄位，格式不相容，舊存檔讀取後資料錯亂。需要做版本管理時，改用 cereal 的 `CEREAL_NVP` 或手動加版本號欄位。

若有兩種性質完全不同的狀態需要分開管理，也可以建兩個 Component（如 `PlayerProgressComponent` + `WorldStateComponent`），分別掛在不同 entity 上，都加入 `AllComponents`。

---

## 為什麼不用 sidecar 檔案？

另一種常見做法是把 C++ 成員另存一個 JSON / 文字檔（sidecar）與主存檔配對。

| | ECS Component 掛載法 | sidecar 方式 |
|---|---|---|
| 序列化自動化 | 加入 AllComponents 即自動 | 需要手寫讀寫邏輯 |
| 原子性 | 主存檔一個 binary 檔 | 兩個檔案，存到一半崩潰時不一致 |
| 格式擴充 | 在 Component 加欄位 | 分別維護 |
| 適用性 | 適合與 ECS 並存的遊戲狀態 | 適合完全獨立的設定／設定檔 |

opennefia-cpp 目前選擇 Component 掛載法，確保單一存檔檔案就能完整還原遊戲狀態。

---

## 關鍵陷阱一覽

| 陷阱 | 說明 | 解法 |
|---|---|---|
| `registry.clear()` 後使用舊 handle | `em.registry().clear()` 後所有 `entt::entity` 值失效，存取會 crash 或取到錯誤 entity | 清空前設 `map_entity_ = entt::null`，`load()` 後用語義查詢重建 |
| 存檔前忘記同步 | 成員修改後若在下次 `save_game()` 前 crash，舊同步值被序列化 | 在每次 `save_game()` 的**第一步**（serialize 之前）同步 |
| 欄位順序改變破壞存檔 | cereal binary 格式是位元組序列，沒有欄位名稱 | 只在末尾加欄位；舊欄位順序不變 |
| `game_over_` 沒有納入持久化 | 若死亡狀態不存，讀檔後 `game_over_` 仍為 `false`，玩家可繼續操作 | 依設計選擇：目前實作在 `load_game()` 主動設 `game_over_ = false`（允許讀存檔復活） |
