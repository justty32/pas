#include "prototype_manager.h"
#include <core/components/meta_data_component.h>
#include <core/ecs/entity_manager.h>
#include <yaml-cpp/yaml.h>
#include <stdexcept>
#include <sstream>

namespace opennefia {

// ---- register_loader -------------------------------------------------------

void PrototypeManager::register_loader(std::string type_name, ComponentLoader loader) {
    loaders_[std::move(type_name)] = std::move(loader);
}

// ---- load_file -------------------------------------------------------------

void PrototypeManager::load_file(const std::string& path) {
    YAML::Node root;
    try {
        root = YAML::LoadFile(path);
    } catch (const YAML::Exception& e) {
        throw std::runtime_error("PrototypeManager::load_file: " + std::string(e.what()));
    }

    if (!root.IsSequence()) {
        throw std::runtime_error(
            "PrototypeManager::load_file: root must be a YAML sequence (" + path + ")");
    }

    // yaml-cpp range-based for 回傳 YAML::detail::iterator_value（繼承自 Node），
    // 但 MSVC 多載解析偏向 template operator=<T> 而不是 copy operator=(const Node&)。
    // 用 root[i] 直接取得 YAML::Node by value，避免 iterator_value 引起的錯誤。
    for (std::size_t i = 0; i < root.size(); ++i) {
        YAML::Node node = root[i];  // operator[] 回傳 YAML::Node by value
        if (!node["id"]) {
            throw std::runtime_error(
                "PrototypeManager::load_file: prototype entry missing 'id' field (" + path + ")");
        }
        std::string id = node["id"].as<std::string>();
        if (raw_defs_.count(id)) {
            throw std::runtime_error(
                "PrototypeManager::load_file: duplicate prototype id '" + id + "' (" + path + ")");
        }
        raw_defs_[id] = node;
    }
    inheritance_resolved_ = false;
}

// ---- resolve_inheritance ---------------------------------------------------

void PrototypeManager::resolve_inheritance() {
    resolved_.clear();

    std::unordered_set<std::string> visiting;  // 偵測循環
    std::unordered_set<std::string> done;       // 已完成

    for (auto& [id, _] : raw_defs_) {
        resolve_one(id, visiting, done);
    }
    inheritance_resolved_ = true;
}

void PrototypeManager::resolve_one(
    const std::string&              id,
    std::unordered_set<std::string>& visiting,
    std::unordered_set<std::string>& done)
{
    if (done.count(id)) return;
    if (visiting.count(id)) {
        throw std::runtime_error("PrototypeManager: circular prototype inheritance at '" + id + "'");
    }
    visiting.insert(id);

    const auto& raw = raw_defs_.at(id);
    Prototype proto;
    proto.id = id;

    // ---- 繼承合併 --------------------------------------------------------
    if (raw["parent"] && !raw["parent"].IsNull()) {
        proto.parent_id = raw["parent"].as<std::string>();
        if (!raw_defs_.count(proto.parent_id)) {
            throw std::runtime_error(
                "PrototypeManager: prototype '" + id +
                "' references unknown parent '" + proto.parent_id + "'");
        }
        // 先遞迴解析 parent
        resolve_one(proto.parent_id, visiting, done);

        // 以 parent 的解析結果為底。
        // 必須用 YAML::Clone 做 deep copy：若只做 map copy（handle copy），
        // 所有 child 會共享同一個 detail::node 物件。之後 child 對共享 handle
        // 做 operator=（AssignNode）時，會呼叫 set_ref 修改底層 detail::node，
        // 導致所有指向該 node 的 handle（包含其他 sibling prototype）都被污染。
        for (const auto& [name, parent_node] : resolved_.at(proto.parent_id).components) {
            proto.components[name] = YAML::Clone(parent_node);
        }
    }

    // ---- 套用 child 的 component（覆蓋 parent 的同名 component）----------
    if (raw["components"] && raw["components"].IsMap()) {
        YAML::Node comps = raw["components"];
        for (auto it = comps.begin(); it != comps.end(); ++it) {
            YAML::Node key_node   = it->first;
            YAML::Node value_node = it->second;
            std::string comp_name = key_node.as<std::string>();
            // 同樣 Clone：確保 child 自有的 node 與 raw_defs_ 中的原始節點獨立，
            // 避免未來對 proto.components 的操作回溯污染 raw_defs_。
            proto.components[comp_name] = YAML::Clone(value_node);
        }
    }

    visiting.erase(id);
    done.insert(id);
    resolved_[id] = std::move(proto);
}

// ---- 存取 ------------------------------------------------------------------

bool PrototypeManager::has(const std::string& id) const {
    return resolved_.count(id) > 0;
}

const Prototype& PrototypeManager::get(const std::string& id) const {
    auto it = resolved_.find(id);
    if (it == resolved_.end()) {
        throw std::runtime_error("PrototypeManager::get: unknown prototype '" + id + "'");
    }
    return it->second;
}

// ---- apply_to --------------------------------------------------------------

void PrototypeManager::apply_to(
    entt::registry&    reg,
    entt::entity       e,
    const std::string& proto_id) const
{
    if (!inheritance_resolved_) {
        throw std::runtime_error("PrototypeManager::apply_to: call resolve_inheritance() first");
    }

    const auto& proto = get(proto_id);
    for (auto& [comp_name, comp_node] : proto.components) {
        auto it = loaders_.find(comp_name);
        if (it != loaders_.end()) {
            it->second(reg, e, comp_node);
        }
        // 未知的 component 型別靜默略過（前向相容：新 YAML 不會讓舊二進位崩潰）
    }
}

// ---- spawn -----------------------------------------------------------------

entt::entity PrototypeManager::spawn(EntityManager& em, const std::string& proto_id) {
    auto e = em.create();
    apply_to(em.registry(), e, proto_id);

    // 確保 MetaDataComponent 存在且 proto_id 欄位已設定
    if (!em.has<MetaDataComponent>(e)) {
        em.emplace<MetaDataComponent>(e);
    }
    em.get<MetaDataComponent>(e).proto_id = proto_id;
    return e;
}

// ---- clear -----------------------------------------------------------------

void PrototypeManager::clear() {
    raw_defs_.clear();
    resolved_.clear();
    inheritance_resolved_ = false;
}

} // namespace opennefia
