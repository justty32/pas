#pragma once

#include <cstdint>

namespace OpenNefia::Core::GameObjects {

/**
 * @brief Life stages of an ECS Entity.
 * Ported from EntityLifeStage.cs.
 */
enum class EntityLifeStage : uint8_t {
    PreInit = 0,
    Initializing,
    Initialized,
    MapInitialized,
    Terminating,
    Deleted,
};

} // namespace OpenNefia::Core::GameObjects
