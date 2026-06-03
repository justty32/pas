#pragma once

namespace zone {

struct HealthComponent {
    int hp;
    int max_hp;

    HealthComponent() : hp(10), max_hp(10) {}
    HealthComponent(int hp_, int max_hp_) : hp(hp_), max_hp(max_hp_) {}

    template<class Archive>
    void serialize(Archive& ar) { ar(hp, max_hp); }
};

} // namespace zone
