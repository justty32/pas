#pragma once

#include "IEntityManager.hpp"
#include <unordered_map>
#include <unordered_set>
#include <queue>

namespace OpenNefia::Core::GameObjects {

class EntityManager : public IEntityManager {
private:
    std::unordered_set<EntityUid> _entities;
    std::unordered_map<EntityUid, std::unordered_map<std::string, std::unique_ptr<IComponent>>> _components;
    int32_t _nextUid = (int32_t)EntityUid::FirstUid;

public:
    EntityManager() = default;
    virtual ~EntityManager() = default;

    void Initialize() override {}
    void Startup() override {}
    void Shutdown() override;

    IEventBus& GetEventBus() override;

    EntityUid CreateEntity() override;
    void DeleteEntity(EntityUid uid) override;
    bool EntityExists(EntityUid uid) const override;
    bool IsDeleted(EntityUid uid) const override;

    void AddComponent(EntityUid uid, std::unique_ptr<IComponent> component) override;
    IComponent* GetComponent(EntityUid uid, const std::string& name) override;
    bool HasComponent(EntityUid uid, const std::string& name) const override;
    void RemoveComponent(EntityUid uid, const std::string& name) override;

private:
    EntityUid GenerateUid() { return EntityUid(_nextUid++); }
};

} // namespace OpenNefia::Core::GameObjects
