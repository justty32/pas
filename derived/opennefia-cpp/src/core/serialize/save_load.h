#pragma once
#include "all_components.h"
#include "entt_cereal_archive.h"
#include "save_store.h"
#include <entt/entt.hpp>
#include <cereal/archives/portable_binary.hpp>
#include <cereal/types/string.hpp>   // MetaDataComponent::proto_id (std::string)
// 新增含有 STL 容器的 component 時，在此補對應的 cereal/types/*.hpp
#include <filesystem>
#include <fstream>
#include <sstream>

// save_load.h — entt::registry ↔ bytes 的核心序列化（移植自 medps zone_io.h）。
//
// 設計原則（同 medps）：
// - AllComponents type_list 是唯一真相來源；save/load 用 fold expression 展開。
// - snapshot / snapshot_loader 保留 entity ID（在 target registry 為空時 = 原始 ID）。
// - loader.orphans() 刪除無 component 的殘留 entity（防止孤兒污染）。
//
// 三層 API：
//   stream  → 最底層（save / load to ostream / istream）
//   path    → 便利包裝（直接讀寫檔案）
//   store   → SaveStore 介面（bytes ↔ 儲存後端）

namespace opennefia::serialize {

namespace detail {

    template<typename... Cs>
    void save_impl(entt::registry& reg, output_archive& out,
                   entt::type_list<Cs...>) {
        auto snap = entt::snapshot{reg};
        snap.get<entt::entity>(out);
        (snap.get<Cs>(out), ...);
    }

    template<typename... Cs>
    void load_impl(entt::registry& reg, input_archive& in,
                   entt::type_list<Cs...>) {
        auto loader = entt::snapshot_loader{reg};
        loader.get<entt::entity>(in);
        (loader.get<Cs>(in), ...);
        // orphans() 刪除最終沒有任何 component 的 entity（防孤兒）。
        // 規約（仿 medps）：每個被序列化的 entity 至少持有一個 component。
        loader.orphans();
    }

} // namespace detail

// ---- stream API（最底層）-------------------------------------------------

inline void save(entt::registry& reg, std::ostream& os) {
    cereal::PortableBinaryOutputArchive cereal_out{os};
    output_archive out{cereal_out};
    detail::save_impl(reg, out, AllComponents{});
}

inline void load(entt::registry& reg, std::istream& is) {
    cereal::PortableBinaryInputArchive cereal_in{is};
    input_archive in{cereal_in};
    detail::load_impl(reg, in, AllComponents{});
}

// ---- 檔案 API ------------------------------------------------------------

inline void save(entt::registry& reg, const std::filesystem::path& path) {
    if (path.has_parent_path())
        std::filesystem::create_directories(path.parent_path());
    std::ofstream ofs{path, std::ios::binary};
    save(reg, ofs);
}

inline void load(entt::registry& reg, const std::filesystem::path& path) {
    if (!std::filesystem::exists(path)) return;
    std::ifstream ifs{path, std::ios::binary};
    load(reg, ifs);
}

// ---- SaveStore API -------------------------------------------------------

inline void save(entt::registry& reg, SaveStore& store,
                 const std::string& slot_name) {
    std::ostringstream oss;
    save(reg, oss);
    store.write(slot_name, oss.str());
}

inline void load(entt::registry& reg, SaveStore& store,
                 const std::string& slot_name) {
    auto bytes = store.read(slot_name);
    if (!bytes) return;
    std::istringstream iss{*bytes};
    load(reg, iss);
}

} // namespace opennefia::serialize
