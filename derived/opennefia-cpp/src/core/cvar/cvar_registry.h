#pragma once
#include <any>
#include <stdexcept>
#include <string>
#include <unordered_map>

namespace opennefia {

// 單一 CVar 的儲存單位
struct CvarEntry {
    std::any    value;
    std::any    default_value;
    std::string description;
    std::string type_tag;  // "int" | "float" | "bool" | "string"
};

// 型別 → type_tag 字串對應（只允許四種基本型別）
template<typename T> struct cvar_type_tag;
template<> struct cvar_type_tag<int>         { static constexpr const char* value = "int";    };
template<> struct cvar_type_tag<float>       { static constexpr const char* value = "float";  };
template<> struct cvar_type_tag<bool>        { static constexpr const char* value = "bool";   };
template<> struct cvar_type_tag<std::string> { static constexpr const char* value = "string"; };

// CvarRegistry：有名の型付き変数レジストリ。
//
// 使用例：
//   cvars.reg<int>("game.map_width", 60, "地圖寬度（格）");
//   int w = cvars.get<int>("game.map_width");
//   cvars.set<int>("game.map_width", 80);
//   cvars.save("user_settings.yaml");
//   cvars.load("user_settings.yaml");
//
// 設計原則：
//   - 只支援 int / float / bool / std::string（static_assert 防止誤用）
//   - 存讀使用 yaml-cpp（與 PrototypeManager 共用相同依賴）
//   - 未知 key：get/set 丟 std::out_of_range；load 時靜默略過（前向相容）
class CvarRegistry {
public:
    // 登錄 CVar（重複登錄會覆蓋；型別必須是 int/float/bool/std::string）
    template<typename T>
    void reg(std::string name, T default_val, std::string description = "") {
        static_assert(
            std::is_same_v<T, int>    || std::is_same_v<T, float> ||
            std::is_same_v<T, bool>   || std::is_same_v<T, std::string>,
            "CvarRegistry: 只支援 int, float, bool, std::string");
        vars_[std::move(name)] = CvarEntry{
            std::any{ default_val },
            std::any{ default_val },
            std::move(description),
            cvar_type_tag<T>::value
        };
    }

    bool has(const std::string& name) const {
        return vars_.count(name) > 0;
    }

    template<typename T>
    T get(const std::string& name) const {
        auto it = vars_.find(name);
        if (it == vars_.end())
            throw std::out_of_range("CvarRegistry::get: 未知 cvar '" + name + "'");
        return std::any_cast<T>(it->second.value);
    }

    template<typename T>
    void set(const std::string& name, T value) {
        auto it = vars_.find(name);
        if (it == vars_.end())
            throw std::out_of_range("CvarRegistry::set: 未知 cvar '" + name + "'");
        it->second.value = std::any{ value };
    }

    // 重置指定 / 全部 CVar 為預設值
    void reset(const std::string& name);
    void reset_all();

    // YAML 存讀（定義在 cvar_registry.cpp）
    void save(const std::string& path) const;
    void load(const std::string& path);  // 不存在時 no-op；未知 key 靜默略過

private:
    std::unordered_map<std::string, CvarEntry> vars_;
};

} // namespace opennefia
