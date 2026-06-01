#include "entity_manager.h"
#include "system_ctx.h"
#include <core/prototypes/prototype_manager.h>

namespace opennefia {

entt::entity EntityManager::create() {
    return reg_.create();
}

void EntityManager::destroy(entt::entity e) {
    reg_.destroy(e);
}

bool EntityManager::valid(entt::entity e) const {
    return reg_.valid(e);
}

void EntityManager::add_system(SystemFn fn) {
    systems_.push_back(std::move(fn));
}

void EntityManager::tick(SystemCtx& ctx) {
    for (auto& sys : systems_) {
        sys(reg_, ctx);
    }
}

entt::entity EntityManager::spawn(const std::string& proto_id, PrototypeManager& pm) {
    return pm.spawn(*this, proto_id);
}

} // namespace opennefia
