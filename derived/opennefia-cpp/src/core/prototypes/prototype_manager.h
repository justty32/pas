#pragma once
#include "prototype.h"
#include "prototype_id.h"
#include <entt/entt.hpp>
#include <functional>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <vector>

namespace opennefia {
class EntityManager;

// ComponentLoader：把一個 YAML 節點 emplace 成 component 到 entity 上。
// 在 register_loader<C>() 樣板邊界保證型別安全；內部以 std::function 存放（型別抹除）。
using ComponentLoader =
    std::function<void(entt::registry&, entt::entity, const YAML::Node&)>;

// PrototypeManager：資料驅動的原型系統（zero-reflection）。
//
// 流程：
//   1. register_loader<C>("TypeName", fn) — 登錄 component 讀取器（啟動期）
//   2. load_file(path)                   — 讀 YAML，存入 raw_defs_
//   3. resolve_inheritance()             — 拓撲排序 + merge，產出 resolved_
//   4. spawn(em, id) / apply_to(...)     — 生成實體
//
// 不靠反射——TypeName 字串到 C++ 型別的映射由 register_loader 顯式建立。
// 對應 OpenNefia SerializationManager + PrototypeManager 的融合功能，但拆成兩條路：
//   - YAML 原型（人編輯的定義）→ 本類別；
//   - 執行期存讀檔（cereal binary snapshot）→ Phase 3 的 save_load.h。
class PrototypeManager {
public:
    // ---- 登錄 ComponentLoader ------------------------------------------

    // 登錄 component 讀取器。
    // TypeName 需與 YAML 的 components 鍵名一致（如 "Spatial"）。
    void register_loader(std::string type_name, ComponentLoader loader);

    // 便利樣板包裝：自動推導型別。
    template<typename C>
    void register_loader(std::string type_name,
                         std::function<C(const YAML::Node&)> parse_fn) {
        register_loader(std::move(type_name),
            [fn = std::move(parse_fn)](entt::registry& reg, entt::entity e,
                                       const YAML::Node& node) {
                reg.emplace_or_replace<C>(e, fn(node));
            }
        );
    }

    // ---- 載入與解析 ----------------------------------------------------

    // 從 YAML 檔案載入原型定義。可多次呼叫以合併多個檔案。
    // 格式（序列）：
    //   - id: "SomeName"
    //     parent: "OptionalParent"  # 省略代表無父
    //     components:
    //       TypeName: { field: value, ... }
    void load_file(const std::string& path);

    // 解析繼承關係（拓撲排序 + component 合併）。
    // 必須在所有 load_file() 之後、spawn() 之前呼叫。
    void resolve_inheritance();

    // ---- 存取 ----------------------------------------------------------

    bool has(const std::string& id) const;
    const Prototype& get(const std::string& id) const;

    // ---- 生成實體 ------------------------------------------------------

    // 將原型的所有 component 套用至已存在的 entity（不自動建立實體）。
    void apply_to(entt::registry& reg, entt::entity e,
                  const std::string& proto_id) const;

    // 建立新實體 + apply_to + 確保 MetaDataComponent 的 proto_id 已設定。
    entt::entity spawn(EntityManager& em, const std::string& proto_id);

    // ---- 清除（重新載入用）--------------------------------------------
    void clear();

private:
    void resolve_one(const std::string& id,
                     std::unordered_set<std::string>& visiting,
                     std::unordered_set<std::string>& done);

    // key = prototype id；value = 原始 YAML 節點（含 id / parent / components）
    std::unordered_map<std::string, YAML::Node> raw_defs_;

    // 繼承解析後的平展定義
    std::unordered_map<std::string, Prototype> resolved_;

    // ComponentLoader map
    std::unordered_map<std::string, ComponentLoader> loaders_;

    bool inheritance_resolved_{false};
};

} // namespace opennefia
