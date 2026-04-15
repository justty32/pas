#pragma once

#include "EntityUid.hpp"
#include "ComponentLifeStage.hpp"
#include <string>

namespace OpenNefia::Core::GameObjects {

/**
 * @brief Base interface for ECS components.
 * Ported from IComponent.cs.
 */
class IComponent {
public:
    virtual ~IComponent() = default;

    virtual ComponentLifeStage GetLifeStage() const = 0;
    virtual EntityUid GetOwner() const = 0;
    virtual std::string GetName() const = 0;

    virtual bool IsInitialized() const = 0;
    virtual bool IsRunning() const = 0;
    virtual bool IsDeleted() const = 0;
};

} // namespace OpenNefia::Core::GameObjects
