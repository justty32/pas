#pragma once
#include <cstdint>

namespace opennefia {

enum class ItemType : uint8_t {
    health_potion = 0,
};

struct ItemComponent {
    ItemType type{ ItemType::health_potion };
    int      value{ 8 };
    int      value_per_floor{ 0 };  // 每層效果量增量（YAML 原型填入）

    template<class Archive>
    void serialize(Archive& ar) { ar(type, value, value_per_floor); }
};

} // namespace opennefia
