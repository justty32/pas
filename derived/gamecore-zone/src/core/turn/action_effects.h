#pragma once
#include <array>
#include <cstddef>
#include <entt/entt.hpp>
#include "core/turn/action.h"

namespace zone {

struct TurnWorld;  // 前置宣告（turn_world.h 完整定義）；打破循環依賴。

// 可替換的行為介面（spec §3.2）。每個 ActionKind 註冊一份。
//   on_channel：逐回合效果（B/C 用；A 不觸發）。turn = 已進行的回合序（0-based）
//   on_resolve：結算效果（三版都呼叫）
struct ActionEffects {
    virtual void on_channel(TurnWorld&, entt::entity, const Action&, int /*turn*/) {}
    virtual void on_resolve(TurnWorld&, entt::entity, const Action&) = 0;
    virtual ~ActionEffects() = default;
};

// ActionKind → ActionEffects* 註冊表。現階段 C++ 寫死註冊；之後可換成讀資料。
class EffectRegistry {
public:
    void register_kind(ActionKind k, ActionEffects* e) { table_[idx(k)] = e; }
    ActionEffects* get(ActionKind k) const { return table_[idx(k)]; }

private:
    static std::size_t idx(ActionKind k) { return static_cast<std::size_t>(k); }
    std::array<ActionEffects*, kActionKindCount> table_{};
};

} // namespace zone
