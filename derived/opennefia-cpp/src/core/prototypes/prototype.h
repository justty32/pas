#pragma once
#include <string>
#include <unordered_map>
#include <yaml-cpp/yaml.h>

namespace opennefia {

// 繼承解析後的平展原型定義。
// components：map<component 型別名稱, YAML::Node>——child 的 node 覆蓋 parent 的。
// 此為 PrototypeManager::resolve_inheritance() 的輸出，只讀。
struct Prototype {
    std::string id;
    std::string parent_id;  // "" 代表無父

    // key = 在 register_loader() 時使用的型別名稱字串（如 "Spatial"、"MetaData"）
    // value = YAML 節點（原始資料，供 ComponentLoader 讀取）
    std::unordered_map<std::string, YAML::Node> components;
};

} // namespace opennefia
