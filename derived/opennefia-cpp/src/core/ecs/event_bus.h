#pragma once
#include <entt/entt.hpp>
#include <functional>
#include <typeindex>
#include <unordered_map>
#include <vector>

namespace opennefia {

// 事件匯流排：支援兩種派發模式。
//
// 1. 定向（directed）：RaiseLocalEvent(entity, ev)
//    針對特定實體發送事件；所有訂閱此事件型別的 handler 依序被呼叫。
//    handler 可修改事件物件（by-reference），實現攔截 / 取消語意。
//    仿 OpenNefia EntityEventBus.RaiseLocalEvent，但不靠反射——改用
//    void* 類型抹除，型別安全由 subscribe<T> 樣板邊界保證。
//
// 2. 廣播（broadcast）：直接使用 entt::dispatcher。
//    dispatcher().trigger<T>(ev)        ← 立即派發
//    dispatcher().enqueue<T>(ev)        ← 排入佇列
//    dispatcher().update<T>()           ← 清空佇列
//    dispatcher().sink<T>().connect<&fn>(instance)  ← 訂閱
//
// 訂閱順序 = 執行順序（FIFO）。

class EventBus {
public:
    // ---- 定向事件 ------------------------------------------------

    template<typename Event>
    void subscribe(std::function<void(entt::registry&, entt::entity, Event&)> handler) {
        auto& vec = directed_[std::type_index(typeid(Event))];
        // type erasure：把 Event& 的 handler 包成 void* 形式存放
        vec.emplace_back(
            [h = std::move(handler)](entt::registry& reg, entt::entity e, void* ptr) {
                h(reg, e, *static_cast<Event*>(ptr));
            }
        );
    }

    template<typename Event>
    void raise_local(entt::registry& reg, entt::entity target, Event& ev) {
        auto it = directed_.find(std::type_index(typeid(Event)));
        if (it == directed_.end()) return;
        for (auto& fn : it->second) {
            fn(reg, target, &ev);
        }
    }

    // ---- 廣播事件 ------------------------------------------------

    entt::dispatcher& dispatcher() { return broadcast_; }

private:
    using DirectedHandler = std::function<void(entt::registry&, entt::entity, void*)>;
    std::unordered_map<std::type_index, std::vector<DirectedHandler>> directed_;
    entt::dispatcher broadcast_;
};

} // namespace opennefia
