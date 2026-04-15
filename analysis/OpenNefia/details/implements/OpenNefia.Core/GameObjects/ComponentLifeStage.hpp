#pragma once

#include <cstdint>

namespace OpenNefia::Core::GameObjects {

/**
 * @brief Life stages of an ECS component.
 * Ported from Component.cs.
 */
enum class ComponentLifeStage : uint8_t {
    PreAdd = 0,
    Adding,
    Added,
    Initializing,
    Initialized,
    Starting,
    Running,
    Stopping,
    Stopped,
    Removing,
    Deleted,
};

} // namespace OpenNefia::Core::GameObjects
