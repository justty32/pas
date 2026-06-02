#pragma once
#include <cstdint>

namespace opennefia {

enum class ItemType : uint8_t {
    health_potion = 0,
};

struct ItemComponent {
    ItemType type{ ItemType::health_potion };
    int      value{ 8 };   // 效果量（回血藥 = 回復 HP）

    template<class Archive>
    void serialize(Archive& ar) { ar(type, value); }
};

} // namespace opennefia
