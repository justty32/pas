#pragma once
#include <entt/entt.hpp>
#include <core/components/meta_data_component.h>
#include <core/components/spatial_component.h>

// AllComponents：snapshot save/load 的單一來源（仿 medps all_components.h）。
// 新增 component 型別只需在此加一行；save 與 load 都透過 fold expression 自動展開。
// Phase 3：MetaDataComponent + SpatialComponent。
// Phase 4 起陸續加入 MapData 等。

namespace opennefia::serialize {

using AllComponents = entt::type_list<
    MetaDataComponent,
    SpatialComponent
    // Phase 4: MapData, ...
>;

} // namespace opennefia::serialize
