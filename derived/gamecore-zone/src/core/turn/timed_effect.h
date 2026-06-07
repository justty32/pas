#pragma once
#include <vector>
#include <cstdint>

namespace zone {

// 持續性效果（ToME4 ActorTemporaryEffects 風）。每個 actor 的「回合開始」tick 一次。
// 讓 A（能量瞬發、無 channel）也能有時間延展的效果，並讓 Cast 留下燃燒。
enum class TimedEffectKind : uint8_t { Burning, Poison, Regen };

struct TimedEffect {
    TimedEffectKind kind{ TimedEffectKind::Burning };
    int turns_left{ 0 };
    int power{ 0 };

    template<class Archive>
    void serialize(Archive& ar) { ar(kind, turns_left, power); }
};

struct TimedEffectsComponent {
    std::vector<TimedEffect> effects;

    template<class Archive>
    void serialize(Archive& ar) { ar(effects); }
};

} // namespace zone
