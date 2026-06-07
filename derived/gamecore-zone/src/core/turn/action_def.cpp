#include "core/turn/action_def.h"

#include <cereal/archives/json.hpp>
#include <cereal/types/vector.hpp>
#include <cereal/types/string.hpp>
#include <fstream>

namespace zone {

void ActionLibrary::reindex() {
    index_.clear();
    for (int i = 0; i < static_cast<int>(defs_.size()); ++i)
        index_[defs_[i].name] = i;
}

int ActionLibrary::find(const std::string& name) const {
    auto it = index_.find(name);
    return it == index_.end() ? -1 : it->second;
}

bool ActionLibrary::load_json(const std::string& path) {
    std::ifstream is(path);
    if (!is) return false;
    try {
        cereal::JSONInputArchive ar(is);
        std::vector<ActionDef> defs;
        ar(cereal::make_nvp("actions", defs));
        defs_ = std::move(defs);
        reindex();
        return true;
    } catch (...) {
        return false;
    }
}

void ActionLibrary::load_defaults() {
    defs_.clear();
    ActionDef fireball;
    fireball.name = "fireball"; fireball.weight = 3;
    fireball.nova_damage = 4; fireball.dot_turns = 3; fireball.dot_power = 2;
    ActionDef heal;
    heal.name = "heal"; heal.weight = 2; heal.self_heal = 8;
    heal.self_regen_turns = 3; heal.self_regen_power = 2;
    ActionDef smite;
    smite.name = "smite"; smite.weight = 1; smite.nova_damage = 6;
    ActionDef meteor;
    meteor.name = "meteor"; meteor.weight = 4; meteor.nova_damage = 5;
    meteor.radius = 2; meteor.dot_turns = 2; meteor.dot_power = 3;
    ActionDef venom;
    venom.name = "venom"; venom.weight = 2; venom.nova_damage = 1;
    venom.dot_turns = 5; venom.dot_power = 2; venom.dot_kind = 1;  // 中毒
    ActionDef npc_flame;
    npc_flame.name = "npc_flame"; npc_flame.weight = 1;
    npc_flame.nova_damage = 3; npc_flame.dot_turns = 2; npc_flame.dot_power = 2;
    defs_.push_back(fireball);
    defs_.push_back(heal);
    defs_.push_back(smite);
    defs_.push_back(meteor);
    defs_.push_back(venom);
    defs_.push_back(npc_flame);
    reindex();
}

} // namespace zone
