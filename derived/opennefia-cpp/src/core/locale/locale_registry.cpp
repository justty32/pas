#include "locale_registry.h"
#include <yaml-cpp/yaml.h>
#include <filesystem>

namespace opennefia {

void LocaleRegistry::load(const std::string& path) {
    if (!std::filesystem::exists(path)) return;
    YAML::Node root;
    try {
        root = YAML::LoadFile(path);
    } catch (const YAML::Exception&) {
        return;  // 格式錯誤時保留已載入的字串
    }
    if (!root.IsMap()) return;
    for (auto it = root.begin(); it != root.end(); ++it) {
        strings_[it->first.as<std::string>()] = it->second.as<std::string>();
    }
}

bool LocaleRegistry::has(const std::string& key) const {
    return strings_.count(key) > 0;
}

std::string LocaleRegistry::get(const std::string& key) const {
    auto it = strings_.find(key);
    return it != strings_.end() ? it->second : key;
}

std::string LocaleRegistry::get(const std::string& key, const std::string& fallback) const {
    auto it = strings_.find(key);
    return it != strings_.end() ? it->second : fallback;
}

std::string LocaleRegistry::get(
    const std::string& key,
    const std::unordered_map<std::string, std::string>& vars) const
{
    return substitute(get(key), vars);
}

std::string LocaleRegistry::substitute(
    const std::string& tmpl,
    const std::unordered_map<std::string, std::string>& vars)
{
    std::string result;
    result.reserve(tmpl.size());
    std::size_t i = 0;
    while (i < tmpl.size()) {
        if (tmpl[i] == '{') {
            std::size_t close = tmpl.find('}', i + 1);
            if (close != std::string::npos) {
                std::string var_name = tmpl.substr(i + 1, close - i - 1);
                auto it = vars.find(var_name);
                if (it != vars.end()) {
                    result += it->second;
                } else {
                    result += tmpl.substr(i, close - i + 1);  // 找不到的占位符保留原樣
                }
                i = close + 1;
                continue;
            }
        }
        result += tmpl[i++];
    }
    return result;
}

} // namespace opennefia
