#pragma once
#include "core/turn/action_effects.h"
#include "core/turn/timed_effect.h"

namespace zone {

class ActionLibrary;  // 前置宣告（LibraryEffects 用）

// 持續效果工具：施加 / 逐回合 tick（後者由 TurnWorld::on_actor_turn 在回合開始呼叫）。
void apply_timed_effect(entt::registry&, entt::entity, TimedEffectKind, int turns, int power);
void tick_timed_effects(TurnWorld&, entt::entity);

// 可組合行為原語（free functions）：寫死的 effect 與資料驅動的 LibraryEffects 共用。
void resolve_move(TurnWorld&, entt::entity, int dx, int dy);                      // 移動/撞牆/攻擊/拾取/樓梯
void resolve_nova(TurnWorld&, entt::entity, int damage, int dot_turns, int dot_power,
                  int radius = 1, int dot_kind = 0);  // 範圍傷害 + 殘留 DoT

// Move：依 param 方向移動一格（搬自 zone_world_gd.cpp::move()）。
struct MoveEffects : ActionEffects {
    void on_resolve(TurnWorld&, entt::entity, const Action&) override;
};

// Wait：消耗一回合、無效果。
struct WaitEffects : ActionEffects {
    void on_resolve(TurnWorld&, entt::entity, const Action&) override {}
};

// Cast：多回合詠唱（weight>1 會 channel），結算時 nova + 殘留燃燒。
struct CastEffects : ActionEffects {
    int damage{ 4 };
    void on_resolve(TurnWorld&, entt::entity, const Action&) override;
};

// 資料驅動：行為由 Action.def 指向的 ActionDef（JSON 載入）決定，組合上面的原語。
struct LibraryEffects : ActionEffects {
    const ActionLibrary* lib{ nullptr };
    void on_resolve(TurnWorld&, entt::entity, const Action&) override;
};

} // namespace zone
