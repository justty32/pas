# 02 - ECS 與 事件系統 (ECS Core)

ECS 是引擎的核心。我們將使用 **EnTT** 作為高效能後端，並在其上封裝出符合 OpenNefia 風格的 API。

## 2.1 實體與組件 (EntityManager)

對應 `OpenNefia.Core.GameObjects.EntityManager`。

- **EntityUid**: 在 C++ 中，EnTT 使用 `entt::entity` 作為 ID。我們可以建立一個 `EntityUid` 型別 alias 或 wrapper。
- **Component**: C++ 中的組件不需要繼承基底類別（POCO），但為了相容原本的生命週期，我們可能需要定義一些標記或使用 EnTT 的掛勾 (Hooks)。

```cpp
// src/core/ecs/EntityManager.hpp
class EntityManager {
public:
    EntityUid CreateEntity(PrototypeId<EntityPrototype> protoId);
    void DeleteEntity(EntityUid uid);

    template<typename T>
    T& AddComponent(EntityUid uid);

    template<typename T>
    T& GetComponent(EntityUid uid);

private:
    entt::registry _registry;
};
```

## 2.2 基礎組件 (Core Components)

每個實體都應包含的基礎組件：

- **MetaDataComponent**: 儲存原型 ID、生命週期狀態。
- **SpatialComponent**: 儲存座標、父子關係（對應 OpenNefia 的 Scene Graph）。

## 2.3 事件匯流排 (EntityEventBus)

對應 `OpenNefia.Core.GameObjects.EntityEventBus`。
這是 OpenNefia 系統間解耦的關鍵。我們需要實作兩類事件：

1. **廣播事件 (Broadcast)**: 全域系統事件。
2. **定向事件 (Directed)**: 針對特定實體的事件（例如 `DamageEvent` 只發送給受傷的實體）。

**實作方案：**
- 使用 EnTT 的 `entt::dispatcher` 作為基礎。
- 封裝 `EventBus` 類別，支援 `SubscribeLocalEvent` 與 `RaiseLocalEvent`。

```cpp
// 範例：發送事件
_eventBus.RaiseLocalEvent(entityUid, DamageEvent{ .amount = 10 });
```

## 2.4 系統管理器 (EntitySystemManager)

對應 `OpenNefia.Core.GameObjects.EntitySystemManager`。

- 在 C++ 中，我們手動注冊系統或使用靜態注冊機制。
- 每個 `EntitySystem` 都有 `Initialize()`、`Update(float dt)` 與 `Shutdown()` 方法。

```cpp
class DamageSystem : public EntitySystem {
public:
    void Initialize() override {
        SubscribeLocalEvent<DamageEvent>(&DamageSystem::OnDamage);
    }

private:
    void OnDamage(EntityUid uid, DamageEvent& ev);
};
```
