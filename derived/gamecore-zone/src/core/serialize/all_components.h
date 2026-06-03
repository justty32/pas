#pragma once
#include <entt/entt.hpp>
#include <core/components/actor_component.h>
#include <core/components/spatial_component.h>
#include <core/maps/map_data.h>
#include <core/components/npc_ai_component.h>
#include <core/components/health_component.h>
#include <core/components/item_component.h>
#include <core/components/combat_stats_component.h>
#include <core/components/world_state_component.h>
#include <core/components/hero_component.h>

namespace zone::serialize {

using AllComponents = entt::type_list<
    ActorComponent,
    SpatialComponent,
    MapData,
    NpcAiComponent,
    HealthComponent,
    ItemComponent,
    CombatStatsComponent,
    WorldStateComponent,
    HeroComponent
>;

} // namespace zone::serialize
