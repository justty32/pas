#pragma once

#include "EntityUid.hpp"
#include <vector>
#include <functional>

namespace OpenNefia::Core::GameObjects {

class IComponent;
class IEventBus;

/**
 * @brief Interface for managing entities and their components.
 * Ported from IEntityManager.cs.
 */
class IEntityManager {
public:
    virtual ~IEntityManager() = default;

    virtual void Initialize() = 0;
    virtual void Startup() = 0;
    virtual void Shutdown() = 0;

    virtual IEventBus& GetEventBus() = 0;

    /**
     * @brief Creates a new entity.
     */
    virtual EntityUid CreateEntity() = 0;

    /**
     * @brief Deletes an entity.
     */
    virtual void DeleteEntity(EntityUid uid) = 0;

    /**
     * @brief Checks if an entity exists.
     */
    virtual bool EntityExists(EntityUid uid) const = 0;

    /**
     * @brief Checks if an entity is deleted.
     */
    virtual bool IsDeleted(EntityUid uid) const = 0;

    // Component Management (simplified for now)
    virtual void AddComponent(EntityUid uid, std::unique_ptr<IComponent> component) = 0;
    virtual IComponent* GetComponent(EntityUid uid, const std::string& name) = 0;
    virtual bool HasComponent(EntityUid uid, const std::string& name) const = 0;
    virtual void RemoveComponent(EntityUid uid, const std::string& name) = 0;

    // Events
    std::function<void(EntityUid)> OnEntityAdded;
    std::function<void(EntityUid)> OnEntityDeleted;
};

} // namespace OpenNefia::Core::GameObjects
