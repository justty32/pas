#include "cvar_registry.h"
#include <yaml-cpp/yaml.h>
#include <fstream>
#include <filesystem>
#include <stdexcept>

namespace opennefia {

void CvarRegistry::reset(const std::string& name) {
    auto it = vars_.find(name);
    if (it == vars_.end()) return;
    it->second.value = it->second.default_value;
}

void CvarRegistry::reset_all() {
    for (auto& [k, e] : vars_) e.value = e.default_value;
}

void CvarRegistry::save(const std::string& path) const {
    YAML::Emitter out;
    out << YAML::BeginMap;
    for (const auto& [name, entry] : vars_) {
        out << YAML::Key << name;
        if      (entry.type_tag == "int")    out << YAML::Value << std::any_cast<int>(entry.value);
        else if (entry.type_tag == "float")  out << YAML::Value << std::any_cast<float>(entry.value);
        else if (entry.type_tag == "bool")   out << YAML::Value << std::any_cast<bool>(entry.value);
        else if (entry.type_tag == "string") out << YAML::Value << std::any_cast<std::string>(entry.value);
    }
    out << YAML::EndMap;
    std::ofstream f(path);
    if (!f) throw std::runtime_error("CvarRegistry::save: 無法開啟 '" + path + "'");
    f << out.c_str();
}

void CvarRegistry::load(const std::string& path) {
    if (!std::filesystem::exists(path)) return;
    YAML::Node root;
    try {
        root = YAML::LoadFile(path);
    } catch (const YAML::Exception&) {
        return;  // 格式錯誤時保留 defaults
    }
    if (!root.IsMap()) return;
    for (auto it = root.begin(); it != root.end(); ++it) {
        std::string name = it->first.as<std::string>();
        auto vit = vars_.find(name);
        if (vit == vars_.end()) continue;  // 未知 key 靜默略過（前向相容）
        try {
            auto& entry = vit->second;
            if      (entry.type_tag == "int")    entry.value = it->second.as<int>();
            else if (entry.type_tag == "float")  entry.value = it->second.as<float>();
            else if (entry.type_tag == "bool")   entry.value = it->second.as<bool>();
            else if (entry.type_tag == "string") entry.value = it->second.as<std::string>();
        } catch (...) {}  // 型別不符靜默略過
    }
}

} // namespace opennefia
