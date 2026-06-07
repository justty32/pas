#pragma once
#include <entt/entt.hpp>

namespace zone {

// 效果結算時產生的遊戲事件；ZoneWorld 在 advance 後讀取並轉成 Godot signal。
// 核心層不認識 Godot，只把事件丟進 TurnWorld::events。
enum class EventKind {
    BumpedWall,        // 撞牆（未移動）
    BumpedActor,       // 攻擊命中但未殺死（a 攻擊 b，amount = 傷害）
    ActorDied,         // b 被 a 殺死（b 已 destroy）
    ItemPickedUp,      // a 拾取道具 b（amount = 實際治療量）
    ReachedStairDown,  // a 走到下樓梯
};

struct ZoneEvent {
    EventKind    kind;
    entt::entity a{ entt::null };
    entt::entity b{ entt::null };
    int          amount{ 0 };
};

} // namespace zone
