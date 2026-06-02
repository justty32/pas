#pragma once
#include <entt/entt.hpp>
#include <core/components/meta_data_component.h>
#include <core/components/spatial_component.h>
#include <core/maps/map_data.h>
#include <core/components/npc_ai_component.h>
#include <core/components/health_component.h>
#include <core/components/item_component.h>
#include <core/components/combat_stats_component.h>

// AllComponents：snapshot save/load 的單一來源（仿 medps all_components.h）。
// 新增 component 型別只需在此加一行；save 與 load 都透過 fold expression 自動展開。
// Phase 3：MetaDataComponent + SpatialComponent。
// Phase 4：+ MapData（稠密 tile 網格）。
// NPC AI：+ NpcAiComponent。
// 戰鬥：+ HealthComponent。
// 物品：+ ItemComponent。
// NPC 類型：+ CombatStatsComponent。

namespace opennefia::serialize {

using AllComponents = entt::type_list<
    MetaDataComponent,
    SpatialComponent,
    MapData,
    NpcAiComponent,
    HealthComponent,
    ItemComponent,
    CombatStatsComponent
>;

} // namespace opennefia::serialize
