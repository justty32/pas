#pragma once
#include <entt/entt.hpp>
#include <functional>
#include <vector>

namespace zone {
struct SystemCtx;

// EntityManager — entt::registry 的薄封裝。
//
// 設計原則（仿 medps + 依 docs/01_core_architecture.md §3）：
// - 底層查詢直接暴露 registry()，不另包 view/query API。
// - 生命週期事件用 EnTT 原生 signal（on_construct / on_destroy），不手寫狀態機。
// - 系統以自由函式（void(registry&, SystemCtx&)）明確註冊於 systems_ vector，
//   順序即執行序（仿 medps global_manager.cpp:130 的 tick 迴圈）。
class EntityManager {
public:
    // ---- 實體生命週期 ----------------------------------------

    entt::entity create();
    void         destroy(entt::entity e);
    bool         valid(entt::entity e) const;

    // ---- Component 存取（thin wrapper，不擋路） ---------------

    template<typename C, typename... Args>
    decltype(auto) emplace(entt::entity e, Args&&... args) {
        return reg_.emplace<C>(e, std::forward<Args>(args)...);
    }

    template<typename C>
    C& get(entt::entity e) { return reg_.get<C>(e); }

    template<typename C>
    const C& get(entt::entity e) const { return reg_.get<C>(e); }

    template<typename C>
    C* try_get(entt::entity e) { return reg_.try_get<C>(e); }

    template<typename C>
    bool has(entt::entity e) const { return reg_.all_of<C>(e); }

    template<typename C>
    void remove(entt::entity e) { reg_.remove<C>(e); }

    // ---- 系統註冊與 tick （仿 medps global_manager） ----------

    using SystemFn = std::function<void(entt::registry&, SystemCtx&)>;

    void add_system(SystemFn fn);
    void tick(SystemCtx& ctx);

    // ---- 底層存取（序列化 / 複雜查詢用） ----------------------
    entt::registry&       registry()       { return reg_; }
    const entt::registry& registry() const { return reg_; }

private:
    entt::registry        reg_;
    std::vector<SystemFn> systems_;
};

} // namespace zone
