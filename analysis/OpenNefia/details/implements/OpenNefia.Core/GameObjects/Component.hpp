#pragma once

#include "IComponent.hpp"

namespace OpenNefia::Core::GameObjects {

/**
 * @brief Base class for ECS components.
 * Ported from Component.cs.
 */
class Component : public IComponent {
private:
    EntityUid _owner = EntityUid::Invalid;
    ComponentLifeStage _lifeStage = ComponentLifeStage::PreAdd;

public:
    virtual ~Component() = default;

    EntityUid GetOwner() const override { return _owner; }
    void SetOwner(EntityUid owner) { _owner = owner; }

    ComponentLifeStage GetLifeStage() const override { return _lifeStage; }
    void SetLifeStage(ComponentLifeStage stage) { _lifeStage = stage; }

    bool IsInitialized() const override { return _lifeStage >= ComponentLifeStage::Initialized; }
    bool IsRunning() const override { 
        return _lifeStage >= ComponentLifeStage::Starting && _lifeStage <= ComponentLifeStage::Stopping; 
    }
    bool IsDeleted() const override { return _lifeStage >= ComponentLifeStage::Removing; }

    // Internal life cycle methods
    void LifeAddToEntity() {
        _lifeStage = ComponentLifeStage::Adding;
        OnAdd();
    }

    void LifeInitialize() {
        _lifeStage = ComponentLifeStage::Initializing;
        Initialize();
    }

    void LifeStartup() {
        _lifeStage = ComponentLifeStage::Starting;
        Startup();
    }

    void LifeShutdown() {
        _lifeStage = ComponentLifeStage::Stopping;
        Shutdown();
    }

    void LifeRemoveFromEntity() {
        _lifeStage = ComponentLifeStage::Removing;
        OnRemove();
    }

protected:
    virtual void OnAdd() { _lifeStage = ComponentLifeStage::Added; }
    virtual void Initialize() { _lifeStage = ComponentLifeStage::Initialized; }
    virtual void Startup() { _lifeStage = ComponentLifeStage::Running; }
    virtual void Shutdown() { _lifeStage = ComponentLifeStage::Stopped; }
    virtual void OnRemove() { _lifeStage = ComponentLifeStage::Deleted; }
};

} // namespace OpenNefia::Core::GameObjects
