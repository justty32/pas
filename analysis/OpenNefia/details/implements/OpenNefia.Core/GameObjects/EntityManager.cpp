#include "EntityManager.hpp"
#include "Component.hpp"
#include <stdexcept>

namespace OpenNefia::Core::GameObjects {

void EntityManager::Shutdown() {
    auto uids = std::vector<EntityUid>(_entities.begin(), _entities.end());
    for (auto uid : uids) {
        DeleteEntity(uid);
    }
    _entities.clear();
    _components.clear();
}

IEventBus& EntityManager::GetEventBus() {
    // Return a dummy for now or port EventBus
    static class DummyBus : public IEventBus {
        void RaiseEvent(int source, const std::any& ev) override {}
    } dummy;
    return dummy;
}

EntityUid EntityManager::CreateEntity() {
    EntityUid uid = GenerateUid();
    _entities.insert(uid);
    if (OnEntityAdded) OnEntityAdded(uid);
    return uid;
}

void EntityManager::DeleteEntity(EntityUid uid) {
    if (!EntityExists(uid)) return;

    // Shutdown components
    auto& comps = _components[uid];
    for (auto& [name, comp] : comps) {
        auto baseComp = static_cast<Component*>(comp.get());
        baseComp->LifeShutdown();
        baseComp->LifeRemoveFromEntity();
    }

    _components.erase(uid);
    _entities.erase(uid);
    if (OnEntityDeleted) OnEntityDeleted(uid);
}

bool EntityManager::EntityExists(EntityUid uid) const {
    return _entities.find(uid) != _entities.end();
}

bool EntityManager::IsDeleted(EntityUid uid) const {
    return !EntityExists(uid);
}

void EntityManager::AddComponent(EntityUid uid, std::unique_ptr<IComponent> component) {
    if (!EntityExists(uid)) throw std::runtime_error("Entity does not exist.");
    
    auto baseComp = static_cast<Component*>(component.get());
    baseComp->SetOwner(uid);
    baseComp->LifeAddToEntity();
    
    _components[uid][component->GetName()] = std::move(component);
}

IComponent* EntityManager::GetComponent(EntityUid uid, const std::string& name) {
    if (!EntityExists(uid)) return nullptr;
    auto it = _components[uid].find(name);
    if (it == _components[uid].end()) return nullptr;
    return it->second.get();
}

bool EntityManager::HasComponent(EntityUid uid, const std::string& name) const {
    if (!EntityExists(uid)) return false;
    auto it = _components.at(uid).find(name);
    return it != _components.at(uid).end();
}

void EntityManager::RemoveComponent(EntityUid uid, const std::string& name) {
    if (!EntityExists(uid)) return;
    auto& comps = _components[uid];
    auto it = comps.find(name);
    if (it != comps.end()) {
        auto baseComp = static_cast<Component*>(it->second.get());
        baseComp->LifeShutdown();
        baseComp->LifeRemoveFromEntity();
        comps.erase(it);
    }
}

} // namespace OpenNefia::Core::GameObjects
