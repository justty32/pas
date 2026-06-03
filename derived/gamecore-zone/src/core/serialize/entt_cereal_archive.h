#pragma once
#include <entt/entt.hpp>
#include <cereal/archives/portable_binary.hpp>
#include <type_traits>

// entt ↔ cereal 橋接（直接移植自 medps entt_cereal_archive.h）。
//
// 問題：entt::entity 是強型別 enum（underlying_type_t<entt::entity> 通常是 uint32_t）。
// cereal 無法直接序列化強型別 enum，需要顯式轉型成底層整數再存。
// output_archive / input_archive 作為 entt::snapshot / snapshot_loader 的 Archive 型別，
// 把所有 entt::entity 操作轉型後交給 cereal::PortableBinaryOutputArchive 處理。

namespace zone::serialize {

using entt_id_t = std::underlying_type_t<entt::entity>;

struct output_archive {
    cereal::PortableBinaryOutputArchive& ar;

    void operator()(entt_id_t v)                { ar(v); }
    void operator()(entt::entity e)             { ar(static_cast<entt_id_t>(e)); }
    template<typename T>
    void operator()(entt::entity e, const T& c) { ar(static_cast<entt_id_t>(e), c); }
    template<typename T>
    void operator()(const T& v)                 { ar(v); }
};

struct input_archive {
    cereal::PortableBinaryInputArchive& ar;

    void operator()(entt_id_t& v)   { ar(v); }
    void operator()(entt::entity& e) {
        entt_id_t v{};
        ar(v);
        e = static_cast<entt::entity>(v);
    }
    template<typename T>
    void operator()(entt::entity& e, T& c) {
        entt_id_t v{};
        ar(v, c);
        e = static_cast<entt::entity>(v);
    }
    template<typename T>
    void operator()(T& v) { ar(v); }
};

} // namespace zone::serialize
