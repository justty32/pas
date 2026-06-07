#pragma once
#include <functional>
#include <vector>
#include <string>
#include <entt/entt.hpp>
#include "core/turn/action.h"
#include "core/turn/action_effects.h"
#include "core/turn/zone_event.h"

namespace zone {

struct MapData;  // 前置宣告；effect 才 include map_data.h。scheduler 不碰地圖。

// 時間/能量常數（spec §4），可調。
struct TurnConfig {
    int energy_to_act   = 1000;  // 能量達此值才能出手
    int energy_per_tick = 100;   // 速度 100 時每 tick 的能量增量
    int ticks_per_turn  = 10;    // 1 標準回合 = 10 ticks
};

// NPC 決策：給 registry + entity，回傳下一個 action（spec §3.4）。
using NpcDecider = std::function<Action(entt::registry&, entt::entity)>;

// 排程器運作所需的一切。scheduler 只用 reg/effects/npc_decide/cfg；
// map 與 events 供 effect 使用（scheduler 不碰），皆可為 null。
struct TurnWorld {
    entt::registry&         reg;
    EffectRegistry&         effects;
    NpcDecider              npc_decide;
    TurnConfig              cfg{};
    long long               clock = 0;   // 已過 ticks
    MapData*                map = nullptr;
    std::vector<ZoneEvent>* events = nullptr;

    // 每個 actor「回合開始」時呼叫（若有設）：用來 tick 持續效果(DoT)等。
    // scheduler 不認識其內容，只在 actor 取得回合時觸發。
    std::function<void(TurnWorld&, entt::entity)> on_actor_turn = nullptr;

    // 詳細 debug 追蹤（若有設）：效果/DoT 在發生事的當下吐出細節字串。
    // 為 null 時呼叫端不應建字串（以 if (w.trace) 包住）。
    std::function<void(const std::string&)> trace = nullptr;
};

} // namespace zone
