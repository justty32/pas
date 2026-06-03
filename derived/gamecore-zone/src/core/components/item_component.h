#pragma once
#include <cstdint>

namespace zone {

enum class ItemType : uint8_t {
    health_potion = 0,
};

struct ItemComponent {
    ItemType type{ ItemType::health_potion };
    int      value{ 8 };

    template<class Archive>
    void serialize(Archive& ar) { ar(type, value); }
};

} // namespace zone
